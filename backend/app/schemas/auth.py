from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from backend.app.models.enums import EnumUserRole


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    role: EnumUserRole = EnumUserRole.public
    faskes_id: Optional[str] = None


class UserLogin(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # in seconds


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: EnumUserRole
    faskes_id: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
