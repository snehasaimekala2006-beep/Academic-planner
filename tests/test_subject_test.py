import pytest
import json
from app.models.syllabus import SubjectTestAttempt
from app.models.academic import Subject
from app.models.user import StudentProfile
from tests.conftest import login_helper


def test_subject_mastery_test_workflow(client, init_database):
    """
    Test student taking subject mastery test and receiving graded score & mastery badge.
    """
    subject = Subject.query.first()
    assert subject is not None

    login_helper(client, 'student1', 'StudPass123')

    # GET test page
    res_get = client.get(f'/student/subject/{subject.id}/test')
    assert res_get.status_code == 200
    assert b'Mastery Test' in res_get.data

    # POST answers
    res_post = client.post(f'/student/subject/{subject.id}/test', data={
        'q_1': '0',
        'q_2': '0'
    })
    assert res_post.status_code == 200
    assert b'Subject Mastery Status' in res_post.data

    # Verify attempt saved in DB
    student = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    attempt = SubjectTestAttempt.query.filter_by(student_id=student.id, subject_id=subject.id).first()
    assert attempt is not None
    assert attempt.score_percentage >= 0.0
    assert attempt.mastery_level is not None
