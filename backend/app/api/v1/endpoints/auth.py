from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.models.auth import AuthUser, AuthSession
from backend.app.models.enums import EnumUserRole
from backend.app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    UserProfile,
)
from backend.app.schemas.common import APIResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/register", response_model=APIResponse[UserProfile], status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    # Check if username or email already exists
    stmt = select(AuthUser).where(
        or_(AuthUser.email == payload.email, AuthUser.username == payload.username)
    )
    existing = await db.scalar(stmt)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered.",
        )

    # Hash password & create user
    hashed_pwd = get_password_hash(payload.password)
    user = AuthUser(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role,
        faskes_id=payload.faskes_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return APIResponse(
        success=True,
        message="User registered successfully.",
        data=UserProfile.model_validate(user),
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login_user(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuthUser).where(
        or_(AuthUser.email == payload.username_or_email, AuthUser.username == payload.username_or_email)
    )
    user = await db.scalar(stmt)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    # Generate tokens
    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    # Persist session
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_record = AuthSession(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.commit()

    return APIResponse(
        success=True,
        message="Login successful.",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_access_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    stmt = select(AuthSession).where(
        AuthSession.refresh_token == payload.refresh_token,
        AuthSession.is_revoked == False,
        AuthSession.expires_at > datetime.utcnow(),
    )
    session_record = await db.scalar(stmt)
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked.",
        )

    user = await db.get(AuthUser, session_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is no longer active.",
        )

    new_access_token = create_access_token(subject=user.id, role=user.role.value)

    return APIResponse(
        success=True,
        message="Token refreshed successfully.",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=payload.refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/me", response_model=APIResponse[UserProfile])
async def get_my_profile(
    current_user: AuthUser = Depends(get_current_user),
):
    return APIResponse(
        success=True,
        message="Profile retrieved.",
        data=UserProfile.model_validate(current_user),
    )


@router.post("/logout", response_model=APIResponse[dict])
async def logout_user(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    stmt = select(AuthSession).where(
        AuthSession.refresh_token == payload.refresh_token,
        AuthSession.user_id == current_user.id,
    )
    session_record = await db.scalar(stmt)
    if session_record:
        session_record.is_revoked = True
        await db.commit()

    return APIResponse(
        success=True,
        message="Logged out successfully.",
        data={"revoked": True},
    )
