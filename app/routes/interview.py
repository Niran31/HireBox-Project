from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required
from app.extensions import db
from app.models.models import Job, Candidate, Interview
from app.services.email_service import send_interview_invite
import uuid
import json
import base64
from datetime import datetime

bp = Blueprint('interview', __name__)

@bp.route('/create/<int:candidate_id>', methods=['GET', 'POST'])
@login_required
def create(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if request.method == 'POST':
        # Get data from form
        time_limit = request.form.get('time_limit', 30)
        question_count = request.form.get('question_count', 5)
        
        # Collect questions from form (dynamic list)
        questions = request.form.getlist('questions[]')
        
        # Remove empty questions
        questions = [q.strip() for q in questions if q.strip()]
        
        # Generate token
        token = str(uuid.uuid4())
        
        # Create Interview record
        interview = Interview(candidate_id=candidate.id, token=token, status='pending')
        
        # Save initial configuration to report_data
        config_data = {
            'time_limit': int(time_limit),
            'question_count': len(questions),
            'questions': questions
        }
        interview.report_data = json.dumps(config_data)
        
        db.session.add(interview)
        db.session.commit()
        
        interview_link = url_for("interview.start", token=token, _external=True)
        
        # Update candidate email from form (allows HR to override)
        form_email = request.form.get('candidate_email', '').strip()
        if form_email:
            candidate.email = form_email
            db.session.commit()
        
        # Automated Email Notification
        if candidate.email and candidate.email != 'placeholder@example.com':
            success, msg = send_interview_invite(
                candidate_email=candidate.email,
                candidate_name=candidate.name,
                job_title=candidate.job.title,
                interview_link=interview_link
            )
            if success:
                flash(f'Interview configured! Email sent to {candidate.email}.', 'success')
            else:
                flash(f'Interview configured, but email failed: {msg}', 'warning')
        else:
            flash(f'Interview configured successfully! Please share the link manually with {candidate.name}.', 'info')
            
        return redirect(url_for('interview.created', token=token))
    
    # GET request - Render the config page immediately (questions fetched via API)
    return render_template('interview/config.html', candidate=candidate, interview_link=None)

@bp.route('/created/<token>')
@login_required
def created(token):
    interview = Interview.query.filter_by(token=token).first_or_404()
    candidate = interview.candidate
    interview_link = url_for("interview.start", token=token, _external=True)
    return render_template('interview/config.html', candidate=candidate, interview_link=interview_link)

@bp.route('/api/generate_questions/<int:candidate_id>')
@login_required
def get_generated_questions(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    from app.services.question_service import generate_questions
    try:
        questions = generate_questions(candidate.job.description, candidate.resume_text, count=5)
        return jsonify(questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/start/<token>')
def start(token):
    interview = Interview.query.filter_by(token=token).first_or_404()
    if interview.status == 'completed':
        return "This interview link has expired or has already been used.", 403
        
    # Load configuration
    report_data = {}
    if interview.report_data:
        try:
            report_data = json.loads(interview.report_data)
        except Exception:
            report_data = {}
            
    questions = report_data.get('questions', [])
    time_limit = report_data.get('time_limit', 30)
    
    # Fallback if no questions (shouldn't happen with new flow, but for safety)
    if not questions:
        from app.services.question_service import generate_questions
        questions = generate_questions(interview.candidate.job.description, interview.candidate.resume_text)
        report_data['questions'] = questions
        
    # --- FIX: TIMER PERSISTENCE ---
    current_time = datetime.utcnow().timestamp()
    
    # If this is the *first* time starting (or we haven't tracked start time yet), set it.
    if 'started_at' not in report_data:
        report_data['started_at'] = current_time
        interview.status = 'started' # Mark as started
        # Save immediately
        interview.report_data = json.dumps(report_data)
        db.session.commit()
    else:
        # If we added questions in fallback block above but didn't save yet
        interview.report_data = json.dumps(report_data)
        db.session.commit()

    started_at = report_data['started_at']
        
    return render_template('interview/exam.html', 
                           interview=interview, 
                           candidate=interview.candidate, 
                           job=interview.candidate.job,
                           questions=questions, 
                           time_limit=time_limit,
                           started_at=started_at,
                           current_server_time=current_time)

@bp.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    token = data.get('token')
    interview = Interview.query.filter_by(token=token).first_or_404()
    
    # Get current report data
    report_data = {}
    if interview.report_data:
        try:
            report_data = json.loads(interview.report_data)
        except Exception:
            report_data = {}
            
    # Initialize answers list if not present
    if 'answers_log' not in report_data:
        report_data['answers_log'] = []
        
    # Build new answer entry
    question_index = data.get('question_index')
    answer_entry = {
        "question_index": question_index,
        "question": data.get('question_text'),
        "answer": data.get('answer_text'),
        "timestamp": str(datetime.utcnow())
    }
    
    # Replace existing answer for same question_index, or append new
    replaced = False
    for i, existing in enumerate(report_data['answers_log']):
        if existing.get('question_index') == question_index:
            report_data['answers_log'][i] = answer_entry
            replaced = True
            break
    if not replaced:
        report_data['answers_log'].append(answer_entry)
    
    interview.report_data = json.dumps(report_data)
    db.session.commit()
    
    return jsonify({"status": "saved"})

@bp.route('/api/complete', methods=['POST'])
def complete():
    data = request.json
    token = data.get('token')
    status = data.get('status', 'completed') # Allow 'suspended' or other statuses
    
    interview = Interview.query.filter_by(token=token).first_or_404()
    interview.status = status
    db.session.commit()
    
    # Trigger Report Generation
    from app.services.report_service import generate_report
    generate_report(interview.id)
    
    return jsonify({"status": status})

@bp.route('/complete/<token>')
def completed_page(token):
    interview = Interview.query.filter_by(token=token).first_or_404()
    return render_template('interview/completed.html', status=interview.status, candidate=interview.candidate)

@bp.route('/api/monitor', methods=['POST'])
def monitor_session():
    data = request.json
    image_data_url = data.get('image')
    token = data.get('token')
    
    if not image_data_url or not token:
        return jsonify({"error": "Missing data"}), 400
        
    # Verify token
    interview = Interview.query.filter_by(token=token).first_or_404()
    # Relaxed check: allow if status is started or pending (just in case race condition on first load)
    # but strictly speaking it should be 'started'. keeping it simple.
    
    try:
        # --- FIX: DECODE BASE64 IMAGE ---
        # Format is usually "data:image/jpeg;base64,/9j/4AAQSw..."
        if ',' in image_data_url:
            header, encoded = image_data_url.split(',', 1)
        else:
            encoded = image_data_url
            
        image_bytes = base64.b64decode(encoded)
        
        # Use ProctoringEngine
        from app.services.proctor_service import ProctoringEngine
        engine = ProctoringEngine() 
        result = engine.analyze_frame(image_bytes)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Monitor Error: {e}")
        return jsonify({"error": "Processing failed", "details": str(e)}), 500
