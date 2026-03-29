from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.utils.oauth2 import get_current_user


# factory function — returns a dependency configured for specific roles
def require_roles(*roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user
    return role_checker