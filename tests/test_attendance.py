import pytest
from datetime import date
from app.models.academic import SubjectOffering
from app.models.user import StudentProfile, FacultyProfile
from app.models.attendance import AttendanceSession, AttendanceRecord
from tests.conftest import login_helper


def test_faculty_marks_attendance_and_student_sees_update(client, init_database):
    """
    TEST 3 Acceptance Test:
    Faculty marks attendance. Student logs in. Student sees updated attendance percentage.
    """
    offering = SubjectOffering.query.first()
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    s2 = StudentProfile.query.filter_by(roll_number='218T1A0502').first()
    
    # 1. Login as faculty
    login_helper(client, 'faculty_cse1', 'FacPass123')
    
    # 2. Mark attendance (s1 Present, s2 Absent)
    att_date = date(2026, 9, 20)
    post_data = {
        'offering_id': offering.id,
        'session_date': att_date.strftime('%Y-%m-%d'),
        'period_number': 3,
        'topic_covered': 'Master Theorem and Recurrence Analysis',
        'remarks': 'Class test discussion',
        f'student_{s1.id}': 'present',
        f'student_{s2.id}': 'absent'
    }
    res = client.post('/faculty/attendance/take', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'Attendance successfully recorded' in res.data
    
    # 3. Verify session in database
    session = AttendanceSession.query.filter_by(offering_id=offering.id, session_date=att_date, period_number=3).first()
    assert session is not None
    assert session.present_students_count == 1
    assert session.total_students == 2
    
    # 4. Student 1 logs in and checks attendance page
    login_helper(client, 'student1', 'StudPass123')
    res_student = client.get('/student/attendance')
    assert res_student.status_code == 200
    assert b'100.0%' in res_student.data or b'Master Theorem' in res_student.data


def test_duplicate_attendance_prevention(client, init_database):
    offering = SubjectOffering.query.first()
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    
    login_helper(client, 'faculty_cse1', 'FacPass123')
    att_date = date(2026, 9, 21)
    
    # Post first session
    client.post('/faculty/attendance/take', data={
        'offering_id': offering.id,
        'session_date': att_date.strftime('%Y-%m-%d'),
        'period_number': 1,
        'topic_covered': 'Intro',
        f'student_{s1.id}': 'present'
    }, follow_redirects=True)
    
    # Post duplicate session for same offering, date, and period
    res_dup = client.post('/faculty/attendance/take', data={
        'offering_id': offering.id,
        'session_date': att_date.strftime('%Y-%m-%d'),
        'period_number': 1,
        'topic_covered': 'Intro Duplicate',
        f'student_{s1.id}': 'present'
    }, follow_redirects=True)
    
    assert b'already exists' in res_dup.data
