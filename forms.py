"""
Form definitions for the Job Portal application.

This module contains all the WTForms form classes used throughout the application
for data validation and rendering. Each form corresponds to a specific user action
such as registration, login, job posting, etc.

All forms include appropriate validators to ensure data integrity and security.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError
from flask_wtf.file import FileAllowed, FileRequired
import re

def validate_password_strength(form, field):
    """
    Validate password strength according to security requirements.
    
    Ensures passwords meet the following criteria:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    
    Args:
        form: The form containing the password field
        field: The password field to validate
        
    Raises:
        ValidationError: If the password doesn't meet requirements
    """
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', password):
        raise ValidationError('Password must contain at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character')


class RegistrationForm(FlaskForm):
    """
    Form for user registration.
    
    This form is used for standard user registration (job seekers and employers).
    It includes fields for username, email, password, and role selection.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[A-Za-z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=72),
        validate_password_strength
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        ('job_seeker', 'Job Seeker'), 
        ('employer', 'Employer')
    ], validators=[DataRequired()])
    submit = SubmitField('Register')


class AdminRegistrationForm(FlaskForm):
    """
    Form for admin-created user registration.
    
    This form is used by administrators to create new users of any role.
    It extends the standard registration form to include the admin role option.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[A-Za-z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=72),
        validate_password_strength
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        ('job_seeker', 'Job Seeker'),
        ('employer', 'Employer'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    submit = SubmitField('Create User')


class LoginForm(FlaskForm):
    """
    Form for user login.
    
    Contains fields for email and password authentication.
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class JobForm(FlaskForm):
    """
    Form for creating and editing job listings.
    
    This form is used by employers to post new jobs or edit existing ones.
    It includes all fields necessary for a complete job listing.
    """
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=5, max=100)
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=20, max=5000)
    ])
    salary = StringField('Salary', validators=[
        Optional(),
        Regexp(r'^[$€£¥₹]?[\d,]+(\s*-\s*[$€£¥₹]?[\d,]+)?$', message='Invalid salary format')
    ])
    location = StringField('Location', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    category = StringField('Category', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    company = StringField('Company', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    company_logo = FileField('Company Logo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only (jpg, png, jpeg)!')
    ])
    submit = SubmitField('Post Job')


class ApplicationForm(FlaskForm):
    """
    Form for submitting job applications.
    
    Used by job seekers to apply for jobs. Includes a field for resume upload.
    """
    resume = FileField('Resume', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx'], 'PDF or Word documents only!')
    ])
    submit = SubmitField('Apply')


class ContactForm(FlaskForm):
    """
    Form for the contact page.
    
    Allows users to send messages to the site administrators.
    """
    name = StringField('Your Name', validators=[
        DataRequired(),
        Length(min=2, max=50),
        Regexp(r'^[A-Za-z\s\-\']+$', message='Name can only contain letters, spaces, hyphens, and apostrophes')
    ])
    email = StringField('Your Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[
        DataRequired(), 
        Length(min=5, max=100)
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(), 
        Length(min=10, max=2000)
    ])
    submit = SubmitField('Send Message')


class UserEditForm(FlaskForm):
    """
    Form for administrators to edit user details.
    
    Allows admins to modify username, email, and role of any user.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[A-Za-z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('job_seeker', 'Job Seeker'),
        ('employer', 'Employer'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    submit = SubmitField('Update User')


class ProfileForm(FlaskForm):
    """
    Form for users to edit their own profile.
    
    Allows users to update their username, email, and profile picture.
    """
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[A-Za-z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    profile_picture = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only (jpg, png, jpeg)!')
    ])
    submit = SubmitField('Update Profile')


class ApplicationStatusForm(FlaskForm):
    """
    Form for updating job application status.
    
    Used by employers and admins to update the status of job applications.
    Includes a dropdown with all possible status values.
    """
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('rejected', 'Rejected'),
        ('shortlisted', 'Shortlisted'),
        ('hired', 'Hired')
    ], validators=[DataRequired()])
    application_id = HiddenField('Application ID', validators=[DataRequired()])
    submit = SubmitField('Update Status')
