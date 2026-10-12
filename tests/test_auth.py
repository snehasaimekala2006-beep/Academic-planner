import pytest
from app.models.user import User
from tests.conftest import login_helper


def test_password_hashing(init_database):
    user = User(username='test_user', email='test@diet.ac.in', full_name='Test', role_id=1)
    user.set_password('Secret123')
    assert user.check_password('Secret123') is True
    assert user.check_password('WrongPass') is False
    assert user.password_hash != 'Secret123'


def test_valid_login_and_redirect(client, init_database):
    # Test student login
    res = login_helper(client, 'student1', 'StudPass123')
    assert res.status_code == 200
    assert b'Student Dashboard' in res.data or b'Student One' in res.data


def test_invalid_login(client, init_database):
    res = login_helper(client, 'student1', 'WrongPassword')
    assert res.status_code == 200
    assert b'Invalid username/ID or password' in res.data


def test_logout(client, init_database):
    login_helper(client, 'student1', 'StudPass123')
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b'You have been securely logged out' in res.data


def test_student_registration_success(client, init_database):
    res = client.get('/logout', follow_redirects=True)
    res = client.get('/register/student')
    assert res.status_code == 200
    assert b'Student Portal Registration' in res.data

    post_data = {
        'full_name': 'Registered Student',
        'username': 'new_student_01',
        'email': 'new_student01@diet.ac.in',
        'roll_number': '24DIET9999',
        'branch_id': '1',
        'academic_year_id': '1',
        'semester_id': '1',
        'section_id': '1',
        'admission_year': '2024',
        'phone': '9876543210',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }
    res = client.post('/register/student', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'Welcome to DIET Academic Portal, Registered Student!' in res.data
    assert b'Student Dashboard' in res.data


def test_faculty_registration_success(client, init_database):
    res = client.get('/logout', follow_redirects=True)
    res = client.get('/register/faculty')
    assert res.status_code == 200
    assert b'Faculty Portal Registration' in res.data

    post_data = {
        'full_name': 'Dr. New Faculty',
        'username': 'new_fac_01',
        'email': 'new_faculty01@diet.ac.in',
        'employee_id': 'EMP-NEW-999',
        'department_id': '1',
        'designation': 'Assistant Professor',
        'qualification': 'Ph.D in AI',
        'phone': '9876543211',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }
    res = client.post('/register/faculty', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'Welcome Professor Dr. New Faculty!' in res.data
    assert b'Faculty Dashboard' in res.data


def test_duplicate_registration_rejection(client, init_database):
    res = client.get('/logout', follow_redirects=True)
    # Attempt duplicate username
    post_data = {
        'full_name': 'Duplicate User',
        'username': 'student1',  # already exists in seed data
        'email': 'unique_email@diet.ac.in',
        'roll_number': '24DIET0000',
        'branch_id': '1',
        'academic_year_id': '1',
        'semester_id': '1',
        'admission_year': '2024',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }
    res = client.post('/register/student', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'Username is already taken' in res.data
