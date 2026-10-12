# REST API Documentation

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management API

---

## 1. Authentication & Security

All API endpoints require either an active session cookie or user authorization. Unauthenticated or unauthorized requests return `401 Unauthorized` or `403 Forbidden`.

---

## 2. Endpoints Reference

### A. Topic Completion Toggle (Single Source of Truth)
- **Endpoint**: `POST /api/topics/<int:topic_id>/completion`
- **Access**: Logged-in Student
- **Request Body**:
```json
{
  "completed": true
}
```
- **Response (200 OK)**:
```json
{
  "success": true,
  "topic_id": 14,
  "completed": true,
  "unit": {
    "unit_id": 3,
    "completed_topics": 3,
    "total_topics": 4,
    "percentage": 75.0
  },
  "subject": {
    "subject_id": 1,
    "code": "CS501PC",
    "completed_topics": 12,
    "remaining_topics": 7,
    "total_topics": 19,
    "completion_percentage": 63.2,
    "remaining_estimated_hours": 11.5
  }
}
```

### B. Curriculum & Branches
- `GET /api/branches`: Lists all 9 supported engineering branches.
- `GET /api/semesters`: Lists all 8 academic semesters.
- `GET /api/subjects?branch_id=1&semester_id=5`: Returns filtered list of active subjects with unit and topic counts.

### C. Notifications
- `GET /api/notifications?unread=true`: Returns recent user notifications.
- `POST /api/notifications/<id>/read`: Marks notification as read.
