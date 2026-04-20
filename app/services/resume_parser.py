import os
import pypdf
import docx
import json
import time
from flask import current_app

def parse_resume(filepath):
    """
    Extracts text from a resume file (PDF or DOCX).
    """
    ext = filepath.rsplit('.', 1)[1].lower()
    text = ""
    
    try:
        if ext == 'pdf':
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        elif ext == 'docx':
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'txt':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        current_app.logger.error(f"Error parsing resume {filepath}: {e}")
        return None

    return text.strip()


def extract_candidate_info(resume_text, api_key):
    """
    Uses Gemini AI to extract structured candidate information from resume text.
    Returns dict with: name, email, phone, skills
    Includes retry logic with exponential backoff for rate limits (429 errors).
    """
    if not resume_text or not api_key:
        return None
    
    max_retries = 4
    base_delay = 15  # seconds - generous delay for free tier rate limits
    
    for attempt in range(max_retries):
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            Extract the following information from this resume text. Be precise and extract only what is explicitly stated.
            
            Resume Text:
            {resume_text[:8000]}
            
            Return a JSON object with these keys:
            - "name": Full name of the candidate (string)
            - "email": Email address (string, or "N/A" if not found)
            - "phone": Phone number (string, or "N/A" if not found)
            - "skills": Comma-separated list of key technical skills (string, max 10 skills)
            
            Return ONLY valid JSON, no other text.
            """
            
            response = client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            result = json.loads(response.text.replace('```json', '').replace('```', ''))
            return result
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                wait_time = base_delay * (2 ** attempt)  # 15s, 30s, 60s, 120s
                current_app.logger.warning(
                    f"Rate limited on attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
                continue
            else:
                current_app.logger.error(f"Error extracting candidate info: {e}")
                return None
    
    current_app.logger.error("Max retries exceeded for extract_candidate_info due to rate limiting.")
    return None
