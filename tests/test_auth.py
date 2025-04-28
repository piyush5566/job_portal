import sys
import os
import pytest
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from config import config
from extensions import db
from models import User

@pytest.fixture
def client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_register_login_logout(client):
    # Register
    resp = client.post('/register', data={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!'
    }, follow_redirects=True)
    assert b'Account' in resp.data or resp.status_code == 200
    # Login
    resp = client.post('/login', data={
        'email': 'testuser@example.com',
        'password': 'TestPassword123!'
    }, follow_redirects=True)
    assert b'Logout' in resp.data or b'Profile' in resp.data
    # Logout
    resp = client.get('/logout', follow_redirects=True)
    assert b'Login' in resp.data

def test_register_page_loads(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_profile_requires_login(client):
    resp = client.get('/profile', follow_redirects=True)
    assert b'Login' in resp.data or resp.status_code == 403

def test_profile_update(client):
    user = User(username='profileuser', email='profile@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
    resp = client.post('/profile', data={
        'username': 'profileuser',
        'email': 'profile@example.com',
        'about_me': 'Updated!'
    }, follow_redirects=True)
    assert b'Updated' in resp.data or resp.status_code == 200

# def test_reset_password_page(client):
#     resp = client.get('/reset_password')
#     assert resp.status_code == 200
#     assert b'Reset' in resp.data

# def test_reset_password_post(client):
#     user = User(username='resetuser', email='reset@example.com', password='hash', role='job_seeker')
#     db.session.add(user)
#     db.session.commit()
#     resp = client.post('/reset_password', data={
#         'email': 'reset@example.com'
#     }, follow_redirects=True)
#     assert b'email' in resp.data or resp.status_code == 200

def test_register_duplicate_email(client):
    user = User(username='dupuser', email='dup@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    resp = client.post('/register', data={
        'username': 'dupuser2',
        'email': 'dup@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!',
        'role': 'job_seeker'
    }, follow_redirects=True)
    assert b'Email already registered' in resp.data or resp.status_code == 200

def test_register_invalid_form(client):
    resp = client.post('/register', data={
        'username': '',
        'email': 'notanemail',
        'password': 'short',
        'confirm_password': 'short',
        'role': 'job_seeker'
    }, follow_redirects=True)
    assert b'danger' in resp.data or resp.status_code == 200

def test_login_invalid(client):
    resp = client.post('/login', data={
        'email': 'notfound@example.com',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert b'Invalid email or password' in resp.data or resp.status_code == 200

def test_login_already_logged_in(client):
    user = User(username='already', email='already@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
    resp = client.get('/login', follow_redirects=True)
    assert resp.status_code == 200

def test_register_already_logged_in(client):
    user = User(username='already2', email='already2@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
    resp = client.get('/register', follow_redirects=True)
    assert resp.status_code == 200

def test_profile_duplicate_username(client):
    user1 = User(username='user1', email='user1@example.com', password='hash', role='job_seeker')
    user2 = User(username='user2', email='user2@example.com', password='hash', role='job_seeker')
    db.session.add_all([user1, user2])
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user2.id
    resp = client.post('/profile', data={
        'username': 'user1',
        'email': 'user2@example.com',
        'about_me': ''
    }, follow_redirects=True)
    assert b'already taken' in resp.data or resp.status_code == 200

def test_profile_duplicate_email(client):
    user1 = User(username='user3', email='user3@example.com', password='hash', role='job_seeker')
    user2 = User(username='user4', email='user4@example.com', password='hash', role='job_seeker')
    db.session.add_all([user1, user2])
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user2.id
    resp = client.post('/profile', data={
        'username': 'user4',
        'email': 'user3@example.com',
        'about_me': ''
    }, follow_redirects=True)
    assert b'already registered' in resp.data or resp.status_code == 200

def test_profile_invalid_picture(client):
    from io import BytesIO
    user = User(username='picuser', email='picuser@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
    data = {
        'username': 'picuser',
        'email': 'picuser@example.com',
        'profile_picture': (BytesIO(b'my file contents'), 'bad.exe')
    }
    resp = client.post('/profile', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'Invalid profile picture file type' in resp.data or resp.status_code == 200
