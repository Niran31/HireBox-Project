import os
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
