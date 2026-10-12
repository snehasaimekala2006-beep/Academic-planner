import math
from datetime import datetime, timedelta
from app.models.syllabus import Topic, TopicCompletion, Unit
from app.models.academic import Subject


def generate_deterministic_study_plan(student, subject_ids, start_date, target_date, available_hours_per_day=3.0, 
                                      days_per_week=6, revision_preference=True, practice_preference=True, 
                                      break_duration_minutes=15, preferred_study_time='Evening', include_completed=False):
    """
    Generates a realistic, conflict-free, deterministic daily study plan for a student.
    Excludes already completed topics unless include_completed/revision is explicitly requested.
    Interleaves subjects intelligently and distributes topics fairly across days while strictly respecting available_hours_per_day.
    """
    if start_date >= target_date:
        raise ValueError("Target date must be after start date.")
        
    # 1. Fetch topics
    completions = {c.topic_id: c.is_completed for c in TopicCompletion.query.filter_by(student_id=student.id).all()}
    selected_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).order_by(Subject.code).all()
    
    # Collect tasks per subject for balanced round-robin interleaving
    subject_task_queues = {subj.id: [] for subj in selected_subjects}
    
    for subj in selected_subjects:
        for unit in subj.units:
            unit_topics_added = 0
            for topic in unit.topics:
                is_done = completions.get(topic.id, False)
                if not is_done or include_completed:
                    # Learn Task
                    subject_task_queues[subj.id].append({
                        'subject_id': subj.id,
                        'subject_name': subj.name,
                        'unit_id': unit.id,
                        'unit_title': unit.unit_title,
                        'topic_id': topic.id,
                        'topic_name': topic.topic_name,
                        'task_type': 'Learn',
                        'duration_hours': topic.estimated_hours,
                        'reason_notes': f"Core curriculum: {subj.code} - {topic.topic_name}"
                    })
                    unit_topics_added += 1
                    
                    # Practice Task if preferred
                    if practice_preference and topic.estimated_hours >= 1.5:
                        subject_task_queues[subj.id].append({
                            'subject_id': subj.id,
                            'subject_name': subj.name,
                            'unit_id': unit.id,
                            'unit_title': unit.unit_title,
                            'topic_id': topic.id,
                            'topic_name': topic.topic_name,
                            'task_type': 'Practice',
                            'duration_hours': round(min(topic.estimated_hours * 0.5, 1.5), 1),
                            'reason_notes': f"Hands-on exercises & problem solving for {topic.topic_name}"
                        })
            
            # Add unit revision block at the end of each unit if requested
            if revision_preference and unit_topics_added > 0:
                subject_task_queues[subj.id].append({
                    'subject_id': subj.id,
                    'subject_name': subj.name,
                    'unit_id': unit.id,
                    'unit_title': unit.unit_title,
                    'topic_id': None,
                    'topic_name': f"Unit {unit.unit_number} Comprehensive Revision",
                    'task_type': 'Revision',
                    'duration_hours': 1.5,
                    'reason_notes': f"Review, formula recap & self-assessment for {unit.unit_title}"
                })

    # Interleave tasks across subjects in round-robin fashion
    tasks_to_schedule = []
    has_more = True
    while has_more:
        has_more = False
        for subj in selected_subjects:
            if subject_task_queues[subj.id]:
                tasks_to_schedule.append(subject_task_queues[subj.id].pop(0))
                if subject_task_queues[subj.id]:
                    has_more = True

    # 2. Base start hour for preferred study time
    time_offsets = {
        'Early Morning': (6, 0),
        'Morning': (9, 0),
        'Afternoon': (14, 0),
        'Evening': (17, 30),
        'Night': (21, 0)
    }
    base_hour, base_minute = time_offsets.get(preferred_study_time, (17, 30))

    # 3. Schedule across available calendar days
    scheduled_tasks = []
    current_date = start_date
    task_idx = 0
    total_tasks = len(tasks_to_schedule)
    
    while current_date <= target_date and task_idx < total_tasks:
        # Respect weekly rest day (e.g. skip Sunday if 6 days/week, skip Sat/Sun if 5 days/week)
        if days_per_week == 5 and current_date.weekday() in [5, 6]:
            current_date += timedelta(days=1)
            continue
        elif days_per_week == 6 and current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue
            
        daily_accumulated_hours = 0.0
        current_minute_offset = base_hour * 60 + base_minute
        
        while task_idx < total_tasks and (daily_accumulated_hours + tasks_to_schedule[task_idx]['duration_hours']) <= available_hours_per_day:
            task_info = tasks_to_schedule[task_idx]
            task_dur = task_info['duration_hours']
            
            # Time slot formatting
            start_h = int(current_minute_offset // 60) % 24
            start_m = int(current_minute_offset % 60)
            end_minutes = current_minute_offset + int(task_dur * 60)
            end_h = int(end_minutes // 60) % 24
            end_m = int(end_minutes % 60)
            time_slot_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
            
            notes = task_info['reason_notes']
            if not notes.startswith('['):
                notes = f"[{time_slot_str}] {notes}"

            scheduled_tasks.append({
                'task_date': current_date,
                'subject_id': task_info['subject_id'],
                'unit_id': task_info['unit_id'],
                'topic_id': task_info['topic_id'],
                'task_type': task_info['task_type'],
                'duration_hours': task_dur,
                'break_duration_minutes': break_duration_minutes,
                'reason_notes': notes,
                'status': 'PENDING'
            })
            daily_accumulated_hours += task_dur
            current_minute_offset = end_minutes + break_duration_minutes
            task_idx += 1
            
        if daily_accumulated_hours == 0.0 and task_idx < total_tasks:
            task_info = tasks_to_schedule[task_idx]
            task_dur = min(task_info['duration_hours'], available_hours_per_day)
            
            start_h = int(current_minute_offset // 60) % 24
            start_m = int(current_minute_offset % 60)
            end_minutes = current_minute_offset + int(task_dur * 60)
            end_h = int(end_minutes // 60) % 24
            end_m = int(end_minutes % 60)
            time_slot_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
            
            notes = task_info['reason_notes']
            if not notes.startswith('['):
                notes = f"[{time_slot_str}] {notes}"

            scheduled_tasks.append({
                'task_date': current_date,
                'subject_id': task_info['subject_id'],
                'unit_id': task_info['unit_id'],
                'topic_id': task_info['topic_id'],
                'task_type': task_info['task_type'],
                'duration_hours': task_dur,
                'break_duration_minutes': break_duration_minutes,
                'reason_notes': notes,
                'status': 'PENDING'
            })
            task_idx += 1
            
        current_date += timedelta(days=1)

    return scheduled_tasks


def reschedule_missed_tasks_deterministic(study_plan, from_date=None):
    """
    Finds all MISSED tasks in a study plan and redistributes them into remaining future days
    without overloading daily study hours.
    """
    from_date = from_date or datetime.utcnow().date()
    
    # 1. Identify missed tasks
    missed_tasks = [t for t in study_plan.tasks if t.status == 'MISSED' or (t.status == 'PENDING' and t.task_date < from_date)]
    if not missed_tasks:
        return 0
        
    # Mark them as RESCHEDULED
    for mt in missed_tasks:
        mt.status = 'RESCHEDULED'
        
    # 2. Identify available dates up to target_date
    current_date = max(from_date, study_plan.start_date)
    target_date = study_plan.target_date
    
    # Calculate current daily workload on future dates
    future_workload = {}
    for t in study_plan.tasks:
        if t.status == 'PENDING' and t.task_date >= current_date:
            future_workload[t.task_date] = future_workload.get(t.task_date, 0.0) + t.duration_hours
            
    # Redistribute
    rescheduled_count = 0
    for mt in missed_tasks:
        allocated = False
        scan_date = current_date
        while scan_date <= target_date:
            # Skip Sundays if days_per_week <= 6
            if study_plan.days_per_week < 7 and scan_date.weekday() == 6:
                scan_date += timedelta(days=1)
                continue
                
            used = future_workload.get(scan_date, 0.0)
            if (used + mt.duration_hours) <= study_plan.available_hours_per_day:
                # Add new task
                from app.models.planner import StudyPlanTask
                new_task = StudyPlanTask(
                    study_plan_id=study_plan.id,
                    task_date=scan_date,
                    subject_id=mt.subject_id,
                    unit_id=mt.unit_id,
                    topic_id=mt.topic_id,
                    task_type=mt.task_type,
                    duration_hours=mt.duration_hours,
                    break_duration_minutes=mt.break_duration_minutes,
                    status='PENDING',
                    reason_notes=f"Rescheduled from {mt.task_date}"
                )
                from app.extensions import db
                db.session.add(new_task)
                future_workload[scan_date] = used + mt.duration_hours
                allocated = True
                rescheduled_count += 1
                break
            scan_date += timedelta(days=1)
            
        # If target date exceeded, schedule on next available day extending slightly
        if not allocated:
            scan_date = max(target_date + timedelta(days=1), current_date)
            from app.models.planner import StudyPlanTask
            new_task = StudyPlanTask(
                study_plan_id=study_plan.id,
                task_date=scan_date,
                subject_id=mt.subject_id,
                unit_id=mt.unit_id,
                topic_id=mt.topic_id,
                task_type=mt.task_type,
                duration_hours=mt.duration_hours,
                break_duration_minutes=mt.break_duration_minutes,
                status='PENDING',
                reason_notes=f"Rescheduled from {mt.task_date} (Extended schedule)"
            )
            from app.extensions import db
            db.session.add(new_task)
            future_workload[scan_date] = future_workload.get(scan_date, 0.0) + mt.duration_hours
            rescheduled_count += 1
            
    return rescheduled_count
