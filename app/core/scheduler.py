import logging
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def run_friday_reminders():
    from app.core.database import SessionLocal
    from app.models.user import User, UserRole
    from app.models.company import Company
    from app.models.timesheet_submission import TimesheetSubmission
    from app.core.email import send_reminder_email

    db = SessionLocal()
    try:
        week_start = _current_week_start()
        week_start_formatted = week_start.strftime("%B %d, %Y")
        companies = db.query(Company).filter(Company.is_active == True).all()
        total_sent = 0

        for company in companies:
            employees = db.query(User).filter(
                User.company_id == company.id,
                User.is_active == True,
                User.role == UserRole.employee,
            ).all()

            sent = 0
            for employee in employees:
                submitted = db.query(TimesheetSubmission).filter(
                    TimesheetSubmission.user_id == employee.id,
                    TimesheetSubmission.week_start == week_start,
                ).first()

                if not submitted:
                    snap = SimpleNamespace(full_name=employee.full_name, email=employee.email)
                    send_reminder_email(snap, week_start_formatted, company.name)
                    sent += 1

            logger.info("Friday reminders — %s: %d sent", company.name, sent)
            total_sent += sent

        logger.info("Friday reminders complete — total sent: %d", total_sent)
    except Exception as e:
        logger.error("Friday reminder job failed: %s", e)
    finally:
        db.close()


def start_scheduler():
    # 8 PM every Friday, America/New_York — handles EST/EDT automatically
    scheduler.add_job(
        run_friday_reminders,
        CronTrigger(day_of_week="fri", hour=20, minute=0, timezone="America/New_York"),
        id="friday_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — Friday reminders at 20:00 America/New_York")


def stop_scheduler():
    scheduler.shutdown()
