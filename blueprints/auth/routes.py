from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from models import db, User
from forms import RegistrationForm, LoginForm, ProfileForm
from functools import wraps
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
from utils import logger, ALLOWED_PIC_EXTENSIONS, save_profile_picture

auth = Blueprint('auth', __name__)

# Helper functions
def login_required(f):
    """
    Decorator to ensure user is authenticated before accessing a route.
    
    Args:
        f: The route function to decorate
        
    Returns:
        Decorated function that checks authentication
        
    Side Effects:
        - Redirects to login page if not authenticated
        - Flashes warning message
        
    Example:
        @login_required
        def protected_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    Decorator to restrict route access based on user role.
    
    Args:
        *roles: Allowed role(s) for the route
        
    Returns:
        Decorator function that checks user role
        
    Side Effects:
        - Redirects to home page if role doesn't match
        - Flashes danger message
        
    Example:
        @role_required('admin')
        def admin_only_route():
            ...
            
        @role_required('admin', 'employer')
        def admin_or_employer_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_pic_file(filename):
    """
    Check if a filename has an allowed image extension.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: True if extension is allowed, False otherwise
        
    Example:
        allowed_pic_file('profile.jpg') -> True
        allowed_pic_file('document.pdf') -> False
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_PIC_EXTENSIONS

# Routes
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Creates new user record if validation passes
        - Logs registration attempts (success/failure)
        - Flashes success/error messages
        - Prevents duplicate email registration
        
    Example:
        /register
    """
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            if User.query.filter_by(email=form.email.data).first():
                logger.warning(
                    f"Registration failed: Email {form.email.data} already registered")
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.register'))
            
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            logger.info(f"New user registered: {form.email.data}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration failed: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html', form=form)

    # If form validation fails, log the validation errors
    if form.errors:
        logger.warning(f"Form validation failed: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')

    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user authentication.
    
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Sets session variables if authentication succeeds
        - Logs login attempts (success/failure)
        - Flashes success/error messages
        - Handles 'next' parameter for redirect after login
        
    Example:
        /login
    """
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['role'] = user.role
            logger.info(
                f"Successful login for user {user.id} from IP {request.remote_addr}")
            flash('Login successful!', 'success')
            # Redirect to the page they were trying to access, or home
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        else:
            logger.warning(
                f"Failed login attempt for email {form.email.data} from IP {request.remote_addr}")
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@auth.route('/logout')
def logout():
    """
    Handle user logout.
    
    Returns:
        Redirect to home page
        
    Side Effects:
        - Clears session variables
        - Logs logout action
        - Flashes success message
        
    Example:
        /logout
    """
    if 'user_id' in session:
        logger.info(f"User logged out: {session['user_id']}")
        session.pop('user_id', None)
        session.pop('role', None)
        flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Handle user profile management.
    
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Updates user profile if validation passes
        - Handles profile picture uploads
        - Prevents duplicate username/email
        - Logs profile changes
        - Flashes success/error messages
        
    Example:
        /profile
    """
    form = ProfileForm()
    user = db.get_or_404(User, session['user_id'])

    if form.validate_on_submit():
        # Check for username/email conflicts (excluding current user)
        if form.username.data != user.username:
            logger.info(
                f"User {user.id} attempting to change username from {user.username} to {form.username.data}")
            if User.query.filter(User.username == form.username.data, User.id != user.id).first():
                logger.warning(
                    f"Username change rejected - {form.username.data} already taken")
                flash(
                    'That username is already taken. Please choose a different one.', 'danger')
                return render_template('profile.html', form=form, user=user)

        if form.email.data != user.email:
            logger.info(
                f"User {user.id} attempting to change email from {user.email} to {form.email.data}")
            if User.query.filter(User.email == form.email.data, User.id != user.id).first():
                logger.warning(
                    f"Email change rejected - {form.email.data} already registered")
                flash(
                    'That email is already registered. Please choose a different one.', 'danger')
                return render_template('profile.html', form=form, user=user)

        # Update username and email
        old_username = user.username
        old_email = user.email
        user.username = form.username.data
        user.email = form.email.data

        # Handle profile picture upload
        if form.profile_picture.data:
            if allowed_pic_file(form.profile_picture.data.filename):
                logger.info(
                    f"Processing profile picture upload for user {user.id}")
                picture_file = save_profile_picture(form.profile_picture.data)
                user.profile_picture = picture_file
            else:
                logger.warning(
                    f"Invalid profile picture upload attempt by user {user.id} - unsupported file type")
                flash(
                    'Invalid profile picture file type. Allowed: jpg, png, jpeg', 'danger')
                return render_template('profile.html', form=form, user=user)

        db.session.commit()
        logger.info(
            f"Profile updated for user {user.id}. Changes: username: {old_username}->{user.username}, email: {old_email}->{user.email}")
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('auth.profile'))

    elif request.method == 'GET':
        # Pre-populate form with current user data
        form.username.data = user.username
        form.email.data = user.email

    return render_template('profile.html', form=form, user=user)
