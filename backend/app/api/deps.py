from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import decode_token
from backend.app.models.auth import AuthUser
from backend.app.models.enums import EnumUserRole

# OAuth2 Scheme (Optional for public endpoints, enforced for private)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthUser]:
    """
    Returns authenticated user if valid token is supplied, otherwise returns None (for public endpoints).
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    try:
        user_id_int = int(user_id)
    except ValueError:
        return None

    stmt = select(AuthUser).where(AuthUser.id == user_id_int, AuthUser.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def get_current_user(
    user: Optional[AuthUser] = Depends(get_current_user_optional),
) -> AuthUser:
    """
    Guarantees user is authenticated. Raises 401 Unauthorized if missing/invalid.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: List[EnumUserRole]):
    """
    RBAC Role Guard Dependency.
    Ensures authenticated user has one of the allowed roles.
    """
    async def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role == EnumUserRole.superadmin:
            # Superadmin bypasses all role restrictions
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}, your role: {current_user.role.value}"
            )
        return current_user

    return role_checker
