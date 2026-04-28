import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.warning("Email not configured — skipping send to %s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
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


def _base_template(title: str, heading: str, subheading: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <!-- Header -->
        <tr>
          <td style="background:#1d4ed8;padding:28px 32px;">
            <p style="margin:0;color:#bfdbfe;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Fourhub Timesheet</p>
            <h1 style="margin:6px 0 0;color:#ffffff;font-size:22px;font-weight:700;">{heading}</h1>
            <p style="margin:6px 0 0;color:#93c5fd;font-size:14px;">{subheading}</p>
          </td>
        </tr>
        <!-- Body -->
        <tr><td style="padding:28px 32px;">{content}</td></tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f3f4f6;background:#f9fafb;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">This is an automated notification from Fourhub Timesheet. Please do not reply to this email.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_submission_confirmation(employee, week_label: str, entries: list, totals: dict):
    """Email to the employee confirming their submission."""
    total_net = totals["net"]
    net_str = f"{int(total_net // 60)}h {int(total_net % 60)}m"
    days_logged = len([e for e in entries if e.clock_out])

    content = f"""
    <p style="color:#374151;font-size:15px;">Hi <strong>{employee.full_name.split()[0]}</strong>,</p>
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

    <p style="color:#6b7280;font-size:13px;margin-top:20px;">Your manager has been notified. If you need to make changes, please contact your administrator.</p>
    """

    send_email(
        to=employee.email,
        subject=f"✓ Timesheet Submitted — {week_label}",
        html_body=_base_template("Submission Confirmed", "Timesheet Submitted", week_label, content),
    )


def send_submission_alert_to_admin(employee, admin_email: str, week_label: str, entries: list, totals: dict):
    """Email to admin/manager notifying of a new submission."""
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

    send_email(
        to=admin_email,
        subject=f"📋 Timesheet Submitted by {employee.full_name} — {week_label}",
        html_body=_base_template("New Submission", f"{employee.full_name} submitted a timesheet", week_label, content),
    )
