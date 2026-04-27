import uuid
import enum
from sqlalchemy import Column, DateTime, ForeignKey, Text, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class EntryType(str, enum.Enum):
    clock = "clock"
    manual = "manual"


class TimeEntry(Base, TimestampMixin):
    __tablename__ = "time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    break_minutes = Column(Integer, default=0, nullable=False)
    entry_type = Column(Enum(EntryType), default=EntryType.clock, nullable=False)

    user = relationship("User", back_populates="time_entries")
