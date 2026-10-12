import csv
import io
from app.models.attendance import AttendanceRecord
from app.models.assignments import AssignmentSubmission


def export_attendance_csv(session_id=None, branch_id=None):
    """Generates CSV byte string of attendance records."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record ID', 'Student Roll Number', 'Student Name', 'Branch', 'Subject Code', 'Date', 'Period', 'Status', 'Remarks'])
    
    query = AttendanceRecord.query
    if session_id:
        query = query.filter_by(session_id=session_id)
        
    records = query.all()
    for r in records:
        student = r.student
        session = r.session
        subj = session.offering.subject
        writer.writerow([
            r.id,
            student.roll_number,
            student.user.full_name,
            student.branch.code,
            subj.code,
            session.session_date.strftime('%Y-%m-%d'),
            session.period_number,
            'Present' if r.is_present else 'Absent',
            r.remarks or ''
        ])
        
    output.seek(0)
    return output.getvalue().encode('utf-8')
