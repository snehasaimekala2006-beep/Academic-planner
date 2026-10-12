import json
from functools import wraps
from flask import request, abort, current_app
from flask_login import current_user
from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditLog


def log_audit_event(action, resource, details=None, status='SUCCESS', user=None):
    """Record an audit trail event in the database."""
    try:
        user_id = user.id if user else (current_user.id if current_user and current_user.is_authenticated else None)
        ip_addr = request.remote_addr if request else '127.0.0.1'
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else (str(details) if details else None)
        
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            details_json=details_str,
            ip_address=ip_addr,
            status=status
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to write audit log: {str(e)}")


def role_required(*allowed_roles):
    """
    Decorator to enforce Role-Based Access Control (RBAC).
    Returns HTTP 403 Forbidden if user lacks the necessary role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            
            user_role = current_user.role_name
            if user_role not in allowed_roles:
                log_audit_event(
                    action='UNAUTHORIZED_ACCESS_ATTEMPT',
                    resource=request.path,
                    details={'required_roles': list(allowed_roles), 'user_role': user_role},
                    status='DENIED'
                )
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def student_owner_required(param_name='student_id'):
    """
    Decorator to prevent IDOR vulnerabilities.
    Ensures a student can only view/modify their own academic profile.
    Admin/Principal/HOD/Faculty can access if authorized.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            
            target_student_id = kwargs.get(param_name)
            if current_user.is_student():
                if not current_user.student_profile or current_user.student_profile.id != int(target_student_id):
                    log_audit_event(
                        action='IDOR_PREVENTION_TRIGGERED',
                        resource=request.path,
                        details={'attempted_student_id': target_student_id, 'actual_student_id': getattr(current_user.student_profile, 'id', None)},
                        status='DENIED'
                    )
                    abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def authenticate_user(username_or_id, password):
    """
    Authenticate user by username, email, or roll/employee ID.
    """
    user = User.query.filter(
        (User.username == username_or_id) | 
        (User.email == username_or_id)
    ).first()
    
    if not user:
        # Check student roll number
        from app.models.user import StudentProfile, FacultyProfile
        student_prof = StudentProfile.query.filter_by(roll_number=username_or_id).first()
        if student_prof:
            user = student_prof.user
        else:
            faculty_prof = FacultyProfile.query.filter_by(employee_id=username_or_id).first()
            if faculty_prof:
                user = faculty_prof.user
                
    if user and user.check_password(password) and user.is_active:
        return user
    return None
