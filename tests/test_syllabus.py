import io
import json
import pytest
from app.models.syllabus import SyllabusSource, SyllabusImport, Unit, Topic
from app.models.academic import Branch, Semester, Subject, Section
from tests.conftest import login_helper


def test_official_syllabus_pdf_upload_and_validation(client, init_database):
    """
    TEST 7 Acceptance Test:
    Admin uploads official syllabus PDF. System stores filename, hash, timestamp, regulation,
    validation status (PENDING_VALIDATION). Admin validates and activates.
    """
    b = Branch.query.first()
    sem = Semester.query.first()
    
    # 1. Admin uploads syllabus PDF
    login_helper(client, 'admin', 'AdminPass123')
    
    pdf_content = b"%PDF-1.4 Course Code: CS509PC Title: Advanced Cloud Architecture UNIT I: Cloud Virtualization Topic: Hypervisors Topic: Containerization"
    pdf_file = (io.BytesIO(pdf_content), "official_cloud_curriculum.pdf")
    
    res = client.post('/syllabus/upload', data={
        'file': pdf_file,
        'branch_id': b.id,
        'semester_id': sem.id,
        'regulation': 'R20',
        'academic_year_label': '2026-2027'
    }, content_type='multipart/form-data', follow_redirects=True)
    
    assert res.status_code == 200
    
    # 2. Verify SyllabusSource and SyllabusImport
    source = SyllabusSource.query.filter_by(original_filename='official_cloud_curriculum.pdf').first()
    assert source is not None
    assert source.file_hash is not None
    assert len(source.file_hash) == 64  # Valid SHA-256 hex string
    assert source.regulation == 'R20'
    assert source.is_official is True
    
    s_import = SyllabusImport.query.filter_by(source_id=source.id).first()
    assert s_import is not None
    assert s_import.status == 'PENDING_VALIDATION'
    
    # 3. Admin Validates & Activates
    res_val = client.post(f'/syllabus/imports/{s_import.id}/review', data={
        'action': 'validate',
        'notes': 'Verified against official academic senate board resolution.',
        'raw_json': s_import.raw_extracted_json
    }, follow_redirects=True)
    assert res_val.status_code == 200
    
    from app.extensions import db
    s_import_refreshed = db.session.get(SyllabusImport, s_import.id)
    assert s_import_refreshed.status == 'VALIDATED'



def test_supported_academic_structure_has_9_branches_and_8_semesters(app):
    from app.academic_bootstrap import ensure_academic_structure, BRANCHES
    with app.app_context():
        ensure_academic_structure()
        branches = Branch.query.filter(Branch.code.in_([b[0] for b in BRANCHES])).all()
        assert len(branches) == 9
        assert Semester.query.count() >= 8
        for branch in branches:
            assert branch.duration_years == 4
            assert branch.total_semesters == 8
            assert Section.query.filter_by(branch_id=branch.id).count() >= 16
