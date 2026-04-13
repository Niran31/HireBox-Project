import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, upload_folder):
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        # Add UUID prefix to prevent overwrite collisions
        unique_filename = f"{uuid.uuid4().hex[:8]}_{original_filename}"
        # Ensure upload folder exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        return filepath
    return None

