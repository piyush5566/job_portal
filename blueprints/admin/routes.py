from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Job, Application
from forms import UserEditForm, JobForm, AdminRegistrationForm
from utils import logger, save_company_logo
from blueprints.auth.routes import login_required, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    """
    Render the admin dashboard.
    
    Returns:
        Rendered admin dashboard template
        
    Side Effects:
        - Logs dashboard access
        
    Example:
        /admin/dashboard
    """
    logger.info(f"Admin {session['user_id']} accessed the admin dashboard")
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@login_required
@role_required('admin')
def admin_users():
    """
    Display all users for admin management.
    
    Returns:
        Rendered template with list of all users
        
    Side Effects:
        - Logs access to user management
        - Retrieves all users from database
        
    Example:
        /admin/users
    """
    logger.info(f"Admin {session['user_id']} accessed the users management page")
    users = User.query.all()
    logger.info(f"Retrieved {len(users)} users for admin view")
    return render_template('admin/users.html', users=users, form=UserEditForm())

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_new_user():
    """
    Handle creation of new users by admin.
    
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Creates new user record in database
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        /admin/users/new
    """
    logger.info(f"Admin {session['user_id']} accessed the new user creation page")
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            logger.warning(f"Admin user creation failed: Email {form.email.data} already exists")
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.admin_new_user'))
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Admin {session['user_id']} created new user: {user.id} ({user.username}, {user.email}) with role {user.role}")
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.admin_users'))
    
    if form.errors:
        logger.warning(f"Admin user creation form validation failed: {form.errors}")
        
    return render_template('admin/new_user.html', form=form)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_user(user_id):
    """
    Handle editing user details as an admin.
    
    Args:
        user_id: ID of the user to edit
        
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Updates user record in database
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        /admin/users/42/edit
    """
    user = db.get_or_404(User, user_id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        # Check for email conflicts
        if form.email.data != user.email and User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.admin_edit_user', user_id=user_id))
        
        try:
            # Update user data
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            
            db.session.commit()
            logger.info(
                f"Admin {session['user_id']} updated user {user_id}: {user.username}, {user.email}, role: {user.role}")
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.admin_users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            flash('An error occurred while updating the user.', 'danger')
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    """
    Handle user deletion by admin.
    
    Args:
        user_id: ID of the user to delete
        
    Returns:
        Redirect to users list
        
    Side Effects:
        - Removes user record from database
        - Prevents self-deletion
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        POST /admin/users/42/delete
    """
    user = db.get_or_404(User, user_id)
    
    # Prevent admins from deleting themselves
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.admin_users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        logger.info(
            f"Admin {session['user_id']} deleted user {user_id}: {user.username}, {user.email}")
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash('An error occurred while deleting the user.', 'danger')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/jobs')
@login_required
@role_required('admin')
def admin_jobs():
    """
    Display all job listings for admin management.
    
    Returns:
        Rendered template with list of all jobs
        
    Side Effects:
        - Logs access to job management
        - Retrieves all jobs from database
        
    Example:
        /admin/jobs
    """
    logger.info(f"Admin {session['user_id']} accessed the jobs management page")
    jobs = Job.query.all()
    logger.info(f"Retrieved {len(jobs)} jobs for admin view")
    return render_template('admin/jobs.html', jobs=jobs, form=JobForm())

@admin_bp.route('/jobs/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_create_job():
    """
    Handle job creation from admin interface.
    
    Returns:
        GET: Rendered job creation form
        POST: Redirect to jobs list or re-render form with errors
        
    Side Effects:
        - Creates new job record if validation passes
        - Logs creation attempts (success/failure)
        - Flashes success/error messages
    """
    form = JobForm()
    
    if form.validate_on_submit():
        try:
            # Handle file upload if present
            logo_filename = None
            if form.company_logo.data:
                logo_filename = save_company_logo(form.company_logo.data)
                logger.info(f"Saved company logo: {logo_filename}")
            
            # Create job as admin (note: poster_id set to admin's ID)
            job = Job(
                title=form.title.data,
                description=form.description.data,
                salary=form.salary.data,
                location=form.location.data,
                category=form.category.data,
                company=form.company.data,
                company_logo=logo_filename,
                poster_id=session['user_id']  # Admin is creating this job
            )
            
            db.session.add(job)
            db.session.commit()
            
            logger.info(f"Admin {session['user_id']} created new job ID {job.id}")
            flash('Job created successfully!', 'success')
            return redirect(url_for('admin.admin_jobs'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Job creation failed: {str(e)}")
            flash('An error occurred while creating the job.', 'danger')
    
    return render_template('admin/create_job.html', form=form)


@admin_bp.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_job(job_id):
    """
    Handle editing job listings as an admin.
    
    Args:
        job_id: ID of the job to edit
        
    Returns:
        Rendered template (GET) or redirect (POST)
        
    Side Effects:
        - Updates job record in database
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        /admin/jobs/15/edit
    """
    job = db.get_or_404(Job, job_id)
    form = JobForm(obj=job)
    
    if form.validate_on_submit():
        try:
            job.title = form.title.data
            job.company = form.company.data
            job.location = form.location.data
            job.description = form.description.data
            job.salary = form.salary.data
            job.category = form.category.data
            
            db.session.commit()
            logger.info(
                f"Admin {session['user_id']} updated job {job_id}: {job.title} at {job.company}")
            flash('Job updated successfully.', 'success')
            return redirect(url_for('admin.admin_jobs'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating job {job_id}: {str(e)}")
            flash('An error occurred while updating the job.', 'danger')
    
    return render_template('admin/edit_job.html', form=form, job=job)

@admin_bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_job(job_id):
    """
    Handle job deletion by admin (including associated applications).
    
    Args:
        job_id: ID of the job to delete
        
    Returns:
        Redirect to jobs list
        
    Side Effects:
        - Removes job record and associated applications from database
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        POST /admin/jobs/15/delete
    """
    job = db.get_or_404(Job, job_id)
    
    try:
        # Delete associated applications first
        applications = Application.query.filter_by(job_id=job.id).all()
        for application in applications:
            db.session.delete(application)
        
        # Now delete the job
        db.session.delete(job)
        db.session.commit()
        logger.info(
            f"Admin {session['user_id']} deleted job {job_id}: {job.title} at {job.company}")
        flash('Job deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        flash('An error occurred while deleting the job.', 'danger')
    
    return redirect(url_for('admin.admin_jobs'))

@admin_bp.route('/applications')
@login_required
@role_required('admin')
def admin_applications():
    """
    Display all job applications for admin management.
    
    Returns:
        Rendered template with list of all applications
        
    Side Effects:
        - Logs access to application management
        - Retrieves all applications from database
        
    Example:
        /admin/applications
    """
    logger.info(f"Admin {session['user_id']} accessed the applications management page")
    applications = Application.query.all()
    logger.info(f"Retrieved {len(applications)} applications for admin view")
    return render_template('admin/applications.html', applications=applications)

@admin_bp.route('/applications/<int:application_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def admin_update_application(application_id):
    """
    Update application status as admin.
    
    Args:
        application_id: ID of the application to update
        
    Returns:
        Redirect to applications list
        
    Side Effects:
        - Updates application status in database
        - Validates status against allowed values
        - Logs admin actions
        - Flashes success/error messages
        
    Example:
        POST /admin/applications/42/update
    """
    application = db.get_or_404(Application, application_id)
    new_status = request.form.get('status')
    
    # Validate status with strict input validation
    valid_statuses = ['pending', 'reviewed', 'rejected', 'shortlisted', 'hired']
    if not new_status or new_status not in valid_statuses:
        logger.warning(f"Admin {session['user_id']} attempted invalid application status update: '{new_status}' for application {application_id}")
        flash('Invalid application status.', 'danger')
        return redirect(url_for('admin.admin_applications'))
    
    previous_status = application.status
    application.status = new_status
    db.session.commit()
    
    logger.info(f"Admin {session['user_id']} updated application {application_id} status from '{previous_status}' to '{new_status}'")
    flash(f'Application status updated to {new_status}.', 'success')
    
    return redirect(url_for('admin.admin_applications'))
