from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from app.models.user import UserRole


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.employee


class UpdateUserRequest(BaseModel):
    role: Optional[UserRole] = None
    future_time_log_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class BatchFutureAccessRequest(BaseModel):
    user_ids: List[UUID]
    enabled: bool
