import os
import sys
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from app import create_app


def test_app_factory_development():
    config['development'].SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app(config['development'])
    assert app.config['DEBUG']
    assert app.config['SQLALCHEMY_ECHO']
    # Assuming DevelopmentConfig sets TESTING to False or it defaults to False
    assert not app.config['TESTING']


def test_app_factory_production():
    config['production'].SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app(config['production'])
    assert not app.config['DEBUG']
    assert app.config['SESSION_COOKIE_SECURE']
    assert app.config['PREFERRED_URL_SCHEME'] == 'https'
