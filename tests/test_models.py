import pytest
from app import create_app
from extensions import db
from config import config
from models import User, Job, Application



@pytest.fixture
def app():
    app = create_app(config['dev_testing'])
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session

def test_user_model(session):
    user = User(username='testuser', email='test@example.com', password='hash', role='job_seeker')
    session.add(user)
    session.commit()
    assert User.query.filter_by(username='testuser').first() is not None

def test_job_model(session):
    user = User(username='employer', email='emp@example.com', password='hash', role='employer')
    session.add(user)
    session.commit()
    job = Job(title='Developer', description='Job desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=user.id)
    session.add(job)
    session.commit()
    assert Job.query.filter_by(title='Developer').first() is not None

def test_application_model(session):
    user = User(username='seeker', email='seek@example.com', password='hash', role='job_seeker')
    employer = User(username='employer2', email='emp2@example.com', password='hash', role='employer')
    session.add_all([user, employer])
    session.commit()
    job = Job(title='QA', description='QA desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=employer.id)
    session.add(job)
    session.commit()
    app = Application(job_id=job.id, applicant_id=user.id, status='applied')
    session.add(app)
    session.commit()
    assert Application.query.filter_by(job_id=job.id, applicant_id=user.id).first() is not None
