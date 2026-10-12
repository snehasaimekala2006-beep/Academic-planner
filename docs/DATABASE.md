# Database Schema & Data Models

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Schema Architecture Overview

The database is normalized, enforcing relational integrity via foreign keys, unique composite indexes, and cascading delete/set-null rules across all institutional entities.

---

## 2. Core Entity Relational Structure

### A. Authentication & User Profiles
- `roles`: `id`, `name` (Student, Faculty, HOD, Principal, Admin), `description`
- `users`: `id`, `username` (indexed, unique), `email` (indexed, unique), `password_hash`, `full_name`, `role_id`, `is_active`, `created_at`, `updated_at`
- `student_profiles`: `id`, `user_id` (FK `users.id`, unique), `roll_number` (indexed, unique), `branch_id`, `academic_year_id`, `semester_id`, `section_id`, `admission_year`, `phone`
- `faculty_profiles`: `id`, `user_id` (FK `users.id`, unique), `employee_id` (indexed, unique), `department_id`, `designation`, `qualification`, `phone`
- `hod_profiles`: `id`, `user_id` (FK `users.id`, unique), `employee_id`, `department_id`, `appointed_date`, `phone`
- `principal_profiles`: `id`, `user_id` (FK `users.id`, unique), `employee_id`, `appointed_date`, `phone`

### B. Academic Hierarchy
- `departments`: `id`, `code` (unique), `name` (unique), `description`, `created_at`
- `branches`: `id`, `code` (unique: CSE, CSE-AIML, CSE-DS, IT, ECE, EEE, CIVIL, MECH, AGRI), `name`, `department_id`, `duration_years`, `total_semesters`
- `academic_years`: `id`, `year_number` (1 to 4), `label` ('1st Year' to '4th Year')
- `semesters`: `id`, `semester_number` (1 to 8), `academic_year_id`, `label` ('Semester I' to 'Semester VIII')
- `sections`: `id`, `name` ('A', 'B'), `branch_id`, `semester_id` (Unique composite: `name` + `branch_id` + `semester_id`)
- `subjects`: `id`, `code` (indexed), `name`, `credits`, `course_type` (Theory, Lab, Project, Seminar, Elective), `branch_id`, `semester_id`, `regulation` ('R20'), `is_active`, `is_demo_data`
- `subject_offerings`: `id`, `subject_id`, `faculty_id`, `section_id`, `academic_session` (Unique composite: `subject_id` + `section_id` + `academic_session`)

### C. Syllabus & Topic Completion (Single Source of Truth)
- `syllabus_sources`: `id`, `original_filename`, `stored_filename`, `file_hash` (SHA-256), `file_size`, `upload_timestamp`, `branch_id`, `semester_id`, `regulation`, `uploaded_by_id`, `is_official`
- `syllabus_imports`: `id`, `source_id`, `status` (`PENDING_VALIDATION`, `VALIDATED`, `REJECTED`), `raw_extracted_json`, `extracted_at`
- `syllabus_validations`: `id`, `import_id` (unique), `validated_by_id`, `validated_at`, `validation_notes`, `is_active`
- `units`: `id`, `subject_id`, `unit_number`, `unit_title`, `description` (Unique composite: `subject_id` + `unit_number`)
- `topics`: `id`, `unit_id`, `topic_number`, `topic_name`, `description`, `estimated_hours` (Unique composite: `unit_id` + `topic_number`)
- `topic_completions`: `id`, `student_id`, `topic_id`, `is_completed`, `completed_at`, `updated_at` (Unique composite: `student_id` + `topic_id`)

### D. Academic Planning & Operations
- `study_plans`: `id`, `student_id`, `title`, `start_date`, `target_date`, `exam_date`, `available_hours_per_day`, `days_per_week`, `is_ai_generated`, `is_active`, `created_at`
- `study_plan_tasks`: `id`, `study_plan_id`, `task_date`, `subject_id`, `unit_id`, `topic_id`, `task_type` (Learn, Practice, Revision, Self-test), `duration_hours`, `break_duration_minutes`, `status` (PENDING, COMPLETED, MISSED, RESCHEDULED), `reason_notes`
- `faculty_teaching_plans`: `id`, `offering_id`, `faculty_id`, `subject_id`, `target_completion_date`, `classes_per_week`
- `teaching_plan_weeks`: `id`, `teaching_plan_id`, `week_number`, `title`, `topics_covered`, `plan_type`, `is_completed`
- `attendance_sessions`: `id`, `offering_id`, `faculty_id`, `session_date`, `period_number`, `topic_covered`, `remarks` (Unique composite: `offering_id` + `session_date` + `period_number`)
- `attendance_records`: `id`, `session_id`, `student_id`, `is_present`, `remarks` (Unique composite: `session_id` + `student_id`)
- `assignments`: `id`, `offering_id`, `faculty_id`, `title`, `description`, `max_marks`, `due_date`, `attachment_path`
- `assignment_submissions`: `id`, `assignment_id`, `student_id`, `submission_text`, `file_path`, `submitted_at`, `is_late`, `marks_awarded`, `feedback`, `graded_by_id`, `graded_at` (Unique composite: `assignment_id` + `student_id`)
- `classrooms`: `id`, `room_number` (unique), `building`, `capacity`, `room_type`
- `timetable_entries`: `id`, `section_id`, `subject_id`, `faculty_id`, `classroom_id`, `day_of_week`, `period_number`, `academic_session` (Unique constraints preventing Section, Faculty, and Classroom double bookings)
- `academic_calendar_events`: `id`, `title`, `description`, `event_type`, `start_date`, `end_date`, `department_id`, `branch_id`
- `notifications`: `id`, `user_id`, `title`, `message`, `category`, `link_url`, `is_read`, `created_at`
- `audit_logs`: `id`, `user_id`, `action`, `resource`, `details_json`, `ip_address`, `status`, `timestamp`
