from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.models.user import UserRole


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    company_id: UUID
    is_active: bool

    model_config = {"from_attributes": True}
