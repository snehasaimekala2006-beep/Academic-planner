import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.auth.services import role_required, log_audit_event
from app.extensions import db
from app.models.user import FacultyProfile, StudentProfile
from app.models.academic import SubjectOffering, Subject, Section, Branch
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.planner import FacultyTeachingPlan, TeachingPlanWeek
from app.models.timetable import TimetableEntry
from app.models.notifications import Notification

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')


@faculty_bp.route('/dashboard')
@login_required
@role_required('Faculty')
def dashboard():
    faculty = current_user.faculty_profile
    if not faculty:
        flash('Faculty profile not configured.', 'danger')
        return redirect(url_for('auth.logout'))
        
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id, is_active=True).all()
    offering_ids = [o.id for o in offerings]
    
    # Calculate syllabus coverage per offering
    from app.models.syllabus import FacultyTopicCompletion
    offering_coverage = []
    for o in offerings:
        all_topics = [t for u in o.subject.units for t in u.topics]
        total_t = len(all_topics)
        done_t = 0
        if total_t > 0:
            topic_ids = [t.id for t in all_topics]
            done_t = FacultyTopicCompletion.query.filter(
                FacultyTopicCompletion.faculty_id == faculty.id,
                FacultyTopicCompletion.topic_id.in_(topic_ids),
                FacultyTopicCompletion.is_completed == True
            ).count()
        cov_pct = round((done_t / total_t * 100), 1) if total_t > 0 else 0.0
        offering_coverage.append({
            'offering': o,
            'completed_topics': done_t,
            'total_topics': total_t,
            'coverage_percentage': cov_pct
        })
    
    # Recent Attendance Sessions
    recent_sessions = AttendanceSession.query.filter(
        AttendanceSession.offering_id.in_(offering_ids)
    ).order_by(AttendanceSession.session_date.desc()).limit(5).all()
    
    # Active Assignments
    assignments = Assignment.query.filter(
        Assignment.offering_id.in_(offering_ids)
    ).order_by(Assignment.due_date.desc()).limit(5).all()
    
    # Teaching Plans
    teaching_plans = FacultyTeachingPlan.query.filter_by(faculty_id=faculty.id).all()
    
    return render_template(
        'faculty/dashboard.html',
        faculty=faculty,
        offerings=offerings,
        offering_coverage=offering_coverage,
        recent_sessions=recent_sessions,
        assignments=assignments,
        teaching_plans=teaching_plans
    )


@faculty_bp.route('/attendance')
@login_required
@role_required('Faculty')
def attendance():
    faculty = current_user.faculty_profile
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id, is_active=True).all()
    offering_ids = [o.id for o in offerings]
    sessions = AttendanceSession.query.filter(
        AttendanceSession.offering_id.in_(offering_ids)
    ).order_by(AttendanceSession.session_date.desc(), AttendanceSession.period_number.desc()).all()
    
    return render_template('faculty/attendance.html', faculty=faculty, offerings=offerings, sessions=sessions)


@faculty_bp.route('/attendance/take', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def take_attendance():
    faculty = current_user.faculty_profile
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id, is_active=True).all()
    
    selected_offering_id = request.args.get('offering_id', type=int)
    selected_offering = None
    students = []
    
    if selected_offering_id:
        selected_offering = db.session.get(SubjectOffering, selected_offering_id)
        if selected_offering and selected_offering.faculty_id == faculty.id:
            # Find students in offering section
            students = StudentProfile.query.filter_by(
                section_id=selected_offering.section_id
            ).order_by(StudentProfile.roll_number).all()
            
    if request.method == 'POST':
        offering_id = request.form.get('offering_id', type=int)
        session_date_str = request.form.get('session_date')
        period = int(request.form.get('period_number', 1))
        topic_covered = request.form.get('topic_covered', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
        offering = db.session.get(SubjectOffering, offering_id)
        if not offering or offering.faculty_id != faculty.id:
            abort(403)
            
        try:
            s_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
            
            # Check duplicate session constraint
            existing = AttendanceSession.query.filter_by(
                offering_id=offering.id,
                session_date=s_date,
                period_number=period
            ).first()
            if existing:
                flash(f'Attendance session for Period {period} on {s_date} already exists for this subject/section!', 'danger')
                return redirect(url_for('faculty.take_attendance', offering_id=offering.id))
                
            session_rec = AttendanceSession(
                offering_id=offering.id,
                faculty_id=faculty.id,
                session_date=s_date,
                period_number=period,
                topic_covered=topic_covered,
                remarks=remarks
            )
            db.session.add(session_rec)
            db.session.flush()
            
            # Process present/absent for students
            students_in_sec = StudentProfile.query.filter_by(section_id=offering.section_id).all()
            present_count = 0
            for st in students_in_sec:
                is_pres = request.form.get(f'student_{st.id}') == 'present'
                if is_pres:
                    present_count += 1
                rec = AttendanceRecord(
                    session_id=session_rec.id,
                    student_id=st.id,
                    is_present=is_pres
                )
                db.session.add(rec)
                
            db.session.commit()
            log_audit_event('ATTENDANCE_RECORDED', f'/faculty/attendance/session/{session_rec.id}', {
                'offering_id': offering.id,
                'date': str(s_date),
                'period': period,
                'present_count': present_count,
                'total_students': len(students_in_sec)
            }, 'SUCCESS')
            flash(f'Attendance successfully recorded for {len(students_in_sec)} students ({present_count} Present)!', 'success')
            return redirect(url_for('faculty.attendance'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to record attendance: {str(e)}', 'danger')
            
    return render_template(
        'faculty/take_attendance.html',
        faculty=faculty,
        offerings=offerings,
        selected_offering=selected_offering,
        students=students,
        today=datetime.utcnow().date()
    )


@faculty_bp.route('/assignments')
@login_required
@role_required('Faculty')
def assignments():
    faculty = current_user.faculty_profile
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id).all()
    offering_ids = [o.id for o in offerings]
    assignment_list = Assignment.query.filter(Assignment.offering_id.in_(offering_ids)).order_by(Assignment.created_at.desc()).all()
    return render_template('faculty/assignments.html', faculty=faculty, assignments=assignment_list)


@faculty_bp.route('/assignments/create', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def create_assignment():
    faculty = current_user.faculty_profile
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id).all()
    
    if request.method == 'POST':
        offering_id = request.form.get('offering_id', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        max_marks = float(request.form.get('max_marks', 100.0))
        due_date_str = request.form.get('due_date')
        
        offering = db.session.get(SubjectOffering, offering_id)
        if not offering or offering.faculty_id != faculty.id:
            abort(403)
            
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # File attachment
            file = request.files.get('attachment')
            attachment_path = None
            if file and file.filename:
                fname = secure_filename(f"assign_{faculty.employee_id}_{file.filename}")
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, fname))
                attachment_path = f"assignments/{fname}"
                
            assignment = Assignment(
                offering_id=offering.id,
                faculty_id=faculty.id,
                title=title,
                description=description,
                max_marks=max_marks,
                due_date=due_date,
                attachment_path=attachment_path
            )
            db.session.add(assignment)
            db.session.flush()
            
            # Send notifications to students in that section
            students = StudentProfile.query.filter_by(section_id=offering.section_id).all()
            for st in students:
                notif = Notification(
                    user_id=st.user_id,
                    title=f"New Assignment: {title}",
                    message=f"Prof. {current_user.full_name} posted a new assignment for {offering.subject.name}. Due: {due_date.strftime('%d %b %Y, %H:%M')}.",
                    category='Assignment',
                    link_url=url_for('student.assignment_detail', assignment_id=assignment.id)
                )
                db.session.add(notif)
                
            db.session.commit()
            log_audit_event('ASSIGNMENT_CREATED', f'/faculty/assignments/{assignment.id}', {'title': title}, 'SUCCESS')
            flash('Assignment published successfully and notified enrolled students!', 'success')
            return redirect(url_for('faculty.assignments'))
        except Exception as e:
            flash(f'Error creating assignment: {str(e)}', 'danger')
            
    return render_template('faculty/create_assignment.html', faculty=faculty, offerings=offerings)


@faculty_bp.route('/assignments/<int:assignment_id>/submissions')
@login_required
@role_required('Faculty')
def view_submissions(assignment_id):
    faculty = current_user.faculty_profile
    assignment = db.session.get(Assignment, assignment_id)
    if not assignment or assignment.faculty_id != faculty.id:
        abort(403)
        
    return render_template('faculty/submissions.html', assignment=assignment)


@faculty_bp.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
@role_required('Faculty')
def grade_submission(submission_id):
    faculty = current_user.faculty_profile
    submission = db.session.get(AssignmentSubmission, submission_id)
    if not submission or submission.assignment.faculty_id != faculty.id:
        abort(403)
        
    marks = float(request.form.get('marks', 0.0))
    feedback = request.form.get('feedback', '').strip()
    
    submission.marks_awarded = marks
    submission.feedback = feedback
    submission.graded_by_id = current_user.id
    submission.graded_at = datetime.utcnow()
    
    # Notify student
    notif = Notification(
        user_id=submission.student.user_id,
        title=f"Assignment Graded: {submission.assignment.title}",
        message=f"Your submission for {submission.assignment.title} has been graded: {marks}/{submission.assignment.max_marks} marks.",
        category='Assignment',
        link_url=url_for('student.assignment_detail', assignment_id=submission.assignment.id)
    )
    db.session.add(notif)
    db.session.commit()
    
    log_audit_event('ASSIGNMENT_GRADED', f'/faculty/submissions/{submission.id}/grade', {
        'marks': marks,
        'student': submission.student.roll_number
    }, 'SUCCESS')
    flash(f'Submission graded successfully for student {submission.student.roll_number}!', 'success')
    return redirect(url_for('faculty.view_submissions', assignment_id=submission.assignment_id))


@faculty_bp.route('/teaching-planner', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def teaching_planner():
    faculty = current_user.faculty_profile
    offerings = SubjectOffering.query.filter_by(faculty_id=faculty.id).all()
    
    if request.method == 'POST':
        offering_id = request.form.get('offering_id', type=int)
        target_date_str = request.form.get('target_completion_date')
        classes_per_week = int(request.form.get('classes_per_week', 4))
        
        offering = db.session.get(SubjectOffering, offering_id)
        if not offering or offering.faculty_id != faculty.id:
            abort(403)
            
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            
            plan = FacultyTeachingPlan(
                offering_id=offering.id,
                faculty_id=faculty.id,
                subject_id=offering.subject_id,
                target_completion_date=target_date,
                classes_per_week=classes_per_week
            )
            db.session.add(plan)
            db.session.flush()
            
            # Generate 16 week teaching structure mapped to units
            subject = offering.subject
            units = subject.units
            
            week_idx = 1
            for u in units:
                topics_str = ", ".join([t.topic_name for t in u.topics[:3]]) or u.unit_title
                w = TeachingPlanWeek(
                    teaching_plan_id=plan.id,
                    week_number=week_idx,
                    title=f"Week {week_idx} - {u.unit_title}",
                    topics_covered=topics_str,
                    plan_type='Lecture'
                )
                db.session.add(w)
                week_idx += 1
                
                # Add revision/assessment week
                w_rev = TeachingPlanWeek(
                    teaching_plan_id=plan.id,
                    week_number=week_idx,
                    title=f"Week {week_idx} - Unit {u.unit_number} Practice & Tutorial",
                    topics_covered=f"Tutorial, Problem Solving & Quiz on {u.unit_title}",
                    plan_type='Practice'
                )
                db.session.add(w_rev)
                week_idx += 1
                
            db.session.commit()
            log_audit_event('TEACHING_PLAN_CREATED', f'/faculty/teaching-planner/{plan.id}', {'subject': subject.code}, 'SUCCESS')
            flash(f'Teaching Plan generated with {week_idx-1} planned instructional weeks!', 'success')
            return redirect(url_for('faculty.teaching_planner'))
        except Exception as e:
            flash(f'Error creating teaching plan: {str(e)}', 'danger')
            
    plans = FacultyTeachingPlan.query.filter_by(faculty_id=faculty.id).all()
    return render_template('faculty/teaching_planner.html', faculty=faculty, offerings=offerings, plans=plans)


@faculty_bp.route('/timetable')
@login_required
@role_required('Faculty')
def timetable():
    faculty = current_user.faculty_profile
    entries = TimetableEntry.query.filter_by(faculty_id=faculty.id).all()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_grid = {day: {p: None for p in range(1, 9)} for day in days}
    
    for e in entries:
        if e.day_of_week in timetable_grid and 1 <= e.period_number <= 8:
            timetable_grid[e.day_of_week][e.period_number] = e
            
    return render_template('faculty/timetable.html', faculty=faculty, timetable_grid=timetable_grid, days=days)
