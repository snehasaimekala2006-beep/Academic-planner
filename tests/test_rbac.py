import pytest
from app.models.user import StudentProfile
from app.models.academic import Department
from tests.conftest import login_helper


def test_student_cannot_access_another_student_profile(client, init_database):
    """
    TEST 2 Acceptance Test:
    Student 1 attempts to access Student 2's direct profile URL (/student/<student2_id>).
    Server must enforce strict IDOR protection and return 403 Forbidden.
    """
    s2 = StudentProfile.query.filter_by(roll_number='218T1A0502').first()
    assert s2 is not None
    
    # Login as student1
    login_helper(client, 'student1', 'StudPass123')
    
    # Student 1 attempts to access Student 2 ID
    res = client.get(f'/student/{s2.id}')
    assert res.status_code == 403


def test_student_can_access_own_profile(client, init_database):
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    assert s1 is not None
    
    login_helper(client, 'student1', 'StudPass123')
    res = client.get(f'/student/{s1.id}')
    assert res.status_code == 200
    assert b'218T1A0501' in res.data


def test_hod_cannot_access_unauthorized_department(client, init_database):
    """
    TEST 5 Acceptance Test:
    HOD CSE attempts to access ECE department restricted endpoint (/hod/department/<ece_dept_id>).
    Server must return 403 Forbidden.
    """
    dept_ece = Department.query.filter_by(code='ECE_DEPT').first()
    assert dept_ece is not None
    
    # Login as HOD CSE
    login_helper(client, 'hod_cse', 'HodPass123')
    
    # Attempt to access ECE department restricted URL
    res = client.get(f'/hod/department/{dept_ece.id}')
    assert res.status_code == 403


def test_principal_can_access_institutional_dashboard(client, init_database):
    """
    TEST 6 Acceptance Test:
    Principal logs in and sees institution-level analytics.
    """
    login_helper(client, 'principal', 'PrinPass123')
    res = client.get('/principal/dashboard')
    assert res.status_code == 200
    assert b'Principal Dashboard' in res.data or b'OFFICE OF THE PRINCIPAL' in res.data


def test_admin_access_allowed(client, init_database):
    login_helper(client, 'admin', 'AdminPass123')
    res = client.get('/admin/dashboard')
    assert res.status_code == 200
    assert b'Admin Dashboard' in res.data
