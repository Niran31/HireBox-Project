import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os
from dotenv import dotenv_values

def send_interview_invite(candidate_email, candidate_name, job_title, interview_link):
    """
    Sends an automated interview invitation email to the candidate.
    Uses smtplib. If no SMTP credentials are provided, it logs the email securely.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@hirebox.com')

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

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = candidate_email

    msg.attach(MIMEText(html_content, "html"))

    if not smtp_server or not smtp_user or not smtp_password:
        current_app.logger.warning(
            f"SMTP not configured. Mocking email send to {candidate_email}:\n"
            f"--- EMAIL BEGIN ---\n{html_content}\n--- EMAIL END ---"
        )
        return False, "SMTP credentials missing; email was mocked and logged."

    try:
        # Add a 5-second timeout to prevent hanging if the host blocks SMTP ports (e.g. Hugging Face)
        server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=5)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, candidate_email, msg.as_string())
        server.quit()
        return True, "Email sent successfully."
    except TimeoutError:
        current_app.logger.error(f"SMTP connection timed out. Host provider may block port {smtp_port}.")
        return False, "Connection timed out. Your hosting provider (like Hugging Face) likely blocks email ports."
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {candidate_email}: {e}")
        return False, str(e)
