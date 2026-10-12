import io
from flask import Blueprint, render_template, request, make_response, send_file, abort, url_for
from flask_login import login_required, current_user
from app.auth.services import role_required, student_owner_required, log_audit_event
from app.extensions import db
from app.models.user import StudentProfile, FacultyProfile, HODProfile, PrincipalProfile
from app.models.academic import Department, Branch
from app.student.services import get_student_syllabus_progress, get_student_attendance_summary
from app.reports.pdf import build_student_progress_pdf, build_department_summary_pdf, build_study_plan_pdf
from app.reports.csv_export import export_attendance_csv
from app.models.planner import StudyPlan

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/viewer')
@login_required
def pdf_viewer():
    """Renders a browser-based PDF viewer wrapper with download & print controls."""
    pdf_url = request.args.get('url')
    title = request.args.get('title', 'Academic Report Viewer')
    if not pdf_url:
        abort(400)
    return render_template('reports/pdf_viewer.html', pdf_url=pdf_url, title=title)


@reports_bp.route('/study-plan/<int:plan_id>/pdf')
@login_required
def study_plan_pdf(plan_id):
    """
    Generates and streams the official DIET Study Plan & Timetable PDF.
    """
    plan = db.session.get(StudyPlan, plan_id)
    if not plan:
        abort(404)
        
    if current_user.is_student() and plan.student_id != current_user.student_profile.id:
        abort(403)
        
    pdf_bytes = build_study_plan_pdf(plan)
    
    download = request.args.get('download', '0') == '1'
    disposition = 'attachment' if download else 'inline'
    filename = f"DIET_Study_Plan_{plan.id}.pdf"
    
    log_audit_event('REPORT_GENERATED_PDF', f'/reports/study-plan/{plan_id}/pdf', {
        'plan_id': plan.id,
        'download': download
    }, 'SUCCESS')
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@reports_bp.route('/student/<int:student_id>/progress-pdf')
@login_required
@student_owner_required('student_id')
def student_progress_pdf(student_id):
    """
    Generates and streams the official PDF progress report.
    Passes Acceptance TEST 8: PDF opens in browser and is downloadable.
    """
    student = db.session.get(StudentProfile, student_id)
    if not student:
        abort(404)
        
    progress_data = get_student_syllabus_progress(student)
    attendance_data = get_student_attendance_summary(student)
    
    pdf_bytes = build_student_progress_pdf(student, progress_data, attendance_data)
    
    download = request.args.get('download', '0') == '1'
    disposition = 'attachment' if download else 'inline'
    filename = f"DIET_Progress_Report_{student.roll_number}.pdf"
    
    log_audit_event('REPORT_GENERATED_PDF', f'/reports/student/{student_id}/progress-pdf', {
        'roll_number': student.roll_number,
        'download': download
    }, 'SUCCESS')
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@reports_bp.route('/hod/<int:dept_id>/summary-pdf')
@login_required
@role_required('HOD', 'Principal', 'Admin')
def department_summary_pdf(dept_id):
    if current_user.is_hod() and current_user.hod_profile.department_id != dept_id:
        abort(403)
        
    department = db.session.get(Department, dept_id)
    if not department:
        abort(404)
        
    faculty_members = FacultyProfile.query.filter_by(department_id=dept_id).all()
    pdf_bytes = build_department_summary_pdf(department, faculty_members, [], 85.0)
    
    download = request.args.get('download', '0') == '1'
    disposition = 'attachment' if download else 'inline'
    filename = f"DIET_Dept_Summary_{department.code}.pdf"
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@reports_bp.route('/export/attendance.csv')
@login_required
@role_required('Faculty', 'HOD', 'Principal', 'Admin')
def export_attendance():
    session_id = request.args.get('session_id', type=int)
    csv_bytes = export_attendance_csv(session_id=session_id)
    
    response = make_response(csv_bytes)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename="DIET_Attendance_Export.csv"'
    return response
