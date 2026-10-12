import sys
import os
import io
import pytest
from datetime import datetime, date, time, timedelta

# Add root project path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import (
    User, Role, StudentProfile, FacultyProfile, HODProfile, PrincipalProfile,
    Department, Branch, AcademicYear, Semester, Section, Subject, SubjectOffering,
    Unit, Topic, TopicCompletion, StudyPlan, StudyPlanTask,
    AttendanceSession, AttendanceRecord, Assignment, AssignmentSubmission,
    Classroom, TimetableEntry, AcademicCalendarEvent, Notification,
    SyllabusSource, SyllabusImport, SyllabusValidation
)


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def init_database(app):
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        # 1. Roles
        roles = {}
        for r_name in ['Student', 'Faculty', 'HOD', 'Principal', 'Admin']:
            role = Role(name=r_name, description=f"{r_name} role")
            db.session.add(role)
            roles[r_name] = role
        db.session.flush()

        # 2. Departments
        dept_cse = Department(code='CSE_DEPT', name='Department of Computer Science and Engineering')
        dept_ece = Department(code='ECE_DEPT', name='Department of Electronics and Communication Engineering')
        db.session.add_all([dept_cse, dept_ece])
        db.session.flush()

        # 3. Branches
        b_cse = Branch(code='CSE', name='Computer Science and Engineering', department_id=dept_cse.id)
        b_ece = Branch(code='ECE', name='Electronics and Communication Engineering', department_id=dept_ece.id)
        db.session.add_all([b_cse, b_ece])
        db.session.flush()

        # 4. Years & Semesters
        y3 = AcademicYear(year_number=3, label='3rd Year')
        db.session.add(y3)
        db.session.flush()

        sem5 = Semester(semester_number=5, academic_year_id=y3.id, label='Semester V')
        db.session.add(sem5)
        db.session.flush()

        # 5. Sections
        sec_a = Section(name='A', branch_id=b_cse.id, semester_id=sem5.id)
        sec_b = Section(name='B', branch_id=b_cse.id, semester_id=sem5.id)
        db.session.add_all([sec_a, sec_b])
        db.session.flush()

        # 6. Users
        admin = User(username='admin', email='admin@diet.ac.in', full_name='Admin User', role_id=roles['Admin'].id)
        admin.set_password('AdminPass123')
        
        principal = User(username='principal', email='principal@diet.ac.in', full_name='Dr. Principal', role_id=roles['Principal'].id)
        principal.set_password('PrinPass123')
        
        hod_cse = User(username='hod_cse', email='hod_cse@diet.ac.in', full_name='Dr. HOD CSE', role_id=roles['HOD'].id)
        hod_cse.set_password('HodPass123')

        hod_ece = User(username='hod_ece', email='hod_ece@diet.ac.in', full_name='Dr. HOD ECE', role_id=roles['HOD'].id)
        hod_ece.set_password('HodPass123')
        
        faculty1 = User(username='faculty_cse1', email='fac1@diet.ac.in', full_name='Prof. Suresh', role_id=roles['Faculty'].id)
        faculty1.set_password('FacPass123')

        student1 = User(username='student1', email='student1@diet.ac.in', full_name='Student One', role_id=roles['Student'].id)
        student1.set_password('StudPass123')

        student2 = User(username='student2', email='student2@diet.ac.in', full_name='Student Two', role_id=roles['Student'].id)
        student2.set_password('StudPass123')

        db.session.add_all([admin, principal, hod_cse, hod_ece, faculty1, student1, student2])
        db.session.flush()

        # Profiles
        p_prof = PrincipalProfile(user_id=principal.id, employee_id='EMP-P01')
        h_prof = HODProfile(user_id=hod_cse.id, employee_id='EMP-H01', department_id=dept_cse.id)
        h_ece_prof = HODProfile(user_id=hod_ece.id, employee_id='EMP-H02', department_id=dept_ece.id)
        f_prof = FacultyProfile(user_id=faculty1.id, employee_id='EMP-F01', department_id=dept_cse.id, designation='Assistant Professor')
        
        s1_prof = StudentProfile(
            user_id=student1.id, roll_number='218T1A0501', branch_id=b_cse.id,
            academic_year_id=y3.id, semester_id=sem5.id, section_id=sec_a.id, admission_year=2021
        )
        s2_prof = StudentProfile(
            user_id=student2.id, roll_number='218T1A0502', branch_id=b_cse.id,
            academic_year_id=y3.id, semester_id=sem5.id, section_id=sec_a.id, admission_year=2021
        )
        db.session.add_all([p_prof, h_prof, h_ece_prof, f_prof, s1_prof, s2_prof])
        db.session.flush()

        # Subjects
        subj_daa = Subject(
            code='CS501PC', name='Design and Analysis of Algorithms',
            credits=3.0, course_type='Theory', branch_id=b_cse.id,
            semester_id=sem5.id, regulation='R20', is_active=True
        )
        db.session.add(subj_daa)
        db.session.flush()

        # Units & Topics
        u1 = Unit(subject_id=subj_daa.id, unit_number=1, unit_title='Unit I: Divide and Conquer')
        u2 = Unit(subject_id=subj_daa.id, unit_number=2, unit_title='Unit II: Greedy Method')
        db.session.add_all([u1, u2])
        db.session.flush()

        t1 = Topic(unit_id=u1.id, topic_number=1, topic_name='Binary Search Analysis', estimated_hours=2.0)
        t2 = Topic(unit_id=u1.id, topic_number=2, topic_name='Merge Sort & Recurrences', estimated_hours=3.0)
        t3 = Topic(unit_id=u2.id, topic_number=1, topic_name='Knapsack Problem', estimated_hours=2.0)
        t4 = Topic(unit_id=u2.id, topic_number=2, topic_name='Dijkstra Algorithm', estimated_hours=2.5)
        db.session.add_all([t1, t2, t3, t4])
        db.session.flush()

        # Subject Offering
        offering = SubjectOffering(
            subject_id=subj_daa.id, faculty_id=f_prof.id,
            section_id=sec_a.id, academic_session='2026-2027'
        )
        db.session.add(offering)

        # Classroom
        room = Classroom(room_number='LH-101', building='Main Block', capacity=70)
        db.session.add(room)

        db.session.commit()
        yield db


def login_helper(client, username, password):
    client.get('/logout', follow_redirects=True)
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

