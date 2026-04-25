import resend
from flask import current_app
import os
from dotenv import dotenv_values

def send_interview_invite(candidate_email, candidate_name, job_title, interview_link):
    """
    Sends an automated interview invitation email to the candidate.
    Uses the Resend HTTP API to bypass Hugging Face SMTP blocks.
    """
    resend.api_key = os.environ.get('RESEND_API_KEY')
    
    # If the user hasn't set a custom sender, use Resend's testing email
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER', 'onboarding@resend.dev')
    
    # Resend does not allow sending FROM @gmail.com or other unverified domains.
    if sender_email.endswith('@gmail.com'):
        sender_email = 'onboarding@resend.dev'

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

    if not resend.api_key:
        current_app.logger.warning(
            f"RESEND_API_KEY not configured. Mocking email send to {candidate_email}:\n"
            f"--- EMAIL BEGIN ---\n{html_content}\n--- EMAIL END ---"
        )
        return False, "API key missing; email was mocked and logged."

    try:
        params = {
            "from": sender_email,
            "to": [candidate_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        return True, "Email sent successfully."
    except Exception as e:
        current_app.logger.error(f"Failed to send email via Resend to {candidate_email}: {e}")
        return False, str(e)
