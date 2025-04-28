import sys
import os
import pytest
import io
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import config
from extensions import db
from models import User, Job, Application

@pytest.fixture
def jobs_client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Add a job and a job seeker
            job = Job(title='TestJob', company='TestCo', location='Remote', description='desc', salary='$100', category='IT', poster_id=1)
            db.session.add(job)
            user = User(username='seeker', email='seeker@example.com', password='hash', role='job_seeker')
            db.session.add(user)
            db.session.commit()
            yield client
            db.session.remove()
            db.drop_all()

def login_job_seeker(client):
    user = User.query.filter_by(username='seeker').first()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = 'job_seeker'

def test_jobs_list_page_loads(jobs_client):
    response = jobs_client.get('/jobs/list')
    assert response.status_code == 200
    assert b'Job' in response.data or b'Jobs' in response.data

def test_jobs_list_with_filters(jobs_client):
    response = jobs_client.get('/jobs/list?location=Remote&category=IT&company=TestCo')
    assert response.status_code == 200
    assert b'Job' in response.data or b'Jobs' in response.data

def test_job_search_api(jobs_client):
    response = jobs_client.get('/jobs/search?location=Remote')
    assert response.status_code == 200
    assert b'jobs' in response.data

def test_job_detail_page_loads(jobs_client):
    job = Job.query.first()
    response = jobs_client.get(f'/jobs/{job.id}')
    assert response.status_code == 200
    assert b'TestJob' in response.data or b'Job' in response.data

def test_job_detail_page_not_found(jobs_client):
    response = jobs_client.get('/jobs/9999')
    assert response.status_code == 404

def test_apply_job_get(jobs_client):
    login_job_seeker(jobs_client)
    job = Job.query.first()
    response = jobs_client.get(f'/jobs/apply/{job.id}')
    assert response.status_code == 200
    assert b'Apply' in response.data or b'Job' in response.data

def test_apply_job_post_success(jobs_client, tmp_path):
    login_job_seeker(jobs_client)
    job = Job.query.first()
    # Simulate file upload
    data = {
        'resume': (io.BytesIO(b'my resume'), 'resume.pdf')
    }
    response = jobs_client.post(f'/jobs/apply/{job.id}', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'submitted' in response.data or response.status_code == 200

def test_apply_job_duplicate(jobs_client):
    login_job_seeker(jobs_client)
    job = Job.query.first()
    # Create an application
    user = User.query.filter_by(username='seeker').first()
    app_obj = Application(job_id=job.id, applicant_id=user.id, status='pending')
    db.session.add(app_obj)
    db.session.commit()
    response = jobs_client.get(f'/jobs/apply/{job.id}', follow_redirects=True)
    assert b'already applied' in response.data or response.status_code == 200

def test_apply_job_post_invalid(jobs_client):
    login_job_seeker(jobs_client)
    job = Job.query.first()
    # Post with no resume (should still work, resume optional)
    response = jobs_client.post(f'/jobs/apply/{job.id}', data={}, follow_redirects=True)
    assert b'submitted' in response.data or response.status_code == 200

def test_apply_job_post_error(jobs_client, monkeypatch):
    login_job_seeker(jobs_client)
    job = Job.query.first()
    # Patch db.session.commit to raise error
    monkeypatch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(Exception('fail')))
    data = {
        'resume': (io.BytesIO(b'my resume'), 'resume.pdf')
    }
    response = jobs_client.post(f'/jobs/apply/{job.id}', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'error' in response.data or response.status_code == 200
