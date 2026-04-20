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
    Extracts candidate info using regex/text parsing instead of AI.
    This avoids consuming Gemini API quota for simple data extraction.
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
