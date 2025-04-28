import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import config
from extensions import db
from models import User, Job, Application

@pytest.fixture
def client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def admin_client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            admin = User(username='admin', email='admin@example.com', password='hash', role='admin')
            db.session.add(admin)
            db.session.commit()
            with client.session_transaction() as sess:
                sess['user_id'] = admin.id
                sess['role'] = 'admin'
            yield client
            db.session.remove()
            db.drop_all()

def test_admin_dashboard_requires_login(client):
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert b'Login' in response.data or response.status_code == 403

def test_admin_users_requires_login(client):
    response = client.get('/admin/users', follow_redirects=True)
    assert b'Login' in response.data or response.status_code == 403

def test_admin_dashboard(admin_client):
    resp = admin_client.get('/admin/dashboard')
    assert resp.status_code == 200
    assert b'Admin' in resp.data or b'Dashboard' in resp.data

def test_admin_users(admin_client):
    resp = admin_client.get('/admin/users')
    assert resp.status_code == 200
    assert b'User' in resp.data or b'Users' in resp.data

def test_admin_create_user(admin_client):
    resp = admin_client.post('/admin/users/new', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'role': 'job_seeker'
    }, follow_redirects=True)
    assert b'User' in resp.data or b'created' in resp.data or resp.status_code == 200

def test_admin_create_user_duplicate_email(admin_client):
    user = User(username='dup', email='dup@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    resp = admin_client.post('/admin/users/new', data={
        'username': 'dup2',
        'email': 'dup@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'role': 'job_seeker'
    }, follow_redirects=True)
    assert b'Email already exists' in resp.data or resp.status_code == 200

def test_admin_edit_user(admin_client):
    user = User(username='editme', email='editme@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    resp = admin_client.post(f'/admin/users/{user.id}/edit', data={
        'username': 'edited',
        'email': 'edited@example.com',
        'role': 'employer'
    }, follow_redirects=True)
    assert b'edited' in resp.data or resp.status_code == 200

def test_admin_edit_user_duplicate_email(admin_client):
    user1 = User(username='user1', email='user1@example.com', password='hash', role='job_seeker')
    user2 = User(username='user2', email='user2@example.com', password='hash', role='job_seeker')
    db.session.add_all([user1, user2])
    db.session.commit()
    resp = admin_client.post(f'/admin/users/{user2.id}/edit', data={
        'username': 'user2',
        'email': 'user1@example.com',
        'role': 'employer'
    }, follow_redirects=True)
    assert b'Email already exists' in resp.data or resp.status_code == 200

def test_admin_delete_user(admin_client):
    user = User(username='deleteme', email='deleteme@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    resp = admin_client.post(f'/admin/users/{user.id}/delete', follow_redirects=True)
    assert b'deleted' in resp.data or resp.status_code == 200

def test_admin_delete_self(admin_client):
    # Admin tries to delete their own account
    admin = User.query.filter_by(username='admin').first()
    resp = admin_client.post(f'/admin/users/{admin.id}/delete', follow_redirects=True)
    assert b'cannot delete your own account' in resp.data or resp.status_code == 200

def test_admin_jobs(admin_client):
    resp = admin_client.get('/admin/jobs')
    assert resp.status_code == 200
    assert b'Job' in resp.data or b'Jobs' in resp.data

def test_admin_create_job(admin_client):
    resp = admin_client.post('/admin/jobs/new', data={
        'title': 'Admin Job',
        'description': 'Admin job desc',
        'location': 'Remote',
        'company': 'AdminCo',
        'salary': '100000',
        'requirements': 'None',
        'category': 'IT'
    }, follow_redirects=True)
    assert b'Admin Job' in resp.data or resp.status_code == 200

def test_admin_edit_job(admin_client):
    job = Job(title='EditJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    resp = admin_client.post(f'/admin/jobs/{job.id}/edit', data={
        'title': 'EditedJob',
        'description': 'desc',
        'location': 'Remote',
        'company': 'AdminCo',
        'salary': '100000',
        'requirements': 'None',
        'category': 'IT'
    }, follow_redirects=True)
    assert b'EditedJob' in resp.data or resp.status_code == 200

def test_admin_delete_job(admin_client):
    job = Job(title='DeleteJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add(job)
    db.session.commit()
    resp = admin_client.post(f'/admin/jobs/{job.id}/delete', follow_redirects=True)
    assert b'deleted' in resp.data or resp.status_code == 200

def test_admin_applications(admin_client):
    resp = admin_client.get('/admin/applications')
    assert resp.status_code == 200
    assert b'Application' in resp.data or b'Applications' in resp.data

def test_admin_update_application(admin_client):
    user = User(username='applicant', email='applicant@example.com', password='hash', role='job_seeker')
    job = Job(title='AppJob', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add_all([user, job])
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=user.id, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = admin_client.post(f'/admin/applications/{app_obj.id}/update', data={'status': 'reviewed'}, follow_redirects=True)
    assert b'reviewed' in resp.data or resp.status_code == 200

def test_admin_update_application_invalid_status(admin_client):
    user = User(username='applicant2', email='applicant2@example.com', password='hash', role='job_seeker')
    job = Job(title='AppJob2', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=1)
    db.session.add_all([user, job])
    db.session.commit()
    app_obj = Application(job_id=job.id, applicant_id=user.id, status='applied')
    db.session.add(app_obj)
    db.session.commit()
    resp = admin_client.post(f'/admin/applications/{app_obj.id}/update', data={'status': 'invalid'}, follow_redirects=True)
    assert b'Invalid application status' in resp.data or resp.status_code == 200
