from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.auth.forms import LoginForm, ChangePasswordForm, StudentRegistrationForm, FacultyRegistrationForm
from app.auth.services import authenticate_user, log_audit_event
from app.models.user import User, Role, StudentProfile, FacultyProfile
from app.models.academic import Department, Branch, AcademicYear, Semester, Section

auth_bp = Blueprint('auth', __name__, url_prefix='')


def _redirect_user_to_dashboard(user):
    role = user.role_name
    if role == 'Student':
        return redirect(url_for('student.dashboard'))
    elif role == 'Faculty':
        return redirect(url_for('faculty.dashboard'))
    elif role == 'HOD':
        return redirect(url_for('hod.dashboard'))
    elif role == 'Principal':
        return redirect(url_for('principal.dashboard'))
    elif role == 'Admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.index'))


@auth_bp.route('/register')
def register():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    role_type = request.args.get('role', 'student')
    if role_type == 'faculty':
        return redirect(url_for('auth.register_faculty'))
    return redirect(url_for('auth.register_student'))


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    
    form = StudentRegistrationForm()
    branches = Branch.query.order_by(Branch.code).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year_number).all()
    semesters = Semester.query.order_by(Semester.semester_number).all()
    sections = Section.query.order_by(Section.name).all()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        roll_number = form.roll_number.data.strip().upper()
        
        # Check uniqueness
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email is already registered. Please sign in or use another email.', 'danger')
        elif StudentProfile.query.filter_by(roll_number=roll_number).first():
            flash(f'Roll Number {roll_number} is already registered.', 'danger')
        else:
            role = Role.query.filter_by(name='Student').first()
            if not role:
                role = Role(name='Student', description='Student user')
                db.session.add(role)
                db.session.flush()
                
            new_user = User(
                username=username,
                email=email,
                full_name=form.full_name.data.strip(),
                role_id=role.id,
                is_active=True
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.flush()

            admission_yr = int(form.admission_year.data) if form.admission_year.data and str(form.admission_year.data).isdigit() else 2024
            student_profile = StudentProfile(
                user_id=new_user.id,
                roll_number=roll_number,
                branch_id=int(form.branch_id.data),
                academic_year_id=int(form.academic_year_id.data),
                semester_id=int(form.semester_id.data),
                section_id=int(form.section_id.data) if form.section_id.data and form.section_id.data.isdigit() else None,
                admission_year=admission_yr,
                phone=form.phone.data.strip() if form.phone.data else None
            )
            db.session.add(student_profile)
            db.session.commit()

            log_audit_event('USER_REGISTER', '/register/student', {'username': username, 'role': 'Student', 'roll_number': roll_number}, 'SUCCESS', new_user)
            login_user(new_user)
            flash(f'Welcome to DIET Academic Portal, {new_user.full_name}! Your student account has been successfully created.', 'success')
            return redirect(url_for('student.dashboard'))

    return render_template(
        'auth/register_student.html',
        form=form,
        branches=branches,
        academic_years=academic_years,
        semesters=semesters,
        sections=sections
    )


@auth_bp.route('/register/faculty', methods=['GET', 'POST'])
def register_faculty():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    
    form = FacultyRegistrationForm()
    departments = Department.query.order_by(Department.name).all()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        employee_id = form.employee_id.data.strip().upper()

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email is already registered. Please sign in or use another email.', 'danger')
        elif FacultyProfile.query.filter_by(employee_id=employee_id).first():
            flash(f'Employee ID {employee_id} is already registered.', 'danger')
        else:
            role = Role.query.filter_by(name='Faculty').first()
            if not role:
                role = Role(name='Faculty', description='Faculty user')
                db.session.add(role)
                db.session.flush()

            new_user = User(
                username=username,
                email=email,
                full_name=form.full_name.data.strip(),
                role_id=role.id,
                is_active=True
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.flush()

            faculty_profile = FacultyProfile(
                user_id=new_user.id,
                employee_id=employee_id,
                department_id=int(form.department_id.data),
                designation=form.designation.data.strip() if form.designation.data else 'Assistant Professor',
                qualification=form.qualification.data.strip() if form.qualification.data else None,
                phone=form.phone.data.strip() if form.phone.data else None
            )
            db.session.add(faculty_profile)
            db.session.commit()

            log_audit_event('USER_REGISTER', '/register/faculty', {'username': username, 'role': 'Faculty', 'employee_id': employee_id}, 'SUCCESS', new_user)
            login_user(new_user)
            flash(f'Welcome Professor {new_user.full_name}! Your faculty account has been successfully created.', 'success')
            return redirect(url_for('faculty.dashboard'))

    return render_template(
        'auth/register_faculty.html',
        form=form,
        departments=departments
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_redirect():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    
    form = LoginForm()
    role_type = request.args.get('role', 'Student')
    
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user:
            login_user(user, remember=form.remember_me.data)
            log_audit_event('USER_LOGIN', f'/login (role={user.role_name})', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome back to DIET Academic Portal, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return _redirect_user_to_dashboard(user)
        else:
            log_audit_event('LOGIN_FAILED', '/login', {'attempted_username': form.username.data}, 'FAILURE')
            flash('Invalid username/ID or password. Please verify your credentials.', 'danger')
            
    return render_template('auth/login.html', form=form, role_name=role_type)


@auth_bp.route('/login/student', methods=['GET', 'POST'])
def login_student():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user and user.is_student():
            login_user(user, remember=form.remember_me.data)
            log_audit_event('STUDENT_LOGIN', '/login/student', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome, {user.full_name}!', 'success')
            return redirect(url_for('student.dashboard'))
        else:
            flash('Invalid Student credentials or account is not a Student role.', 'danger')
    return render_template('auth/login_student.html', form=form, role_title='Student Portal')


@auth_bp.route('/login/faculty', methods=['GET', 'POST'])
def login_faculty():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user and user.is_faculty():
            login_user(user, remember=form.remember_me.data)
            log_audit_event('FACULTY_LOGIN', '/login/faculty', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome Professor {user.full_name}!', 'success')
            return redirect(url_for('faculty.dashboard'))
        else:
            flash('Invalid Faculty credentials or account is not a Faculty role.', 'danger')
    return render_template('auth/login_faculty.html', form=form, role_title='Faculty Portal')


@auth_bp.route('/login/hod', methods=['GET', 'POST'])
def login_hod():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user and user.is_hod():
            login_user(user, remember=form.remember_me.data)
            log_audit_event('HOD_LOGIN', '/login/hod', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome Dr. {user.full_name} (HOD)!', 'success')
            return redirect(url_for('hod.dashboard'))
        else:
            flash('Invalid HOD credentials or account is not a HOD role.', 'danger')
    return render_template('auth/login_hod.html', form=form, role_title='HOD Portal')


@auth_bp.route('/login/principal', methods=['GET', 'POST'])
def login_principal():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user and user.is_principal():
            login_user(user, remember=form.remember_me.data)
            log_audit_event('PRINCIPAL_LOGIN', '/login/principal', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome Dr. {user.full_name} (Principal)!', 'success')
            return redirect(url_for('principal.dashboard'))
        else:
            flash('Invalid Principal credentials or account is not a Principal role.', 'danger')
    return render_template('auth/login_principal.html', form=form, role_title='Principal Portal')


@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if current_user.is_authenticated:
        return _redirect_user_to_dashboard(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data.strip(), form.password.data)
        if user and user.is_admin():
            login_user(user, remember=form.remember_me.data)
            log_audit_event('ADMIN_LOGIN', '/login/admin', {'username': user.username}, 'SUCCESS', user)
            flash(f'Welcome System Administrator ({user.full_name})!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid Administrator credentials or account is not an Administrator.', 'danger')
    return render_template('auth/login_admin.html', form=form, role_title='System Admin Portal')


@auth_bp.route('/logout')
@login_required
def logout():
    log_audit_event('USER_LOGOUT', '/logout', {'username': current_user.username}, 'SUCCESS', current_user)
    logout_user()
    flash('You have been securely logged out from DIET Academic Portal.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password entered is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_audit_event('PASSWORD_CHANGE', '/change-password', {'username': current_user.username}, 'SUCCESS', current_user)
            flash('Your password has been successfully updated.', 'success')
            return redirect(url_for('auth.profile'))
    return render_template('auth/change_password.html', form=form)
