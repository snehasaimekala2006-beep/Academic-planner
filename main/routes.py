from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.academic import Branch, Department
from app.models.calendar import AcademicCalendarEvent
from app.models.notifications import Notification

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    branches = Branch.query.order_by(Branch.name).all()
    upcoming_events = AcademicCalendarEvent.query.order_by(AcademicCalendarEvent.start_date.asc()).limit(5).all()

    user_info = None
    syllabus_data = None
    test_attempts = []
    active_plan = None

    if current_user.is_authenticated:
        if current_user.is_student() and current_user.student_profile:
            from app.student.services import get_student_syllabus_progress
            from app.models.planner import StudyPlan
            from app.models.syllabus import SubjectTestAttempt
            student = current_user.student_profile
            syllabus_data = get_student_syllabus_progress(student)
            test_attempts = SubjectTestAttempt.query.filter_by(student_id=student.id).order_by(SubjectTestAttempt.attempted_at.desc()).limit(5).all()
            active_plan = StudyPlan.query.filter_by(student_id=student.id, is_active=True).first()
            user_info = {
                'type': 'Student',
                'id_label': 'Roll Number',
                'id_value': student.roll_number,
                'branch_dept': f"{student.branch.name} ({student.branch.code})",
                'semester_year': f"{student.semester.label} ({student.academic_year.label})",
                'section': student.section.name if student.section else 'A'
            }
        elif current_user.is_faculty() and current_user.faculty_profile:
            from app.models.academic import SubjectOffering
            from app.models.syllabus import FacultyTopicCompletion
            faculty = current_user.faculty_profile
            offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id, is_active=True).all()
            offering_cov = []
            for o in offerings:
                all_t = [t for u in o.subject.units for t in u.topics]
                total_t = len(all_t)
                done_t = 0
                if total_t > 0:
                    topic_ids = [t.id for t in all_t]
                    done_t = FacultyTopicCompletion.query.filter(
                        FacultyTopicCompletion.faculty_id == faculty.id,
                        FacultyTopicCompletion.topic_id.in_(topic_ids),
                        FacultyTopicCompletion.is_completed == True
                    ).count()
                cov_pct = round((done_t / total_t * 100), 1) if total_t > 0 else 0.0
                offering_cov.append({
                    'offering': o,
                    'completed_topics': done_t,
                    'total_topics': total_t,
                    'coverage_percentage': cov_pct
                })
            syllabus_data = {'offerings': offering_cov}
            user_info = {
                'type': 'Faculty',
                'id_label': 'Employee ID',
                'id_value': faculty.employee_id,
                'branch_dept': faculty.department.name,
                'designation': faculty.designation,
                'qualification': faculty.qualification or 'M.Tech / Ph.D'
            }
        else:
            user_info = {
                'type': current_user.role_name,
                'id_label': 'Username',
                'id_value': current_user.username,
                'branch_dept': 'Administration',
                'semester_year': 'N/A'
            }

    return render_template(
        'index.html',
        branches=branches,
        events=upcoming_events,
        user_info=user_info,
        syllabus_data=syllabus_data,
        test_attempts=test_attempts,
        active_plan=active_plan
    )


@main_bp.route('/about')
def about():
    departments = Department.query.order_by(Department.name).all()
    return render_template('about.html', departments=departments)


@main_bp.route('/contact')
def contact():
    return render_template('contact.html')


@main_bp.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/index.html', notifications=notifs)


@main_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('main.notifications'))
