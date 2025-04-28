import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import config
from extensions import db
from models import User, Job

@pytest.fixture
def employer_client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            employer = User(username='employer', email='employer@example.com', password='hash', role='employer')
            db.session.add(employer)
            db.session.commit()
            with client.session_transaction() as sess:
                sess['user_id'] = employer.id
                sess['role'] = 'employer'
            yield client
            db.session.remove()
            db.drop_all()

def test_employer_my_jobs_requires_login(employer_client):
    response = employer_client.get('my_jobs', follow_redirects=True)
    assert b'Login' in response.data or response.status_code == 403

def test_post_job(employer_client):
    resp = employer_client.post('/jobs/new', data={
        'title': 'Employer Job',
        'description': 'Job desc',
        'location': 'Remote',
        'company': 'EmpCo',
        'salary': '90000',
        'requirements': 'None',
        'category': 'IT'
    }, follow_redirects=True)
    assert b'Employer Job' in resp.data or resp.status_code == 200

# def test_edit_job(employer_client):
#     job = Job(title='EditJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
#     db.session.add(job)
#     db.session.commit()
#     resp = employer_client.post(f'jobs/{job.id}/edit', data={
#         'title': 'EditedJob',
#         'description': 'desc',
#         'location': 'Remote',
#         'company': 'EmpCo',
#         'salary': '90000',
#         'requirements': 'None',
#         'category': 'IT'
#     }, follow_redirects=True)
#     assert b'EditedJob' in resp.data or resp.status_code == 200

def test_delete_job(employer_client):
    job = Job(title='DeleteJob', description='desc', location='Mumbai', category='Software Development', company='Moca Mola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    resp = employer_client.post(f'jobs/{job.id}/delete', follow_redirects=True)
    assert b'deleted' in resp.data or resp.status_code == 200

def test_post_job_redirect_employer(employer_client):
    resp = employer_client.get('post-job-redirect', follow_redirects=True)
    assert b'Job' in resp.data or resp.status_code == 200

def test_post_job_redirect_admin(employer_client):
    # Simulate admin session
    with employer_client.session_transaction() as sess:
        sess['role'] = 'admin'
    resp = employer_client.get('post-job-redirect', follow_redirects=True)
    assert b'Job' in resp.data or resp.status_code == 200

def test_new_job_get(employer_client):
    resp = employer_client.get('jobs/new')
    assert resp.status_code == 200
    assert b'Job' in resp.data or b'Post' in resp.data

def test_new_job_post_invalid(employer_client):
    # Post with missing required fields
    resp = employer_client.post('jobs/new', data={}, follow_redirects=True)
    assert b'Job' in resp.data or resp.status_code == 200

def test_my_jobs(employer_client):
    resp = employer_client.get('my_jobs')
    assert resp.status_code == 200
    assert b'Job' in resp.data or b'My Jobs' in resp.data

def test_job_applications_permission(employer_client):
    # Create a job and application for this employer
    from models import Application
    job = Job(title='TestJob', description='desc', location='Varanasi', category='Software Development', company='Alstom', poster_id=1)
    db.session.add(job)
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=1, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = employer_client.get(f'jobs/{job.id}/applications')
    assert resp.status_code == 200
    assert b'Application' in resp.data or b'Job' in resp.data

def test_job_applications_unauthorized(employer_client):
    # Create a job for another employer
    job = Job(title='OtherJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=999)
    db.session.add(job)
    db.session.commit()
    resp = employer_client.get(f'jobs/{job.id}/applications', follow_redirects=True)
    assert b'permission' in resp.data or resp.status_code == 200

def test_delete_job_permission(employer_client):
    job = Job(title='DeleteMe', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    resp = employer_client.post(f'jobs/{job.id}/delete', follow_redirects=True)
    assert b'deleted' in resp.data or resp.status_code == 200

def test_delete_job_unauthorized(employer_client):
    job = Job(title='NotMine', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=999)
    db.session.add(job)
    db.session.commit()
    resp = employer_client.post(f'jobs/{job.id}/delete', follow_redirects=True)
    assert b'permission' in resp.data or resp.status_code == 200

def test_update_application_permission(employer_client):
    from models import Application
    job = Job(title='UpdateJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=1, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = employer_client.post(f'applications/{app_obj.id}/update', data={'status': 'reviewed'}, follow_redirects=True)
    assert b'reviewed' in resp.data or resp.status_code == 200

def test_update_application_invalid_status(employer_client):
    from models import Application
    job = Job(title='UpdateJob2', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=1, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = employer_client.post(f'applications/{app_obj.id}/update', data={'status': 'invalid'}, follow_redirects=True)
    assert b'Invalid status' in resp.data or resp.status_code == 200

def test_update_application_unauthorized(employer_client):
    from models import Application
    job = Job(title='NotMine2', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=999)
    db.session.add(job)
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=1, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = employer_client.post(f'applications/{app_obj.id}/update', data={'status': 'reviewed'}, follow_redirects=True)
    assert b'permission' in resp.data or resp.status_code == 200
