from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, time
from app.core.database import get_db
from app.core.email import send_submission_confirmation, send_submission_alert_to_admin
from app.models.time_entry import TimeEntry
from app.models.timesheet_submission import TimesheetSubmission
from app.models.user import User, UserRole
from app.api.deps import get_current_user

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("/submission-status")
def get_submission_status(
    week_start: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = db.query(TimesheetSubmission).filter(
        TimesheetSubmission.user_id == current_user.id,
        TimesheetSubmission.week_start == week_start,
    ).first()
    if submission:
        return {
            "submitted": True,
            "submitted_at": submission.created_at,
            "net_minutes": submission.net_minutes,
            "days_logged": submission.days_logged,
        }
    return {"submitted": False}


@router.post("/submit")
def submit_week(
    background_tasks: BackgroundTasks,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if already submitted for this week
    existing = db.query(TimesheetSubmission).filter(
        TimesheetSubmission.user_id == current_user.id,
        TimesheetSubmission.week_start == start_date,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already submitted your timesheet for this week.",
        )

    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.clock_in >= datetime.combine(start_date, time.min),
            TimeEntry.clock_in <= datetime.combine(end_date, time.max),
            TimeEntry.clock_out.isnot(None),
        )
        .order_by(TimeEntry.clock_in)
        .all()
    )

    if not entries:
        raise HTTPException(status_code=400, detail="No completed entries found for this week. Log your hours first.")

    total_net = sum(e.net_work_minutes or 0 for e in entries)
    total_break = sum(e.break_minutes or 0 for e in entries)
    total_gross = sum(e.duration_minutes or 0 for e in entries)
    totals = {"net": total_net, "break": total_break, "gross": total_gross}

    # Record the submission
    submission = TimesheetSubmission(
        user_id=current_user.id,
        company_id=current_user.company_id,
        week_start=start_date,
        week_end=end_date,
        net_minutes=total_net,
        days_logged=len(entries),
    )
    db.add(submission)
    db.commit()

    week_label = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}"

    admin = (
        db.query(User)
        .filter(
            User.company_id == current_user.company_id,
            User.role == UserRole.admin,
            User.is_active == True,
        )
        .first()
    )
    admin_email = admin.email if admin else None

    background_tasks.add_task(send_submission_confirmation, current_user, week_label, entries, totals)
    if admin_email and admin_email != current_user.email:
        background_tasks.add_task(
            send_submission_alert_to_admin, current_user, admin_email, week_label, entries, totals
        )

    net_str = f"{int(total_net // 60)}h {int(total_net % 60)}m"
    return {
        "message": "Timesheet submitted successfully",
        "week": week_label,
        "days_logged": len(entries),
        "net_hours": net_str,
    }
