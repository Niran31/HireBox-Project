import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'), override=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'instance', 'hirebox.db') # Ensure path is correct and add timeout?
    # Actually, SQLite URI queries work like this:
    # sqlite:///path/to/db?timeout=30
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite:'):
        SQLALCHEMY_DATABASE_URI += '?timeout=30'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Hugging Face iframe support (Cross-Origin Cookies)
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
