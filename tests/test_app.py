import pytest
from app import create_app
from config import config
import os
from unittest.mock import patch

@patch.dict(os.environ, {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
def test_app_factory_development():
    app = create_app(config['development'])
    assert app.config['DEBUG']
    assert app.config['SQLALCHEMY_ECHO']
    # Assuming DevelopmentConfig sets TESTING to False or it defaults to False
    assert not app.config['TESTING']

@patch.dict(os.environ, {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
def test_app_factory_production():
    app = create_app(config['production'])
    assert not app.config['DEBUG']
    assert app.config['SESSION_COOKIE_SECURE']
    assert app.config['PREFERRED_URL_SCHEME'] == 'https'
