import pytest
from app.models.user import StudentProfile
from tests.conftest import login_helper


def test_student_progress_pdf_report_generation(client, init_database):
    """
    TEST 8 Acceptance Test:
    Student generates progress report. PDF opens in browser / streams application/pdf and is downloadable.
    """
    s1 = StudentProfile.query.filter_by(roll_number='218T1A0501').first()
    login_helper(client, 'student1', 'StudPass123')
    
    # 1. Inline Browser View
    res_inline = client.get(f'/reports/student/{s1.id}/progress-pdf?download=0')
    assert res_inline.status_code == 200
    assert res_inline.headers['Content-Type'] == 'application/pdf'
    assert 'inline' in res_inline.headers['Content-Disposition']
    assert res_inline.data.startswith(b'%PDF')
    
    # 2. Attachment Download View
    res_download = client.get(f'/reports/student/{s1.id}/progress-pdf?download=1')
    assert res_download.status_code == 200
    assert res_download.headers['Content-Type'] == 'application/pdf'
    assert 'attachment' in res_download.headers['Content-Disposition']
    assert res_download.data.startswith(b'%PDF')
