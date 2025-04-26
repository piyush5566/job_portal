import pytest
from app import create_app
from config import config

def test_app_factory_development():
    app = create_app(config['development'])
    assert app.config['DEBUG'] is True
    assert app.config['SQLALCHEMY_ECHO'] is True
    assert app.config['TESTING'] is False

def test_app_factory_production():
    app = create_app(config['production'])
    assert app.config['DEBUG'] is False
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['PREFERRED_URL_SCHEME'] == 'https'
