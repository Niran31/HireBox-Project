import os
import re
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


def extract_candidate_info(resume_text, api_key=None):
    """
    Extracts candidate info using Gemini AI for accurate parsing.
    Falls back to regex/text parsing if AI fails or key is missing.
    Returns dict with: name, email, phone, skills
    """
    if not resume_text:
        return None
    
    result = {
        'name': None,
        'email': 'N/A',
        'phone': 'N/A',
        'skills': ''
    }
    
    # Try using Gemini API first for accurate extraction
    from dotenv import dotenv_values
    config = dotenv_values(".env")
    current_api_key = api_key or config.get('GEMINI_API_KEY') or (current_app.config.get('GEMINI_API_KEY') if current_app else None)
    
    if current_api_key:
        from google import genai
        import json
        import time
        client = genai.Client(api_key=current_api_key)
        prompt = f"""
        Extract the following information from the resume text provided below:
        - name: The candidate's full name. Fix any weird spacing (e.g. N I R A N J A N -> Niranjan) and capitalize properly. Do not include titles or section headers.
        - email: The candidate's email address.
        - phone: The candidate's phone number.
        - skills: A comma-separated list of the candidate's technical skills.
        
        Return ONLY a valid JSON object with these exact keys: "name", "email", "phone", "skills".
        If a value is not found, use "N/A" (or empty string for skills).
        
        Resume Text:
        {resume_text[:5000]}
        """
        
        max_retries = 3
        base_delay = 15
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={'response_mime_type': 'application/json'}
                )
                data = json.loads(response.text.replace('```json', '').replace('```', ''))
                
                if data.get('name') and data.get('name') != 'N/A' and len(data.get('name')) < 50:
                    return {
                        'name': data.get('name'),
                        'email': data.get('email', 'N/A'),
                        'phone': data.get('phone', 'N/A'),
                        'skills': data.get('skills', '')
                    }
                break # Name missing or invalid, fallback to regex
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    wait_time = base_delay * (2 ** attempt)
                    if current_app:
                        current_app.logger.warning(f"Rate limited on parsing attempt {attempt+1}. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    if current_app:
                        current_app.logger.warning(f"Gemini AI extraction failed, falling back to regex: {e}")
                    break

    lines = resume_text.strip().split('\n')
    
    # Extract email using regex
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, resume_text)
    if email_match:
        result['email'] = email_match.group(0)
    
    # Extract phone using regex (various formats)
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_match = re.search(phone_pattern, resume_text)
    if phone_match:
        result['phone'] = phone_match.group(0).strip()
    
    # Extract name - typically the first non-empty line of a resume
    for line in lines:
        clean_line = line.strip()
        # Skip empty lines, lines that look like headers/titles, emails, phones
        if not clean_line:
            continue
        if '@' in clean_line or re.match(r'^[\d\+\(]', clean_line):
            continue
        if len(clean_line) > 50:  # Name shouldn't be too long
            continue
        if clean_line.lower() in ['resume', 'curriculum vitae', 'cv', 'profile']:
            continue
        # This is likely the candidate's name
        result['name'] = clean_line
        break
    
    # Extract skills - look for a skills section
    skills_keywords = ['skills', 'technical skills', 'key skills', 'core competencies', 
                       'technologies', 'tools', 'programming languages']
    
    in_skills_section = False
    skills_lines = []
    
    for line in lines:
        clean_line = line.strip().lower()
        
        # Check if we've entered a skills section
        if any(kw in clean_line for kw in skills_keywords):
            in_skills_section = True
            # If skills are on the same line after a colon
            if ':' in line:
                skills_part = line.split(':', 1)[1].strip()
                if skills_part:
                    skills_lines.append(skills_part)
            continue
        
        # If we're in the skills section, collect lines
        if in_skills_section:
            if clean_line and not any(kw in clean_line for kw in 
                ['experience', 'education', 'project', 'certification', 'achievement',
                 'objective', 'summary', 'reference', 'hobby', 'interest', 'language']):
                skills_lines.append(line.strip())
            else:
                if skills_lines:  # We've left the skills section
                    break
    
    if skills_lines:
        # Clean up and join skills
        all_skills = ', '.join(skills_lines)
        # Remove bullet points, dashes, etc.
        all_skills = re.sub(r'[•▪▸\-–—]', ',', all_skills)
        all_skills = re.sub(r'\s*,\s*', ', ', all_skills)
        all_skills = re.sub(r',\s*,', ',', all_skills)
        result['skills'] = all_skills.strip(', ')
    
    return result
