"""Utility Routes.

This module contains utility endpoints for:
- Secure file serving
- Application helper functions
- System status checks
"""

from flask import Blueprint, send_file, abort, session, current_app
from models import Application, Job, db
from utils import logger, get_resume_file
import os
from blueprints.auth.routes import login_required

utils_bp = Blueprint('utils', __name__)

@utils_bp.route('/resume/<path:filename>')
@login_required
def serve_resume(filename):
    """Securely serve resume files with access control.
    
    Args:
        filename (str): Path to the resume file to serve
        
    Returns:
        file: The requested resume file
        abort: 403 if unauthorized access attempted
        
    Side Effects:
        - Logs all access attempts
        - Verifies user permissions
        - Handles local/GCS file retrieval
        
    Access Rules:
        - Admins: Can access any resume
        - Employers: Can access resumes for their job postings
        - Applicants: Can access their own resumes
        
    Example:
        /resume/user123_resume.pdf
    """
    logger.info(f"Resume access request for file: {filename} by user {session['user_id']} with role {session['role']}")
    
    # Only allow access to resumes if user is admin, employer viewing their job applications,
    # or the applicant viewing their own resume
    ENABLE_GCS_UPLOAD = current_app.config['ENABLE_GCS_UPLOAD']
    GCS_BUCKET_NAME = current_app.config['GCS_BUCKET_NAME']
    
    resume_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    application = Application.query.filter_by(
        resume_path=f"static/resumes/{filename}").first()

    if not application:
        logger.warning(f"Resume access denied: File not found - {filename}")
        abort(404)

    if session['role'] == 'admin':
        logger.info(f"Admin {session['user_id']} accessed resume for application {application.id}")
        pass  # Admin can access all resumes
    elif session['role'] == 'employer':
        job = db.session.get(Job, application.job_id)
        if job.poster_id != session['user_id']:
            logger.warning(f"Unauthorized resume access attempt: Employer {session['user_id']} tried to access resume for job {application.job_id} posted by {job.poster_id}")
            abort(403)  # Employer can only access resumes for their jobs
        logger.info(f"Employer {session['user_id']} accessed resume for application {application.id} to their job {application.job_id}")
    elif session['user_id'] != application.applicant_id:
        logger.warning(f"Unauthorized resume access attempt: User {session['user_id']} tried to access resume for application {application.id} by applicant {application.applicant_id}")
        abort(403)  # Job seekers can only access their own resumes
    else:
        logger.info(f"Job seeker {session['user_id']} accessed their own resume for application {application.id}")

    resume_file, exists = get_resume_file(resume_path, enable_gcs=ENABLE_GCS_UPLOAD, gcs_bucket_name=GCS_BUCKET_NAME)
    if exists:
        logger.info(f"Resume file {filename} successfully served")
        return send_file(resume_file)
    else:
        logger.warning(f"Resume file {filename} not found on disk")
        abort(404)
