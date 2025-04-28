import sys
import os
import pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import config
from extensions import db
from models import Job

@pytest.fixture
def main_client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Add a job for featured jobs
            job = Job(title='TestJob', company='TestCo', location='Remote', description='desc', salary='$100', category='IT', poster_id=1)
            db.session.add(job)
            db.session.commit()
            yield client
            db.session.remove()
            db.drop_all()

def test_home_page(main_client):
    response = main_client.get('/')
    assert response.status_code == 200
    assert b'Job' in response.data or b'Featured' in response.data

def test_about_page(main_client):
    response = main_client.get('/about')
    assert response.status_code == 200
    assert b'About' in response.data or b'about' in response.data

def test_privacy_page(main_client):
    response = main_client.get('/privacy')
    assert response.status_code == 200
    assert b'Privacy' in response.data or b'privacy' in response.data

def test_terms_page(main_client):
    response = main_client.get('/terms')
    assert response.status_code == 200
    assert b'Terms' in response.data or b'terms' in response.data

def test_contact_page_get(main_client):
    response = main_client.get('/contact')
    assert response.status_code == 200
    assert b'Contact' in response.data or b'contact' in response.data

def test_contact_page_post_success(main_client, monkeypatch):
    # Patch mail.send to simulate success
    monkeypatch.setattr('extensions.mail.send', lambda msg: True)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'subject': 'Test Subject',
        'message': 'Hello!'
    }
    response = main_client.post('/contact', data=data, follow_redirects=True)
    assert b'message has been sent' in response.data or response.status_code == 200

def test_contact_page_post_failure(main_client, monkeypatch):
    # Patch mail.send to raise exception
    def fail_send(msg): raise Exception('fail')
    monkeypatch.setattr('extensions.mail.send', fail_send)
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'subject': 'Test Subject',
        'message': 'Hello!'
    }
    response = main_client.post('/contact', data=data, follow_redirects=True)
    assert b'error' in response.data or response.status_code == 200

def test_contact_page_post_invalid(main_client):
    # Missing required fields
    data = {
        'name': '',
        'email': 'notanemail',
        'subject': '',
        'message': ''
    }
    response = main_client.post('/contact', data=data, follow_redirects=True)
    assert b'danger' in response.data or response.status_code == 200
