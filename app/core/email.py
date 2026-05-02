import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, html_body: str) -> bool:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False

    recipient = settings.EMAIL_DEV_RECIPIENT or to
    if settings.EMAIL_DEV_RECIPIENT and recipient != to:
        logger.info("DEV MODE: redirecting email from %s to %s", to, recipient)

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": f"TimekeepingHub <{settings.EMAIL_FROM}>",
            "to": [recipient],
            "reply_to": settings.EMAIL_REPLY_TO,
            "subject": subject,
            "html": html_body,
        })
        logger.info("Email sent to %s: %s", recipient, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", recipient, e)
        return False


def _entry_rows(entries: list) -> str:
    rows = ""
    for e in sorted(entries, key=lambda x: x.clock_in):
        day = e.clock_in.strftime("%a, %b %d")
        start = e.clock_in.strftime("%I:%M %p")
        end = e.clock_out.strftime("%I:%M %p") if e.clock_out else "—"
        brk = f"{e.break_minutes}m" if e.break_minutes else "—"
        net = max(0, (e.clock_out - e.clock_in).total_seconds() / 60 - (e.break_minutes or 0)) if e.clock_out else 0
        net_str = f"{int(net // 60)}h {int(net % 60)}m" if net else "—"
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;">{day}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;">{start} – {end}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:#d97706;">{brk}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f3f4f6;color:#16a34a;font-weight:600;">{net_str}</td>
        </tr>"""
    return rows


def _base_template(heading: str, subheading: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <tr>
          <td style="background:linear-gradient(135deg,#1d4ed8,#1e3a8a);padding:28px 32px;">
            <p style="margin:0;color:#bfdbfe;font-size:12px;text-transform:uppercase;letter-spacing:1px;">TimekeepingHub</p>
            <h1 style="margin:6px 0 0;color:#ffffff;font-size:22px;font-weight:700;">{heading}</h1>
            <p style="margin:6px 0 0;color:#93c5fd;font-size:14px;">{subheading}</p>
          </td>
        </tr>
        <tr><td style="padding:28px 32px;">{content}</td></tr>
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f3f4f6;background:#f9fafb;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">
              This is an automated email — please do not reply directly to this message.<br/>
              For questions or support, email us at <a href="mailto:support@timekeepinghub.com" style="color:#3b82f6;text-decoration:none;">support@timekeepinghub.com</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_welcome_email(user, company_name: str, company_slug: str):
    """Welcome email sent to a new employee after self-registration."""
    first_name = user.full_name.split()[0]
    content = f"""
    <p style="color:#374151;font-size:15px;">Hi <strong>{first_name}</strong>,</p>
    <p style="color:#374151;font-size:15px;">
      Your account has been created and you are now part of <strong>{company_name}</strong> on TimekeepingHub.
    </p>

    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px 20px;margin:20px 0;">
      <p style="margin:0;color:#1e40af;font-size:14px;font-weight:600;">Your account details</p>
      <p style="margin:8px 0 0;color:#1e3a8a;font-size:13px;">Email: <strong>{user.email}</strong></p>
      <p style="margin:4px 0 0;color:#1e3a8a;font-size:13px;">Company: <strong>{company_name}</strong></p>
    </div>

    <p style="color:#374151;font-size:15px;">You can now sign in and start logging your hours:</p>

    <div style="text-align:center;margin:24px 0;">
      <a href="https://timekeepinghub.com/#/login"
         style="background:#1d4ed8;color:#ffffff;text-decoration:none;padding:12px 32px;border-radius:8px;font-size:15px;font-weight:600;display:inline-block;">
        Sign in to TimekeepingHub
      </a>
    </div>

    <p style="color:#6b7280;font-size:13px;">
      If you have any questions, contact your company admin or email us at
      <a href="mailto:support@timekeepinghub.com" style="color:#3b82f6;text-decoration:none;">support@timekeepinghub.com</a>
    </p>
    """
    _send(
        to=user.email,
        subject=f"Welcome to TimekeepingHub — {company_name}",
        html_body=_base_template("Welcome to TimekeepingHub", company_name, content),
    )


def send_submission_confirmation(employee, week_label: str, entries: list, totals: dict):
    """Confirmation email to employee after they submit their timesheet."""
    total_net = totals["net"]
    net_str = f"{int(total_net // 60)}h {int(total_net % 60)}m"
    days_logged = len([e for e in entries if e.clock_out])
    first_name = employee.full_name.split()[0]

    content = f"""
    <p style="color:#374151;font-size:15px;">Hi <strong>{first_name}</strong>,</p>
    <p style="color:#374151;font-size:15px;">Your timesheet for <strong>{week_label}</strong> has been successfully submitted.</p>

    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px 20px;margin:20px 0;">
      <p style="margin:0;color:#15803d;font-size:14px;font-weight:600;">✓ Submission confirmed</p>
      <p style="margin:4px 0 0;color:#166534;font-size:13px;">{days_logged} day(s) logged · {net_str} net hours worked</p>
    </div>

    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-top:20px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Day</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Hours</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Break</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Net</th>
        </tr>
      </thead>
      <tbody>{_entry_rows(entries)}</tbody>
    </table>

    <p style="color:#6b7280;font-size:13px;margin-top:20px;">
      Your manager has been notified. If you need to make changes, contact your administrator or email
      <a href="mailto:support@timekeepinghub.com" style="color:#3b82f6;text-decoration:none;">support@timekeepinghub.com</a>
    </p>
    """
    _send(
        to=employee.email,
        subject=f"✓ Timesheet Submitted — {week_label}",
        html_body=_base_template("Timesheet Submitted", week_label, content),
    )


def send_reminder_email(employee, week_start_formatted: str, company_name: str) -> bool:
    first_name = employee.full_name.split()[0]
    content = f"""
    <p style="color:#374151;font-size:15px;">Hi <strong>{first_name}</strong>,</p>
    <p style="color:#374151;font-size:15px;">
      This is a friendly reminder that your timesheet for the week of
      <strong>{week_start_formatted}</strong> has not yet been submitted.
    </p>
    <div style="text-align:center;margin:32px 0;">
      <a href="https://timekeepinghub.com/#/dashboard"
         style="background:#1d4ed8;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:15px;font-weight:600;display:inline-block;">
        Submit My Timesheet
      </a>
    </div>
    <p style="color:#6b7280;font-size:13px;">
      If you have already submitted, please ignore this message.
    </p>
    <p style="color:#6b7280;font-size:13px;">Thanks,<br><strong>{company_name} Admin Team</strong></p>
    """
    return _send(
        to=employee.email,
        subject="Reminder: Please submit your timesheet for this week",
        html_body=_base_template(
            "Timesheet Reminder",
            f"Week of {week_start_formatted}",
            content,
        ),
    )


def send_password_reset_email(user, reset_url: str) -> bool:
    first_name = user.full_name.split()[0]
    content = f"""
    <p style="color:#374151;font-size:15px;">Hi <strong>{first_name}</strong>,</p>
    <p style="color:#374151;font-size:15px;">
      We received a request to reset your password. Click the button below — this link expires in <strong>1 hour</strong>.
    </p>
    <div style="text-align:center;margin:32px 0;">
      <a href="{reset_url}"
         style="background:#1d4ed8;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:15px;font-weight:600;display:inline-block;">
        Reset My Password
      </a>
    </div>
    <p style="color:#6b7280;font-size:13px;">
      If you didn't request this, you can safely ignore this email — your password won't change.
    </p>
    """
    return _send(
        to=user.email,
        subject="Reset your TimekeepingHub password",
        html_body=_base_template("Reset your password", "This link expires in 1 hour", content),
    )


def send_submission_alert_to_admin(employee, admin_email: str, week_label: str, entries: list, totals: dict):
    """Notification email to admin when an employee submits their timesheet."""
    total_net = totals["net"]
    net_str = f"{int(total_net // 60)}h {int(total_net % 60)}m"
    days_logged = len([e for e in entries if e.clock_out])

    content = f"""
    <p style="color:#374151;font-size:15px;">
      <strong>{employee.full_name}</strong> has submitted their timesheet for <strong>{week_label}</strong>.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin:20px 0;">
      <tr style="background:#f9fafb;">
        <td style="padding:12px 16px;font-size:13px;color:#6b7280;">Employee</td>
        <td style="padding:12px 16px;font-size:14px;font-weight:600;color:#111827;">{employee.full_name}</td>
      </tr>
      <tr>
        <td style="padding:12px 16px;font-size:13px;color:#6b7280;border-top:1px solid #f3f4f6;">Email</td>
        <td style="padding:12px 16px;font-size:14px;color:#111827;border-top:1px solid #f3f4f6;">{employee.email}</td>
      </tr>
      <tr style="background:#f9fafb;">
        <td style="padding:12px 16px;font-size:13px;color:#6b7280;border-top:1px solid #f3f4f6;">Week</td>
        <td style="padding:12px 16px;font-size:14px;color:#111827;border-top:1px solid #f3f4f6;">{week_label}</td>
      </tr>
      <tr>
        <td style="padding:12px 16px;font-size:13px;color:#6b7280;border-top:1px solid #f3f4f6;">Days logged</td>
        <td style="padding:12px 16px;font-size:14px;color:#111827;border-top:1px solid #f3f4f6;">{days_logged}</td>
      </tr>
      <tr style="background:#f9fafb;">
        <td style="padding:12px 16px;font-size:13px;color:#6b7280;border-top:1px solid #f3f4f6;">Net hours</td>
        <td style="padding:12px 16px;font-size:14px;font-weight:700;color:#16a34a;border-top:1px solid #f3f4f6;">{net_str}</td>
      </tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Day</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Hours</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Break</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">Net</th>
        </tr>
      </thead>
      <tbody>{_entry_rows(entries)}</tbody>
    </table>
    """
    _send(
        to=admin_email,
        subject=f"📋 Timesheet Submitted — {employee.full_name} · {week_label}",
        html_body=_base_template(f"{employee.full_name} submitted a timesheet", week_label, content),
    )
