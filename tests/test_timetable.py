import pytest
from datetime import time
from app.models.academic import Section, Subject
from app.models.user import FacultyProfile
from app.models.timetable import Classroom, TimetableEntry
from tests.conftest import login_helper


def test_timetable_conflict_rejection(client, init_database):
    """
    TEST 11 Acceptance Test:
    Two timetable entries conflict. System rejects the conflicting entry.
    """
    sec = Section.query.first()
    subj = Subject.query.first()
    faculty = FacultyProfile.query.first()
    room = Classroom.query.first()
    
    login_helper(client, 'admin', 'AdminPass123')
    
    # 1. Add first slot (Monday, Period 1)
    res1 = client.post('/admin/timetable', data={
        'section_id': sec.id,
        'subject_id': subj.id,
        'faculty_id': faculty.id,
        'classroom_id': room.id,
        'day_of_week': 'Monday',
        'period_number': 1,
        'academic_session': '2026-2027'
    }, follow_redirects=True)
    assert res1.status_code == 200
    assert b'scheduled successfully' in res1.data
    
    # 2. Attempt to add conflicting slot with same section on Monday Period 1
    res_conflict = client.post('/admin/timetable', data={
        'section_id': sec.id,
        'subject_id': subj.id,
        'faculty_id': faculty.id,
        'classroom_id': room.id,
        'day_of_week': 'Monday',
        'period_number': 1,
        'academic_session': '2026-2027'
    }, follow_redirects=True)
    assert res_conflict.status_code == 200
    assert b'Conflict Error' in res_conflict.data
