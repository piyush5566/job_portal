"""Utility Routes.

This module contains utility endpoints for:
- Secure file serving
- Application helper functions
- System status checks
"""

from flask import Blueprint, send_file, abort, session, current_app
from models import Application, Job, db
from google.cloud import storage
import io
from utils import logger # Keep logger
from blueprints.auth.routes import login_required
import os # Keep os if needed for other parts, but not for path joining here

utils_bp = Blueprint('utils', __name__)

@utils_bp.route('/resume/<path:cs_suffix>')
@login_required
def serve_resume(cs_suffix):
    """
    Securely serve resume files, checking local storage first, then GCS.

    Args:
        cs_suffix (str): The suffix of the GCS object name or local path
                          (e.g., 'user_id/filename.pdf').

    Returns:
        file: The requested resume file streamed from local disk or GCS.
        abort: 403 if unauthorized, 404 if not found, 500 on error.
        
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
    user_id = session.get('user_id')
    user_role = session.get('role')
    logger.info(f"Resume access request for path suffix: {cs_suffix} by user {user_id} with role {user_role}")

    # Construct the full GCS object name (used for DB lookup and GCS fetch)
    # Assuming resume_path in DB stores the full path like 'resumes/123/file.pdf'
    gcs_object_name = f"resumes/{cs_suffix}"

    # Find the application associated with this GCS path/identifier
    application = Application.query.filter_by(resume_path=cs_suffix).first()

    if not application:
        logger.warning(f"Resume access denied: No application found matching path '{cs_suffix}'")
        # Try finding based on legacy local path format if necessary?
        # legacy_local_path = f"static/resumes/{cs_suffix}"
        # application = Application.query.filter_by(resume_path=legacy_local_path).first()
        # if not application:
        #     abort(404)
        # else: # Found legacy path, proceed carefully
        #     logger.info(f"Found application using legacy path format: {legacy_local_path}")
        abort(404) # Keep it simple for now, assume resume_path is GCS path

    # --- Permission Checks (same logic as before) ---
    if user_role == 'admin':
        logger.info(f"Admin {user_id} accessing resume for application {application.id} (Path: {gcs_object_name})")
        pass # Admin can access
    elif user_role == 'employer':
        job = db.session.get(Job, application.job_id)
        if not job or job.poster_id != user_id:
            logger.warning(f"Unauthorized resume access attempt: Employer {user_id} for path '{gcs_object_name}' (Job {application.job_id})")
            abort(403)
        logger.info(f"Employer {user_id} accessing resume for application {application.id} (Path: {gcs_object_name})")
    elif user_id != application.applicant_id:
        logger.warning(f"Unauthorized resume access attempt: User {user_id} for path '{gcs_object_name}' (Applicant {application.applicant_id})")
        abort(403)
    else: # Applicant accessing their own
        logger.info(f"Applicant {user_id} accessing their own resume for application {application.id} (Path: {gcs_object_name})")
    # --- End Permission Checks ---

    # --- Attempt to Serve Locally First ---
    # Construct the expected local path based on the suffix
    expected_local_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cs_suffix)
    logger.debug(f"Checking for local resume file at: {expected_local_path}")

    if os.path.exists(expected_local_path):
        try:
            logger.info(f"Serving resume file '{cs_suffix}' from local storage.")
            # Extract original filename for download prompt
            original_filename = os.path.basename(cs_suffix)
            return send_file(
                expected_local_path,
                download_name=original_filename,
                as_attachment=True
            )
        except Exception as e:
            logger.error(f"Error serving local file '{expected_local_path}': {str(e)}")
            # Fall through to try GCS if configured, or abort if not an expected error

    logger.info(f"Resume file '{cs_suffix}' not found locally. Attempting GCS fetch.")

    # --- If Not Found Locally, Attempt to Fetch from GCS ---
    enable_gcs = current_app.config.get('ENABLE_GCS_UPLOAD', False)
    gcs_bucket_name = current_app.config.get('GCS_BUCKET_NAME')

    if not enable_gcs or not gcs_bucket_name:
        logger.warning(f"Local file '{cs_suffix}' not found and GCS is not enabled or configured. Cannot serve resume.")
        abort(404) # Not found locally, GCS disabled -> 404

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        # Use the gcs_object_name derived earlier for GCS path
        blob = bucket.blob(gcs_object_name)

        if not blob.exists():
            logger.warning(f"Resume file not found locally or in GCS: {gcs_object_name}")
            abort(404)

        # Download blob content into memory
        file_bytes = blob.download_as_bytes()
        file_stream = io.BytesIO(file_bytes)

        # Extract original filename for download prompt
        original_filename = os.path.basename(cs_suffix) # Get 'filename.pdf' from '123/filename.pdf'

        logger.info(f"Resume file {gcs_object_name} successfully retrieved from GCS and serving.")
        # Send the file from the in-memory stream
        return send_file(
            file_stream,
            download_name=original_filename, # Suggests filename to browser
            as_attachment=True # Force download prompt
            # mimetype can be set explicitly if needed, e.g., 'application/pdf'
        )

    except Exception as e:
        logger.error(f"Error retrieving file '{gcs_object_name}' from GCS after local check failed: {str(e)}")
        abort(500) # Internal server error during GCS fetch
