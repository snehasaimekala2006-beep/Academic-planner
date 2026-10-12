import os
from app import create_app, db
from app.models import (
    User, Role, StudentProfile, FacultyProfile, HODProfile, PrincipalProfile,
    Department, Branch, AcademicYear, Semester, Section, Subject, SubjectOffering,
    SyllabusSource, SyllabusImport, SyllabusValidation, Unit, Topic, TopicCompletion,
    StudyPlan, StudyPlanTask, FacultyTeachingPlan, TeachingPlanWeek,
    AttendanceSession, AttendanceRecord, Assignment, AssignmentSubmission,
    Classroom, TimetableEntry, AcademicCalendarEvent, Notification, AuditLog
)

env_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(env_name)


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'StudentProfile': StudentProfile,
        'FacultyProfile': FacultyProfile,
        'HODProfile': HODProfile,
        'PrincipalProfile': PrincipalProfile,
        'Department': Department,
        'Branch': Branch,
        'AcademicYear': AcademicYear,
        'Semester': Semester,
        'Section': Section,
        'Subject': Subject,
        'SubjectOffering': SubjectOffering,
        'Unit': Unit,
        'Topic': Topic,
        'TopicCompletion': TopicCompletion,
        'StudyPlan': StudyPlan,
        'StudyPlanTask': StudyPlanTask,
        'AttendanceSession': AttendanceSession,
        'AttendanceRecord': AttendanceRecord,
        'Assignment': Assignment,
        'AssignmentSubmission': AssignmentSubmission,
        'TimetableEntry': TimetableEntry,
        'AuditLog': AuditLog
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from app.academic_bootstrap import ensure_academic_structure
        ensure_academic_structure()
    app.run(host='0.0.0.0', port=5000, debug=True)
