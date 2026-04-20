from google import genai
from flask import current_app
import json
from dotenv import dotenv_values

def generate_questions(job_description, resume_text, count=5):
    """
    Generates interview questions based on JD and Resume.
    """
    config = dotenv_values(".env")
    api_key = config.get('GEMINI_API_KEY') or current_app.config.get('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Act as an expert Technical Interviewer.
    
    Job Description:
    {job_description}
    
    Candidate Resume:
    {resume_text}
    
    Task:
    Generate {count} interview questions to evaluate the candidate's fit for this role.
    Include a mix of technical and behavioral questions.
    
    Output format JSON array of strings:
    ["Question 1", "Question 2", ...]
    """
    
    max_retries = 4
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt
            )
            text_response = response.text
            questions = json.loads(text_response.replace('```json', '').replace('```', ''))
            return questions
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or '503' in error_str or 'UNAVAILABLE' in error_str:
                import time
                wait_time = base_delay * (2 ** attempt)
                current_app.logger.warning(f"Rate limited or 503 on question generation attempt {attempt + 1}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                current_app.logger.error(f"Error generating questions: {e}")
                break
                
    # Fallback questions if API fails
    return [
        "Tell me about yourself.",
        "Why are you interested in this role?",
        "Describe a challenging project you worked on.",
        "What are your strengths and weaknesses?",
        "Where do you see yourself in 5 years?"
    ]
