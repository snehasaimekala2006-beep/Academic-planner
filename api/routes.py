from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.syllabus import Topic, TopicCompletion, FacultyTopicCompletion, Unit
from app.models.academic import Subject, Branch, Semester
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.notifications import Notification
from app.models.timetable import TimetableEntry, Classroom
from app.auth.services import log_audit_event

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/topics/<int:topic_id>/completion', methods=['POST'])
@login_required
def toggle_topic_completion(topic_id):
    """
    CRITICAL CHECKBOX / RADIO BUTTON API: Single source of truth for topic completion.
    Accepts JSON: {"completed": true/false, "offering_id": optional_int}
    Persists state for Student or Faculty and computes updated subject & unit completion stats.
    """
    topic = db.session.get(Topic, topic_id)
    if not topic:
        return jsonify({'error': 'Topic not found.'}), 404
        
    data = request.get_json(silent=True) or {}
    is_completed = bool(data.get('completed', True))
    offering_id = data.get('offering_id')
    
    unit = topic.unit
    subject = unit.subject

    if current_user.is_student():
        student = current_user.student_profile
        if not student:
            return jsonify({'error': 'Student profile not found.'}), 404
            
        completion = TopicCompletion.query.filter_by(student_id=student.id, topic_id=topic.id).first()
        if not completion:
            completion = TopicCompletion(
                student_id=student.id,
                topic_id=topic.id,
                is_completed=is_completed,
                completed_at=datetime.utcnow() if is_completed else None
            )
            db.session.add(completion)
        else:
            completion.is_completed = is_completed
            completion.completed_at = datetime.utcnow() if is_completed else None
            completion.updated_at = datetime.utcnow()
            
        # Also auto-update StudyPlanTask if student completes topic
        if is_completed:
            from app.models.planner import StudyPlan, StudyPlanTask
            active_plan = StudyPlan.query.filter_by(student_id=student.id, is_active=True).first()
            if active_plan:
                StudyPlanTask.query.filter_by(study_plan_id=active_plan.id, topic_id=topic.id, status='PENDING').update({
                    'status': 'COMPLETED',
                    'completed_at': datetime.utcnow()
                })

        db.session.commit()
        
        # Calculate fresh subject and unit progress for student
        unit_topic_ids = [t.id for t in unit.topics]
        unit_total = len(unit_topic_ids)
        unit_done = TopicCompletion.query.filter(
            TopicCompletion.student_id == student.id,
            TopicCompletion.topic_id.in_(unit_topic_ids),
            TopicCompletion.is_completed == True
        ).count()
        unit_percentage = round((unit_done / unit_total * 100), 1) if unit_total > 0 else 0.0
        
        all_subject_topics = [t for u in subject.units for t in u.topics]
        subj_total = len(all_subject_topics)
        subj_topic_ids = [t.id for t in all_subject_topics]
        
        subj_done_records = TopicCompletion.query.filter(
            TopicCompletion.student_id == student.id,
            TopicCompletion.topic_id.in_(subj_topic_ids),
            TopicCompletion.is_completed == True
        ).all()
        subj_done_ids = {r.topic_id for r in subj_done_records}
        
        subj_done_count = len(subj_done_ids)
        subj_remaining_count = subj_total - subj_done_count
        subj_percentage = round((subj_done_count / subj_total * 100), 1) if subj_total > 0 else 0.0
        remaining_hours = sum(t.estimated_hours for t in all_subject_topics if t.id not in subj_done_ids)

        log_audit_event('TOPIC_COMPLETION_TOGGLE', f'/api/topics/{topic_id}/completion', {
            'student': student.roll_number,
            'topic_id': topic_id,
            'completed': is_completed,
            'new_subject_percentage': subj_percentage
        }, 'SUCCESS')

        return jsonify({
            'success': True,
            'topic_id': topic.id,
            'completed': is_completed,
            'role': 'student',
            'unit': {
                'unit_id': unit.id,
                'completed_topics': unit_done,
                'total_topics': unit_total,
                'percentage': unit_percentage
            },
            'subject': {
                'subject_id': subject.id,
                'code': subject.code,
                'completed_topics': subj_done_count,
                'remaining_topics': subj_remaining_count,
                'total_topics': subj_total,
                'completion_percentage': subj_percentage,
                'remaining_estimated_hours': round(remaining_hours, 1)
            }
        })

    elif current_user.is_faculty():
        faculty = current_user.faculty_profile
        if not faculty:
            return jsonify({'error': 'Faculty profile not found.'}), 404

        comp = FacultyTopicCompletion.query.filter_by(
            faculty_id=faculty.id,
            topic_id=topic.id,
            offering_id=offering_id
        ).first()

        if not comp:
            comp = FacultyTopicCompletion(
                faculty_id=faculty.id,
                topic_id=topic.id,
                offering_id=offering_id,
                is_completed=is_completed,
                completed_at=datetime.utcnow() if is_completed else None
            )
            db.session.add(comp)
        else:
            comp.is_completed = is_completed
            comp.completed_at = datetime.utcnow() if is_completed else None
            comp.updated_at = datetime.utcnow()

        db.session.commit()

        # Calculate faculty subject progress
        all_subject_topics = [t for u in subject.units for t in u.topics]
        subj_total = len(all_subject_topics)
        subj_topic_ids = [t.id for t in all_subject_topics]

        fac_done_count = FacultyTopicCompletion.query.filter(
            FacultyTopicCompletion.faculty_id == faculty.id,
            FacultyTopicCompletion.topic_id.in_(subj_topic_ids),
            FacultyTopicCompletion.is_completed == True
        ).count()

        unit_topic_ids = [t.id for t in unit.topics]
        unit_total = len(unit_topic_ids)
        unit_done = FacultyTopicCompletion.query.filter(
            FacultyTopicCompletion.faculty_id == faculty.id,
            FacultyTopicCompletion.topic_id.in_(unit_topic_ids),
            FacultyTopicCompletion.is_completed == True
        ).count()

        unit_percentage = round((unit_done / unit_total * 100), 1) if unit_total > 0 else 0.0
        subj_percentage = round((fac_done_count / subj_total * 100), 1) if subj_total > 0 else 0.0

        log_audit_event('FACULTY_TOPIC_COMPLETION_TOGGLE', f'/api/topics/{topic_id}/completion', {
            'faculty': faculty.employee_id,
            'topic_id': topic_id,
            'completed': is_completed,
            'new_subject_percentage': subj_percentage
        }, 'SUCCESS')

        return jsonify({
            'success': True,
            'topic_id': topic.id,
            'completed': is_completed,
            'role': 'faculty',
            'unit': {
                'unit_id': unit.id,
                'completed_topics': unit_done,
                'total_topics': unit_total,
                'percentage': unit_percentage
            },
            'subject': {
                'subject_id': subject.id,
                'code': subject.code,
                'completed_topics': fac_done_count,
                'total_topics': subj_total,
                'completion_percentage': subj_percentage
            }
        })
    else:
        return jsonify({'error': 'Unauthorized role for topic completion.'}), 403


@api_bp.route('/branches', methods=['GET'])
def get_branches():
    branches = Branch.query.order_by(Branch.name).all()
    return jsonify([{
        'id': b.id,
        'code': b.code,
        'name': b.name,
        'department_id': b.department_id
    } for b in branches])


@api_bp.route('/semesters', methods=['GET'])
def get_semesters():
    semesters = Semester.query.order_by(Semester.semester_number).all()
    return jsonify([{
        'id': s.id,
        'number': s.semester_number,
        'label': s.label,
        'year_id': s.academic_year_id
    } for s in semesters])


@api_bp.route('/subjects', methods=['GET'])
def get_subjects():
    branch_id = request.args.get('branch_id', type=int)
    semester_id = request.args.get('semester_id', type=int)
    
    query = Subject.query.filter_by(is_active=True)
    if branch_id:
        query = query.filter_by(branch_id=branch_id)
    if semester_id:
        query = query.filter_by(semester_id=semester_id)
        
    subjects = query.order_by(Subject.code).all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'credits': s.credits,
        'course_type': s.course_type,
        'units_count': len(s.units),
        'topics_count': s.total_topics_count,
        'total_hours': s.total_estimated_hours
    } for s in subjects])


@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    unread_only = request.args.get('unread', type=bool, default=False)
    query = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(is_read=False)
    notifications = query.order_by(Notification.created_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'category': n.category,
        'link_url': n.link_url,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d %b %Y, %H:%M')
    } for n in notifications])


@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notif = db.session.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        abort(404)
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})
