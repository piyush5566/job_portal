# Job Portal Web Application

A full-featured job portal web application built with Flask, allowing job seekers to find and apply for jobs, employers to post job listings, and administrators to manage the entire platform.

Live Deployment: https://jobportal-production-fcd5.up.railway.app

## Features

- **User Management**
  - Multiple user roles: Job Seekers, Employers, and Administrators
  - Secure authentication with password strength requirements
  - Profile management

- **Job Management**
  - Job posting with company logo support
  - Advanced job search functionality
  - Job applications with resume upload
  - Application status tracking

- **Admin Features**
  - User management
  - Job listing moderation
  - Application oversight
  - System monitoring

- **Additional Features**
  - Email notifications
  - Contact form
  - Secure file uploads
  - Role-based access control

## Technology Stack

- **Backend**: Python/Flask
- **Database**: SQLite (configurable for other databases)
- **ORM**: SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Security**: Flask-Talisman, CSRF protection
- **File Storage(Resume)**: Local storage with GCS support
- **Email**: Flask-Mail
- **Task Scheduling**: APScheduler

## Prerequisites

- Python 3.12+
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd job_portal
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a .env file:
   ```
   SECRET_KEY=your_secret_key
   SQLALCHEMY_DATABASE_URI=sqlite:///jobportal.db
   SQLALCHEMY_TRACK_MODIFICATIONS=False
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your_email@gmail.com
   MAIL_PASSWORD=your_app_password
   MAIL_DEFAULT_SENDER=your_email@gmail.com
   CONTACT_EMAIL_RECIPIENT=your_contact_email@gmail.com
   GCS_BUCKET_NAME=your_bucket_name
   ENABLE_GCS_UPLOAD=False
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

## Running the Application

1. Development mode:
   ```bash
   python run.py
   ```

2. Production mode:
   ```bash
   gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - "app:create_app()"
   ```

The application will be available at `http://localhost:5000`

## Project Structure

- `app.py`: Application factory and configuration
- `models.py`: Database models (User, Job, Application)
- `forms.py`: WTForms form definitions
- `extensions.py`: Flask extensions initialization
- `config.py`: Configuration settings
- `blueprints/`: Feature-specific routes and views
  - `admin/`: Administrator features
  - `auth/`: Authentication
  - `employer/`: Employer features
  - `job_seeker/`: Job seeker features
  - `jobs/`: Job listing features
  - `main/`: Core routes
  - `utils/`: Utility routes

## Security Features

- Password hashing with bcrypt
- CSRF protection
- Content Security Policy (CSP)
- Secure session configuration
- File upload validation
- Role-based access control

## Logging

The application uses a comprehensive logging system:
- `logs/job_portal.log`: General application logs
- `logs/errors.log`: Error-specific logs
- Console logging

## Database Migrations

Database migrations are handled with Flask-Migrate:
```bash
# Create a new migration
flask db migrate -m "Migration message"

# Apply migrations
flask db upgrade
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.