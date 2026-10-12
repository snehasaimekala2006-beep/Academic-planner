import os
from datetime import datetime, time
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.auth.services import role_required, log_audit_event
from app.extensions import db
from app.models.user import User, Role, StudentProfile, FacultyProfile, HODProfile, PrincipalProfile
from app.models.academic import Department, Branch, AcademicYear, Semester, Section, Subject, SubjectOffering
from app.models.timetable import TimetableEntry, Classroom
from app.models.syllabus import SyllabusImport, SyllabusSource
from app.models.audit import AuditLog

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@login_required
@role_required('Admin')
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_branches = Branch.query.count()
    total_subjects = Subject.query.count()
    pending_imports = SyllabusImport.query.filter_by(status='PENDING_VALIDATION').count()
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        total_branches=total_branches,
        total_subjects=total_subjects,
        pending_imports=pending_imports,
        recent_logs=recent_logs
    )


@admin_bp.route('/users')
@login_required
@role_required('Admin')
def users_list():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role')
    search_q = request.args.get('q', '').strip()
    
    query = User.query.join(Role)
    if role_filter:
        query = query.filter(Role.name == role_filter)
    if search_q:
        query = query.filter((User.username.ilike(f"%{search_q}%")) | (User.full_name.ilike(f"%{search_q}%")) | (User.email.ilike(f"%{search_q}%")))
        
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=15, error_out=False)
    roles = Role.query.all()
    return render_template('admin/users.html', pagination=pagination, roles=roles, role_filter=role_filter, search_q=search_q)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def create_user():
    roles = Role.query.all()
    departments = Department.query.all()
    branches = Branch.query.all()
    academic_years = AcademicYear.query.all()
    semesters = Semester.query.all()
    sections = Section.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        full_name = request.form.get('full_name', '').strip()
        role_id = request.form.get('role_id', type=int)
        
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already exists.', 'danger')
            return render_template('admin/create_user.html', roles=roles, departments=departments, branches=branches, academic_years=academic_years, semesters=semesters, sections=sections)
            
        role = db.session.get(Role, role_id)
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role_id=role_id,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Create corresponding profile
        if role.name == 'Student':
            roll_number = request.form.get('roll_number', '').strip()
            branch_id = request.form.get('branch_id', type=int)
            year_id = request.form.get('academic_year_id', type=int)
            semester_id = request.form.get('semester_id', type=int)
            section_id = request.form.get('section_id', type=int)
            adm_year = int(request.form.get('admission_year', datetime.utcnow().year))
            
            profile = StudentProfile(
                user_id=user.id,
                roll_number=roll_number,
                branch_id=branch_id,
                academic_year_id=year_id,
                semester_id=semester_id,
                section_id=section_id,
                admission_year=adm_year
            )
            db.session.add(profile)
        elif role.name == 'Faculty':
            emp_id = request.form.get('employee_id', '').strip()
            dept_id = request.form.get('department_id', type=int)
            designation = request.form.get('designation', 'Assistant Professor')
            
            profile = FacultyProfile(
                user_id=user.id,
                employee_id=emp_id,
                department_id=dept_id,
                designation=designation
            )
            db.session.add(profile)
        elif role.name == 'HOD':
            emp_id = request.form.get('employee_id', '').strip()
            dept_id = request.form.get('department_id', type=int)
            
            profile = HODProfile(
                user_id=user.id,
                employee_id=emp_id,
                department_id=dept_id
            )
            db.session.add(profile)
        elif role.name == 'Principal':
            emp_id = request.form.get('employee_id', '').strip()
            profile = PrincipalProfile(
                user_id=user.id,
                employee_id=emp_id
            )
            db.session.add(profile)
            
        db.session.commit()
        log_audit_event('USER_CREATED', f'/admin/users/{user.id}', {'username': username, 'role': role.name}, 'SUCCESS')
        flash(f'User {username} ({role.name}) created successfully!', 'success')
        return redirect(url_for('admin.users_list'))
        
    return render_template('admin/create_user.html', roles=roles, departments=departments, branches=branches, academic_years=academic_years, semesters=semesters, sections=sections)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('Admin')
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot disable your own administrator account.', 'warning')
        return redirect(url_for('admin.users_list'))
        
    user.is_active = not user.is_active
    db.session.commit()
    log_audit_event('USER_STATUS_TOGGLED', f'/admin/users/{user.id}', {'is_active': user.is_active}, 'SUCCESS')
    flash(f"User {user.username} status set to {'Active' if user.is_active else 'Disabled'}.", 'info')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/audit-logs')
@login_required
@role_required('Admin')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action')
    status_filter = request.args.get('status')
    
    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
        
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/audit_logs.html', pagination=pagination, action_filter=action_filter, status_filter=status_filter)


@admin_bp.route('/timetable', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def timetable_manager():
    sections = Section.query.all()
    subjects = Subject.query.filter_by(is_active=True).all()
    faculty_list = FacultyProfile.query.all()
    classrooms = Classroom.query.all()
    
    if request.method == 'POST':
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int)
        classroom_id = request.form.get('classroom_id', type=int)
        day_of_week = request.form.get('day_of_week')
        period_number = int(request.form.get('period_number', 1))
        academic_session = request.form.get('academic_session', '2026-2027')
        
        # Conflict Detection (Section, Faculty, Room)
        # 1. Section Conflict
        sec_conflict = TimetableEntry.query.filter_by(
            section_id=section_id,
            day_of_week=day_of_week,
            period_number=period_number,
            academic_session=academic_session
        ).first()
        if sec_conflict:
            flash(f"Conflict Error: Section already has subject '{sec_conflict.subject.name}' scheduled for {day_of_week} Period {period_number}.", 'danger')
            return redirect(url_for('admin.timetable_manager'))
            
        # 2. Faculty Conflict
        fac_conflict = TimetableEntry.query.filter_by(
            faculty_id=faculty_id,
            day_of_week=day_of_week,
            period_number=period_number,
            academic_session=academic_session
        ).first()
        if fac_conflict:
            flash(f"Conflict Error: Faculty {fac_conflict.faculty.user.full_name} is already assigned to section '{fac_conflict.section.name}' on {day_of_week} Period {period_number}.", 'danger')
            return redirect(url_for('admin.timetable_manager'))
            
        # 3. Room Conflict
        room_conflict = TimetableEntry.query.filter_by(
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            period_number=period_number,
            academic_session=academic_session
        ).first()
        if room_conflict:
            flash(f"Conflict Error: Classroom {room_conflict.classroom.room_number} is already occupied on {day_of_week} Period {period_number}.", 'danger')
            return redirect(url_for('admin.timetable_manager'))
            
        entry = TimetableEntry(
            section_id=section_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            period_number=period_number,
            academic_session=academic_session
        )
        db.session.add(entry)
        db.session.commit()
        log_audit_event('TIMETABLE_ENTRY_CREATED', f'/admin/timetable/{entry.id}', {
            'day': day_of_week,
            'period': period_number,
            'section': section_id,
            'faculty': faculty_id
        }, 'SUCCESS')
        flash('Timetable slot scheduled successfully without any scheduling conflicts!', 'success')
        return redirect(url_for('admin.timetable_manager'))
        
    entries = TimetableEntry.query.order_by(TimetableEntry.day_of_week, TimetableEntry.period_number).all()
    return render_template(
        'admin/timetable_manager.html',
        sections=sections,
        subjects=subjects,
        faculty_list=faculty_list,
        classrooms=classrooms,
        entries=entries
    )


@admin_bp.route('/timetable/<int:entry_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_timetable_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)
    if not entry:
        abort(404)
    db.session.delete(entry)
    db.session.commit()
    log_audit_event('TIMETABLE_ENTRY_DELETED', f'/admin/timetable/{entry_id}', {}, 'SUCCESS')
    flash('Timetable slot removed successfully.', 'info')
    return redirect(url_for('admin.timetable_manager'))
