import json
import csv
from io import StringIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from app.models.models import Job, Candidate, User, Interview
from app.utils.forms import JobForm, CandidateUploadForm
import os
import time
import threading
from app.extensions import db
from app.services.file_service import save_file
from app.services.resume_parser import parse_resume, extract_candidate_info
from app.services.ai_engine import rank_candidates

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    # Basic stats
    total_candidates = Candidate.query.count()
    interviews_completed = Interview.query.filter_by(status='completed').count()
    
    # Chart data: Score distribution buckets
    all_candidates = Candidate.query.filter(Candidate.rank_score.isnot(None)).all()
    score_buckets = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
    for c in all_candidates:
        s = c.rank_score or 0
        if s <= 20: score_buckets[0] += 1
        elif s <= 40: score_buckets[1] += 1
        elif s <= 60: score_buckets[2] += 1
        elif s <= 80: score_buckets[3] += 1
        else: score_buckets[4] += 1
    
    # Chart data: Interview status breakdown
    interviews_pending = Interview.query.filter_by(status='pending').count()
    interviews_started = Interview.query.filter_by(status='started').count()
    interviews_suspended = Interview.query.filter_by(status='suspended').count()
    not_scheduled = total_candidates - Interview.query.count()
    
    interview_statuses = {
        'Not Scheduled': max(not_scheduled, 0),
        'Pending': interviews_pending,
        'In Progress': interviews_started,
        'Completed': interviews_completed,
        'Suspended': interviews_suspended
    }
    
    # Top candidates (highest final interview scores)
    top_candidates = db.session.query(Candidate, Interview).join(
        Interview, Candidate.id == Interview.candidate_id
    ).filter(
        Interview.score.isnot(None)
    ).order_by(Interview.score.desc()).limit(5).all()
    
    return render_template('dashboard/index.html', title='Dashboard', 
                           jobs=jobs, total_candidates=total_candidates, recent_jobs=jobs,
                           interviews_completed=interviews_completed,
                           score_buckets=score_buckets,
                           interview_statuses=interview_statuses,
                           top_candidates=top_candidates)

@bp.route('/create_job', methods=['GET', 'POST'])
@login_required
def create_job():
    form = JobForm()
    if form.validate_on_submit():
        job = Job(title=form.title.data, description=form.description.data)
        db.session.add(job)
        db.session.commit()
        flash(f'Job "{job.title}" created successfully!', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('dashboard/create_job.html', title='Create Job', form=form)

@bp.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    form = JobForm(obj=job)
    if form.validate_on_submit():
        job.title = form.title.data
        job.description = form.description.data
        db.session.commit()
        flash(f'Job "{job.title}" updated successfully!', 'success')
        return redirect(url_for('dashboard.view_job', job_id=job.id))
    return render_template('dashboard/edit_job.html', title='Edit Job', form=form, job=job)

def process_candidates_async(app, candidates_info, job_id, api_key):
    """Background task to parse resumes and rank candidates."""
    with app.app_context():
        try:
            job = Job.query.get(job_id)
            if not job:
                return

            candidates_to_rank = []
            
            for idx, (cand_id, file_path, original_filename) in enumerate(candidates_info):
                candidate = Candidate.query.get(cand_id)
                if not candidate:
                    continue
                    
                candidate.processing_status = 'processing'
                db.session.commit()
                
                # Add delay between candidates to avoid API rate limits
                if idx > 0:
                    time.sleep(10)
                
                text_content = parse_resume(file_path)
                if text_content:
                    candidate.resume_text = text_content
                    candidate_info = extract_candidate_info(text_content, api_key)
                    
                    if candidate_info:
                        candidate.name = candidate_info.get('name', original_filename)
                        cand_email = candidate_info.get('email', 'N/A')
                        candidate.email = cand_email if cand_email != 'N/A' else None
                        candidate.skills = candidate_info.get('skills', '')
                    
                    candidates_to_rank.append(candidate)
                    db.session.commit()
                else:
                    candidate.processing_status = 'failed'
                    db.session.commit()
            
            if candidates_to_rank:
                # Wait before ranking to avoid rate limits after info extraction
                time.sleep(10)
                rank_candidates(job.description, candidates_to_rank)
                for cand in candidates_to_rank:
                    if cand.processing_status != 'failed':
                        cand.processing_status = 'completed'
                db.session.commit()
                
        except Exception as e:
            app.logger.error(f"Background thread error: {e}")
            # Ensure we don't leave candidates stuck in 'processing' state
            try:
                for cand_id, _, _ in candidates_info:
                    candidate = Candidate.query.get(cand_id)
                    if candidate and candidate.processing_status in ['pending', 'processing']:
                        candidate.processing_status = 'failed'
                db.session.commit()
            except Exception as inner_e:
                app.logger.error(f"Failed to update candidate status after error: {inner_e}")

@bp.route('/upload_candidates/<int:job_id>', methods=['GET', 'POST'])
@login_required
def upload_candidates(job_id):
    job = Job.query.get_or_404(job_id)
    form = CandidateUploadForm()
    if form.validate_on_submit():
        uploaded_files = request.files.getlist('resumes')
        upload_folder = os.path.join(current_app.root_path, '..', 'uploads')
        api_key = current_app.config.get('GEMINI_API_KEY')
        
        candidates_info = [] # Stores (cand_id, file_path, filename) to pass to thread
        
        for file in uploaded_files:
            file_path = save_file(file, upload_folder)
            if file_path:
                original_filename = file.filename.split('.')[0]
                # Pre-create candidate as pending
                candidate = Candidate(
                    job_id=job.id,
                    name=f"{original_filename} (Parsing...)",
                    resume_filename=file.filename,
                    processing_status='pending'
                )
                db.session.add(candidate)
                db.session.flush() # flush to get candidate.id
                candidates_info.append((candidate.id, file_path, original_filename))
        
        db.session.commit()
        
        if candidates_info:
            app = current_app._get_current_object()
            t = threading.Thread(target=process_candidates_async, args=(app, candidates_info, job.id, api_key))
            t.start()
            flash(f'Processing {len(candidates_info)} candidates in the background. Please wait a moment.', 'success')
        
        return redirect(url_for('dashboard.view_job', job_id=job.id))
        
    return render_template('dashboard/upload_candidates.html', title='Upload Candidates', form=form, job=job)

@bp.route('/job/<int:job_id>')
@login_required
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    # Sort candidates manually to handle None type in rank_score
    candidates = sorted(job.candidates, key=lambda c: c.rank_score if c.rank_score is not None else -1, reverse=True)
    has_processing = any(c.processing_status in ['pending', 'processing'] for c in candidates)
    return render_template('dashboard/view_job.html', title=job.title, job=job, candidates=candidates, has_processing=has_processing)

@bp.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
@login_required
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    job_id = candidate.job_id
    
    # Remove file from filesystem
    upload_folder = os.path.join(current_app.root_path, '..', 'uploads')
    file_path = os.path.join(upload_folder, candidate.resume_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            current_app.logger.warning(f"Error deleting file {file_path}: {e}")
            
    # Remove from DB
    db.session.delete(candidate)
    db.session.commit()
    
    flash('Candidate deleted successfully.', 'success')
    return redirect(url_for('dashboard.view_job', job_id=job_id))

@bp.route('/job/<int:job_id>/export')
@login_required
def export_csv(job_id):
    job = Job.query.get_or_404(job_id)
    candidates = sorted(job.candidates, key=lambda c: c.rank_score if c.rank_score is not None else -1, reverse=True)
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Rank', 'Name', 'Email', 'Resume Match %', 'AI Interview Status', 'AI Interview Score', 'Extracted Skills'])
    
    for i, c in enumerate(candidates, 1):
        if c.interview:
            c_status = c.interview.status.title()
            i_score = c.interview.score if c.interview.score else 'Pending'
        else:
            if c.processing_status in ['pending', 'processing']:
                c_status = 'Parsing Resume...'
                i_score = 'N/A'
            elif c.processing_status == 'failed':
                c_status = 'Parse Failed'
                i_score = 'N/A'
            else:
                c_status = 'Not Started'
                i_score = 'N/A'
                
        m_score = f"{c.rank_score}%" if c.rank_score is not None else 'Pending'
        cw.writerow([i, c.name, c.email or 'N/A', m_score, c_status, i_score, c.skills or ''])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=job_{job.id}_candidates.csv"}
    )

@bp.route('/delete_all_candidates/<int:job_id>', methods=['POST'])
@login_required
def delete_all_candidates(job_id):
    job = Job.query.get_or_404(job_id)
    candidates = Candidate.query.filter_by(job_id=job.id).all()
    
    upload_folder = os.path.join(current_app.root_path, '..', 'uploads')
    
    count = 0
    for candidate in candidates:
        # Remove file from filesystem
        if candidate.resume_filename:
            file_path = os.path.join(upload_folder, candidate.resume_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"Error deleting file {file_path}: {e}")
        
        db.session.delete(candidate)
        count += 1
        
    db.session.commit()
    
    flash(f'Successfully deleted {count} candidates.', 'success')
    return redirect(url_for('dashboard.view_job', job_id=job.id))

@bp.route('/report/<int:interview_id>')
@login_required
def view_report(interview_id):
    interview = Interview.query.get_or_404(interview_id)
    report = {}
    if interview.report_data:
        try:
            report = json.loads(interview.report_data)
        except:
            report = {}
    
    # Auto-healing: If report is missing but interview is completed, try to regenerate
    if (not report or 'final_score' not in report) and interview.status == 'completed':
        try:
            from app.services.report_service import generate_report
            generated_report = generate_report(interview.id)
            if generated_report:
                report = generated_report
                flash('Report was missing and has been regenerated.', 'info')
        except Exception as e:
            current_app.logger.error(f"Error regenerating report for interview {interview.id}: {e}")
            flash('Error regenerating report.', 'error')
            
    return render_template('dashboard/view_report.html', title='Candidate Report', 
                           interview=interview, report=report)

@bp.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    upload_folder = os.path.join(current_app.root_path, '..', 'uploads')
    
    # Delete all candidates and their interviews
    candidates = Candidate.query.filter_by(job_id=job.id).all()
    for candidate in candidates:
        # Delete interview if exists
        if candidate.interview:
            db.session.delete(candidate.interview)
        # Delete resume file
        if candidate.resume_filename:
            file_path = os.path.join(upload_folder, candidate.resume_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"Error deleting file {file_path}: {e}")
        db.session.delete(candidate)
    
    db.session.delete(job)
    db.session.commit()
    
    flash(f'Job "{job.title}" and all associated data deleted successfully.', 'success')
    return redirect(url_for('dashboard.index'))
