import json
import requests
from datetime import datetime, timedelta
from flask import current_app
from app.models.syllabus import Topic, TopicCompletion
from app.models.academic import Subject


def generate_ai_study_plan(student, subject_ids, start_date, target_date, available_hours_per_day=3.0, 
                            days_per_week=6, revision_preference=True, practice_preference=True):
    """
    Connects to configured LLM API (Gemini or OpenAI compatible) to generate an intelligent, personalized study schedule.
    Returns parsed structured JSON list of tasks, or raises Exception on failure/unavailability.
    """
    api_key = current_app.config.get('AI_API_KEY')
    if not api_key:
        raise ValueError("AI_API_KEY not configured. Using deterministic engine.")
        
    model = current_app.config.get('AI_MODEL', 'gemini-1.5-flash')
    
    # 1. Fetch incomplete topic data
    completions = {c.topic_id: c.is_completed for c in TopicCompletion.query.filter_by(student_id=student.id).all()}
    selected_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
    
    curriculum_items = []
    for subj in selected_subjects:
        for unit in subj.units:
            for topic in unit.topics:
                if not completions.get(topic.id, False):
                    curriculum_items.append({
                        'subject_id': subj.id,
                        'subject_code': subj.code,
                        'subject_name': subj.name,
                        'unit_id': unit.id,
                        'unit_title': unit.unit_title,
                        'topic_id': topic.id,
                        'topic_name': topic.topic_name,
                        'estimated_hours': topic.estimated_hours
                    })

    if not curriculum_items:
        return []

    # 2. Build structured prompt
    prompt = f"""
You are an academic planning expert for Dhanekula Institute of Engineering and Technology (DIET).
Create an optimal study plan for student {student.user.full_name} ({student.roll_number}).

Parameters:
- Start Date: {start_date.isoformat()}
- Target Date: {target_date.isoformat()}
- Available Study Hours Per Day: {available_hours_per_day}
- Days Per Week: {days_per_week}
- Include Revision: {revision_preference}
- Include Practice: {practice_preference}

Incomplete Syllabus Items To Schedule:
{json.dumps(curriculum_items, indent=2)}

Output Requirements:
Return a strictly valid JSON object with a single key "plan" containing an array of task objects matching this schema:
{{
  "plan": [
    {{
      "date": "YYYY-MM-DD",
      "subject_id": <int>,
      "unit_id": <int>,
      "topic_id": <int or null>,
      "task_type": "Learn" | "Practice" | "Revision" | "Self-test",
      "duration_hours": <float>,
      "break_minutes": 15,
      "reason_notes": "<pedagogical explanation>"
    }}
  ]
}}

Ensure no day exceeds {available_hours_per_day} study hours. Do not include extra commentary or Markdown outside the JSON.
"""

    headers = {'Content-Type': 'application/json'}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }

    response = requests.post(url, json=payload, headers=headers, timeout=12)
    response.raise_for_status()
    
    res_data = response.json()
    candidates = res_data.get('candidates', [])
    if not candidates:
        raise ValueError("No response candidates returned by AI model.")
        
    text_content = candidates[0]['content']['parts'][0]['text']
    parsed_json = json.loads(text_content)
    
    raw_tasks = parsed_json.get('plan', [])
    valid_tasks = []
    
    for t in raw_tasks:
        try:
            t_date = datetime.strptime(t['date'], '%Y-%m-%d').date()
            valid_tasks.append({
                'task_date': t_date,
                'subject_id': int(t['subject_id']),
                'unit_id': int(t['unit_id']) if t.get('unit_id') else None,
                'topic_id': int(t['topic_id']) if t.get('topic_id') else None,
                'task_type': t.get('task_type', 'Learn'),
                'duration_hours': float(t.get('duration_hours', 1.0)),
                'break_duration_minutes': int(t.get('break_minutes', 15)),
                'reason_notes': t.get('reason_notes', 'AI planned study block'),
                'status': 'PENDING'
            })
        except Exception as e:
            current_app.logger.warning(f"Skipping malformed AI task item: {t} (Error: {e})")
            
    return valid_tasks
