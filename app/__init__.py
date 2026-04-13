from flask import Flask
from config.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.extensions import db, migrate, login_manager, csrf
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize Database and Workspace at Boot
    import os
    with app.app_context():
        # Ensure the instance folder exists for SQLite
        os.makedirs(app.instance_path, exist_ok=True)
        # Import models so SQLAlchemy knows the schema
        from app.models.models import User, Job, Candidate, Interview
        # Create all tables (safe if they already exist)
        db.create_all()

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.routes.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    from app.routes.interview import bp as interview_bp
    app.register_blueprint(interview_bp, url_prefix='/interview')

    @app.route('/')
    def index():
        from flask import redirect, url_for, render_template
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('landing.html')

    return app
