import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.auth.services import role_required, student_owner_required, log_audit_event
from app.extensions import db
from app.models.user import StudentProfile
from app.models.academic import Subject, Branch, Semester, Section
from app.models.syllabus import Topic, Unit, TopicCompletion, SubjectTestAttempt
from app.models.planner import StudyPlan, StudyPlanTask
from app.models.attendance import AttendanceRecord
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.timetable import TimetableEntry
from app.models.calendar import AcademicCalendarEvent
from app.models.notifications import Notification
from app.student.services import (
    get_student_syllabus_progress,
    get_student_attendance_summary,
    get_student_assignments_summary
)

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@role_required('Student')
def dashboard():
    student = current_user.student_profile
    if not student:
        flash('Student profile not found. Please contact administration.', 'danger')
        return redirect(url_for('auth.logout'))
        
    # Syllabus progress stats
    progress_data = get_student_syllabus_progress(student)
    
    # Attendance summary
    attendance_data = get_student_attendance_summary(student)
    
    # Active Study Plan
    active_plan = StudyPlan.query.filter_by(student_id=student.id, is_active=True).first()
    
    # Today's tasks
    today = datetime.utcnow().date()
    today_tasks = []
    if active_plan:
        today_tasks = StudyPlanTask.query.filter_by(
            study_plan_id=active_plan.id,
            task_date=today
        ).all()
        
    # Upcoming Assignments
    assignments_data = get_student_assignments_summary(student)
    pending_assignments = [a for a in assignments_data if not a['is_submitted'] and a['assignment'].due_date >= datetime.utcnow()]
    
    # Upcoming Calendar Events
    upcoming_events = AcademicCalendarEvent.query.filter(
        AcademicCalendarEvent.end_date >= today
    ).order_by(AcademicCalendarEvent.start_date.asc()).limit(5).all()
    
    # Unread notifications count
    unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    # Recent Subject Test Attempts
    recent_test_attempts = SubjectTestAttempt.query.filter_by(student_id=student.id).order_by(SubjectTestAttempt.attempted_at.desc()).limit(5).all()
    
    return render_template(
        'student/dashboard.html',
        student=student,
        progress=progress_data,
        attendance=attendance_data,
        active_plan=active_plan,
        today_tasks=today_tasks,
        pending_assignments=pending_assignments,
        upcoming_events=upcoming_events,
        unread_notifs=unread_notifs,
        test_attempts=recent_test_attempts
    )


@student_bp.route('/<int:student_id>')
@login_required
@student_owner_required('student_id')
def view_profile_by_id(student_id):
    """
    Direct student ID route protected against IDOR.
    Returns 403 Forbidden if a student tries to access another student's ID.
    """
    student = db.session.get(StudentProfile, student_id)
    if not student:
        abort(404)
        
    progress_data = get_student_syllabus_progress(student)
    attendance_data = get_student_attendance_summary(student)
    return render_template('student/student_profile_view.html', student=student, progress=progress_data, attendance=attendance_data)


@student_bp.route('/syllabus')
@login_required
@role_required('Student')
def syllabus():
    student = current_user.student_profile
    progress_data = get_student_syllabus_progress(student)
    return render_template('student/syllabus.html', student=student, progress=progress_data)


@student_bp.route('/subjects/<int:subject_id>')
@login_required
@role_required('Student')
def subject_detail(subject_id):
    student = current_user.student_profile
    subject = db.session.get(Subject, subject_id)
    if not subject:
        abort(404)
        
    # Verify subject belongs to student's branch/semester
    if subject.branch_id != student.branch_id or subject.semester_id != student.semester_id:
        flash('Subject is outside your current academic branch or semester.', 'warning')
        
    # Get completion map
    completions = TopicCompletion.query.filter_by(student_id=student.id).all()
    completion_map = {c.topic_id: c.is_completed for c in completions}
    
    return render_template('student/subject_detail.html', student=student, subject=subject, completion_map=completion_map)


@student_bp.route('/attendance')
@login_required
@role_required('Student')
def attendance():
    student = current_user.student_profile
    attendance_data = get_student_attendance_summary(student)
    records = AttendanceRecord.query.filter_by(student_id=student.id).order_by(AttendanceRecord.id.desc()).all()
    return render_template('student/attendance.html', student=student, attendance=attendance_data, records=records)


@student_bp.route('/assignments')
@login_required
@role_required('Student')
def assignments():
    student = current_user.student_profile
    assignments_data = get_student_assignments_summary(student)
    return render_template('student/assignments.html', student=student, assignments=assignments_data)


@student_bp.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def assignment_detail(assignment_id):
    student = current_user.student_profile
    assignment = db.session.get(Assignment, assignment_id)
    if not assignment:
        abort(404)
        
    submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=student.id
    ).first()
    
    if request.method == 'POST':
        submission_text = request.form.get('submission_text', '').strip()
        file = request.files.get('file')
        
        file_path = None
        if file and file.filename:
            filename = secure_filename(f"sub_{student.roll_number}_{assignment.id}_{file.filename}")
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
            os.makedirs(upload_dir, exist_ok=True)
            saved_path = os.path.join(upload_dir, filename)
            file.save(saved_path)
            file_path = f"assignments/{filename}"
            
        is_late = datetime.utcnow() > assignment.due_date
        
        if not submission:
            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=student.id,
                submission_text=submission_text,
                file_path=file_path,
                submitted_at=datetime.utcnow(),
                is_late=is_late
            )
            db.session.add(submission)
        else:
            submission.submission_text = submission_text
            if file_path:
                submission.file_path = file_path
            submission.submitted_at = datetime.utcnow()
            submission.is_late = is_late
            
        db.session.commit()
        log_audit_event('ASSIGNMENT_SUBMISSION', f'/student/assignments/{assignment.id}', {
            'assignment_title': assignment.title,
            'is_late': is_late
        }, 'SUCCESS')
        flash('Your assignment submission has been received successfully!', 'success')
        return redirect(url_for('student.assignment_detail', assignment_id=assignment.id))
        
    return render_template('student/assignment_detail.html', student=student, assignment=assignment, submission=submission)


@student_bp.route('/timetable')
@login_required
@role_required('Student')
def timetable():
    student = current_user.student_profile
    entries = []
    if student.section_id:
        entries = TimetableEntry.query.filter_by(section_id=student.section_id).order_by(
            TimetableEntry.day_of_week, TimetableEntry.period_number
        ).all()
        
    # Group by Day -> Period
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_grid = {day: {p: None for p in range(1, 9)} for day in days}
    
    for e in entries:
        if e.day_of_week in timetable_grid and 1 <= e.period_number <= 8:
            timetable_grid[e.day_of_week][e.period_number] = e
            
    return render_template('student/timetable.html', student=student, timetable_grid=timetable_grid, days=days)


@student_bp.route('/calendar')
@login_required
@role_required('Student')
def calendar():
    events = AcademicCalendarEvent.query.order_by(AcademicCalendarEvent.start_date.asc()).all()
    return render_template('student/calendar.html', events=events)


def generate_subject_quiz_questions(subject):
    """
    Generates a set of structured multiple choice questions based on the subject's units and topics.
    """
    questions = []
    units = subject.units
    q_counter = 1

    for u in units:
        for t in u.topics:
            q = {
                'id': q_counter,
                'unit_title': u.unit_title,
                'topic_name': t.topic_name,
                'question': f"In {subject.name} ({u.unit_title}), which statement best describes the fundamental principle of '{t.topic_name}'?",
                'options': [
                    f"It provides core structural and functional capabilities for {t.topic_name}.",
                    f"It is used exclusively as a historical fallback method.",
                    f"It eliminates the need for any algorithmic computation.",
                    f"It is an obsolete standard deprecated in modern engineering curricula."
                ],
                'correct_index': 0,
                'explanation': f"'{t.topic_name}' is a key syllabus topic in {u.unit_title} essential for mastering {subject.name}."
            }
            questions.append(q)
            q_counter += 1
            if len(questions) >= 10:
                break
        if len(questions) >= 10:
            break

    if not questions:
        # Fallback question set if no topics populated yet
        questions = [
            {
                'id': 1,
                'unit_title': 'Unit 1 Overview',
                'topic_name': 'Core Foundations',
                'question': f"What is the primary objective of studying {subject.name} ({subject.code})?",
                'options': [
                    f"To acquire fundamental theoretical and practical mastery of {subject.name}.",
                    "To memorize historical administrative dates.",
                    "To disable automated software tools.",
                    "None of the above."
                ],
                'correct_index': 0,
                'explanation': f"{subject.name} builds core competence in modern engineering."
            },
            {
                'id': 2,
                'unit_title': 'Unit 2 Advanced Concepts',
                'topic_name': 'System Integration',
                'question': f"How are credits ({subject.credits}) and hours allocated for {subject.name}?",
                'options': [
                    f"Structured across lecture, tutorial, and practical sessions based on regulation {subject.regulation}.",
                    "Randomly assigned per semester.",
                    "Without any academic senate guidelines.",
                    "Only via extra-curricular activities."
                ],
                'correct_index': 0,
                'explanation': "Course credit structures follow mandatory university academic guidelines."
            }
        ]

    return questions


@student_bp.route('/subject/<int:subject_id>/test', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def take_subject_test(subject_id):
    student = current_user.student_profile
    subject = db.session.get(Subject, subject_id)
    if not subject:
        abort(404)

    questions = generate_subject_quiz_questions(subject)

    if request.method == 'POST':
        correct_count = 0
        total_questions = len(questions)
        results = []

        for q in questions:
            user_ans = request.form.get(f"q_{q['id']}", type=int)
            is_correct = (user_ans == q['correct_index'])
            if is_correct:
                correct_count += 1

            results.append({
                'question': q,
                'user_ans': user_ans,
                'is_correct': is_correct
            })

        score_percentage = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0.0

        if score_percentage >= 85.0:
            mastery_level = "Mastered 🏆"
        elif score_percentage >= 70.0:
            mastery_level = "Proficient 🌟"
        elif score_percentage >= 50.0:
            mastery_level = "Developing 📈"
        else:
            mastery_level = "Needs Revision ⚠️"

        attempt = SubjectTestAttempt(
            student_id=student.id,
            subject_id=subject.id,
            score_percentage=score_percentage,
            total_questions=total_questions,
            correct_answers=correct_count,
            mastery_level=mastery_level,
            attempted_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()

        log_audit_event('SUBJECT_MASTERY_TEST_TAKEN', f'/student/subject/{subject_id}/test', {
            'student': student.roll_number,
            'subject_code': subject.code,
            'score': score_percentage,
            'mastery_level': mastery_level
        }, 'SUCCESS')

        flash(f'Test completed! Your score: {score_percentage}% ({mastery_level})', 'success')
        return render_template(
            'student/subject_test_results.html',
            student=student,
            subject=subject,
            score_percentage=score_percentage,
            correct_count=correct_count,
            total_questions=total_questions,
            mastery_level=mastery_level,
            results=results,
            attempt=attempt
        )

    return render_template('student/subject_test.html', student=student, subject=subject, questions=questions)

