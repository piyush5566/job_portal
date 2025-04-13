"""
Flask extensions initialization for the Job Portal application.

This module initializes all Flask extensions used throughout the application:
- SQLAlchemy: Database ORM
- Bcrypt: Password hashing
- Migrate: Database migrations
- Mail: Email sending
- CSRFProtect: Cross-Site Request Forgery protection

Extensions are initialized without the app context to support the application factory pattern.
They are later initialized with the app in the init_app function.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()

def init_app(app):
    """
    Initialize all Flask extensions with the application instance.
    
    This function is called in the application factory pattern to bind
    all extensions to the Flask application instance.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)


