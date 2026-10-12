import hashlib
import json
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.syllabus import SyllabusSource, SyllabusImport, Unit, Topic
from app.models.academic import Subject, Branch, Semester


def compute_sha256(filepath):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_text_from_pdf(filepath):
    """Extract text from PDF using pypdf or resilient stream reader."""
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text += f"\n--- Page {page_idx + 1} ---\n" + page_text
        if text.strip():
            return text
    except Exception as e:
        pass

    # Fallback to pure byte stream text extraction
    try:
        with open(filepath, 'rb') as f:
            content = f.read().decode('latin-1', errors='ignore')
            clean_strings = re.findall(r'\(([^\(\)]+)\)\s*T[jJ]', content)
            if clean_strings:
                text = " ".join(clean_strings)
            else:
                text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
    except Exception:
        text = "Curriculum document extracted."
        
    return text


def parse_syllabus_text_to_structure(raw_text, default_branch=None, default_sem=None, default_reg='R20'):
    """
    Parses extracted syllabus text into structured JSON containing subjects, units, topics, hours.
    Preserves exact official units and titles.
    """
    lines = raw_text.splitlines()
    subjects = []
    
    current_subject = None
    current_unit = None
    
    course_header_pattern = re.compile(r'(?:Course Code|Subject Code|Code)\s*[:\-]?\s*([A-Z0-9\-]+)', re.IGNORECASE)
    unit_pattern = re.compile(r'^(?:UNIT\s*[-–—:]?\s*([I|V|X|0-9]+)|Unit\s+([0-9]+))[:\s]*(.*)$', re.IGNORECASE)
    general_subj_pattern = re.compile(r'([A-Z]{2,5}[0-9]{3,4}[A-Z]?)\s*[:\-–]\s*([A-Z\s\(\)&,]+)', re.IGNORECASE)

    unit_counter = 0
    topic_counter = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('--- Page'):
            continue
            
        code_match = course_header_pattern.search(line)
        gen_match = general_subj_pattern.match(line)
        
        if code_match:
            code = code_match.group(1).strip()
            title = line.replace(code_match.group(0), '').strip(' :-\t')
            if not title:
                title = f"Course {code}"
            
            current_subject = {
                'code': code,
                'name': title or f"Course {code}",
                'credits': 3.0,
                'course_type': 'Theory',
                'regulation': default_reg,
                'units': []
            }
            subjects.append(current_subject)
            current_unit = None
            unit_counter = 0
            continue
        elif gen_match and not current_subject:
            code = gen_match.group(1).strip()
            title = gen_match.group(2).strip()
            current_subject = {
                'code': code,
                'name': title,
                'credits': 3.0,
                'course_type': 'Theory',
                'regulation': default_reg,
                'units': []
            }
            subjects.append(current_subject)
            current_unit = None
            unit_counter = 0
            continue
            
        if not current_subject and unit_pattern.match(line):
            current_subject = {
                'code': f'SUBJ-{len(subjects)+1:02d}',
                'name': 'Extracted Curriculum Subject',
                'credits': 3.0,
                'course_type': 'Theory',
                'regulation': default_reg,
                'units': []
            }
            subjects.append(current_subject)
            
        unit_match = unit_pattern.match(line)
        if unit_match and current_subject:
            unit_roman_or_num = unit_match.group(1) or unit_match.group(2)
            unit_title = unit_match.group(3).strip()
            unit_counter += 1
            
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
            u_num = roman_map.get(str(unit_roman_or_num).upper(), unit_counter)
            
            current_unit = {
                'unit_number': u_num,
                'unit_title': unit_title or f"Unit {u_num}",
                'description': '',
                'topics': []
            }
            current_subject['units'].append(current_unit)
            topic_counter = 0
            continue
            
        if current_unit:
            if len(line) > 3 and not line.lower().startswith(('text books', 'reference books', 'outcomes', 'prerequisites', 'course objectives')):
                topic_candidates = [t.strip() for t in re.split(r'[;•\n]', line) if len(t.strip()) > 3]
                for tc in topic_candidates:
                    topic_counter += 1
                    current_unit['topics'].append({
                        'topic_number': topic_counter,
                        'topic_name': tc,
                        'description': tc,
                        'estimated_hours': 1.5
                    })

    if not subjects:
        subjects = [{
            'code': 'OFFICIAL-DOC',
            'name': 'Official Curriculum Syllabus Document',
            'credits': 3.0,
            'course_type': 'Theory',
            'regulation': default_reg,
            'units': [{
                'unit_number': 1,
                'unit_title': 'Section 1 - Content Overview (Pending Validation)',
                'description': 'Raw extracted text pending administrative structure validation.',
                'topics': [{
                    'topic_number': 1,
                    'topic_name': 'Curriculum Review & Topic Breakdown',
                    'description': raw_text[:300] + '...',
                    'estimated_hours': 2.0
                }]
            }]
        }]

    return {
        'regulation': default_reg,
        'branch_id': default_branch,
        'semester_id': default_sem,
        'subjects': subjects,
        'extracted_at': datetime.utcnow().isoformat()
    }


def process_syllabus_upload(file_storage, upload_folder, branch_id=None, semester_id=None, regulation='R20', academic_year_label=None, uploader_id=None):
    os.makedirs(upload_folder, exist_ok=True)
    orig_name = file_storage.filename
    sec_name = secure_filename(orig_name)
    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    stored_name = f"{timestamp_str}_{sec_name}"
    full_path = os.path.join(upload_folder, stored_name)
    
    file_storage.save(full_path)
    file_size = os.path.getsize(full_path)
    file_hash = compute_sha256(full_path)
    
    source = SyllabusSource(
        original_filename=orig_name,
        stored_filename=stored_name,
        file_hash=file_hash,
        file_size=file_size,
        upload_timestamp=datetime.utcnow(),
        branch_id=branch_id,
        semester_id=semester_id,
        regulation=regulation,
        academic_year_label=academic_year_label,
        uploaded_by_id=uploader_id,
        is_official=True
    )
    db.session.add(source)
    db.session.flush()
    
    raw_text = extract_text_from_pdf(full_path)
    structured_data = parse_syllabus_text_to_structure(raw_text, default_branch=branch_id, default_sem=semester_id, default_reg=regulation)
    
    syllabus_import = SyllabusImport(
        source_id=source.id,
        status='PENDING_VALIDATION',
        raw_extracted_json=json.dumps(structured_data, indent=2),
        extracted_at=datetime.utcnow()
    )
    db.session.add(syllabus_import)
    db.session.commit()
    
    return source, syllabus_import
