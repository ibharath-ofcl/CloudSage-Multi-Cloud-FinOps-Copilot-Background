"""
CloudSage User Identity and Authentication Pydantic Schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from backend.app.core.enums import UserRole


class UserBase(BaseModel):
    email: str = Field(..., max_length=256)
    full_name: str = Field(..., max_length=128)
    role: UserRole = Field(default=UserRole.FINANCE_ANALYST)
    department: Optional[str] = Field(None, max_length=64)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
