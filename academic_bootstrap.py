"""Idempotent academic-structure bootstrap for DIET's supported B.Tech branches."""
from app.extensions import db
from app.models.academic import Department, Branch, AcademicYear, Semester, Section

BRANCHES = [
    ('CSE', 'Computer Science and Engineering', 'CSE_DEPT'),
    ('AIML', 'CSE - Artificial Intelligence and Machine Learning', 'CSE_DEPT'),
    ('CSD', 'CSE - Data Science', 'CSE_DEPT'),
    ('CAD', 'Computer-Aided Design', 'CSE_DEPT'),
    ('IT', 'Information Technology', 'IT_DEPT'),
    ('ECE', 'Electronics and Communication Engineering', 'ECE_DEPT'),
    ('EEE', 'Electrical and Electronics Engineering', 'EEE_DEPT'),
    ('MECH', 'Mechanical Engineering', 'MECH_DEPT'),
    ('CIVIL', 'Civil Engineering', 'CIVIL_DEPT'),
]

LEGACY_CODES = {'CSE-AIML': 'AIML', 'CSE-DS': 'CSD'}


def ensure_academic_structure():
    """Create/migrate the branch + 8-semester skeleton without creating fake subjects."""
    # This is intentionally limited to structural records. Official syllabus
    # subjects must come from validated institutional syllabus imports.
    for old_code, new_code in LEGACY_CODES.items():
        old = Branch.query.filter_by(code=old_code).first()
        new = Branch.query.filter_by(code=new_code).first()
        if old and not new:
            old.code = new_code
            old.name = dict((c, n) for c, n, _ in BRANCHES)[new_code]
            db.session.flush()

    departments = {}
    for code, name, desc in [
        ('CSE_DEPT', 'Department of Computer Science and Engineering', 'Computing, Software Systems & Artificial Intelligence'),
        ('IT_DEPT', 'Department of Information Technology', 'Information Systems, Networks & Web Technologies'),
        ('ECE_DEPT', 'Department of Electronics and Communication Engineering', 'Signals, VLSI, Embedded Systems & Telecommunication'),
        ('EEE_DEPT', 'Department of Electrical and Electronics Engineering', 'Power Systems, Control Engineering & Power Electronics'),
        ('CIVIL_DEPT', 'Department of Civil Engineering', 'Structural, Environmental & Geotechnical Engineering'),
        ('MECH_DEPT', 'Department of Mechanical Engineering', 'Thermal, Design & Manufacturing Engineering'),
    ]:
        dept = Department.query.filter_by(code=code).first()
        if not dept:
            dept = Department(code=code, name=name, description=desc)
            db.session.add(dept)
            db.session.flush()
        departments[code] = dept

    branches = {}
    for code, name, dept_code in BRANCHES:
        branch = Branch.query.filter_by(code=code).first()
        if not branch:
            branch = Branch(code=code, name=name, department_id=departments[dept_code].id,
                            duration_years=4, total_semesters=8)
            db.session.add(branch)
            db.session.flush()
        else:
            branch.name = name
            branch.duration_years = 4
            branch.total_semesters = 8
            branch.department_id = departments[dept_code].id
        branches[code] = branch

    years = {}
    for n, label in [(1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year')]:
        year = AcademicYear.query.filter_by(year_number=n).first()
        if not year:
            year = AcademicYear(year_number=n, label=label)
            db.session.add(year)
            db.session.flush()
        years[n] = year

    semesters = {}
    romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
    for n in range(1, 9):
        sem = Semester.query.filter_by(semester_number=n).first()
        if not sem:
            sem = Semester(semester_number=n, academic_year_id=years[(n + 1)//2].id,
                           label=f'Semester {romans[n-1]}')
            db.session.add(sem)
            db.session.flush()
        semesters[n] = sem

    for branch in branches.values():
        for n in range(1, 9):
            for section_name in ('A', 'B'):
                exists = Section.query.filter_by(name=section_name, branch_id=branch.id,
                                                 semester_id=semesters[n].id).first()
                if not exists:
                    db.session.add(Section(name=section_name, branch_id=branch.id,
                                           semester_id=semesters[n].id))

    db.session.commit()
    return branches, semesters
