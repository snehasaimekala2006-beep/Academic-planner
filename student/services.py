from app.models.syllabus import Topic, TopicCompletion, Unit
from app.models.academic import Subject, SubjectOffering
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.assignments import Assignment, AssignmentSubmission


def get_student_syllabus_progress(student):
    """
    Computes real-time subject-by-subject and overall syllabus progress for a student.
    Strictly calculated from individual topic completion checkbox states.
    """
    subjects = Subject.query.filter_by(
        branch_id=student.branch_id,
        semester_id=student.semester_id,
        is_active=True
    ).all()
    
    # Fetch all completed topic ids for this student
    completions = TopicCompletion.query.filter_by(
        student_id=student.id,
        is_completed=True
    ).all()
    completed_topic_ids = {c.topic_id for c in completions}
    
    total_curriculum_topics = 0
    total_completed_topics = 0
    total_estimated_hours = 0.0
    total_remaining_hours = 0.0
    
    subject_progress_list = []
    
    for subj in subjects:
        subj_topics = [t for u in subj.units for t in u.topics]
        subj_total = len(subj_topics)
        subj_done = sum(1 for t in subj_topics if t.id in completed_topic_ids)
        subj_remaining = subj_total - subj_done
        subj_pct = round((subj_done / subj_total * 100), 1) if subj_total > 0 else 0.0
        
        subj_hours = sum(t.estimated_hours for t in subj_topics)
        subj_rem_hours = sum(t.estimated_hours for t in subj_topics if t.id not in completed_topic_ids)
        
        total_curriculum_topics += subj_total
        total_completed_topics += subj_done
        total_estimated_hours += subj_hours
        total_remaining_hours += subj_rem_hours
        
        # Unit breakdown
        unit_breakdown = []
        for unit in subj.units:
            u_topics = unit.topics
            u_total = len(u_topics)
            u_done = sum(1 for t in u_topics if t.id in completed_topic_ids)
            u_pct = round((u_done / u_total * 100), 1) if u_total > 0 else 0.0
            unit_breakdown.append({
                'unit_id': unit.id,
                'unit_number': unit.unit_number,
                'unit_title': unit.unit_title,
                'total_topics': u_total,
                'completed_topics': u_done,
                'percentage': u_pct
            })
            
        subject_progress_list.append({
            'subject_id': subj.id,
            'code': subj.code,
            'name': subj.name,
            'credits': subj.credits,
            'course_type': subj.course_type,
            'total_topics': subj_total,
            'completed_topics': subj_done,
            'remaining_topics': subj_remaining,
            'completion_percentage': subj_pct,
            'total_hours': round(subj_hours, 1),
            'remaining_hours': round(subj_rem_hours, 1),
            'units': unit_breakdown
        })
        
    overall_pct = round((total_completed_topics / total_curriculum_topics * 100), 1) if total_curriculum_topics > 0 else 0.0
    
    return {
        'total_topics': total_curriculum_topics,
        'completed_topics': total_completed_topics,
        'remaining_topics': total_curriculum_topics - total_completed_topics,
        'overall_percentage': overall_pct,
        'total_hours': round(total_estimated_hours, 1),
        'remaining_hours': round(total_remaining_hours, 1),
        'subjects': subject_progress_list
    }


def get_student_attendance_summary(student):
    """
    Calculates exact subject-wise and overall attendance percentage for a student.
    attendance_percentage = present_classes / total_classes * 100
    """
    records = AttendanceRecord.query.filter_by(student_id=student.id).all()
    total_classes = len(records)
    attended_classes = sum(1 for r in records if r.is_present)
    absent_classes = total_classes - attended_classes
    overall_percentage = round((attended_classes / total_classes * 100), 1) if total_classes > 0 else 0.0
    
    # Subject-wise
    subject_map = {}
    for r in records:
        offering = r.session.offering
        subj = offering.subject
        if subj.id not in subject_map:
            subject_map[subj.id] = {
                'subject_id': subj.id,
                'code': subj.code,
                'name': subj.name,
                'total_classes': 0,
                'present_classes': 0,
                'absent_classes': 0
            }
        subject_map[subj.id]['total_classes'] += 1
        if r.is_present:
            subject_map[subj.id]['present_classes'] += 1
        else:
            subject_map[subj.id]['absent_classes'] += 1
            
    for item in subject_map.values():
        t = item['total_classes']
        p = item['present_classes']
        item['percentage'] = round((p / t * 100), 1) if t > 0 else 0.0
        
    return {
        'total_classes': total_classes,
        'attended_classes': attended_classes,
        'absent_classes': absent_classes,
        'overall_percentage': overall_percentage,
        'subject_wise': list(subject_map.values())
    }


def get_student_assignments_summary(student):
    """
    Retrieves assignments and submissions for the student's current semester/branch.
    """
    subjects = Subject.query.filter_by(branch_id=student.branch_id, semester_id=student.semester_id).all()
    subject_ids = [s.id for s in subjects]
    
    offerings = SubjectOffering.query.filter(SubjectOffering.subject_id.in_(subject_ids)).all()
    offering_ids = [o.id for o in offerings]
    
    assignments = Assignment.query.filter(Assignment.offering_id.in_(offering_ids)).order_by(Assignment.due_date.asc()).all()
    
    submissions = {s.assignment_id: s for s in AssignmentSubmission.query.filter_by(student_id=student.id).all()}
    
    assignment_data = []
    for a in assignments:
        sub = submissions.get(a.id)
        assignment_data.append({
            'assignment': a,
            'is_submitted': sub is not None,
            'submission': sub,
            'is_graded': sub.marks_awarded is not None if sub else False
        })
        
    return assignment_data
