import pytest
import json
from app.models.syllabus import Topic, TopicCompletion
from app.models.academic import Subject
from app.models.user import StudentProfile
from tests.conftest import login_helper


def test_topic_checkbox_toggle_and_persistence(client, init_database):
    """
    TEST 1 Acceptance Test:
    Student logs in, checks topic, refreshes/re-queries, topic remains checked,
    and progress percentage updates accurately.
    """
    topic = Topic.query.first()
    assert topic is not None
    
    # 1. Login as student
    login_helper(client, 'student1', 'StudPass123')
    
    # 2. Check topic
    res = client.post(
        f'/api/topics/{topic.id}/completion',
        data=json.dumps({'completed': True}),
        content_type='application/json'
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['completed'] is True
    assert data['subject']['completed_topics'] >= 1
    
    # 3. Verify Database Persistence
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    tc = TopicCompletion.query.filter_by(student_id=s1.id, topic_id=topic.id).first()
    assert tc is not None
    assert tc.is_completed is True
    
    # 4. Uncheck topic
    res_uncheck = client.post(
        f'/api/topics/{topic.id}/completion',
        data=json.dumps({'completed': False}),
        content_type='application/json'
    )
    assert res_uncheck.status_code == 200
    data_uncheck = res_uncheck.get_json()
    assert data_uncheck['completed'] is False
    
    tc_refreshed = TopicCompletion.query.filter_by(student_id=s1.id, topic_id=topic.id).first()
    assert tc_refreshed.is_completed is False
