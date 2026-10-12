# Security & Confidentiality Architecture

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Threat Modeling & Defense Strategies

### A. Broken Object-Level Authorization (IDOR Prevention)
- Direct resource ID requests (e.g. `/student/<student_id>`) are intercepted by `@student_owner_required` decorator.
- If a logged-in student attempts to modify or view another student's ID, the server logs an `IDOR_PREVENTION_TRIGGERED` audit event with IP and returns HTTP 403 Forbidden.

### B. Vertical & Horizontal Privilege Escalation
- Vertically protected using `@role_required(*roles)` on every non-public route.
- Horizontally protected by department and offering matching (e.g., HOD cannot view other department records; faculty cannot mark attendance for courses they do not teach).

### C. Cryptographic Password Hashing
- Utilizes Werkzeug secure password hashing (PBKDF2-HMAC-SHA256 with per-user salt). Plaintext passwords are never stored or logged.

### D. CSRF & Session Protection
- Enabled via `Flask-WTF` CSRF protection with secure tokens embedded across all forms.
- Cookie flags configured: `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and `SESSION_COOKIE_SECURE = True` in production.

### E. File Upload Security
- Strict whitelist: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.docx`, `.xlsx`, `.zip`.
- All uploaded filenames sanitized using `werkzeug.utils.secure_filename` with prepended timestamps and randomized hashes.
- PDFs hashed with SHA-256 upon arrival and quarantined in `PENDING_VALIDATION` state until admin approval.

### F. Security Audit Logging
Every sensitive action writes an immutable record to the `audit_logs` table:
- User ID & Username
- Action name (`USER_LOGIN`, `UNAUTHORIZED_ACCESS_ATTEMPT`, `IDOR_PREVENTION_TRIGGERED`, `SYLLABUS_UPLOADED`, `ATTENDANCE_RECORDED`, etc.)
- Resource URL
- IP Address & Timestamp
- Status (`SUCCESS`, `DENIED`, `FAILURE`)
