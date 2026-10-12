from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.auth.services import role_required, log_audit_event
from app.extensions import db
from app.models.user import HODProfile, FacultyProfile, StudentProfile
from app.models.academic import Department, Branch, Subject, SubjectOffering
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.syllabus import TopicCompletion

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')


@hod_bp.route('/dashboard')
@login_required
@role_required('HOD')
def dashboard():
    hod = current_user.hod_profile
    if not hod:
        flash('HOD profile not found.', 'danger')
        return redirect(url_for('auth.logout'))
        
    dept = hod.department
    branches = Branch.query.filter_by(department_id=dept.id).all()
    branch_ids = [b.id for b in branches]
    
    faculty_list = FacultyProfile.query.filter_by(department_id=dept.id).all()
    students_count = StudentProfile.query.filter(StudentProfile.branch_id.in_(branch_ids)).count()
    
    subjects = Subject.query.filter(Subject.branch_id.in_(branch_ids), Subject.is_active==True).all()
    subject_ids = [s.id for s in subjects]
    
    # Calculate real department syllabus progress
    total_topics_count = sum(len(u.topics) for s in subjects for u in s.units)
    
    # Calculate department attendance average
    dept_students = StudentProfile.query.filter(StudentProfile.branch_id.in_(branch_ids)).all()
    dept_student_ids = [s.id for s in dept_students]
    
    total_att_records = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(dept_student_ids)).count()
    present_att_records = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(dept_student_ids), AttendanceRecord.is_present==True).count()
    dept_att_rate = round((present_att_records / total_att_records * 100), 1) if total_att_records > 0 else 0.0
    
    # Total assignments in department
    offerings = SubjectOffering.query.filter(SubjectOffering.subject_id.in_(subject_ids)).all()
    offering_ids = [o.id for o in offerings]
    dept_assignments = Assignment.query.filter(Assignment.offering_id.in_(offering_ids)).count()
    
    return render_template(
        'hod/dashboard.html',
        hod=hod,
        department=dept,
        branches=branches,
        faculty_count=len(faculty_list),
        students_count=students_count,
        subjects_count=len(subjects),
        dept_att_rate=dept_att_rate,
        dept_assignments=dept_assignments
    )


@hod_bp.route('/department/<int:department_id>')
@login_required
@role_required('HOD')
def view_department(department_id):
    """
    Department view route strictly checking HOD ownership.
    Returns HTTP 403 Forbidden if HOD attempts to view another department (TEST 5).
    """
    hod = current_user.hod_profile
    if not hod or hod.department_id != department_id:
        log_audit_event('UNAUTHORIZED_DEPT_ACCESS', f'/hod/department/{department_id}', {
            'hod_dept': getattr(hod, 'department_id', None),
            'target_dept': department_id
        }, 'DENIED')
        abort(403)
        
    dept = db.session.get(Department, department_id)
    branches = Branch.query.filter_by(department_id=dept.id).all()
    faculty_list = FacultyProfile.query.filter_by(department_id=dept.id).all()
    
    return render_template('hod/department_detail.html', department=dept, branches=branches, faculty_list=faculty_list)


@hod_bp.route('/faculty')
@login_required
@role_required('HOD')
def faculty_list():
    hod = current_user.hod_profile
    faculty_members = FacultyProfile.query.filter_by(department_id=hod.department_id).all()
    return render_template('hod/faculty_list.html', hod=hod, faculty_members=faculty_members)


@hod_bp.route('/students')
@login_required
@role_required('HOD')
def student_analytics():
    hod = current_user.hod_profile
    branches = Branch.query.filter_by(department_id=hod.department_id).all()
    branch_ids = [b.id for b in branches]
    
    students = StudentProfile.query.filter(StudentProfile.branch_id.in_(branch_ids)).all()
    
    student_stats = []
    for s in students:
        # Calculate real syllabus completion for this student
        subj_topics = [t for subj in s.branch.subjects if subj.semester_id == s.semester_id for u in subj.units for t in u.topics]
        total_t = len(subj_topics)
        done_t = TopicCompletion.query.filter_by(student_id=s.id, is_completed=True).count()
        pct = round((done_t / total_t * 100), 1) if total_t > 0 else 0.0
        
        # Attendance
        att_total = AttendanceRecord.query.filter_by(student_id=s.id).count()
        att_pres = AttendanceRecord.query.filter_by(student_id=s.id, is_present=True).count()
        att_pct = round((att_pres / att_total * 100), 1) if att_total > 0 else 0.0
        
        student_stats.append({
            'student': s,
            'completion_percentage': pct,
            'attendance_percentage': att_pct
        })
        
    return render_template('hod/student_analytics.html', hod=hod, student_stats=student_stats)
