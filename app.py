"""Job Portal Application Factory.

This module implements the factory pattern for creating Flask application instances.
It handles:
- Application configuration
- Extension initialization
- Blueprint registration
- Database setup
- Security headers
- Scheduler initialization

Key Components:
- create_app(): Factory function that creates and configures the Flask app
- register_blueprints(): Helper function to register all application blueprints
- Global scheduler management to prevent duplicate initialization

Usage:
    from app import create_app
    app = create_app()
"""

from flask import Flask, session, redirect, url_for
from models import User
from config import config
from extensions import db, init_app
# from tasks import init_scheduler
import os
from logging_config import setup_logger
from flask_talisman import Talisman

# Global scheduler variable
application = None


def create_app(config_class=config[os.getenv('APP_ENV', 'development')]):
    """Create and configure the Flask application instance.
    
    Args:
        config_class: Configuration class to use (defaults to Config)
        
    Returns:
        Flask: Configured Flask application instance
        
    Side Effects:
        - Initializes all Flask extensions
        - Configures security headers
        - Creates required directories
        - Sets up logging
        - Initializes scheduler (once)
        - Creates database tables
    """
    print(f"APP_ENV: {os.getenv('APP_ENV', 'development')}")
    global application
    
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    # db.init_app(app)
    # mail.init_app(app)
    # login_manager.init_app(app)
    init_app(app)
    
    # Set up security headers with Talisman
    csp = {
        'default-src': '\'self\'',
        'img-src': ['\'self\'', 'data:', 'https://cdnjs.cloudflare.com'],
        'script-src': ['\'self\'', 'https://code.jquery.com', 'https://cdn.jsdelivr.net', 'https://cdnjs.cloudflare.com'],
        'style-src': [
            '\'self\'', 
            'https://cdn.jsdelivr.net', 
            'https://cdnjs.cloudflare.com', 
            'https://fonts.googleapis.com',
            '\'unsafe-inline\''
        ],
        'font-src': [
            '\'self\'', 
            'https://cdnjs.cloudflare.com', 
            'https://cdn.jsdelivr.net', 
            'https://fonts.gstatic.com'
        ],
        'frame-src': [
            '\'self\'',
            'https://www.google.com'
        ],
        'form-action': [
            '\'self\'',
            'https://www.google.com'
        ]
    }
    talisman = Talisman(app, content_security_policy=csp, force_https=False)

    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['COMPANY_LOGOS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)
    # Configure logging
    setup_logger(app)

    # Register blueprints
    register_blueprints(app)

    
        
    # Context processor to make current user available in templates
    @app.context_processor
    def inject_user():
        """
        Make the current user available to all templates.
        
        This context processor adds the current_user variable to the template context,
        allowing templates to access the logged-in user's information without
        explicitly passing it to each template.
        
        Returns:
            dict: A dictionary containing the current_user object or None if no user is logged in
        """
        user_id = session.get('user_id')
        if user_id:
            user = db.session.get(User, user_id)
            return dict(current_user=user)
        return dict(current_user=None)

    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Redirect root to main blueprint
    @app.route('/')
    def index():
        """
        Root route that redirects to the main blueprint's index route.
        
        Returns:
            Response: A redirect to the main blueprint's index route
        """
        return redirect(url_for('main.index'))
    
    application = app   

    return app

def register_blueprints(app):
    """Register all application blueprints."""
    from blueprints.main import main
    from blueprints.auth import auth
    from blueprints.jobs import jobs_bp
    from blueprints.job_seeker import job_seeker_bp
    from blueprints.employer import employer_bp
    from blueprints.admin import admin_bp
    from blueprints.utils import utils_bp

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    app.register_blueprint(job_seeker_bp)
    app.register_blueprint(employer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(utils_bp)

