from pydantic import BaseModel, computed_field
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.time_entry import EntryType


class ClockInRequest(BaseModel):
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    notes: Optional[str] = None


class ManualEntryRequest(BaseModel):
    clock_in: datetime
    clock_out: datetime
    break_minutes: int = 0
    notes: Optional[str] = None


class UpdateEntryRequest(BaseModel):
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    break_minutes: Optional[int] = None
    notes: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_id: UUID
    clock_in: datetime
    clock_out: Optional[datetime] = None
    notes: Optional[str] = None
    break_minutes: int = 0
    entry_type: EntryType

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def duration_minutes(self) -> Optional[float]:
        if self.clock_in and self.clock_out:
            return round((self.clock_out - self.clock_in).total_seconds() / 60, 2)
        return None

    @computed_field
    @property
    def net_work_minutes(self) -> Optional[float]:
        if self.duration_minutes is not None:
            return round(self.duration_minutes - self.break_minutes, 2)
        return None
