from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Application
from utils import logger
from blueprints.auth.routes import login_required, role_required

job_seeker_bp = Blueprint('job_seeker', __name__)

@job_seeker_bp.route('/my_applications')
@login_required
@role_required('job_seeker')
def my_applications():
    """Display all job applications submitted by the current user.
    
    Returns:
        rendered_template: Applications list page with all applications
        
    Side Effects:
        - Logs access to applications
        - Retrieves applications from database
        - Tracks application counts
        
    Example:
        /my_applications
    """
    logger.info(f"User {session['user_id']} accessing their job applications")
    applications = Application.query.filter_by(
        applicant_id=session['user_id']).all()
    logger.info(f"Found {len(applications)} applications for user {session['user_id']}")
    return render_template('my_applications.html', applications=applications)
