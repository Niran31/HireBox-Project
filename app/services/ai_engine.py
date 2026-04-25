from google import genai
from flask import current_app
import json
import time

def get_client():
    return genai.Client(api_key=current_app.config['GEMINI_API_KEY'])

def rank_candidates(job_description, candidates):
    """
    Ranks candidates based on JD and Resume content using Gemini.
    candidates: List of Candidate objects (with resume_text).
    Returns: List of (Candidate, Score, Rationale)
    Includes retry logic with exponential backoff for rate limits (429 errors).
    """
    results = []
    
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        current_app.logger.error("GEMINI_API_KEY is not set. Cannot rank candidates.")
        for candidate in candidates:
             candidate.rank_score = 0
             results.append((candidate, 0, "Error: GEMINI_API_KEY is not configured in the environment."))
        return results
        
    try:
        client = get_client()
    except Exception as e:
        current_app.logger.error(f"Error initializing Gemini client: {e}")
        for candidate in candidates:
             candidate.rank_score = 0
             results.append((candidate, 0, f"Error: {str(e)}"))
        return results
        
    # Prepare batch input
    candidates_data = {}
    for cand in candidates:
        # Limit resume text length to avoid context window issues if necessary, 
        # though Gemini has a large window. Truncating to 20k chars is safe.
        candidates_data[cand.id] = cand.resume_text[:20000] if cand.resume_text else ""

    prompt = f"""
    Act as an expert HR Recruiter.
    
    Job Description:
    {job_description}
    
    You have been provided with a list of candidates and their resumes in JSON format below.
    Map of Candidate ID to Resume Text:
    {json.dumps(candidates_data, indent=2)}
    
    Task:
    1. Analyze all candidates against the Job Description.
    2. Assign a relevance score (0-100) for EACH candidate.
    3. Provide a brief rationale for EACH candidate.
    
    Output format:
    Return a SINGLE JSON object where keys are Candidate IDs (as strings) and values are objects containing "score" and "rationale".
    Example:
    {{
        "1": {{ "score": 85, "rationale": "..." }},
        "2": {{ "score": 40, "rationale": "..." }}
    }}
    """
    
    max_retries = 4
    base_delay = 15  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse response
            text_response = response.text
            # Cleanup markdown if present (though response_mime_type should handle it)
            clean_text = text_response.replace('```json', '').replace('```', '')
            batch_results = json.loads(clean_text)
            
            # Update candidates
            for candidate in candidates:
                cand_id_str = str(candidate.id)
                if cand_id_str in batch_results:
                    data = batch_results[cand_id_str]
                    candidate.rank_score = data.get('score', 0)
                    results.append((candidate, candidate.rank_score, data.get('rationale', '')))
                else:
                    current_app.logger.warning(f"Candidate {candidate.id} not found in batch response.")
                    candidate.rank_score = 0
                    results.append((candidate, 0, "Error: Not ranked in batch"))
            
            return results
                    
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or '503' in error_str or 'UNAVAILABLE' in error_str:
                wait_time = base_delay * (2 ** attempt)  # 15s, 30s, 60s, 120s
                current_app.logger.warning(
                    f"Rate limited or server overloaded on ranking attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
                continue
            else:
                current_app.logger.error(f"Error in batch ranking: {e}")
                for candidate in candidates:
                     results.append((candidate, 0, f"Batch Error: {str(e)}"))
                return results
    
    # All retries exhausted
    current_app.logger.error("Max retries exceeded for rank_candidates due to rate limiting or server overload.")
    for candidate in candidates:
        candidate.rank_score = 0
        results.append((candidate, 0, "Error: API server overloaded. Please try again later."))
            
    return results
