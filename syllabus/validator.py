import json
from datetime import datetime
from app.extensions import db
from app.models.syllabus import SyllabusImport, SyllabusValidation, Unit, Topic, SyllabusSource
from app.models.academic import Subject, Branch, Semester


def validate_and_activate_syllabus(import_id, validator_user_id, notes=None, custom_json=None):
    """
    Validates a pending syllabus import and commits the official subjects, units, and topics
    into the database, activating them for student planning and faculty tracking.
    """
    syllabus_import = db.session.get(SyllabusImport, import_id)
    if not syllabus_import:
        raise ValueError("SyllabusImport not found")
        
    source = syllabus_import.source
    data = json.loads(custom_json) if custom_json else json.loads(syllabus_import.raw_extracted_json)
    
    branch_id = data.get('branch_id') or source.branch_id
    semester_id = data.get('semester_id') or source.semester_id
    regulation = data.get('regulation') or source.regulation
    
    if not branch_id or not semester_id:
        raise ValueError("Branch and Semester must be specified for activation.")
        
    created_subjects = []
    
    for s_data in data.get('subjects', []):
        code = s_data.get('code', 'GEN-01').strip()
        name = s_data.get('name', 'Course Name').strip()
        credits = float(s_data.get('credits', 3.0))
        course_type = s_data.get('course_type', 'Theory')
        
        # Check if subject already exists
        subject = Subject.query.filter_by(
            code=code,
            branch_id=branch_id,
            semester_id=semester_id,
            regulation=regulation
        ).first()
        
        if not subject:
            subject = Subject(
                code=code,
                name=name,
                credits=credits,
                course_type=course_type,
                branch_id=branch_id,
                semester_id=semester_id,
                regulation=regulation,
                syllabus_source_id=source.id,
                is_active=True,
                is_demo_data=False
            )
            db.session.add(subject)
            db.session.flush()
        else:
            subject.name = name
            subject.credits = credits
            subject.course_type = course_type
            subject.syllabus_source_id = source.id
            subject.is_active = True
            subject.is_demo_data = False
            # Clear existing units to replace with validated official syllabus
            for existing_u in subject.units:
                db.session.delete(existing_u)
            db.session.flush()
            
        # Add Units & Topics
        for u_data in s_data.get('units', []):
            u_num = int(u_data.get('unit_number', 1))
            u_title = u_data.get('unit_title', f"Unit {u_num}").strip()
            u_desc = u_data.get('description', '')
            
            unit = Unit(
                subject_id=subject.id,
                unit_number=u_num,
                unit_title=u_title,
                description=u_desc
            )
            db.session.add(unit)
            db.session.flush()
            
            for t_data in u_data.get('topics', []):
                t_num = int(t_data.get('topic_number', 1))
                t_name = t_data.get('topic_name', f"Topic {t_num}").strip()
                t_desc = t_data.get('description', t_name)
                t_hours = float(t_data.get('estimated_hours', 1.0))
                
                topic = Topic(
                    unit_id=unit.id,
                    topic_number=t_num,
                    topic_name=t_name,
                    description=t_desc,
                    estimated_hours=t_hours
                )
                db.session.add(topic)
                
        created_subjects.append(subject)

    # Update status to VALIDATED
    syllabus_import.status = 'VALIDATED'
    
    # Record validation history
    val_record = SyllabusValidation.query.filter_by(import_id=syllabus_import.id).first()
    if not val_record:
        val_record = SyllabusValidation(
            import_id=syllabus_import.id,
            validated_by_id=validator_user_id,
            validated_at=datetime.utcnow(),
            validation_notes=notes or "Syllabus verified and activated by administrator.",
            is_active=True
        )
        db.session.add(val_record)
    else:
        val_record.validated_by_id = validator_user_id
        val_record.validated_at = datetime.utcnow()
        val_record.validation_notes = notes
        val_record.is_active = True
        
    db.session.commit()
    return created_subjects
