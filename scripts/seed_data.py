import sys
import os
from datetime import datetime, date, time, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User, Role, StudentProfile, FacultyProfile, HODProfile, PrincipalProfile
from app.models.academic import Department, Branch, AcademicYear, Semester, Section, Subject, SubjectOffering
from app.models.syllabus import Unit, Topic, TopicCompletion
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.assignments import Assignment, AssignmentSubmission
from app.models.timetable import Classroom, TimetableEntry
from app.models.calendar import AcademicCalendarEvent
from app.models.notifications import Notification


def seed_database():
    app = create_app('development')
    with app.app_context():
        print("Initializing Dhanekula Institute of Engineering and Technology (DIET) database schema...")
        db.create_all()

        # 1. Roles
        role_names = ['Student', 'Faculty', 'HOD', 'Principal', 'Admin']
        roles = {}
        for r_name in role_names:
            role = Role.query.filter_by(name=r_name).first()
            if not role:
                role = Role(name=r_name, description=f"{r_name} role for DIET portal")
                db.session.add(role)
                db.session.flush()
            roles[r_name] = role
        print("Roles initialized.")

        # 2. Departments
        departments_data = [
            ('CSE_DEPT', 'Department of Computer Science and Engineering', 'Computing, Software Systems & Artificial Intelligence'),
            ('IT_DEPT', 'Department of Information Technology', 'Information Systems, Networks & Web Technologies'),
            ('ECE_DEPT', 'Department of Electronics and Communication Engineering', 'Signals, VLSI, Embedded Systems & Telecommunication'),
            ('EEE_DEPT', 'Department of Electrical and Electronics Engineering', 'Power Systems, Control Engineering & Power Electronics'),
            ('CIVIL_DEPT', 'Department of Civil Engineering', 'Structural, Environmental & Geotechnical Engineering'),
            ('MECH_DEPT', 'Department of Mechanical Engineering', 'Thermal, Design & Manufacturing Engineering'),
            ('AGRI_DEPT', 'Department of Agricultural Engineering', 'Farm Machinery, Irrigation & Soil Conservation'),
            ('BSH_DEPT', 'Department of Basic Sciences and Humanities', 'Mathematics, Physics, Chemistry & Professional Communication')
        ]
        departments = {}
        for code, name, desc in departments_data:
            dept = Department.query.filter_by(code=code).first()
            if not dept:
                dept = Department(code=code, name=name, description=desc)
                db.session.add(dept)
                db.session.flush()
            departments[code] = dept
        print("Departments initialized.")

        # 3. Branches (9 Supported Branches)
        # Supported B.Tech branches.  Keep these codes stable because they are
        # used by syllabus imports, student profiles, APIs and filters.
        branches_data = [
            ('CSE', 'Computer Science and Engineering', 'CSE_DEPT'),
            ('AIML', 'CSE - Artificial Intelligence and Machine Learning', 'CSE_DEPT'),
            ('CSD', 'CSE - Data Science', 'CSE_DEPT'),
            ('CAD', 'CAD', 'CSE_DEPT'),
            ('IT', 'Information Technology', 'IT_DEPT'),
            ('ECE', 'Electronics and Communication Engineering', 'ECE_DEPT'),
            ('EEE', 'Electrical and Electronics Engineering', 'EEE_DEPT'),
            ('MECH', 'Mechanical Engineering', 'MECH_DEPT'),
            ('CIVIL', 'Civil Engineering', 'CIVIL_DEPT')
        ]
        # Migrate the older branch codes used by the prototype so an existing
        # database is upgraded instead of ending up with duplicate branches.
        legacy_branch_codes = {'CSE-AIML': 'AIML', 'CSE-DS': 'CSD', 'AGRI': 'CAD'}
        for old_code, new_code in legacy_branch_codes.items():
            legacy = Branch.query.filter_by(code=old_code).first()
            target = Branch.query.filter_by(code=new_code).first()
            if legacy and not target:
                legacy.code = new_code
                if new_code == 'AIML':
                    legacy.name = 'CSE - Artificial Intelligence and Machine Learning'
                elif new_code == 'CSD':
                    legacy.name = 'CSE - Data Science'
                else:
                    legacy.name = 'CAD'
                if new_code == 'CAD':
                    legacy.department_id = departments['CSE_DEPT'].id
                db.session.flush()

        branches = {}
        for code, name, dept_code in branches_data:
            b = Branch.query.filter_by(code=code).first()
            if not b:
                b = Branch(code=code, name=name, department_id=departments[dept_code].id, duration_years=4, total_semesters=8)
                db.session.add(b)
                db.session.flush()
            branches[code] = b
        print("9 Academic Branches initialized.")

        # 4. Academic Years (4 Years)
        years = {}
        for yr_num, label in [(1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year')]:
            ay = AcademicYear.query.filter_by(year_number=yr_num).first()
            if not ay:
                ay = AcademicYear(year_number=yr_num, label=label)
                db.session.add(ay)
                db.session.flush()
            years[yr_num] = ay

        # 5. Semesters (8 Semesters)
        semesters = {}
        for sem_num in range(1, 9):
            yr_num = (sem_num + 1) // 2
            sem = Semester.query.filter_by(semester_number=sem_num).first()
            if not sem:
                roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'][sem_num - 1]
                sem = Semester(semester_number=sem_num, academic_year_id=years[yr_num].id, label=f"Semester {roman}")
                db.session.add(sem)
                db.session.flush()
            semesters[sem_num] = sem
        print("4 Academic Years and 8 Semesters initialized.")

        # 6. Sections
        # Every branch is a four-year / eight-semester programme.  Seed the
        # complete branch-semester structure so every syllabus slot is
        # addressable even before an official syllabus PDF is imported.
        sections = {}
        for b_code, b_obj in branches.items():
            for s_num in range(1, 9):
                for sec_letter in ['A', 'B']:
                    sec = Section.query.filter_by(name=sec_letter, branch_id=b_obj.id, semester_id=semesters[s_num].id).first()
                    if not sec:
                        sec = Section(name=sec_letter, branch_id=b_obj.id, semester_id=semesters[s_num].id)
                        db.session.add(sec)
                        db.session.flush()
                    sections[f"{b_code}_S{s_num}_{sec_letter}"] = sec

        # 7. Classrooms
        classrooms_data = [
            ('LH-101', 'Main Academic Block', 70, 'Lecture Hall'),
            ('LH-102', 'Main Academic Block', 70, 'Lecture Hall'),
            ('LH-201', 'Main Academic Block', 70, 'Lecture Hall'),
            ('LAB-CSE1', 'Sir Visvesvaraya Computer Center', 60, 'Computer Lab'),
            ('LAB-ECE1', 'ECE Technology Block', 40, 'Electronics Lab'),
            ('AUD-01', 'K. L. N. Prasad Auditorium', 300, 'Seminar Hall')
        ]
        classrooms = {}
        for r_num, bldg, cap, r_type in classrooms_data:
            rm = Classroom.query.filter_by(room_number=r_num).first()
            if not rm:
                rm = Classroom(room_number=r_num, building=bldg, capacity=cap, room_type=r_type)
                db.session.add(rm)
                db.session.flush()
            classrooms[r_num] = rm

        # 8. User Accounts for Each Role
        # Demo Passwords for development/testing
        # Admin
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@diet.ac.in',
                full_name='Dr. K. Srinivas Rao (System Administrator)',
                role_id=roles['Admin'].id,
                is_active=True
            )
            admin_user.set_password('Admin@DIET2026')
            db.session.add(admin_user)

        # Principal
        principal_user = User.query.filter_by(username='principal').first()
        if not principal_user:
            principal_user = User(
                username='principal',
                email='principal@diet.ac.in',
                full_name='Dr. Ravi Kumar V (Principal)',
                role_id=roles['Principal'].id,
                is_active=True
            )
            principal_user.set_password('Principal@DIET2026')
            db.session.add(principal_user)
            db.session.flush()
            p_prof = PrincipalProfile(user_id=principal_user.id, employee_id='DIET-PRIN-001', phone='9848011223')
            db.session.add(p_prof)

        # HOD CSE
        hod_user = User.query.filter_by(username='hod_cse').first()
        if not hod_user:
            hod_user = User(
                username='hod_cse',
                email='hod_cse@diet.ac.in',
                full_name='Dr. B. Venkateswara Rao',
                role_id=roles['HOD'].id,
                is_active=True
            )
            hod_user.set_password('Hod@DIET2026')
            db.session.add(hod_user)
            db.session.flush()
            hod_prof = HODProfile(user_id=hod_user.id, employee_id='DIET-HOD-CSE', department_id=departments['CSE_DEPT'].id, phone='9848022334')
            db.session.add(hod_prof)

        # HOD ECE (For testing cross-department restriction)
        hod_ece_user = User.query.filter_by(username='hod_ece').first()
        if not hod_ece_user:
            hod_ece_user = User(
                username='hod_ece',
                email='hod_ece@diet.ac.in',
                full_name='Dr. G. Lakshmi Narayana',
                role_id=roles['HOD'].id,
                is_active=True
            )
            hod_ece_user.set_password('Hod@DIET2026')
            db.session.add(hod_ece_user)
            db.session.flush()
            hod_ece_prof = HODProfile(user_id=hod_ece_user.id, employee_id='DIET-HOD-ECE', department_id=departments['ECE_DEPT'].id, phone='9848033445')
            db.session.add(hod_ece_prof)

        # Faculty 1 (CSE)
        fac1_user = User.query.filter_by(username='faculty_cse1').first()
        if not fac1_user:
            fac1_user = User(
                username='faculty_cse1',
                email='fac_cse1@diet.ac.in',
                full_name='Prof. M. Suresh Kumar',
                role_id=roles['Faculty'].id,
                is_active=True
            )
            fac1_user.set_password('Faculty@DIET2026')
            db.session.add(fac1_user)
            db.session.flush()
            fac1_prof = FacultyProfile(user_id=fac1_user.id, employee_id='DIET-FAC-101', department_id=departments['CSE_DEPT'].id, designation='Associate Professor', qualification='M.Tech, Ph.D')
            db.session.add(fac1_prof)
        else:
            fac1_prof = fac1_user.faculty_profile

        # Faculty 2 (CSE)
        fac2_user = User.query.filter_by(username='faculty_cse2').first()
        if not fac2_user:
            fac2_user = User(
                username='faculty_cse2',
                email='fac_cse2@diet.ac.in',
                full_name='Prof. P. Anusha',
                role_id=roles['Faculty'].id,
                is_active=True
            )
            fac2_user.set_password('Faculty@DIET2026')
            db.session.add(fac2_user)
            db.session.flush()
            fac2_prof = FacultyProfile(user_id=fac2_user.id, employee_id='DIET-FAC-102', department_id=departments['CSE_DEPT'].id, designation='Assistant Professor', qualification='M.Tech')
            db.session.add(fac2_prof)
        else:
            fac2_prof = fac2_user.faculty_profile

        # Student 1 (CSE, 3rd Year, Sem 5, Sec A)
        student1_user = User.query.filter_by(username='21diet0501').first()
        if not student1_user:
            student1_user = User(
                username='21diet0501',
                email='21diet0501@diet.ac.in',
                full_name='Chaitanya Krishna',
                role_id=roles['Student'].id,
                is_active=True
            )
            student1_user.set_password('Student@DIET2026')
            db.session.add(student1_user)
            db.session.flush()
            student1_prof = StudentProfile(
                user_id=student1_user.id,
                roll_number='218T1A0501',
                branch_id=branches['CSE'].id,
                academic_year_id=years[3].id,
                semester_id=semesters[5].id,
                section_id=sections['CSE_S5_A'].id,
                admission_year=2021,
                phone='9848055667'
            )
            db.session.add(student1_prof)
        else:
            student1_prof = student1_user.student_profile

        # Student 2 (CSE, 3rd Year, Sem 5, Sec A) - For IDOR & Authorization testing
        student2_user = User.query.filter_by(username='21diet0502').first()
        if not student2_user:
            student2_user = User(
                username='21diet0502',
                email='21diet0502@diet.ac.in',
                full_name='Deepika Reddy',
                role_id=roles['Student'].id,
                is_active=True
            )
            student2_user.set_password('Student@DIET2026')
            db.session.add(student2_user)
            db.session.flush()
            student2_prof = StudentProfile(
                user_id=student2_user.id,
                roll_number='218T1A0502',
                branch_id=branches['CSE'].id,
                academic_year_id=years[3].id,
                semester_id=semesters[5].id,
                section_id=sections['CSE_S5_A'].id,
                admission_year=2021,
                phone='9848066778'
            )
            db.session.add(student2_prof)
        else:
            student2_prof = student2_user.student_profile

        db.session.commit()
        print("Sample User accounts created.")

        # 9. Realistic Curriculum Subjects & Topics (Clearly labeled DEMO DATA)
        # Seed Subjects for CSE Sem 5
        cse_sem5_subjects = [
            {
                'code': 'CS501PC',
                'name': 'Design and Analysis of Algorithms',
                'credits': 3.0,
                'type': 'Theory',
                'units': [
                    ('Unit I: Introduction & Divide and Conquer', [
                        ('Algorithm Definition, Pseudo-code conventions and Performance Analysis', 2.0),
                        ('Asymptotic Notations: Big O, Omega, Theta, Little o, Little omega', 2.0),
                        ('Divide and Conquer general method, Binary Search & Master Theorem', 2.5),
                        ('Merge Sort and Quick Sort with recurrence complexity analysis', 3.0)
                    ]),
                    ('Unit II: Greedy Method', [
                        ('General method, Knapsack Problem', 2.0),
                        ('Job Sequencing with Deadlines', 2.0),
                        ('Minimum Cost Spanning Trees: Prim’s and Kruskal’s algorithms', 3.0),
                        ('Single Source Shortest Paths: Dijkstra’s algorithm', 2.5)
                    ]),
                    ('Unit III: Dynamic Programming', [
                        ('General method, Principle of optimality', 1.5),
                        ('0/1 Knapsack Problem using dynamic programming', 2.5),
                        ('All-Pairs Shortest Paths: Floyd-Warshall algorithm', 2.5),
                        ('Traveling Salesperson Problem and Matrix Chain Multiplication', 3.0)
                    ]),
                    ('Unit IV: Backtracking & Branch and Bound', [
                        ('Backtracking General Method, 8-Queens Problem', 2.5),
                        ('Sum of Subsets problem and Graph Coloring', 2.0),
                        ('Branch and Bound: LC Branch and Bound, FIFO Search', 2.5),
                        ('0/1 Knapsack problem using Branch and Bound', 2.0)
                    ]),
                    ('Unit V: NP-Hard and NP-Complete Problems', [
                        ('Basic concepts: P, NP, NP-Hard, NP-Complete', 2.0),
                        ('Cook’s Theorem overview and non-deterministic algorithms', 2.0),
                        ('NP-Complete reductions: Clique, Vertex Cover, Hamiltonian Cycle', 2.5)
                    ])
                ]
            },
            {
                'code': 'CS502PC',
                'name': 'Database Management Systems',
                'credits': 3.0,
                'type': 'Theory',
                'units': [
                    ('Unit I: Database System Architecture', [
                        ('Introduction to DBMS, File Systems vs DBMS, Data Models', 2.0),
                        ('Three-Schema Architecture, Data Independence, DBMS Languages', 2.0),
                        ('Entity-Relationship (ER) Modeling: Entities, Attributes, Relationships', 2.5),
                        ('Enhanced ER (EER) modeling and converting ER diagrams to Relational Tables', 2.5)
                    ]),
                    ('Unit II: Relational Model & SQL', [
                        ('Relational Model Concepts, Integrity Constraints', 2.0),
                        ('Relational Algebra Operations: Select, Project, Join, Set Operations', 3.0),
                        ('SQL Data Definition (DDL) and Manipulation (DML) Commands', 2.5),
                        ('Complex SQL Queries: Nested Queries, Joins, Aggregation, Views', 3.0)
                    ]),
                    ('Unit III: Schema Refinement & Normalization', [
                        ('Functional Dependencies, Closure of Attribute Sets', 2.0),
                        ('Normal Forms: First, Second, and Third Normal Form (1NF, 2NF, 3NF)', 2.5),
                        ('Boyce-Codd Normal Form (BCNF), Decomposition properties', 2.5),
                        ('Multi-valued Dependencies and Fourth Normal Form (4NF)', 2.0)
                    ]),
                    ('Unit IV: Transaction Management & Concurrency Control', [
                        ('Transaction Concept, ACID Properties, Transaction States', 2.0),
                        ('Schedules, Serializability, Conflict and View Serializability', 2.5),
                        ('Concurrency Control Protocols: Two-Phase Locking (2PL)', 2.5),
                        ('Timestamp Ordering, Deadlock Handling and Prevention', 2.0)
                    ]),
                    ('Unit V: Storage and Indexing', [
                        ('Physical Storage Media, File Organization and RAID Levels', 2.0),
                        ('Indexing: Primary, Clustered, Non-clustered, Dense and Sparse Indexes', 2.0),
                        ('Tree-structured Indexing: B-Trees and B+ Trees Search & Insert', 2.5)
                    ])
                ]
            },
            {
                'code': 'CS503PC',
                'name': 'Computer Networks',
                'credits': 3.0,
                'type': 'Theory',
                'units': [
                    ('Unit I: Physical & Data Link Layer', [
                        ('Network Models: OSI Reference Model vs TCP/IP Suite', 2.0),
                        ('Framing, Error Detection and Correction (CRC, Hamming Code)', 2.5),
                        ('Flow Control Protocols: Stop-and-Wait, Go-Back-N, Selective Repeat', 3.0)
                    ]),
                    ('Unit II: Medium Access Control', [
                        ('Random Access Protocols: ALOHA, CSMA, CSMA/CD, CSMA/CA', 2.5),
                        ('Ethernet Standards (IEEE 802.3) and Wireless LAN (IEEE 802.11)', 2.5)
                    ]),
                    ('Unit III: Network Layer', [
                        ('IPv4 and IPv6 Addressing, Subnetting, CIDR Notation', 2.5),
                        ('Routing Algorithms: Distance Vector (Bellman-Ford), Link State (Dijkstra)', 3.0)
                    ]),
                    ('Unit IV: Transport Layer', [
                        ('Transport Protocols: UDP vs TCP Segment Headers', 2.0),
                        ('TCP Connection Management, Flow Control and Congestion Control', 2.5)
                    ]),
                    ('Unit V: Application Layer', [
                        ('Domain Name System (DNS), HTTP/HTTPS, FTP, SMTP and Email protocols', 2.5)
                    ])
                ]
            },
            {
                'code': 'CS504PC',
                'name': 'Software Engineering',
                'credits': 3.0,
                'type': 'Theory',
                'units': [
                    ('Unit I: Software Process Models', [
                        ('Software Process, SDLC, Waterfall, Spiral, Agile Scrum', 2.5),
                        ('Requirement Engineering, SRS Document preparation', 2.0)
                    ]),
                    ('Unit II: Architectural Design & UML', [
                        ('Software Architecture, Component-level Design, UML Class & Sequence Diagrams', 3.0)
                    ]),
                    ('Unit III: Testing Strategies', [
                        ('Black-box and White-box Testing, Unit, Integration and System Testing', 2.5)
                    ])
                ]
            },
            {
                'code': 'CS505PC',
                'name': 'Database Management Systems Laboratory',
                'credits': 1.5,
                'type': 'Lab',
                'units': [
                    ('Lab Experiments Part A: SQL DDL & DML', [
                        ('Creation of Tables with Primary Key and Foreign Key constraints', 2.0),
                        ('Execution of Complex SQL Queries with Joins and Aggregates', 2.0)
                    ]),
                    ('Lab Experiments Part B: PL/SQL & Triggers', [
                        ('PL/SQL Stored Procedures, Functions and Cursors', 3.0),
                        ('Database Triggers for automatic constraint enforcement and logging', 3.0)
                    ])
                ]
            }
        ]

        created_subjects = {}
        for s_info in cse_sem5_subjects:
            subj = Subject.query.filter_by(code=s_info['code'], branch_id=branches['CSE'].id, semester_id=semesters[5].id).first()
            if not subj:
                subj = Subject(
                    code=s_info['code'],
                    name=s_info['name'],
                    credits=s_info['credits'],
                    course_type=s_info['type'],
                    branch_id=branches['CSE'].id,
                    semester_id=semesters[5].id,
                    regulation='R20',
                    is_active=True,
                    is_demo_data=True  # Explicitly labeled DEMO DATA — NOT OFFICIAL SYLLABUS
                )
                db.session.add(subj)
                db.session.flush()

                for u_idx, (u_title, topics_list) in enumerate(s_info['units'], 1):
                    unit = Unit(
                        subject_id=subj.id,
                        unit_number=u_idx,
                        unit_title=u_title,
                        description=f"{u_title} for {subj.name} [DEMO DATA — NOT OFFICIAL SYLLABUS]"
                    )
                    db.session.add(unit)
                    db.session.flush()

                    for t_idx, (t_name, t_hrs) in enumerate(topics_list, 1):
                        topic = Topic(
                            unit_id=unit.id,
                            topic_number=t_idx,
                            topic_name=t_name,
                            description=f"{t_name} [DEMO DATA — NOT OFFICIAL SYLLABUS]",
                            estimated_hours=t_hrs
                        )
                        db.session.add(topic)

            created_subjects[s_info['code']] = subj

        # Also seed a sample subject for ECE to allow multi-branch testing
        ece_subj = Subject.query.filter_by(code='EC501PC', branch_id=branches['ECE'].id, semester_id=semesters[5].id).first()
        if not ece_subj:
            ece_subj = Subject(
                code='EC501PC',
                name='Digital Signal Processing',
                credits=3.0,
                course_type='Theory',
                branch_id=branches['ECE'].id,
                semester_id=semesters[5].id,
                regulation='R20',
                is_active=True,
                is_demo_data=True
            )
            db.session.add(ece_subj)
            db.session.flush()
            u1 = Unit(subject_id=ece_subj.id, unit_number=1, unit_title='Unit I: Discrete-Time Signals & Systems', description='DFT, FFT [DEMO DATA]')
            db.session.add(u1)
            db.session.flush()
            db.session.add(Topic(unit_id=u1.id, topic_number=1, topic_name='DFT and IDFT Properties', estimated_hours=2.0))

        db.session.commit()
        print("Curriculum subjects, units, and topics seeded.")

        # 10. Subject Offerings (Link Faculty to Subject + Section)
        offering_daa = SubjectOffering.query.filter_by(subject_id=created_subjects['CS501PC'].id, section_id=sections['CSE_S5_A'].id).first()
        if not offering_daa:
            offering_daa = SubjectOffering(
                subject_id=created_subjects['CS501PC'].id,
                faculty_id=fac1_prof.id,
                section_id=sections['CSE_S5_A'].id,
                academic_session='2026-2027',
                is_active=True
            )
            db.session.add(offering_daa)

        offering_dbms = SubjectOffering.query.filter_by(subject_id=created_subjects['CS502PC'].id, section_id=sections['CSE_S5_A'].id).first()
        if not offering_dbms:
            offering_dbms = SubjectOffering(
                subject_id=created_subjects['CS502PC'].id,
                faculty_id=fac2_prof.id,
                section_id=sections['CSE_S5_A'].id,
                academic_session='2026-2027',
                is_active=True
            )
            db.session.add(offering_dbms)

        db.session.commit()

        # 11. Student Topic Completion Seed for Student 1 (to have realistic initial progress)
        daa_topics = [t for u in created_subjects['CS501PC'].units for t in u.topics]
        # Mark first 4 topics of DAA completed
        for t in daa_topics[:4]:
            tc = TopicCompletion.query.filter_by(student_id=student1_prof.id, topic_id=t.id).first()
            if not tc:
                tc = TopicCompletion(student_id=student1_prof.id, topic_id=t.id, is_completed=True, completed_at=datetime.utcnow() - timedelta(days=2))
                db.session.add(tc)

        # 12. Attendance Sessions & Records
        att_session1 = AttendanceSession.query.filter_by(offering_id=offering_daa.id, session_date=date.today() - timedelta(days=2), period_number=1).first()
        if not att_session1:
            att_session1 = AttendanceSession(
                offering_id=offering_daa.id,
                faculty_id=fac1_prof.id,
                session_date=date.today() - timedelta(days=2),
                period_number=1,
                topic_covered='Divide and Conquer Method & Master Theorem',
                remarks='Good class participation'
            )
            db.session.add(att_session1)
            db.session.flush()

            # Mark Student 1 Present, Student 2 Present
            db.session.add(AttendanceRecord(session_id=att_session1.id, student_id=student1_prof.id, is_present=True))
            db.session.add(AttendanceRecord(session_id=att_session1.id, student_id=student2_prof.id, is_present=True))

        att_session2 = AttendanceSession.query.filter_by(offering_id=offering_dbms.id, session_date=date.today() - timedelta(days=1), period_number=2).first()
        if not att_session2:
            att_session2 = AttendanceSession(
                offering_id=offering_dbms.id,
                faculty_id=fac2_prof.id,
                session_date=date.today() - timedelta(days=1),
                period_number=2,
                topic_covered='Relational Model & Integrity Constraints',
                remarks='Covered foreign keys'
            )
            db.session.add(att_session2)
            db.session.flush()

            db.session.add(AttendanceRecord(session_id=att_session2.id, student_id=student1_prof.id, is_present=True))
            db.session.add(AttendanceRecord(session_id=att_session2.id, student_id=student2_prof.id, is_present=False, remarks='Medical leave'))

        # 13. Sample Assignment
        assign1 = Assignment.query.filter_by(offering_id=offering_daa.id, title='DAA Assignment 1: Asymptotic Analysis & Sorting').first()
        if not assign1:
            assign1 = Assignment(
                offering_id=offering_daa.id,
                faculty_id=fac1_prof.id,
                title='DAA Assignment 1: Asymptotic Analysis & Sorting',
                description='Solve the recurrence relations for Merge Sort and Quick Sort under worst/best cases. Submit handwritten or typed PDF.',
                max_marks=20.0,
                due_date=datetime.utcnow() + timedelta(days=5)
            )
            db.session.add(assign1)
            db.session.flush()

            # Seed Student 1 submission
            sub1 = AssignmentSubmission(
                assignment_id=assign1.id,
                student_id=student1_prof.id,
                submission_text='Submitted solutions for Questions 1-5 including recurrence tree diagrams.',
                submitted_at=datetime.utcnow() - timedelta(hours=4),
                marks_awarded=18.5,
                feedback='Excellent analysis and clear complexity proofs.',
                graded_by_id=fac1_user.id,
                graded_at=datetime.utcnow() - timedelta(hours=1)
            )
            db.session.add(sub1)

        # 14. Timetable Entries
        tt1 = TimetableEntry.query.filter_by(section_id=sections['CSE_S5_A'].id, day_of_week='Monday', period_number=1).first()
        if not tt1:
            tt1 = TimetableEntry(
                section_id=sections['CSE_S5_A'].id,
                subject_id=created_subjects['CS501PC'].id,
                faculty_id=fac1_prof.id,
                classroom_id=classrooms['LH-101'].id,
                day_of_week='Monday',
                period_number=1,
                start_time=time(9, 0),
                end_time=time(9, 50),
                academic_session='2026-2027'
            )
            db.session.add(tt1)

        tt2 = TimetableEntry.query.filter_by(section_id=sections['CSE_S5_A'].id, day_of_week='Monday', period_number=2).first()
        if not tt2:
            tt2 = TimetableEntry(
                section_id=sections['CSE_S5_A'].id,
                subject_id=created_subjects['CS502PC'].id,
                faculty_id=fac2_prof.id,
                classroom_id=classrooms['LH-101'].id,
                day_of_week='Monday',
                period_number=2,
                start_time=time(9, 50),
                end_time=time(10, 40),
                academic_session='2026-2027'
            )
            db.session.add(tt2)

        # 15. Academic Calendar Events
        events_data = [
            ('Commencement of Classwork (Odd Semester)', 'Official start of semester instruction for B.Tech II, III, IV years.', 'Semester Start', date(2026, 7, 15), date(2026, 7, 15)),
            ('Mid-Term Examination I', 'First internal assessment examinations across all engineering departments.', 'Internal Assessment', date(2026, 9, 22), date(2026, 9, 27)),
            ('Gandhi Jayanti (Institutional Holiday)', 'College holiday in observance of Gandhi Jayanti.', 'Holiday', date(2026, 10, 2), date(2026, 10, 2)),
            ('Technical Symposium - DIET DHYANAHITA 2026', 'National-level student technical paper presentation and project expo.', 'Workshop', date(2026, 10, 16), date(2026, 10, 17)),
            ('End Semester Practical Examinations', 'University laboratory examinations.', 'Examination', date(2026, 11, 20), date(2026, 11, 28))
        ]
        for title, desc, etype, sdate, edate in events_data:
            ev = AcademicCalendarEvent.query.filter_by(title=title).first()
            if not ev:
                ev = AcademicCalendarEvent(
                    title=title,
                    description=desc,
                    event_type=etype,
                    start_date=sdate,
                    end_date=edate,
                    created_by_id=admin_user.id
                )
                db.session.add(ev)

        # 16. Welcome Notifications
        notif1 = Notification(
            user_id=student1_user.id,
            title="Welcome to DIET Academic Planner",
            message="Track your semester syllabus, manage your study plans, and monitor attendance directly from your portal.",
            category="General"
        )
        db.session.add(notif1)

        db.session.commit()
        print("DIET Academic Planner database successfully seeded with complete operational data!")


if __name__ == '__main__':
    seed_database()
