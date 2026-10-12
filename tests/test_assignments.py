import pytest
from datetime import datetime, timedelta
from app.models.academic import SubjectOffering
from app.models.assignments import Assignment, AssignmentSubmission
from tests.conftest import login_helper


def test_assignment_lifecycle(client, init_database):
    """
    TEST 4 Acceptance Test:
    Faculty creates assignment -> Student submits -> Faculty grades it -> Student sees marks and feedback.
    """
    offering = SubjectOffering.query.first()
    
    # 1. Faculty creates assignment
    login_helper(client, 'faculty_cse1', 'FacPass123')
    due = datetime.utcnow() + timedelta(days=7)
    res_create = client.post('/faculty/assignments/create', data={
        'offering_id': offering.id,
        'title': 'DAA Dynamic Programming Problem Set',
        'description': 'Solve 0/1 Knapsack problem using dynamic programming.',
        'max_marks': 25.0,
        'due_date': due.strftime('%Y-%m-%dT%H:%M')
    }, follow_redirects=True)
    assert res_create.status_code == 200
    
    assignment = Assignment.query.filter_by(title='DAA Dynamic Programming Problem Set').first()
    assert assignment is not None
    
    # 2. Student views and submits assignment
    login_helper(client, 'student1', 'StudPass123')
    res_assign_list = client.get('/student/assignments')
    assert res_assign_list.status_code == 200
    assert b'DAA Dynamic Programming Problem Set' in res_assign_list.data
    
    res_submit = client.post(f'/student/assignments/{assignment.id}', data={
        'submission_text': 'Completed dynamic programming table and code implementation.'
    }, follow_redirects=True)
    assert res_submit.status_code == 200
    assert b'received successfully' in res_submit.data
    
    submission = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).first()
    assert submission is not None
    assert submission.is_late is False
    
    # 3. Faculty grades submission
    login_helper(client, 'faculty_cse1', 'FacPass123')
    res_grade = client.post(f'/faculty/submissions/{submission.id}/grade', data={
        'marks': 24.0,
        'feedback': 'Excellent step-by-step optimal substructure proof.'
    }, follow_redirects=True)
    assert res_grade.status_code == 200
    
    from app.extensions import db
    submission_graded = db.session.get(AssignmentSubmission, submission.id)
    assert submission_graded.marks_awarded == 24.0
    assert submission_graded.feedback == 'Excellent step-by-step optimal substructure proof.'

    
    # 4. Student sees marks & feedback
    login_helper(client, 'student1', 'StudPass123')
    res_student_view = client.get(f'/student/assignments/{assignment.id}')
    assert res_student_view.status_code == 200
    assert b'24' in res_student_view.data
    assert b'Excellent step-by-step optimal substructure proof.' in res_student_view.data
