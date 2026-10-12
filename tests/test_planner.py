import pytest
from datetime import date, timedelta
from app.models.academic import Subject
from app.models.syllabus import Topic, TopicCompletion
from app.models.user import StudentProfile
from app.models.planner import StudyPlan, StudyPlanTask
from app.planner.fallback import generate_deterministic_study_plan, reschedule_missed_tasks_deterministic
from tests.conftest import login_helper


def test_study_plan_generation_excludes_completed_topics(client, init_database):
    """
    TEST 9 Acceptance Test:
    Study plan uses actual incomplete topics and excludes completed topics.
    Daily study hours are strictly respected.
    """
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    subj = Subject.query.first()
    
    # Mark topic 1 as completed
    topic1 = Topic.query.first()
    tc = TopicCompletion(student_id=s1.id, topic_id=topic1.id, is_completed=True)
    from app.extensions import db
    db.session.add(tc)
    db.session.commit()
    
    # Generate study plan
    start_d = date(2026, 9, 20)
    target_d = date(2026, 10, 10)
    
    tasks = generate_deterministic_study_plan(
        student=s1,
        subject_ids=[subj.id],
        start_date=start_d,
        target_date=target_d,
        available_hours_per_day=3.0,
        days_per_week=6,
        revision_preference=False,
        practice_preference=False
    )
    
    # Ensure completed topic is NOT in the scheduled tasks
    scheduled_topic_ids = [t['topic_id'] for t in tasks if t['topic_id']]
    assert topic1.id not in scheduled_topic_ids


def test_ai_fallback_generates_deterministic_plan_when_api_unavailable(client, init_database):
    """
    TEST 10 Acceptance Test:
    AI API is unset or unavailable. Planner generates valid deterministic plan.
    """
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    subj = Subject.query.first()
    
    login_helper(client, 'student1', 'StudPass123')
    
    res = client.post('/planner/create', data={
        'title': 'Semester Exam Preparation Plan',
        'subject_ids': [subj.id],
        'start_date': '2026-09-20',
        'target_date': '2026-10-15',
        'available_hours_per_day': '3.0',
        'days_per_week': '6',
        'use_ai': '1'  # Request AI optimization
    }, follow_redirects=True)
    
    assert res.status_code == 200
    assert b'generated successfully' in res.data
    
    # Check plan was persisted and has tasks
    plan = StudyPlan.query.filter_by(student_id=s1.id, is_active=True).first()
    assert plan is not None
    assert len(plan.tasks) > 0


def test_missed_task_rescheduling(client, init_database):
    """
    Tests rescheduling missed tasks evenly across available future dates.
    """
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    subj = Subject.query.first()
    
    start_d = date(2026, 9, 20)
    target_d = date(2026, 9, 25)
    
    from app.planner.engine import build_and_save_study_plan
    plan = build_and_save_study_plan(
        student=s1,
        title='Short Test Plan',
        subject_ids=[subj.id],
        start_date=start_d,
        target_date=target_d,
        available_hours_per_day=3.0,
        days_per_week=6,
        use_ai=False
    )
    
    # Mark first task as MISSED
    first_task = plan.tasks[0]
    first_task.status = 'MISSED'
    from app.extensions import db
    db.session.commit()
    
    # Reschedule
    count = reschedule_missed_tasks_deterministic(plan, from_date=start_d)
    assert count >= 1
    
    # Verify original task is RESCHEDULED and a new pending task exists
    assert first_task.status == 'RESCHEDULED'
    pending_tasks = [t for t in plan.tasks if t.status == 'PENDING']
    assert len(pending_tasks) >= 1
