"""Employer Blueprint Routes.

This module contains all routes related to employer functionality including:
- Job posting and management
- Application review
- Employer dashboard
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Job, Application, User
from forms import JobForm
from utils import logger, save_company_logo
from blueprints.auth.routes import login_required, role_required
from werkzeug.utils import secure_filename
import os

employer_bp = Blueprint('employer', __name__)


@employer_bp.route('/post-job-redirect')
@login_required
@role_required('employer', 'admin')
def post_job_redirect():
    """Handle navbar job posting redirect with role-based destination.

    Returns:
        redirect: 
            - Admins: Redirect to admin job management
            - Employers: Redirect to job creation form

    Side Effects:
        - Logs redirect action
        - Flashes info message for admin users

    Example:
        /post-job-redirect
    """
    # This route is just a convenience for the navbar link
    if session['role'] == 'admin':
        # Admins can post jobs but they're redirected to the admin interface
        logger.info(
            f"Admin {session['user_id']} redirected to admin job creation")
        flash('As an admin, you can create jobs through the admin interface.', 'info')
        return redirect(url_for('admin.admin_jobs'))
    else:
        logger.info(
            f"Employer {session['user_id']} redirected to job creation form")
        return redirect(url_for('employer.new_job'))


@employer_bp.route('/jobs/new', methods=['GET', 'POST'])
@login_required
@role_required('employer', 'admin')
def new_job():
    """Handle job creation form display and submission.

    Methods:
        GET: Display job creation form
        POST: Process form submission and create new job

    Returns:
        GET: Rendered job creation template
        POST: Redirect to employer dashboard on success

    Side Effects:
        - Creates new Job record in database
        - Handles company logo file upload
        - Logs creation attempts
        - Flashes success/error messages

    Example:
        /jobs/new
    """
    form = JobForm()

    # For admin users, add a dropdown to select which employer posts the job
    if session['role'] == 'admin':
        pass
    else:
        pass

    if form.validate_on_submit():
        try:
            # Validate salary format
            if form.salary.data and not form.salary.data.startswith('$'):
                logger.warning(
                    f"Invalid salary format attempted: {form.salary.data}")
                form.salary.data = '$' + form.salary.data

            # Determine the poster_id
            poster_id = session['user_id']

            # Handle logo upload
            company_logo = 'img/company_logos/default.png'  # Default logo
            if form.company_logo.data:
                logo_filename = save_company_logo(form.company_logo.data)
                if logo_filename:
                    company_logo = f'img/company_logos/{logo_filename}'
                    logger.info(
                        f"Company logo uploaded for new job: {logo_filename}")
                else:
                    logger.error(
                        f"Failed to save company logo for new job")

            # Create job
            job = Job(
                title=form.title.data,
                company=form.company.data,
                location=form.location.data,
                description=form.description.data,
                salary=form.salary.data,
                category=form.category.data,
                company_logo=company_logo,
                poster_id=poster_id
            )
            db.session.add(job)
            db.session.commit()
            logger.info(
                f"New job created: {job.id} - {job.title} at {job.company} by user {poster_id}")
            flash('Job posted successfully!', 'success')
            return redirect(url_for('employer.my_jobs'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating job: {str(e)}")
            flash('An error occurred while posting the job.', 'danger')

    return render_template('new_job.html', form=form)


@employer_bp.route('/my_jobs')
@login_required
@role_required('employer', 'admin')
def my_jobs():
    """Display all jobs posted by the current employer/admin.

    Returns:
        rendered_template: Jobs list page with all jobs posted by user

    Side Effects:
        - Logs access to job list
        - Retrieves jobs from database

    Example:
        /my_jobs
    """
    logger.info(f"User {session['user_id']} accessing their posted jobs")
    jobs = Job.query.filter_by(poster_id=session['user_id']).all()
    # Get application counts for each job
    # for job in jobs:
    #     job.application_count = Application.query.filter_by(
    #         job_id=job.id).count()
    logger.info(f"Found {len(jobs)} jobs posted by user {session['user_id']}")
    return render_template('my_jobs.html', jobs=jobs, form=JobForm())


@employer_bp.route('/jobs/<int:job_id>/applications')
@login_required
@role_required('employer', 'admin')
def job_applications(job_id):
    """Display applications for a specific job.

    Args:
        job_id (int): ID of job to view applications for

    Returns:
        rendered_template: Applications list page

    Side Effects:
        - Verifies job ownership (unless admin)
        - Logs access to applications

    Example:
        /jobs/42/applications
    """
    logger.info(
        f"User {session['user_id']} accessing applications for job {job_id}")
    job = db.get_or_404(Job, job_id)
    # Only allow access if user is admin or the job poster
    if session['role'] != 'admin' and job.poster_id != session['user_id']:
        logger.warning(
            f"Unauthorized access attempt: User {session['user_id']} tried to view applications for job {job_id} posted by user {job.poster_id}")
        flash('You do not have permission to view these applications.', 'danger')
        return redirect(url_for('employer.my_jobs'))

    applications = Application.query.filter_by(job_id=job.id).all()
    logger.info(f"Found {len(applications)} applications for job {job_id}")
    return render_template('job_applications.html', job=job, applications=applications)


@employer_bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('employer', 'admin')
def delete_job(job_id):
    """Delete a job posting and its applications.

    Args:
        job_id (int): ID of job to delete

    Returns:
        redirect: Back to jobs list with success/error message

    Side Effects:
        - Deletes job and all its applications
        - Logs deletion attempts
        - Flashes confirmation messages

    Example:
        POST /jobs/42/delete
    """
    job = db.get_or_404(Job, job_id)

    # Check if the user has permission to delete this job
    if session['role'] != 'admin' and job.poster_id != session['user_id']:
        logger.warning(
            f"Unauthorized job deletion attempt: User {session['user_id']} tried to delete job {job_id} posted by user {job.poster_id}")
        flash('You do not have permission to delete this job.', 'danger')
        return redirect(url_for('employer.my_jobs'))

    try:
        # Delete associated applications first
        applications = Application.query.filter_by(job_id=job.id).all()
        for application in applications:
            db.session.delete(application)

        # Now delete the job
        db.session.delete(job)
        db.session.commit()
        logger.info(
            f"Job {job_id} ({job.title} at {job.company}) deleted by user {session['user_id']}")
        flash('Job deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        flash('An error occurred while deleting the job.', 'danger')

    return redirect(url_for('employer.my_jobs'))


@employer_bp.route('/applications/<int:application_id>/update', methods=['POST'])
@login_required
@role_required('employer', 'admin')
def update_application(application_id):
    """Update an application's status or notes.

    Args:
        application_id (int): ID of application to update

    Returns:
        redirect: Back to applications page with success/error message

    Side Effects:
        - Updates application in database
        - Logs update attempts
        - Flashes success/error messages

    Valid Status Values:
        - pending
        - reviewed  
        - rejected
        - shortlisted
        - hired

    Example:
        POST /applications/42/update
        Form Data: {'status': 'shortlisted', 'notes': 'Strong candidate'}
    """
    application = db.get_or_404(Application, application_id)
    job = db.get_or_404(Job, application.job_id)

    # Security check: Ensure the employer owns this job or is an admin
    if session['role'] != 'admin' and job.poster_id != session['user_id']:
        logger.warning(
            f"Unauthorized application status update attempt: User {session['user_id']} tried to update application {application_id} for job {job.id} posted by {job.poster_id}")
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('employer.job_applications', job_id=job.id))

    # Validate the status input
    new_status = request.form.get('status')
    valid_statuses = ['pending', 'reviewed',
                      'rejected', 'shortlisted', 'hired']

    if not new_status or new_status not in valid_statuses:
        logger.warning(
            f"Invalid status update attempt: User {session['user_id']} tried to set invalid status '{new_status}' for application {application_id}")
        flash('Invalid status.', 'danger')
        return redirect(url_for('employer.job_applications', job_id=job.id))

    # Update the application status
    application.status = new_status
    db.session.commit()

    logger.info(
        f"Employer {session['user_id']} updated application {application_id} status to {new_status}")
    flash(f'Application status updated to {new_status}.', 'success')

    return redirect(url_for('employer.job_applications', job_id=job.id))
