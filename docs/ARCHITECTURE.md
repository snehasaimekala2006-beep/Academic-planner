# Architecture & System Design

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning and Academic Management System

---

## 1. System Overview

The DIET Academic Planner is an enterprise-grade institutional web platform designed to streamline outcome-based engineering education. It unifies official curriculum management, persistent topic-level syllabus tracking, AI and deterministic study planning, classroom attendance, coursework assignments, and multi-constraint timetable conflict resolution across 9 engineering departments.

```
+-----------------------------------------------------------------------------------+
|                     Presentation Layer (Bootstrap 5 + AJAX)                       |
|   Student Portal  |  Faculty Portal  |  HOD Portal  |  Principal  |  Admin Portal  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|               Application Layer (Flask 3.1 + Blueprints + RBAC)                   |
|  - Auth & Security Middleware (Zero-IDOR, CSRF, Secure Sessions)                 |
|  - Syllabus PDF Importer & SHA-256 Validation Workflow                            |
|  - Real-Time Topic Checkbox Single Source of Truth Engine                         |
|  - Dual Planning Engine (Structured AI Generator + Deterministic Scheduler)       |
|  - Academic Attendance & Assignment Management                                    |
|  - Timetable 3-Way Conflict Detection (Room, Faculty, Section)                    |
|  - ReportLab Institutional PDF Engine & CSV Exporters                             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|             Data Layer (PostgreSQL / SQLite via SQLAlchemy 2.0 ORM)               |
|  Users, Roles, Profiles, Departments, Branches, Semesters, Subjects, Units,      |
|  Topics, Completions, StudyPlans, Attendance, Assignments, Timetables, AuditLogs  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Role-Based Access Hierarchy (RBAC)

The application enforces strict vertical and horizontal isolation:

1. **Student**: Accesses only personal academic records, syllabus progress, study schedules, attendance, and assignment submissions. URL manipulation (`/student/<id>`) is strictly blocked (403 Forbidden).
2. **Faculty**: Manages assigned subject offerings, takes class attendance, publishes assignments, grades student submissions, and generates 16-week teaching plans.
3. **Head of Department (HOD)**: Oversees department faculty workload, reviews student syllabus completion and attendance benchmarks, and accesses department-level summary reports. Cross-department access is restricted.
4. **Principal**: Accesses institution-wide analytics, cross-branch comparison metrics, college attendance averages, and institutional audit reports.
5. **System Administrator**: Full administrative governance, user account management, timetable conflict resolution, official syllabus PDF import, SHA-256 verification, and security audit log analysis.

---

## 3. Academic Hierarchy

The core curriculum structure follows official JNTUK and AICTE regulations:

- **Department** (e.g. `CSE_DEPT`, `ECE_DEPT`, `CIVIL_DEPT`)
  - **Branch** (9 Branches: CSE, AIML, CSD, CAD, IT, ECE, EEE, MECH, CIVIL)
    - **Academic Year** (1st to 4th Year)
      - **Semester** (Semester I to Semester VIII)
        - **Section** ('A', 'B', 'C')
        - **Subject** (Theory, Lab, Project, Seminar, Elective)
          - **Unit** (Preserved official unit titles)
            - **Topic** (Estimated study hours, description)
              - **TopicCompletion** (Single source of truth checkbox)

---

## 4. Key Subsystems

### A. Topic Checkbox Persistence System
Topic checkboxes serve as the real-time single source of truth for student progress. Every toggle fires an asynchronous POST to `/api/topics/<id>/completion`, persisting to the `TopicCompletion` table and returning recalculated subject, unit, and overall semester completion percentages and remaining hours.

### B. Dual Study Planning Engine
- **AI Mode**: Prompts configured LLM with strict JSON schema containing only incomplete topics, target dates, and available daily hours.
- **Deterministic Fallback Engine**: Local algorithm that distributes incomplete topics across active study days, respecting daily capacity limits and inserting revision and practice blocks without requiring an internet connection.
- **Missed Task Rescheduling**: Redistributes missed tasks into future days while strictly capping daily workloads.

### C. Timetable Conflict Resolution
Enforces 3 distinct unique database constraints preventing:
1. Section double-booking (Section + Day + Period + Session)
2. Faculty double-booking (Faculty + Day + Period + Session)
3. Room double-booking (Classroom + Day + Period + Session)
