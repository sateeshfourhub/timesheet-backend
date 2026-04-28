import uuid
from sqlalchemy import Column, Date, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.models.base import TimestampMixin


class TimesheetSubmission(Base, TimestampMixin):
    __tablename__ = "timesheet_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    net_minutes = Column(Integer, nullable=False, default=0)
    days_logged = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_user_week_submission"),
    )
