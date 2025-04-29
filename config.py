import os
from dotenv import load_dotenv
from utils import UPLOAD_FOLDER, COMPANY_LOGOS_FOLDER, PROFILE_UPLOAD_FOLDER, ALLOWED_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_RESUME_EXTENSIONS, ALLOWED_PIC_EXTENSIONS


load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # File upload settings
    UPLOAD_FOLDER = UPLOAD_FOLDER
    COMPANY_LOGOS_FOLDER = COMPANY_LOGOS_FOLDER
    PROFILE_UPLOAD_FOLDER = PROFILE_UPLOAD_FOLDER
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    ALLOWED_IMAGE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS
    
    # GCS Configuration
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    ENABLE_GCS_UPLOAD = os.environ.get('ENABLE_GCS_UPLOAD', 'False').lower() == 'true'
    
    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # REMEMBER_COOKIE_SECURE = True
    # REMEMBER_COOKIE_HTTPONLY = True
    # REMEMBER_COOKIE_SAMESITE = 'Lax'
    SQLALCHEMY_ECHO = False
    PREFERRED_URL_SCHEME = 'https'
    DEBUG = False
    TESTING = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    SCHEDULER_INTERVAL_MINUTES = int(os.environ.get('SCHEDULER_INTERVAL_MINUTES', 15))
    SCHEDULER_INITIALIZED = False # No longer used by app factory


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True # Useful for debugging queries
    SESSION_COOKIE_SECURE = False # Allow HTTP for local dev
    # REMEMBER_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = 'http'
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    # Production specific settings (already mostly covered by base Config)
    # Ensure SECRET_KEY, DATABASE_URL etc are set securely via environment variables
    LOG_LEVEL = 'WARNING'
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory DB for tests
    SECRET_KEY = 'test'
    WTF_CSRF_ENABLED = False # Disable CSRF for easier form testing
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = 'http'
    DEBUG = False # Ensure debug is off even in testing unless needed


class DevelopmentTestingConfig(TestingConfig):
    # Inherits from TestingConfig, can add specific overrides if needed
    DEBUG = True # Enable debug for dev testing if helpful
    SQLALCHEMY_ECHO = True

class ProductionTestingConfig(TestingConfig):
    # Inherits from TestingConfig, closer to production settings
    pass

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'dev_testing': DevelopmentTestingConfig,
    'prod_testing': ProductionTestingConfig,
    'default': DevelopmentConfig
}

