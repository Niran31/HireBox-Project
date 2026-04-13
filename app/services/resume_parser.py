import os
import pypdf
import docx
import json
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
    """
    if not resume_text or not api_key:
        return None
    
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
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        
        result = json.loads(response.text.replace('```json', '').replace('```', ''))
        return result
    except Exception as e:
        current_app.logger.error(f"Error extracting candidate info: {e}")
        return None
