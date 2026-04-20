from app.models.models import Interview, Candidate
from app.extensions import db
import json
from flask import current_app

def generate_report(interview_id):
    """
    Aggregates all data for an interview and generates a final report.
    """
    interview = Interview.query.get(interview_id)
    if not interview:
        return None
        
    candidate = interview.candidate
    
    # 1. Resume Score (already computed)
    resume_score = candidate.rank_score or 0
    
    # 2. Tech Score (Average of all answer evaluations)
    # Retrieve existing report_data to get answers
    existing_data = {}
    if interview.report_data:
        try:
            existing_data = json.loads(interview.report_data)
        except Exception:
            existing_data = {}
            
    raw_transcript = existing_data.get('answers_log', [])
    processed_transcript = existing_data.get('transcript', [])
    
    # Start with existing processed transcript
    transcript = list(processed_transcript) if processed_transcript else []
    
    # Process and append unique new answers
    if raw_transcript:
        from google import genai
        try:
            from flask import current_app
            client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
        except Exception as e:
            current_app.logger.error(f"Error initializing AI client: {e}")
            client = None

        # Avoid duplicates if raw entries somehow persisted (check by timestamp or question index)
        existing_indices = {item.get('question_index') for item in transcript if 'question_index' in item}
        
        for entry in raw_transcript:
            if entry.get('question_index') not in existing_indices:
                question_text = entry.get('question', '')
                answer_text = entry.get('answer', '')

                # Default values
                score = 50
                feedback = "Analysis unavailable"

                if client and answer_text and len(answer_text) > 5:
                    try:
                        prompt = f"""
                        Evaluate the following interview answer for the role of {candidate.job.title}.
                        
                        Question: {question_text}
                        Answer: {answer_text}
                        
                        Provide a JSON response with:
                        - "score": integer (0-100)
                        - "feedback": string (concise feedback, max 20 words)
                        
                        Strict JSON format only.
                        """
                        response = client.models.generate_content(
                            model='gemini-flash-lite-latest', 
                            contents=prompt
                        )
                        eval_data = json.loads(response.text.replace('```json', '').replace('```', ''))
                        score = eval_data.get('score', 50)
                        feedback = eval_data.get('feedback', 'Feedback unavailable')
                    except Exception as e:
                         current_app.logger.error(f"Error scoring answer: {e}")
                         score = 40 # Penalty for error/empty
                         feedback = "Could not evaluate answer."
                
                entry['score'] = score
                entry['feedback'] = feedback
                transcript.append(entry)
                existing_indices.add(entry.get('question_index'))  # Prevent duplicates within same batch
                
    # Recalculate Tech Score
    if transcript:
        total_score = sum(item.get('score', 0) for item in transcript)
        tech_score = total_score / len(transcript)
    else:
        tech_score = 0.0 # No answers = 0 score
    
    # 3. Real Behavioral Score (computed from actual interview data)
    behavioral_score = _compute_behavioral_score(interview, existing_data, transcript)
    
    # 4. AI-powered Emotion & Speech Analysis
    emotion_analysis, speech_analysis = _analyze_behavioral_signals(transcript, candidate)
    
    # 5. Proctoring Flags
    flags = existing_data.get('integrity_flags', [])
    
    # 50% Interview Performance, 20% Behavioral, 30% Resume Match
    final_score = (resume_score * 0.3) + (tech_score * 0.5) + (behavioral_score * 0.2)
    
    # Penalty for cheating (if flagged during session)
    if interview.status == 'suspended':
        final_score = 0
        flags.append("Interview Suspended due to cheating violations.")

    # 6. Recommendation based on final score
    if final_score >= 75:
        recommendation = "Strong Hire"
    elif final_score >= 55:
        recommendation = "Consider"
    else:
        recommendation = "Not Recommended"

    # 7. Generate AI Executive Summary
    summary_text = "Analysis pending."
    try:
        from google import genai
        from flask import current_app
        client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])

        # Prepare context for AI
        qa_pairs = []
        for t in transcript:
            q = t.get('question', 'Unknown Question')
            a = t.get('answer', 'No answer')
            qa_pairs.append(f"Q: {q}\nA: {a}")
        
        qa_text = "\n\n".join(qa_pairs)
        
        prompt = f"""
        Act as a Senior Technical Recruiter. Write a concise Executive Summary (3-4 sentences) for {candidate.name} applying for {candidate.job.title}.
        
        Interview Data:
        - Resume Score: {resume_score}
        - Technical Score: {tech_score:.1f}
        - Behavioral Score: {behavioral_score:.1f}
        - Integrity Flags: {len(flags)} detected ({', '.join(flags) if flags else 'None'})
        - Recommendation: {recommendation}
        
        Transcript Excerpt:
        {qa_text[:2000]}... (truncated)
        
        Focus on their strengths, weaknesses, and overall recommendation. Do not use asterisks or markdown formatting. Keep it professional.
        """
        
        response = client.models.generate_content(
            model='gemini-flash-lite-latest', 
            contents=prompt
        )
        summary_text = response.text.strip()
        
    except Exception as e:
        current_app.logger.error(f"Error generating summary: {e}")
        summary_text = f"Candidate demonstrated a {emotion_analysis['dominant_emotion'].lower()} demeanor during the interview. Technical answers were assessed with a score of {tech_score:.1f}/100."

    report = {
        "candidate_name": candidate.name,
        "job_role": candidate.job.title if candidate.job else "N/A",
        "final_score": round(final_score, 2),
        "recommendation": recommendation,
        "breakdown": {
            "resume_match": resume_score,
            "technical": round(tech_score, 1),
            "behavioral": round(behavioral_score, 1)
        },
        "transcript": transcript,
        "advanced_analytics": {
            "emotion": emotion_analysis,
            "speech": speech_analysis,
            "answer_relevance": _compute_answer_relevance(transcript)
        },
        "integrity_flags": flags,
        "summary": summary_text
    }
    
    # Save to interview record
    interview.report_data = json.dumps(report)
    interview.score = final_score
    db.session.commit()
    
    return report


def _compute_behavioral_score(interview, existing_data, transcript):
    """
    Computes a real behavioral score based on interview signals:
    - Interview completion (completed = +30, suspended = 0)
    - Answer quality consistency (low variance = better behavioral signals)
    - Answer completeness (answered all questions vs skipped)
    - Proctoring compliance (fewer violations = higher score)
    """
    score = 0.0
    
    # Factor 1: Completion status (max 30 points)
    if interview.status == 'completed':
        score += 30.0
    elif interview.status == 'suspended':
        return 0.0  # Cheating = 0 behavioral score
    else:
        score += 15.0  # Partial/pending
    
    # Factor 2: Answer completeness (max 25 points)
    questions = existing_data.get('questions', [])
    total_questions = len(questions) if questions else 5
    answered_count = len(transcript)
    if total_questions > 0:
        completeness_ratio = min(answered_count / total_questions, 1.0)
        score += completeness_ratio * 25.0
    
    # Factor 3: Answer quality consistency (max 25 points)
    # Low standard deviation in scores = consistent performance = good behavioral signal
    if transcript and len(transcript) >= 2:
        scores = [item.get('score', 50) for item in transcript]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        # Lower std_dev = more consistent = higher score
        # std_dev of 0 = 25 points, std_dev of 40+ = 0 points
        consistency_score = max(0, 25 * (1 - std_dev / 40))
        score += consistency_score
    elif transcript:
        score += 15.0  # Only one answer, give moderate score
    
    # Factor 4: Proctoring compliance (max 20 points)
    integrity_flags = existing_data.get('integrity_flags', [])
    violation_count = len(integrity_flags)
    if violation_count == 0:
        score += 20.0
    elif violation_count == 1:
        score += 10.0
    elif violation_count == 2:
        score += 5.0
    # 3+ violations = 0 bonus
    
    return min(score, 100.0)


def _analyze_behavioral_signals(transcript, candidate):
    """
    Analyzes behavioral signals from the transcript using AI.
    Returns (emotion_analysis, speech_analysis) dicts.
    """
    # Default values
    emotion_analysis = {
        "dominant_emotion": "Neutral",
        "confidence_level": "Moderate",
        "stress_markers": "Not detected"
    }
    
    speech_analysis = {
        "clarity": 75,
        "pace": "Normal",
        "filler_words_detected": "Not analyzed"
    }
    
    if not transcript:
        return emotion_analysis, speech_analysis
    
    try:
        from google import genai
        from flask import current_app
        client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
        
        # Prepare answer text for analysis
        answers = [t.get('answer', '') for t in transcript if t.get('answer')]
        answer_text = "\n\n".join(answers[:5])  # Limit to 5 answers
        
        prompt = f"""
        Analyze the following interview answers for behavioral signals. The candidate is applying for {candidate.job.title}.
        
        Answers:
        {answer_text[:3000]}
        
        Return a JSON object with:
        {{
            "emotion": {{
                "dominant_emotion": "one of: Confident, Calm, Nervous, Enthusiastic, Neutral",
                "confidence_level": "one of: High, Moderate, Low",
                "stress_markers": "one of: None detected, Minimal, Moderate, Significant"
            }},
            "speech": {{
                "clarity": integer 0-100,
                "pace": "one of: Slow, Normal, Fast",
                "filler_words_detected": "one of: None, Minimal, Moderate, Frequent"
            }}
        }}
        
        Strict JSON only.
        """
        
        response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        result = json.loads(response.text.replace('```json', '').replace('```', ''))
        emotion_analysis = result.get('emotion', emotion_analysis)
        speech_analysis = result.get('speech', speech_analysis)
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing behavioral signals: {e}")
    
    return emotion_analysis, speech_analysis


def _compute_answer_relevance(transcript):
    """Generates a brief summary of answer relevance based on scores."""
    if not transcript:
        return "No answers recorded for relevance analysis."
    
    scores = [item.get('score', 0) for item in transcript]
    avg = sum(scores) / len(scores) if scores else 0
    
    if avg >= 80:
        return "Answers were highly relevant and demonstrated strong alignment with the job requirements."
    elif avg >= 60:
        return "Answers were generally relevant, with some areas showing room for deeper technical knowledge."
    elif avg >= 40:
        return "Answers showed partial understanding. Several responses lacked depth or specificity."
    else:
        return "Answers showed limited relevance to the job requirements. Significant gaps in knowledge were observed."
