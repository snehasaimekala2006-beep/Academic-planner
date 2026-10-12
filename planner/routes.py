from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app.auth.services import role_required, student_owner_required, log_audit_event
from app.extensions import db
from app.models.planner import StudyPlan, StudyPlanTask
from app.models.academic import Subject
from app.planner.engine import build_and_save_study_plan
from app.planner.fallback import reschedule_missed_tasks_deterministic

planner_bp = Blueprint('planner', __name__, url_prefix='/planner')


@planner_bp.route('/')
@login_required
def index():
    if current_user.is_student():
        student = current_user.student_profile
        active_plan = StudyPlan.query.filter_by(student_id=student.id, is_active=True).first()
        all_plans = StudyPlan.query.filter_by(student_id=student.id).order_by(StudyPlan.created_at.desc()).all()
        return render_template('planner/student_planner.html', active_plan=active_plan, all_plans=all_plans)
    elif current_user.is_faculty():
        return redirect(url_for('faculty.teaching_planner'))
    else:
        return redirect(url_for('main.index'))


@planner_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def create():
    student = current_user.student_profile
    semester_subjects = Subject.query.filter_by(branch_id=student.branch_id, semester_id=student.semester_id, is_active=True).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject_ids = request.form.getlist('subject_ids', type=int)
        start_date_str = request.form.get('start_date')
        target_date_str = request.form.get('target_date')
        exam_date_str = request.form.get('exam_date')
        
        hours_per_day = float(request.form.get('available_hours_per_day', 3.0))
        days_per_week = int(request.form.get('days_per_week', 6))
        study_time = request.form.get('preferred_study_time', 'Evening')
        revision_pref = bool(request.form.get('revision_preference'))
        practice_pref = bool(request.form.get('practice_preference'))
        use_ai = bool(request.form.get('use_ai'))
        
        if not subject_ids:
            flash('Please select at least one subject for your study plan.', 'danger')
            return render_template('planner/create_plan.html', subjects=semester_subjects)
            
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date() if exam_date_str else None
            
            if start_date >= target_date:
                flash('Target date must be strictly after start date.', 'danger')
                return render_template('planner/create_plan.html', subjects=semester_subjects)
                
            plan = build_and_save_study_plan(
                student=student,
                title=title,
                subject_ids=subject_ids,
                start_date=start_date,
                target_date=target_date,
                exam_date=exam_date,
                available_hours_per_day=hours_per_day,
                days_per_week=days_per_week,
                preferred_study_time=study_time,
                revision_preference=revision_pref,
                practice_preference=practice_pref,
                use_ai=use_ai
            )
            log_audit_event('STUDY_PLAN_CREATED', f'/planner/{plan.id}', {'title': plan.title, 'tasks': len(plan.tasks)}, 'SUCCESS')
            flash(f'Study Plan "{plan.title}" generated successfully with {len(plan.tasks)} organized study tasks!', 'success')
            return redirect(url_for('planner.view_plan', plan_id=plan.id))
        except Exception as e:
            flash(f'Failed to generate study plan: {str(e)}', 'danger')
            
    return render_template('planner/create_plan.html', subjects=semester_subjects)


@planner_bp.route('/<int:plan_id>')
@login_required
def view_plan(plan_id):
    plan = db.session.get(StudyPlan, plan_id)
    if not plan:
        abort(404)
        
    if current_user.is_student() and plan.student_id != current_user.student_profile.id:
        abort(403)
        
    # Group tasks by date
    tasks_by_date = {}
    for task in plan.tasks:
        d = task.task_date
        if d not in tasks_by_date:
            tasks_by_date[d] = []
        tasks_by_date[d].append(task)
        
    sorted_dates = sorted(tasks_by_date.keys())
    return render_template('planner/view_plan.html', plan=plan, tasks_by_date=tasks_by_date, sorted_dates=sorted_dates)


@planner_bp.route('/<int:plan_id>/reschedule', methods=['POST'])
@login_required
@role_required('Student')
def reschedule_plan(plan_id):
    plan = db.session.get(StudyPlan, plan_id)
    if not plan or plan.student_id != current_user.student_profile.id:
        abort(403)
        
    count = reschedule_missed_tasks_deterministic(plan)
    db.session.commit()
    log_audit_event('STUDY_PLAN_RESCHEDULED', f'/planner/{plan.id}/reschedule', {'rescheduled_count': count}, 'SUCCESS')
    flash(f'Successfully rescheduled {count} missed task(s) evenly across future study dates!', 'success')
    return redirect(url_for('planner.view_plan', plan_id=plan.id))


@planner_bp.route('/task/<int:task_id>/status', methods=['POST'])
@login_required
@role_required('Student')
def update_task_status(task_id):
    task = db.session.get(StudyPlanTask, task_id)
    if not task or task.study_plan.student_id != current_user.student_profile.id:
        abort(403)
        
    new_status = request.form.get('status')
    if new_status in ['PENDING', 'COMPLETED', 'MISSED', 'RESCHEDULED']:
        task.status = new_status
        if new_status == 'COMPLETED':
            task.completed_at = datetime.utcnow()
            # If linked to a topic, mark topic completed as well
            if task.topic_id:
                from app.models.syllabus import TopicCompletion
                tc = TopicCompletion.query.filter_by(student_id=current_user.student_profile.id, topic_id=task.topic_id).first()
                if not tc:
                    tc = TopicCompletion(student_id=current_user.student_profile.id, topic_id=task.topic_id, is_completed=True, completed_at=datetime.utcnow())
                    db.session.add(tc)
                else:
                    tc.is_completed = True
                    tc.completed_at = datetime.utcnow()
        db.session.commit()
        log_audit_event('STUDY_TASK_STATUS_UPDATED', f'/planner/task/{task.id}', {'new_status': new_status}, 'SUCCESS')
        
    return redirect(request.referrer or url_for('planner.view_plan', plan_id=task.study_plan_id))
