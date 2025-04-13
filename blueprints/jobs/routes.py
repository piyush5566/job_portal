from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from models import db, Job, Application
from utils import logger, save_resume
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
        try:
            # Save resume file
            if form.resume.data:
                resume_path = save_resume(form.resume.data, session['user_id'])
                logger.info(f"Resume saved for application to job {job_id} by user {session['user_id']}")
            else:
                resume_path = None

            # Create application
            application = Application(
                job_id=job_id,
                applicant_id=session['user_id'],
                resume_path=resume_path,
                status='pending'
            )
            db.session.add(application)
            db.session.commit()
            logger.info(f"User {session['user_id']} successfully applied to job {job_id}")
            flash('Your application has been submitted!', 'success')
            return redirect(url_for('job_seeker.my_applications'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error applying to job {job_id}: {str(e)}")
            flash('An error occurred while submitting your application.', 'danger')

    return render_template('apply_job.html', form=form, job=job)
