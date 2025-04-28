from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from models import db, Job, Application
from utils import logger, upload_to_gcs, allowed_file
from blueprints.auth.routes import login_required, role_required
from forms import ApplicationForm

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/list')
def jobs_list():
    location = request.args.get('location')
    category = request.args.get('category')
    company = request.args.get('company')
    
    logger.info(f"Jobs page accessed with filters - location: {location}, category: {category}, company: {company}")
    
    query = Job.query
    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))
    if category:
        query = query.filter(Job.category.ilike(f'%{category}%'))
    if company:
        query = query.filter(Job.company.ilike(f'%{company}%'))
    jobs = query.all()
    
    logger.info(f"Found {len(jobs)} jobs matching the criteria")
    return render_template('jobs.html', jobs=jobs)

@jobs_bp.route('/search')
def search_jobs():
    """
    API endpoint for searching jobs (returns JSON).
    
    Query Parameters:
        location (optional): Filter by location
        category (optional): Filter by category
        company (optional): Filter by company
        
    Returns:
        JSON response with job listings matching criteria
        
    Side Effects:
        - Logs search parameters
        - Logs number of results returned
        
    Example:
        /jobs/search?location=New+York
    """
    location = request.args.get('location')
    category = request.args.get('category')
    company = request.args.get('company')

    logger.info(f"API search_jobs called with filters - location: {location}, category: {category}, company: {company}")

    query = Job.query

    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))
    if category:
        query = query.filter(Job.category.ilike(f'%{category}%'))
    if company:
        query = query.filter(Job.company.ilike(f'%{company}%'))

    jobs = query.all()
    logger.info(f"API search_jobs returned {len(jobs)} results")

    return jsonify({
        'jobs': [{
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'category': job.category,
            'salary': job.salary,
            'company_logo': job.company_logo,
            'posted_date': job.posted_date.isoformat()
        } for job in jobs]
    })

@jobs_bp.route('/<int:job_id>')
def job_detail(job_id):
    """
    Display detailed information about a specific job.
    
    Args:
        job_id: ID of the job to display
        
    Returns:
        Rendered template with job details
        
    Side Effects:
        - Logs job detail page access
        - For admin users, logs application count
        - For job seekers, checks and logs application status
        
    Example:
        /jobs/42
    """
    logger.info(f"Job detail page accessed for job_id: {job_id}")
    job = db.get_or_404(Job, job_id)
    # Add application count for admin users
    if session.get('role') == 'admin':
        job.application_count = Application.query.filter_by(
            job_id=job.id).count()
        logger.info(f"Admin viewing job {job_id} with {job.application_count} applications")

    # Check if the current user has already applied
    has_applied = False
    if session.get('user_id') and session.get('role') == 'job_seeker':
        existing_application = Application.query.filter_by(
            job_id=job_id, applicant_id=session['user_id']).first()
        has_applied = existing_application is not None
        logger.info(f"User {session['user_id']} has {'already applied' if has_applied else 'not applied'} to job {job_id}")

    return render_template('job_detail.html', job=job, has_applied=has_applied)

@jobs_bp.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required
@role_required('job_seeker')
def apply_job(job_id):
    """
    Handle job application submissions.
    
    Args:
        job_id: ID of the job being applied to
        
    Returns:
        Rendered form (GET) or redirect (POST)
        
    Side Effects:
        - Validates and saves resume file
        - Creates application record
        - Prevents duplicate applications
        - Logs application attempts and results
        - Flashes success/error messages
        
    Example:
        /jobs/apply/42
    """
    job = db.get_or_404(Job, job_id)
    form = ApplicationForm()

    # Check if already applied
    existing_application = Application.query.filter_by(
        job_id=job_id, applicant_id=session['user_id']).first()
    if existing_application:
        flash('You have already applied to this job.', 'warning')
        return redirect(url_for('jobs.job_detail', job_id=job_id))

    if form.validate_on_submit():
        resume_path_for_db = None # Will store GCS object name or None
        gcs_upload_successful = True # Assume success if no file or GCS disabled
        try:
            # --- Handle Resume Upload ---
            resume_file = form.resume.data
            if resume_file:
                # Check config if GCS should be used
                enable_gcs = current_app.config.get('ENABLE_GCS_UPLOAD', False)
                gcs_bucket_name = current_app.config.get('GCS_BUCKET_NAME')

                if enable_gcs and gcs_bucket_name:
                    logger.info(f"Attempting GCS upload for application to job {job_id} by user {session['user_id']}")
                    # Attempt direct upload to GCS
                    gcs_object_name = upload_to_gcs(
                        file_storage=resume_file,
                        user_id=session['user_id'],
                        gcs_bucket_name=gcs_bucket_name
                    )

                    if gcs_object_name:
                        resume_path_for_db = gcs_object_name.removeprefix('resumes/') # Store GCS path
                        logger.info(f"GCS upload successful for job {job_id}, user {session['user_id']}. Path: {resume_path_for_db}")
                    else:
                        # GCS upload failed
                        gcs_upload_successful = False
                        logger.error(f"GCS upload failed for job {job_id}, user {session['user_id']}")
                        flash('There was an error uploading your resume to cloud storage. Please try again.', 'danger')
                        # Optionally, save locally as a fallback ONLY IF GCS fails?
                        # Or just fail the application? Let's fail for now.
                        # return render_template('apply_job.html', form=form, job=job) # Stay on page
                else:
                    # GCS not enabled, handle locally (or disallow?)
                    # For now, let's log a warning and not save the resume if GCS isn't enabled
                    logger.warning(f"Resume provided for job {job_id}, user {session['user_id']}, but GCS upload is disabled or bucket not configured. Resume not saved.")
                    # Optionally flash a message to the user
                    # flash('Resume upload is currently disabled.', 'info')
                    # resume_path_for_db = None # Explicitly set to None

            # --- Create Application Record (only if GCS upload was successful or no resume) ---
            if gcs_upload_successful:
                application = Application(
                    job_id=job_id,
                    applicant_id=session['user_id'],
                    resume_path=resume_path_for_db, # Store GCS path or None
                    status='applied' # Changed from 'pending' to 'applied'
                )
                db.session.add(application)
                db.session.commit()
                logger.info(f"User {session['user_id']} successfully applied to job {job_id}. Resume path (GCS): {resume_path_for_db}")
                flash('Your application has been submitted!', 'success')
                return redirect(url_for('job_seeker.my_applications'))
            # else: GCS upload failed, already flashed message, stay on page

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing application for job {job_id}, user {session['user_id']}: {str(e)}")
            flash('An unexpected error occurred while submitting your application.', 'danger')
            
    elif request.method == 'POST':
        # Log validation errors if POST request failed validation
        logger.warning(f"Application form validation failed for job {job_id}, user {session['user_id']}: {form.errors}")
        flash('Please correct the errors in the form.', 'warning')
        
    return render_template('apply_job.html', form=form, job=job)
