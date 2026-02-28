# backend/app/auth/permissions.py
"""
Role-based access control permissions.
"""

from typing import List
from functools import wraps
from fastapi import Depends, HTTPException, status

from app.models.user import User, UserRole
from app.auth.jwt_handler import get_current_user
from app.core.exceptions import AuthorizationError


class RoleChecker:
    """
    Dependency class for checking user roles.
    """

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise AuthorizationError(
                f"Role '{user.role.value}' is not authorized for this action"
            )
        return user


# Pre-configured role checkers
require_admin = RoleChecker([UserRole.ADMIN])
require_analyst = RoleChecker([UserRole.ADMIN, UserRole.ANALYST])
require_viewer = RoleChecker(
    [UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER])


def check_resource_ownership(user: User, resource_user_id: str) -> bool:
    """
    Check if user owns a resource or is admin.

    Args:
        user: Current user
        resource_user_id: User ID of resource owner

    Returns:
        True if user has access, False otherwise
    """
    if user.role == UserRole.ADMIN:
        return True
    return str(user.id) == str(resource_user_id)
