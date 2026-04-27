from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, time
from app.core.database import get_db
from app.core.email import send_submission_confirmation, send_submission_alert_to_admin
from app.models.time_entry import TimeEntry
from app.models.user import User, UserRole
from app.api.deps import get_current_user

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.post("/submit")
def submit_week(
    background_tasks: BackgroundTasks,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        raise HTTPException(status_code=400, detail="No completed entries found for this week")

    total_net = sum(e.net_work_minutes or 0 for e in entries)
    total_break = sum(e.break_minutes or 0 for e in entries)
    total_gross = sum(e.duration_minutes or 0 for e in entries)
    totals = {"net": total_net, "break": total_break, "gross": total_gross}

    week_label = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}"

    # Find the admin of this company to notify
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

    # Send both emails in the background so the API responds immediately
    background_tasks.add_task(send_submission_confirmation, current_user, week_label, entries, totals)
    if admin_email and admin_email != current_user.email:
        background_tasks.add_task(
            send_submission_alert_to_admin, current_user, admin_email, week_label, entries, totals
        )
    elif admin_email == current_user.email:
        # User is the admin — send single combined email
        background_tasks.add_task(send_submission_confirmation, current_user, week_label, entries, totals)

    net_str = f"{int(total_net // 60)}h {int(total_net % 60)}m"
    return {
        "message": "Timesheet submitted successfully",
        "week": week_label,
        "days_logged": len(entries),
        "net_hours": net_str,
        "emails_sent_to": [current_user.email] + ([admin_email] if admin_email and admin_email != current_user.email else []),
    }
