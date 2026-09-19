from typing import Callable, Sequence
from fastapi import Depends

from backend.app.core.auth import get_current_user
from backend.app.core.errors import forbidden_error
from backend.app.models.user import User


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory enforcing role-based access control (RBAC)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise forbidden_error(
                message=f"Role '{current_user.role}' is not authorized to perform this action",
                code="FORBIDDEN",
                details={
                    "user_role": current_user.role,
                    "allowed_roles": list(allowed_roles),
                },
            )
        return current_user

    return role_checker
