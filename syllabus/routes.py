import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_login import login_required, current_user
from app.auth.services import role_required, log_audit_event
from app.extensions import db
from app.models.syllabus import SyllabusSource, SyllabusImport, SyllabusValidation, Unit, Topic
from app.models.academic import Branch, Semester, Subject
from app.syllabus.importer import process_syllabus_upload
from app.syllabus.validator import validate_and_activate_syllabus

syllabus_bp = Blueprint('syllabus', __name__, url_prefix='/syllabus')


@syllabus_bp.route('/repair-academic-structure', methods=['POST'])
@login_required
@role_required('Admin')
def repair_academic_structure():
    from app.academic_bootstrap import ensure_academic_structure
    try:
        ensure_academic_structure()
        flash('Academic structure synchronized: 9 branches × 8 semesters. Official subjects still require validated syllabus imports.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Academic structure repair failed: {exc}', 'danger')
    return redirect(url_for('syllabus.index'))


@syllabus_bp.route('/')
@login_required
def index():
    branches = Branch.query.order_by(Branch.name).all()
    semesters = Semester.query.order_by(Semester.semester_number).all()
    
    selected_branch_id = request.args.get('branch_id', type=int)
    selected_sem_id = request.args.get('semester_id', type=int)
    
    query = Subject.query.filter_by(is_active=True)
    if selected_branch_id:
        query = query.filter_by(branch_id=selected_branch_id)
    if selected_sem_id:
        query = query.filter_by(semester_id=selected_sem_id)
        
    subjects = query.order_by(Subject.code).all()
    
    return render_template('syllabus/index.html', 
                           branches=branches, 
                           semesters=semesters, 
                           subjects=subjects,
                           selected_branch_id=selected_branch_id,
                           selected_sem_id=selected_sem_id)


@syllabus_bp.route('/subject/<int:subject_id>')
@login_required
def subject_detail(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        abort(404)
        
    # Retrieve completion status map for student or faculty
    completion_map = {}
    if current_user.is_student() and current_user.student_profile:
        from app.models.syllabus import TopicCompletion
        completions = TopicCompletion.query.filter_by(student_id=current_user.student_profile.id).all()
        completion_map = {c.topic_id: c.is_completed for c in completions}
    elif current_user.is_faculty() and current_user.faculty_profile:
        from app.models.syllabus import FacultyTopicCompletion
        completions = FacultyTopicCompletion.query.filter_by(faculty_id=current_user.faculty_profile.id).all()
        completion_map = {c.topic_id: c.is_completed for c in completions}
        
    return render_template('syllabus/subject_detail.html', subject=subject, completion_map=completion_map)


@syllabus_bp.route('/upload', methods=['GET', 'POST'], endpoint='upload')
@syllabus_bp.route('/upload-syllabus', methods=['GET', 'POST'], endpoint='upload_syllabus')
@login_required
@role_required('Admin')
def upload_syllabus():
    branches = Branch.query.order_by(Branch.name).all()
    semesters = Semester.query.order_by(Semester.semester_number).all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part selected.', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for upload.', 'danger')
            return redirect(request.url)
            
        branch_id = request.form.get('branch_id', type=int)
        semester_id = request.form.get('semester_id', type=int)
        regulation = request.form.get('regulation', 'R20')
        academic_year_label = request.form.get('academic_year_label', '2026-2027')
        
        if not file.filename.lower().endswith('.pdf'):
            flash('Only official PDF syllabus files are accepted.', 'danger')
            return redirect(request.url)
            
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'syllabus')
        try:
            source, s_import = process_syllabus_upload(
                file_storage=file,
                upload_folder=upload_folder,
                branch_id=branch_id,
                semester_id=semester_id,
                regulation=regulation,
                academic_year_label=academic_year_label,
                uploader_id=current_user.id
            )
            log_audit_event('SYLLABUS_UPLOADED', f'/syllabus/upload (Source={source.id})', {
                'filename': source.original_filename,
                'hash': source.file_hash,
                'size': source.file_size
            }, 'SUCCESS')
            flash(f'Official Syllabus PDF uploaded successfully! Status: PENDING VALIDATION (Hash: {source.file_hash[:12]}...)', 'success')
            return redirect(url_for('syllabus.review_import', import_id=s_import.id))
        except Exception as e:
            current_app.logger.error(f"Syllabus upload error: {str(e)}")
            flash(f'Failed to process syllabus PDF: {str(e)}', 'danger')
            
    return render_template('syllabus/upload.html', branches=branches, semesters=semesters)


@syllabus_bp.route('/imports')
@login_required
@role_required('Admin')
def list_imports():
    imports = SyllabusImport.query.order_by(SyllabusImport.extracted_at.desc()).all()
    return render_template('syllabus/imports_list.html', imports=imports)


@syllabus_bp.route('/imports/<int:import_id>/review', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def review_import(import_id):
    s_import = db.session.get(SyllabusImport, import_id)
    if not s_import:
        abort(404)
        
    branches = Branch.query.order_by(Branch.name).all()
    semesters = Semester.query.order_by(Semester.semester_number).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes', '')
        custom_json = request.form.get('raw_json')
        
        if action == 'validate':
            try:
                subjects = validate_and_activate_syllabus(
                    import_id=import_id,
                    validator_user_id=current_user.id,
                    notes=notes,
                    custom_json=custom_json
                )
                log_audit_event('SYLLABUS_VALIDATED', f'/syllabus/imports/{import_id}/review', {
                    'subjects_activated': [s.code for s in subjects],
                    'validator': current_user.username
                }, 'SUCCESS')
                flash(f'Successfully validated and activated {len(subjects)} subjects from official syllabus!', 'success')
                return redirect(url_for('syllabus.list_imports'))
            except Exception as e:
                flash(f'Validation failed: {str(e)}', 'danger')
        elif action == 'reject':
            s_import.status = 'REJECTED'
            db.session.commit()
            log_audit_event('SYLLABUS_REJECTED', f'/syllabus/imports/{import_id}/review', {'notes': notes}, 'SUCCESS')
            flash('Syllabus import marked as REJECTED.', 'warning')
            return redirect(url_for('syllabus.list_imports'))
            
    return render_template('syllabus/review_import.html', 
                           s_import=s_import, 
                           raw_json=s_import.raw_extracted_json,
                           branches=branches,
                           semesters=semesters)


@syllabus_bp.route('/download-source/<int:source_id>')
@login_required
def download_source_file(source_id):
    source = db.session.get(SyllabusSource, source_id)
    if not source:
        abort(404)
        
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'syllabus')
    file_path = os.path.join(upload_folder, source.stored_filename)
    if not os.path.exists(file_path):
        abort(404)
        
    return send_file(file_path, as_attachment=True, download_name=source.original_filename)
