"""Logging Configuration Module.

This module configures application-wide logging with:
- Rotating file handler (max 10MB per file, keeps 5 backups)
- Standardized log format
- Console output in development mode
- Automatic log directory creation

Log Format:
    %(asctime)s - %(name)s - %(levelname)s - %(message)s

Log Files:
    - logs/job_portal.log (main application log)
    - logs/job_portal_error.log (error-only log)

Usage:
    from logging_config import setup_logger
    app = Flask(__name__)
    setup_logger(app)
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logger(app):
    """Configure application logging handlers and formatters.
    
    Args:
        app (Flask): Flask application instance
        
    Side Effects:
        - Creates 'logs' directory if not exists
        - Configures two file handlers:
            - job_portal.log (all logs)
            - job_portal_error.log (errors only)
        - Adds console handler in debug mode
        - Sets log level based on app config
        
    Configuration:
        LOG_LEVEL (str): Defaults to 'INFO'
        DEBUG (bool): Enables console output when True
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure the main application logger
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler for all logs
    file_handler = RotatingFileHandler(
        'logs/job_portal.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Error file handler for errors only
    error_file_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10485760,
        backupCount=10
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    
    # Console handler for outputting logs to the console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Configure Flask logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # Create a general purpose logger
    logger = logging.getLogger('job_portal')
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    return logger
