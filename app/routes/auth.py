from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlsplit
from itsdangerous import URLSafeTimedSerializer
from app.extensions import db
from app.models.models import User
from app.utils.forms import LoginForm, RegistrationForm, ProfileForm, ForgotPasswordForm, ResetPasswordForm
from app.services.email_service import send_password_reset_email

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        login_id = form.login_id.data.strip()
        if '@' in login_id:
            user = User.query.filter_by(email=login_id).first()
        else:
            user = User.query.filter_by(username=login_id).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username/email or password', 'error')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('dashboard.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        # Check username uniqueness (if changed)
        if form.username.data != current_user.username:
            existing = User.query.filter_by(username=form.username.data).first()
            if existing:
                flash('That username is already taken.', 'error')
                return redirect(url_for('auth.profile'))
        
        # Check email uniqueness (if changed)
        if form.email.data != current_user.email:
            existing = User.query.filter_by(email=form.email.data).first()
            if existing:
                flash('That email is already in use.', 'error')
                return redirect(url_for('auth.profile'))
        
        # Handle password change
        if form.new_password.data:
            if not form.current_password.data:
                flash('Current password is required to set a new password.', 'error')
                return redirect(url_for('auth.profile'))
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('auth.profile'))
            current_user.set_password(form.new_password.data)
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', title='Profile', form=form)

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate timed token
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            
            # Send reset email
            success, msg = send_password_reset_email(user.email, user.username, reset_link)
            if success:
                flash('An email with instructions to reset your password has been sent.', 'success')
            else:
                flash(f'Failed to send email: {msg}. Reset Link (logged): {reset_link}', 'warning')
        else:
            # Standard security practice: display the same success message to prevent user enumeration
            flash('An email with instructions to reset your password has been sent.', 'success')
        
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', title='Forgot Password', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Verify the token
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=1800) # 30 minutes
    except Exception:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
        
    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', title='Reset Password', form=form)

