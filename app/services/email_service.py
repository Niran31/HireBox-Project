import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_interview_invite(candidate_email, candidate_name, job_title, interview_link):
    """
    Sends an automated interview invitation email to the candidate.
    Uses the SendGrid HTTP API to bypass Hugging Face SMTP blocks and allows Single Sender Verification.
    """
    api_key = os.environ.get('SENDGRID_API_KEY')
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER')

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

    if not api_key or not sender_email:
        current_app.logger.warning(
            f"SENDGRID_API_KEY or MAIL_DEFAULT_SENDER not configured. Mocking email send to {candidate_email}:\n"
            f"--- EMAIL BEGIN ---\n{html_content}\n--- EMAIL END ---"
        )
        return False, "SendGrid API key or sender email missing; email was mocked and logged."

    try:
        message = Mail(
            from_email=sender_email,
            to_emails=candidate_email,
            subject=subject,
            html_content=html_content)
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        # SendGrid typically returns 202 Accepted on success
        if response.status_code in [200, 201, 202]:
            return True, "Email sent successfully."
        else:
            return False, f"SendGrid API failed with status code: {response.status_code}"
            
    except Exception as e:
        current_app.logger.error(f"Failed to send email via SendGrid to {candidate_email}: {e}")
        return False, str(e)

def send_password_reset_email(user_email, user_name, reset_link):
    """
    Sends a password reset email to the user.
    Uses SendGrid HTTP API if configured, otherwise falls back to SMTP server configuration.
    """
    api_key = os.environ.get('SENDGRID_API_KEY')
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER')
    
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

    # 1. Try SendGrid
    if api_key and sender_email:
        try:
            message = Mail(
                from_email=sender_email,
                to_emails=user_email,
                subject=subject,
                html_content=html_content)
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                return True, "Email sent successfully via SendGrid."
        except Exception as e:
            current_app.logger.error(f"SendGrid failed for password reset, trying fallback: {e}")

    # 2. Try SMTP
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if smtp_server and smtp_port and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email or smtp_user
            msg['To'] = user_email
            
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
            server.sendmail(msg['From'], [user_email], msg.as_string())
            server.quit()
            return True, "Email sent successfully via SMTP."
        except Exception as e:
            current_app.logger.error(f"SMTP failed to send email to {user_email}: {e}")
            return False, f"SMTP error: {str(e)}"
            
    # 3. Fallback/Mock
    current_app.logger.warning(
        f"No email provider configured. Mocking password reset email to {user_email}:\n"
        f"--- EMAIL BEGIN ---\n{html_content}\n--- EMAIL END ---"
    )
    return False, "No email configuration found. Email was mocked and logged."

