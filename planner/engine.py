from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.planner import StudyPlan, StudyPlanTask
from app.planner.ai import generate_ai_study_plan
from app.planner.fallback import generate_deterministic_study_plan, reschedule_missed_tasks_deterministic


def build_and_save_study_plan(student, title, subject_ids, start_date, target_date, exam_date=None,
                              available_hours_per_day=3.0, days_per_week=6, preferred_study_time='Evening',
                              revision_preference=True, practice_preference=True, use_ai=False):
    """
    Main entry point for generating study plans.
    Attempts AI generation if requested and configured; falls back gracefully to deterministic scheduler.
    Persists the plan and all individual tasks to the database.
    """
    plan_tasks_data = []
    is_ai_successful = False
    
    if use_ai:
        try:
            plan_tasks_data = generate_ai_study_plan(
                student=student,
                subject_ids=subject_ids,
                start_date=start_date,
                target_date=target_date,
                available_hours_per_day=available_hours_per_day,
                days_per_week=days_per_week,
                revision_preference=revision_preference,
                practice_preference=practice_preference
            )
            if plan_tasks_data:
                is_ai_successful = True
        except Exception as e:
            current_app.logger.warning(f"AI planner encountered an issue ({str(e)}). Falling back to deterministic planner.")
            
    if not plan_tasks_data:
        # Run deterministic engine
        plan_tasks_data = generate_deterministic_study_plan(
            student=student,
            subject_ids=subject_ids,
            start_date=start_date,
            target_date=target_date,
            available_hours_per_day=available_hours_per_day,
            days_per_week=days_per_week,
            revision_preference=revision_preference,
            practice_preference=practice_preference,
            preferred_study_time=preferred_study_time
        )

    # Deactivate previous active plans if creating a new active one
    StudyPlan.query.filter_by(student_id=student.id, is_active=True).update({'is_active': False})

    study_plan = StudyPlan(
        student_id=student.id,
        title=title or f"Study Plan ({start_date.strftime('%d %b')} - {target_date.strftime('%d %b %Y')})",
        start_date=start_date,
        target_date=target_date,
        exam_date=exam_date,
        available_hours_per_day=available_hours_per_day,
        days_per_week=days_per_week,
        preferred_study_time=preferred_study_time,
        revision_preference=revision_preference,
        practice_preference=practice_preference,
        is_ai_generated=is_ai_successful,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(study_plan)
    db.session.flush()

    for td in plan_tasks_data:
        task = StudyPlanTask(
            study_plan_id=study_plan.id,
            task_date=td['task_date'],
            subject_id=td['subject_id'],
            unit_id=td.get('unit_id'),
            topic_id=td.get('topic_id'),
            task_type=td.get('task_type', 'Learn'),
            duration_hours=td.get('duration_hours', 1.0),
            break_duration_minutes=td.get('break_duration_minutes', 15),
            status=td.get('status', 'PENDING'),
            reason_notes=td.get('reason_notes', '')
        )
        db.session.add(task)

    db.session.commit()
    return study_plan
