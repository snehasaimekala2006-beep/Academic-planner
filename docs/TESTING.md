# Testing & Quality Assurance Guide

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Test Suite Architecture

The test suite is built on `pytest` and validates every core module, security layer, and all 12 user acceptance scenarios.

```bash
pytest -v
```

---

## 2. Acceptance Criteria Test Coverage Matrix

| Acceptance Test | Requirement Description | Test File |
| :--- | :--- | :--- |
| **TEST 1** | Topic checkbox toggle persistence & real-time percentage | `tests/test_checkbox.py` |
| **TEST 2** | IDOR URL tampering returns HTTP 403 Forbidden | `tests/test_rbac.py` |
| **TEST 3** | Faculty marks attendance; student sees updated % | `tests/test_attendance.py` |
| **TEST 4** | Assignment lifecycle (create, submit, grade, feedback) | `tests/test_assignments.py` |
| **TEST 5** | HOD department-level isolation (cannot access other depts) | `tests/test_rbac.py` |
| **TEST 6** | Principal institution-wide analytics access | `tests/test_rbac.py` |
| **TEST 7** | Official syllabus PDF upload with SHA-256 validation | `tests/test_syllabus.py` |
| **TEST 8** | Student progress PDF report generation & browser viewer | `tests/test_reports.py` |
| **TEST 9** | Study plan excludes completed topics & respects hours | `tests/test_planner.py` |
| **TEST 10** | AI API failure fallback to deterministic scheduler | `tests/test_planner.py` |
| **TEST 11** | Timetable multi-constraint conflict rejection | `tests/test_timetable.py` |
| **TEST 12** | Unauthorized API requests return 401/403 | `tests/test_api.py` |
