# Dhanekula Institute of Engineering and Technology (DIET)
## Academic Planning and Academic Management System

![DIET Banner](https://img.shields.io/badge/DIET-Academic%20Planner-002B5B?style=for-the-badge)
![Status](https://img.shields.io/badge/Build-Production%20Ready-success?style=for-the-badge)
![Coverage](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-black?style=for-the-badge&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)

---

## 1. Overview

The **DIET Academic Planner** is a complete, full-stack, production-ready academic planning and institutional management system built specifically for **Dhanekula Institute of Engineering and Technology (DIET)**, located in Ganguru, Vijayawada, Andhra Pradesh.

It integrates outcome-based engineering education across **4 Years**, **8 Semesters**, and **9 Engineering Branches** with topic-level checkbox syllabus completion, intelligent AI and deterministic study scheduling, class attendance, coursework assignments, conflict-free timetable management, and ReportLab PDF reporting.

---

## 2. Institutional Engineering Branches Supported

1. **Computer Science and Engineering (CSE)**
2. **Computer Science and Engineering – Artificial Intelligence and Machine Learning (CSE-AIML)**
3. **Computer Science and Engineering – Data Science (CSE-DS)**
4. **Information Technology (IT)**
5. **Electronics and Communication Engineering (ECE)**
6. **Electrical and Electronics Engineering (EEE)**
7. **Civil Engineering (CIVIL)**
8. **Mechanical Engineering (MECH)**
9. **Agricultural Engineering (AGRI)**

---

## 3. Key Operational Roles & Portals

| Role | Portal Route | Key Features & Responsibilities |
| :--- | :--- | :--- |
| **Student** | `/login/student` | Topic checkbox tracking, study plans, attendance %, assignments, timetables, ReportLab progress PDF download |
| **Faculty** | `/login/faculty` | Class attendance marking, assignment creation & grading, 16-week teaching planner, faculty schedule |
| **HOD** | `/login/hod` | Department analytics, faculty workload monitoring, student completion rates, department summary reports |
| **Principal** | `/login/principal` | Institution-level analytics, cross-branch comparison metrics, college attendance average, governance reports |
| **Administrator** | `/login/admin` | User management, official syllabus PDF importer, SHA-256 validation, conflict-checked timetable, audit logs |

---

## 4. Default Demo Credentials (Development Only)

> [!NOTE]
> All sample data is explicitly labeled `DEMO DATA — NOT OFFICIAL SYLLABUS`. Official syllabus documents are managed via the administrative PDF validation workflow.

| Role | Username / ID | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@DIET2026` | System Administration & Syllabus Validation |
| **Principal** | `principal` | `Principal@DIET2026` | Institutional Analytics & Governance |
| **HOD (CSE)** | `hod_cse` | `Hod@DIET2026` | Department of CSE Analytics & Faculty |
| **HOD (ECE)** | `hod_ece` | `Hod@DIET2026` | Department of ECE Analytics & Faculty |
| **Faculty (CSE)** | `faculty_cse1` / `DIET-FAC-101` | `Faculty@DIET2026` | DAA & DBMS Courses, Attendance, Assignments |
| **Student (CSE 1)** | `21diet0501` / `218T1A0501` | `Student@DIET2026` | 3rd Year CSE, Sem 5, Section A |
| **Student (CSE 2)** | `21diet0502` / `218T1A0502` | `Student@DIET2026` | 3rd Year CSE, Sem 5, Section A (IDOR Test User) |

---

## 5. Quick Start Guide

### Prerequisites
- Python 3.10+
- pip

### Local Development Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed development database
python scripts/seed_data.py

# 3. Run application server
python run.py
```
Open browser at: `http://localhost:5000`

### Running Test Suite
```bash
pytest -v
```

---

## 6. Docker Deployment

```bash
docker-compose up -d --build
```
Access at: `http://localhost:8000`

---

## 7. Documentation Index

- [Architecture & Design](file:///c:/Users/Admin/Desktop/E_Planner/docs/ARCHITECTURE.md)
- [Database Schema & Models](file:///c:/Users/Admin/Desktop/E_Planner/docs/DATABASE.md)
- [Security & Confidentiality](file:///c:/Users/Admin/Desktop/E_Planner/docs/SECURITY.md)
- [REST API Reference](file:///c:/Users/Admin/Desktop/E_Planner/docs/API.md)
- [Official Syllabus Import Guide](file:///c:/Users/Admin/Desktop/E_Planner/docs/SYLLABUS_IMPORT.md)
- [AI & Deterministic Planner](file:///c:/Users/Admin/Desktop/E_Planner/docs/AI_PLANNER.md)
- [Deployment & DevOps](file:///c:/Users/Admin/Desktop/E_Planner/docs/DEPLOYMENT.md)
- [Testing & Acceptance Matrix](file:///c:/Users/Admin/Desktop/E_Planner/docs/TESTING.md)
