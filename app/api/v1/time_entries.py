from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, time, timezone, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.models.time_entry import TimeEntry, EntryType
from app.models.user import User, UserRole
from uuid import UUID
from app.schemas.time_entry import (
    ClockInRequest,
    ClockOutRequest,
    ManualEntryRequest,
    UpdateEntryRequest,
    TimeEntryResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/time-entries", tags=["time-entries"])


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _check_date_allowed(entry_date: date, user: User) -> None:
    if user.is_superuser or user.role == UserRole.admin:
        return
    today = date.today()
    current_week = _week_start(today)
    last_week = current_week - timedelta(weeks=1)
    entry_week = _week_start(entry_date)
    if entry_week < last_week:
        raise HTTPException(status_code=403, detail="Cannot log time more than one week in the past")
    if entry_week > current_week and not user.future_time_log_enabled:
        raise HTTPException(status_code=403, detail="Future week time logging is not enabled for your account")


@router.post("/clock-in", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
def clock_in(
    payload: ClockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    open_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.clock_out == None,
    ).first()
    if open_entry:
        raise HTTPException(status_code=400, detail="Already clocked in")

    entry = TimeEntry(
        user_id=current_user.id,
        company_id=current_user.company_id,
        clock_in=datetime.now(timezone.utc),
        notes=payload.notes,
        entry_type=EntryType.clock,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/clock-out", response_model=TimeEntryResponse)
def clock_out(
    payload: ClockOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    open_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.clock_out == None,
    ).first()
    if not open_entry:
        raise HTTPException(status_code=400, detail="Not clocked in")

    open_entry.clock_out = datetime.now(timezone.utc)
    if payload.notes:
        open_entry.notes = payload.notes
    db.commit()
    db.refresh(open_entry)
    return open_entry


@router.get("/status")
def get_clock_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    open_entry = db.query(TimeEntry).filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.clock_out == None,
    ).first()
    return {
        "is_clocked_in": open_entry is not None,
        "clock_in_time": open_entry.clock_in if open_entry else None,
    }


@router.get("/", response_model=List[TimeEntryResponse])
def list_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TimeEntry).filter(TimeEntry.user_id == current_user.id)

    if start_date:
        query = query.filter(TimeEntry.clock_in >= datetime.combine(start_date, time.min))
    if end_date:
        query = query.filter(TimeEntry.clock_in <= datetime.combine(end_date, time.max))

    return query.order_by(TimeEntry.clock_in.desc()).all()


@router.post("/manual", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
def create_manual_entry(
    payload: ManualEntryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.clock_out <= payload.clock_in:
        raise HTTPException(status_code=400, detail="clock_out must be after clock_in")

    _check_date_allowed(payload.clock_in.date(), current_user)

    entry = TimeEntry(
        user_id=current_user.id,
        company_id=current_user.company_id,
        clock_in=payload.clock_in,
        clock_out=payload.clock_out,
        notes=payload.notes,
        break_minutes=payload.break_minutes,
        entry_type=EntryType.manual,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=TimeEntryResponse)
def update_entry(
    entry_id: UUID,
    payload: UpdateEntryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if payload.clock_in is not None:
        _check_date_allowed(payload.clock_in.date(), current_user)
        entry.clock_in = payload.clock_in
    if payload.clock_out is not None:
        entry.clock_out = payload.clock_out
    if payload.break_minutes is not None:
        entry.break_minutes = payload.break_minutes
    if payload.notes is not None:
        entry.notes = payload.notes

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
