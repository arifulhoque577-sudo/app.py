"""
Sends the password-reset code by email.

Set ONE of these on your server (Render > Environment):

  Option A - Brevo (HTTPS API, works on Render free tier, 300 emails/day free):
      BREVO_API_KEY      = your Brevo API key
      MAIL_FROM_EMAIL    = a sender address you verified in Brevo
      MAIL_FROM_NAME     = AI Scalper            (optional)

  Option B - plain SMTP (many hosts, incl. Render free tier, block SMTP ports):
      SMTP_USER, SMTP_PASS  (and optionally SMTP_HOST=smtp.gmail.com, SMTP_PORT=465, MAIL_FROM_EMAIL)
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests


def configured():
    return bool(os.environ.get("BREVO_API_KEY") or (os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS")))


def _html(code, minutes):
    return (f"<div style='font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px'>"
            f"<h2 style='margin:0 0 8px'>AI Scalper</h2><p>Use this code to reset your password:</p>"
            f"<p style='font-size:34px;letter-spacing:8px;font-weight:700;margin:16px 0'>{code}</p>"
            f"<p style='color:#6b7280'>It expires in {minutes} minutes. If you did not request it, you can ignore this email.</p></div>")


def send_code(to_email, code, minutes=10):
    """Returns (ok, error_message)."""
    if not to_email:
        return False, "This account has no email address."
    sender = os.environ.get("MAIL_FROM_EMAIL") or os.environ.get("SMTP_USER") or ""
    name = os.environ.get("MAIL_FROM_NAME", "AI Scalper")
    subject = f"Your AI Scalper reset code: {code}"
    try:
        if os.environ.get("BREVO_API_KEY"):
            r = requests.post("https://api.brevo.com/v3/smtp/email", timeout=15,
                              headers={"api-key": os.environ["BREVO_API_KEY"], "content-type": "application/json", "accept": "application/json"},
                              json={"sender": {"name": name, "email": sender}, "to": [{"email": to_email}],
                                    "subject": subject, "htmlContent": _html(code, minutes)})
            if r.status_code >= 300:
                return False, f"Email provider error {r.status_code}"
            return True, ""
        host, port = os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, f"{name} <{sender}>", to_email
        msg.set_content(f"Your AI Scalper password reset code is {code}. It expires in {minutes} minutes.")
        msg.add_alternative(_html(code, minutes), subtype="html")
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as s:
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls(context=ssl.create_default_context()); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"Could not send email ({type(e).__name__})"
