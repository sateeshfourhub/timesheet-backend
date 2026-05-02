from datetime import date, datetime, time, timedelta
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.deps import get_db, require_admin
from app.models.user import User, UserRole
from app.models.time_entry import TimeEntry
from app.models.timesheet_submission import TimesheetSubmission
from app.models.company import Company
from app.core.email import send_reminder_email

router = APIRouter(prefix="/admin/reports", tags=["reports"])

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def _net_minutes(entry) -> float:
    if not entry.clock_out:
        return 0
    total = (entry.clock_out - entry.clock_in).total_seconds() / 60
    return max(0, total - (entry.break_minutes or 0))


def _week_end(week_start: date) -> date:
    return week_start + timedelta(days=4)


def _mondays_in_month(year: int, month: int) -> List[date]:
    first = date(year, month, 1)
    # Find first Monday
    first_monday = first + timedelta(days=(7 - first.weekday()) % 7)
    mondays = []
    d = first_monday
    while d.month == month:
        mondays.append(d)
        d += timedelta(days=7)
    return mondays


def _get_company_users(current_user: User, db: Session) -> List[User]:
    q = db.query(User).filter(User.is_active == True)
    if not current_user.is_superuser:
        q = q.filter(User.company_id == current_user.company_id)
    return q.order_by(User.full_name).all()


def _employee_week_data(user: User, week_start: date, db: Session) -> dict:
    week_end = _week_end(week_start)
    entries = db.query(TimeEntry).filter(
        TimeEntry.user_id == user.id,
        TimeEntry.clock_in >= datetime.combine(week_start, time.min),
        TimeEntry.clock_in <= datetime.combine(week_end, time.max),
        TimeEntry.clock_out.isnot(None),
    ).all()

    days = {}
    for i, day_name in enumerate(DAY_NAMES):
        day_date = week_start + timedelta(days=i)
        day_entries = [e for e in entries if e.clock_in.date() == day_date]
        if day_entries:
            days[day_name] = round(sum(_net_minutes(e) for e in day_entries))

    total_minutes = sum(days.values())

    submission = db.query(TimesheetSubmission).filter(
        TimesheetSubmission.user_id == user.id,
        TimesheetSubmission.week_start == week_start,
    ).first()

    return {
        "id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "days": days,
        "total_minutes": total_minutes,
        "submitted": submission is not None,
        "submitted_at": submission.created_at.isoformat() if submission else None,
    }


# ── Weekly report ─────────────────────────────────────────────────────────────

@router.get("/weekly")
def weekly_report(
    week_start: date,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start must be a Monday")

    users = _get_company_users(current_user, db)
    employees = [_employee_week_data(u, week_start, db) for u in users]

    return {
        "week_start": week_start.isoformat(),
        "week_end": _week_end(week_start).isoformat(),
        "employees": employees,
    }


# ── Monthly report ────────────────────────────────────────────────────────────

@router.get("/monthly")
def monthly_report(
    year: int,
    month: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")

    mondays = _mondays_in_month(year, month)
    if not mondays:
        raise HTTPException(status_code=400, detail="No working weeks found for this month")

    weeks = [
        {
            "label": f"Week {i + 1}",
            "week_start": m.isoformat(),
            "week_end": _week_end(m).isoformat(),
        }
        for i, m in enumerate(mondays)
    ]

    users = _get_company_users(current_user, db)

    employees = []
    company_week_minutes = [0] * len(mondays)

    for user in users:
        week_minutes = []
        for i, monday in enumerate(mondays):
            data = _employee_week_data(user, monday, db)
            mins = data["total_minutes"]
            week_minutes.append(mins)
            company_week_minutes[i] += mins

        employees.append({
            "id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "week_minutes": week_minutes,
            "total_minutes": sum(week_minutes),
        })

    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    return {
        "year": year,
        "month": month,
        "month_name": month_names[month - 1],
        "weeks": weeks,
        "employees": employees,
        "company_week_minutes": company_week_minutes,
        "company_total_minutes": sum(company_week_minutes),
    }


# ── Send reminder ─────────────────────────────────────────────────────────────

class SendReminderRequest(BaseModel):
    week_start: date
    user_ids: List[UUID]


@router.post("/send-reminder")
def send_reminder(
    payload: SendReminderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_name = company.name if company else "Your"

    q = db.query(User).filter(
        User.id.in_(payload.user_ids),
        User.is_active == True,
    )
    if not current_user.is_superuser:
        q = q.filter(User.company_id == current_user.company_id)

    users = q.all()
    if not users:
        raise HTTPException(status_code=404, detail="No matching employees found")

    week_start_formatted = payload.week_start.strftime("%B %d, %Y")
    recipients = []
    for user in users:
        from types import SimpleNamespace
        snap = SimpleNamespace(full_name=user.full_name, email=user.email)
        background_tasks.add_task(send_reminder_email, snap, week_start_formatted, company_name)
        recipients.append(user.email)

    return {"sent": len(recipients), "recipients": recipients}
