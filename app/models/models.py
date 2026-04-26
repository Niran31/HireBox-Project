from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    candidates = db.relationship('Candidate', backref='job', lazy='dynamic')

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    name = db.Column(db.String(64))
    email = db.Column(db.String(120))
    resume_filename = db.Column(db.String(256))
    resume_text = db.Column(db.Text) # Extracted text
    rank_score = db.Column(db.Float) # Semantic match score
    skills = db.Column(db.Text)
    processing_status = db.Column(db.String(20), default='pending') # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    interview = db.relationship('Interview', backref='candidate', uselist=False, cascade='all, delete-orphan')

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    token = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default='pending') # pending, started, completed
    score = db.Column(db.Float)
    report_data = db.Column(db.Text) # JSON blob for report
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
