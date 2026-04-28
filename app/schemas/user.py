from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.models.user import UserRole


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    company_id: UUID
    company_name: str | None = None
    is_active: bool
    is_superuser: bool
    future_time_log_enabled: bool

    model_config = {"from_attributes": True}
