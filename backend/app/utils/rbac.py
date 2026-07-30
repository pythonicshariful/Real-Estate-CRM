from __future__ import annotations
"""
Role-Based Access Control (RBAC) utilities.

Provides decorators and helpers for:
- Role-level access control (@require_role)
- Field-level visibility control (@field_visible)
- Permission matrix definitions
"""

from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request, get_jwt

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role Hierarchy (higher index = more privileged)
# ---------------------------------------------------------------------------

ROLE_HIERARCHY = {
    "EXECUTIVE": 1,
    "LEAD_OWNER": 2,
    "MANAGER": 3,
    "GM": 4,
    "CEO": 5,
    "ADMIN": 6,
}

MFA_REQUIRED_ROLES = {"ADMIN"}


def is_admin(role: str) -> bool:
    """Check if the given role is a Main Admin."""
    return _role_to_str(role) == "ADMIN"


def is_lead_owner(role: str) -> bool:
    """Check if the given role is a Lead Owner."""
    return _role_to_str(role) == "LEAD_OWNER"


# ---------------------------------------------------------------------------
# Field-Level Permission Matrix
# ---------------------------------------------------------------------------

FIELD_PERMISSIONS = {
    # Fields visible only to Manager and above
    "manager_assessment": ["MANAGER", "GM", "CEO", "ADMIN"],
    "manager_label": ["MANAGER", "GM", "CEO", "ADMIN"],
    "manager_coaching_score": ["MANAGER", "GM", "CEO", "ADMIN"],

    # Fields visible only to GM and above
    "salary_info": ["GM", "CEO", "ADMIN"],
    "hr_private_notes": ["GM", "CEO", "ADMIN"],

    # Financial details restricted
    "total_deal_value": ["MANAGER", "GM", "CEO", "ADMIN"],
    "booking_amount": ["MANAGER", "GM", "CEO", "ADMIN"],

    # Audit log and security
    "audit_log": ["GM", "CEO", "ADMIN"],
    "recording_download_log": ["MANAGER", "GM", "CEO", "ADMIN"],

    # Data export: Admin only
    "data_export": ["ADMIN"],

    # Deactivation: Admin only
    "account_deactivation": ["ADMIN"],
}


def get_field_permissions(user_role: str) -> dict:
    """Return a dict of field_name -> bool (can_see) for a given role."""
    permissions = {}
    for field, allowed_roles in FIELD_PERMISSIONS.items():
        permissions[field] = user_role in allowed_roles
    return permissions


def can_see_field(user_role: str, field_name: str) -> bool:
    """Check if a user role can see a specific field."""
    allowed = FIELD_PERMISSIONS.get(field_name, [])
    if not allowed:
        return True  # Field not restricted, everyone can see
    return user_role in allowed


def _role_to_str(r):
    """Normalize enum or string to string representation."""
    if hasattr(r, 'value'):
        return str(r.value)
    return str(r) if r is not None else ""


def has_min_role(user_role, min_role) -> bool:
    """Check if user has at least the minimum required role level."""
    user_str = _role_to_str(user_role)
    min_str = _role_to_str(min_role)
    user_level = ROLE_HIERARCHY.get(user_str, 0)
    min_level = ROLE_HIERARCHY.get(min_str, 0)
    return user_level >= min_level


# ---------------------------------------------------------------------------
# JWT Claims Helper
# ---------------------------------------------------------------------------

def get_current_user_claims() -> dict:
    """Extract claims from current JWT token."""
    try:
        claims = get_jwt()
        return claims
    except Exception:
        return {}


def get_current_user_role() -> str | None:
    """Get the role of the currently authenticated user from JWT claims."""
    claims = get_current_user_claims()
    return claims.get("role")


def get_current_user_id() -> int | None:
    """Get the user ID from JWT identity."""
    try:
        identity = get_jwt_identity()
        return identity
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def require_role(*allowed_roles):
    """
    Decorator that restricts endpoint access to users with specific roles.

    Usage:
        @require_role('MANAGER', 'GM', 'CEO')
        def my_view():
            ...
    """
    allowed_set = {_role_to_str(r) for r in allowed_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_role = get_current_user_role()

            if not user_role:
                logger.warning("JWT has no role claim")
                return jsonify({"error": "Access denied: no role assigned"}), 403

            if _role_to_str(user_role) not in allowed_set:
                logger.warning(
                    f"Access denied: user role '{user_role}' not in {allowed_set}"
                )
                return jsonify({
                    "error": "Access denied: insufficient permissions",
                    "required_roles": list(allowed_set),
                    "your_role": user_role
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_min_role(min_role):
    """
    Decorator that restricts access to users at or above a role level.

    Role hierarchy: EXECUTIVE < MANAGER < GM < CEO < ADMIN

    Usage:
        @require_min_role('MANAGER')
        def manager_view():
            ...
    """
    min_str = _role_to_str(min_role)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_role = get_current_user_role()

            if not user_role:
                return jsonify({"error": "Access denied: no role assigned"}), 403

            if not has_min_role(user_role, min_str):
                return jsonify({
                    "error": f"Access denied: requires '{min_str}' or higher",
                    "minimum_role": min_str,
                    "your_role": user_role
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_mfa_verified(fn):
    """
    Decorator that ensures MFA has been completed for roles requiring it.
    Must be used after @jwt_required().
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_current_user_claims()
        user_role = _role_to_str(claims.get("role"))
        mfa_verified = claims.get("mfa_verified", False)

        if user_role in MFA_REQUIRED_ROLES and not mfa_verified:
            return jsonify({
                "error": "MFA verification required",
                "code": "MFA_REQUIRED"
            }), 403

        return fn(*args, **kwargs)
    return wrapper


def audit_action(action_type: str):
    """
    Decorator to automatically create an audit log entry for an endpoint.

    Usage:
        @audit_action('UPDATE_LEAD_STAGE')
        def update_stage(lead_id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import request, g
            g.audit_action = action_type
            g.audit_ip = request.remote_addr
            result = fn(*args, **kwargs)
            return result
        return wrapper
    return decorator


def strip_restricted_fields(data: dict, user_role: str) -> dict:
    """
    Remove fields from a response dict that the user_role cannot see.

    Args:
        data: The response dictionary to filter.
        user_role: The current user's role string.

    Returns:
        Filtered dict with restricted fields removed.
    """
    filtered = {}
    for key, value in data.items():
        if can_see_field(user_role, key):
            filtered[key] = value
    return filtered
