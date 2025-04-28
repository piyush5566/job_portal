import os
from dotenv import load_dotenv
from utils import UPLOAD_FOLDER, COMPANY_LOGOS_FOLDER, PROFILE_UPLOAD_FOLDER, ALLOWED_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_RESUME_EXTENSIONS, ALLOWED_PIC_EXTENSIONS


# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
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
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
class DevTestConfig(DevelopmentConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    WTF_CSRF_ENABLED = False
    
class ProdTestConfig(ProductionConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    'dev_testing': DevTestConfig,
    'prod_testing': ProdTestConfig,
}