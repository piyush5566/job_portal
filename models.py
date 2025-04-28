"""
Database models for the Job Portal application.

This module defines the data models used throughout the application:
- User: Represents application users (job seekers, employers, admins)
- Job: Represents job listings posted by employers
- Application: Represents job applications submitted by job seekers

All models use SQLAlchemy ORM for database interactions.
"""

from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from extensions import db, bcrypt


class User(db.Model):
    """
    User model representing all types of users in the system.
    
    This model stores authentication information and basic user details.
    Users can have one of three roles: job_seeker, employer, or admin.
    
    Attributes:
        id (int): Primary key for the user
        username (str): User's username (3-50 characters)
        email (str): User's email address (unique)
        password (str): Hashed password
        role (str): User's role (job_seeker, employer, or admin)
        profile_picture (str): Path to user's profile picture
        jobs_posted (relationship): Jobs posted by this user (for employers)
        applications (relationship): Job applications submitted by this user (for job seekers)
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    profile_picture = db.Column(
        db.String(200), nullable=True, default='img/profiles/default.jpg')

    jobs_posted = db.relationship('Job', backref='poster', lazy=True, cascade="all, delete-orphan")
    applications = db.relationship(
        'Application', backref='applicant', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """
        Set the user's password by hashing it with bcrypt.
        
        Args:
            password (str): The plain text password to hash and store
        """
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """
        Verify if the provided password matches the stored hash.
        
        Args:
            password (str): The plain text password to check
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return bcrypt.check_password_hash(self.password, password)

    def __repr__(self):
        """String representation of the User object."""
        return f'<User {self.username} ({self.role})>'


class Job(db.Model):
    """
    Job model representing job listings posted by employers.
    
    Attributes:
        id (int): Primary key for the job
        title (str): Job title
        description (str): Detailed job description
        salary (str): Salary information (optional)
        location (str): Job location
        category (str): Job category
        company (str): Company name
        company_logo (str): Path to company logo
        posted_date (datetime): When the job was posted
        poster_id (int): Foreign key to the employer who posted the job
        applications (relationship): Applications submitted for this job
    """
    __tablename__ = 'job'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    salary = db.Column(db.String(50))
    location = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    company = db.Column(db.String(100), nullable=False, index=True)
    company_logo = db.Column(
        db.String(200), nullable=True, default='img/company_logos/default.png')
    posted_date = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    applications = db.relationship('Application', backref='job', lazy=True, cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('title', 'company', 'poster_id', 'location',
                                       name='uq_job_title_company_poster_location'),)

    # Property to easily get application count (consider if this causes N+1 issues later)
    @property
    def application_count(self):
        return len(self.applications)
    
    def __repr__(self):
        """String representation of the Job object."""
        return f'<Job {self.title} at {self.company}>'


class Application(db.Model):
    """
    Application model representing job applications submitted by job seekers.
    
    Attributes:
        id (int): Primary key for the application
        job_id (int): Foreign key to the job being applied for
        applicant_id (int): Foreign key to the user applying for the job
        application_date (datetime): When the application was submitted
        status (str): Current status of the application
                     (applied, pending, reviewed, rejected, shortlisted, hired)
        resume_path (str): Path to the uploaded resume file
    """
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    applicant_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    application_date = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), index=True)
    status = db.Column(db.String(20), default='applied', index=True)
    resume_path = db.Column(db.String(200), nullable=True)

    # Add unique constraint to prevent duplicate applications
    __table_args__ = (db.UniqueConstraint('job_id', 'applicant_id', name='_job_applicant_uc'),)
    
    def __repr__(self):
        """String representation of the Application object."""
        return f'<Application {self.id}>'
