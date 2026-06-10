import os
import smtplib
import json
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def _send_email_http_or_smtp(to_email, subject, html_content):
    """
    Centralized email delivery service that attempts:
    1. Resend HTTP API (Port 443, highly reliable in Hugging Face sandbox)
    2. SendGrid HTTP API (Port 443, reliable in Hugging Face sandbox)
    3. SMTP standard delivery (often blocked in cloud sandboxes like Hugging Face)
    """
    resend_api_key = os.environ.get('RESEND_API_KEY')
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER')

    # 1. Try Resend HTTP API
    if resend_api_key:
        try:
            # Resend sandbox restricts from email to onboarding@resend.dev unless domain is verified
            from_addr = sender_email or "onboarding@resend.dev"
            if "re_" in resend_api_key and not sender_email:
                from_addr = "onboarding@resend.dev"
                
            from_str = f"HireBox <{from_addr}>"
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-urllib/3.0"
            }
            payload = {
                "from": from_str,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in [200, 201, 202]:
                    return True, "Email sent successfully via Resend API."
        except urllib.error.HTTPError as e:
            current_app.logger.error(f"Resend HTTP Error: {e.code} {e.read().decode('utf-8')}")
        except Exception as e:
            current_app.logger.error(f"Resend failed: {e}")

    # 2. Try SendGrid HTTP API
    if sendgrid_api_key and sender_email:
        try:
            message = Mail(
                from_email=sender_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content)
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                return True, "Email sent successfully via SendGrid."
        except Exception as e:
            current_app.logger.error(f"SendGrid failed: {e}")

    # 3. Try SMTP Fallback
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if smtp_server and smtp_port and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email or smtp_user
            msg['To'] = to_email
            
            part = MIMEText(html_content, 'html')
            msg.attach(part)
            
            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_server, port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, port, timeout=10)
                if port == 587:
                    server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.sendmail(msg['From'], [to_email], msg.as_string())
            server.quit()
            return True, "Email sent successfully via SMTP."
        except Exception as e:
            current_app.logger.error(f"SMTP failed: {e}")
            return False, f"SMTP error: {str(e)}"

    # 4. Mock Output
    current_app.logger.warning(
        f"No email provider configured or all failed. Mocking email send to {to_email}:\n"
        f"--- EMAIL BEGIN ---\n{html_content}\n--- EMAIL END ---"
    )
    return False, "No email configuration found or all delivery attempts failed."

def send_interview_invite(candidate_email, candidate_name, job_title, interview_link):
    """
    Sends an automated interview invitation email to the candidate.
    """
    subject = f"Interview Invitation: {job_title} at HireBox"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <h2>Hello {candidate_name},</h2>
            <p>We are excited to invite you to the next stage of our hiring process for the <strong>{job_title}</strong> position.</p>
            <p>Please click the button below to start your AI-proctored interview session.</p>
            <p style="margin: 30px 0;">
                <a href="{interview_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Start Interview</a>
            </p>
            <p><strong>Note:</strong> You will need a working webcam and microphone. Please ensure you are in a quiet environment.</p>
            <p>Best regards,<br>The HireBox Team</p>
        </body>
    </html>
    """
    return _send_email_http_or_smtp(candidate_email, subject, html_content)

def send_password_reset_email(user_email, user_name, reset_link):
    """
    Sends a password reset email to the user.
    """
    subject = "Reset Your Password - HireBox"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <h2>Hello {user_name},</h2>
            <p>You requested to reset your password for your HireBox account.</p>
            <p>Please click the button below to reset your password. This link is valid for 30 minutes.</p>
            <p style="margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
            </p>
            <p>If you did not make this request, you can safely ignore this email.</p>
            <p>Best regards,<br>The HireBox Team</p>
        </body>
    </html>
    """
    return _send_email_http_or_smtp(user_email, subject, html_content)


