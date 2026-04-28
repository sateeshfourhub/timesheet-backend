import uuid
import enum
from sqlalchemy import Column, String, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.employee, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    future_time_log_enabled = Column(Boolean, default=False, nullable=False)

    company = relationship("Company", back_populates="users")
    time_entries = relationship("TimeEntry", back_populates="user")
