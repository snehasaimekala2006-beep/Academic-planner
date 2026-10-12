from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.auth.services import role_required
from app.extensions import db
from app.models.user import PrincipalProfile, FacultyProfile, StudentProfile
from app.models.academic import Department, Branch, Subject, AcademicYear, Semester
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.syllabus import TopicCompletion

principal_bp = Blueprint('principal', __name__, url_prefix='/principal')


@principal_bp.route('/dashboard')
@login_required
@role_required('Principal')
def dashboard():
    principal = current_user.principal_profile
    if not principal:
        flash('Principal profile not configured.', 'danger')
        return redirect(url_for('auth.logout'))
        
    total_departments = Department.query.count()
    total_branches = Branch.query.count()
    total_faculty = FacultyProfile.query.count()
    total_students = StudentProfile.query.count()
    total_subjects = Subject.query.filter_by(is_active=True).count()
    
    # Institution-wide Attendance Rate
    total_att = AttendanceRecord.query.count()
    present_att = AttendanceRecord.query.filter_by(is_present=True).count()
    institution_att_rate = round((present_att / total_att * 100), 1) if total_att > 0 else 0.0
    
    # Institution-wide Assignment Statistics
    total_assignments = Assignment.query.count()
    total_submissions = AssignmentSubmission.query.count()
    
    # Branch-by-Branch Breakdown
    branches = Branch.query.order_by(Branch.name).all()
    branch_stats = []
    
    for b in branches:
        b_students = StudentProfile.query.filter_by(branch_id=b.id).all()
        b_student_ids = [s.id for s in b_students]
        b_faculty_count = FacultyProfile.query.filter_by(department_id=b.department_id).count()
        
        # Branch Attendance
        b_att_total = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(b_student_ids)).count() if b_student_ids else 0
        b_att_pres = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(b_student_ids), AttendanceRecord.is_present==True).count() if b_student_ids else 0
        b_att_pct = round((b_att_pres / b_att_total * 100), 1) if b_att_total > 0 else 0.0
        
        # Branch Syllabus Completion Average
        b_done_topics = TopicCompletion.query.filter(TopicCompletion.student_id.in_(b_student_ids), TopicCompletion.is_completed==True).count() if b_student_ids else 0
        b_avg_completion = round((b_done_topics / (len(b_students) * 30) * 100), 1) if b_students else 0.0
        
        branch_stats.append({
            'branch': b,
            'student_count': len(b_students),
            'faculty_count': b_faculty_count,
            'attendance_rate': b_att_pct,
            'completion_rate': min(b_avg_completion, 100.0)
        })
        
    return render_template(
        'principal/dashboard.html',
        principal=principal,
        total_departments=total_departments,
        total_branches=total_branches,
        total_faculty=total_faculty,
        total_students=total_students,
        total_subjects=total_subjects,
        institution_att_rate=institution_att_rate,
        total_assignments=total_assignments,
        total_submissions=total_submissions,
        branch_stats=branch_stats
    )


@principal_bp.route('/departments')
@login_required
@role_required('Principal')
def departments():
    departments = Department.query.order_by(Department.name).all()
    return render_template('principal/departments.html', departments=departments)


@principal_bp.route('/analytics')
@login_required
@role_required('Principal')
def analytics():
    branches = Branch.query.order_by(Branch.name).all()
    semesters = Semester.query.order_by(Semester.semester_number).all()
    return render_template('principal/analytics.html', branches=branches, semesters=semesters)
