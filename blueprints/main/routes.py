"""Main Application Routes.

This module contains core application routes including:
- Home page and public views
- Contact form handling
- Static pages
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_mail import Message
import os
from forms import ContactForm
from utils import logger
from models import Job
from extensions import mail
import time

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Display the application home page with featured jobs and categories.
    
    Returns:
        rendered_template: Home page with:
            - Featured jobs (5 most recent)
            - Job category counts
            - Statistics
            
    Side Effects:
        - Logs home page access
        - Queries database for jobs and categories
        
    Example:
        /
    """
    logger.info("Home page accessed")
    # Get featured jobs (most recent jobs)
    featured_jobs = Job.query.order_by(Job.posted_date.desc()).limit(5).all()

    # Count jobs by category
    job_categories = {}
    jobs = Job.query.all()
    for job in jobs:
        if job.category in job_categories:
            job_categories[job.category] += 1
        else:
            job_categories[job.category] = 1

    # Sort categories by count (descending)
    sorted_categories = sorted(job_categories.items(), key=lambda x: x[1], reverse=True)

    return render_template('index.html', featured_jobs=featured_jobs, job_categories=sorted_categories)

@main.route('/about')
def about():
    logger.info("About page accessed")
    return render_template('about.html')

@main.route('/privacy')
def privacy():
    logger.info("Privacy policy page accessed")
    return render_template('privacy.html', current_date='April 12, 2025')

@main.route('/terms')
def terms():
    logger.info("Terms of service page accessed")
    return render_template('terms.html', current_date='April 12, 2025')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    """Handle contact form submissions.
    
    Methods:
        GET: Display contact form
        POST: Process form submission and send email
        
    Returns:
        GET: Rendered contact form template
        POST: Redirect to home page with success message
        
    Side Effects:
        - Sends email to configured contact address
        - Logs contact attempts
        - Flashes success/error messages
        
    Example:
        POST /contact
        Form Data: {'name': 'John', 'email': 'john@example.com', 'message': 'Hello'}
    """
    logger.info("Contact page accessed")
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message_body = form.message.data

        logger.info(f"Contact form submitted by {name} <{email}> with subject: {subject}")

        try:
            msg = Message(
                subject=f"Job Portal Contact: {subject}",
                sender=mail.default_sender,
                recipients=[os.getenv('CONTACT_EMAIL_RECIPIENT')],
                body=f"From: {name} <{email}>\n\n{message_body}"
            )
            
            # Add retry logic for email sending
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    mail.send(msg)
                    logger.info(f"Contact email sent successfully from {email} (attempt {attempt + 1})")
                    flash('Your message has been sent! We will get back to you soon.', 'success')
                    break
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt failed
                        logger.error(f"Failed to send contact email after {max_retries} attempts: {str(e)}")
                        flash('An error occurred while sending your message. Please try again later.', 'danger')
                    else:
                        logger.warning(f"Email send attempt {attempt + 1} failed, retrying...")
                        time.sleep(1)  # Wait before retrying
                        continue
            
            return redirect(url_for('main.contact'))
        except Exception as e:
            logger.error(f"Failed to send contact email from {email}: {str(e)}")
            flash(f'An error occurred while sending your message: {e}', 'danger')

    # Log form validation errors
    if form.errors:
        logger.warning(f"Contact form validation failed: {form.errors}")
        
    return render_template('contact.html', form=form)
