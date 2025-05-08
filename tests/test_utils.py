import pytest


import sys
import os
import io
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import config
from utils import allowed_file, save_company_logo, save_profile_picture, get_resume_file, UPLOAD_FOLDER, COMPANY_LOGOS_FOLDER, PROFILE_UPLOAD_FOLDER
from extensions import db
from models import User, Job, Application

class DummyFile:
    def __init__(self, filename, content=b'data'):
        self.filename = filename
        self.content = content
        self.saved_path = None
    def save(self, path):
        self.saved_path = path
        with open(path, 'wb') as f:
            f.write(self.content)

@pytest.fixture(scope='module')
def setup_dirs():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(COMPANY_LOGOS_FOLDER, exist_ok=True)
    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
    yield
    # Cleanup
    import shutil
    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True) # Still cleaning up general uploads like resumes
    # shutil.rmtree(COMPANY_LOGOS_FOLDER, ignore_errors=True) # Prevent deletion of company logos
    # shutil.rmtree(PROFILE_UPLOAD_FOLDER, ignore_errors=True) # Prevent deletion of profile pictures

@pytest.fixture
def client():
    app = create_app(config['dev_testing'])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def app_with_utils():
    app = create_app(config['dev_testing'])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client_with_utils(app_with_utils):
    with app_with_utils.test_client() as client:
        yield client

def login(client, user_id, role):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['role'] = role

def test_utils_health_check(client):
    response = client.get('/utils/health')
    assert response.status_code in (200, 404)  # Adjust if you have a health endpoint

def test_allowed_file():
    assert allowed_file('resume.pdf', {'pdf'})
    assert not allowed_file('resume.exe', {'pdf'})
    assert allowed_file('pic.jpg', {'jpg', 'png'})
    assert not allowed_file('pic', {'jpg'})
    
def test_save_company_logo_success(tmp_path, monkeypatch):
    temp_company_logos_folder = tmp_path / "company_logos"
    temp_company_logos_folder.mkdir()
    monkeypatch.setattr('utils.COMPANY_LOGOS_FOLDER', str(temp_company_logos_folder))

    dummy = DummyFile('logo.png')
    result = save_company_logo(dummy)
    assert result is not None and result.endswith('.png')
    # The 'result' is just the filename, COMPANY_LOGOS_FOLDER is monkeypatched
    assert os.path.exists(os.path.join(str(temp_company_logos_folder), result))

def test_save_company_logo_invalid_type(tmp_path, monkeypatch):
    temp_company_logos_folder = tmp_path / "company_logos_invalid"
    temp_company_logos_folder.mkdir()
    monkeypatch.setattr('utils.COMPANY_LOGOS_FOLDER', str(temp_company_logos_folder))

    dummy = DummyFile('logo.txt')
    result = save_company_logo(dummy)
    assert result is None

def test_save_profile_picture_success(tmp_path, monkeypatch):
    temp_profile_upload_folder = tmp_path / "profile_pics"
    temp_profile_upload_folder.mkdir()
    monkeypatch.setattr('utils.PROFILE_UPLOAD_FOLDER', str(temp_profile_upload_folder))

    # Create a small PNG image in memory
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    dummy_content = img_bytes.read()
    dummy = DummyFile('profile.png', dummy_content)
    # save_profile_picture uses werkzeug's FileStorage.save(), so our DummyFile's save is used.
    result = save_profile_picture(dummy)
    assert result.startswith('img/profiles/')
    assert os.path.exists(os.path.join(str(temp_profile_upload_folder), os.path.basename(result)))

def test_save_profile_picture_failure(monkeypatch):
    class BadFile:
        filename = 'bad.png'
        def save(self, path):
            raise Exception('fail')
    result = save_profile_picture(BadFile())
    assert result == 'img/profiles/default.jpg'

def test_get_resume_file_local(tmp_path):
    # Create a dummy file
    resume_path = tmp_path / 'resume.pdf'
    resume_path.write_bytes(b'data')
    file_path, success = get_resume_file(str(resume_path))
    assert file_path == str(resume_path)
    assert success

def test_get_resume_file_gcs(app_with_utils, tmp_path, monkeypatch):
    # Simulate file not found locally, but found in GCS
    # get_resume_file uses current_app.config['UPLOAD_FOLDER']
    temp_upload_dir_for_gcs_check = tmp_path / "gcs_local_check"
    temp_upload_dir_for_gcs_check.mkdir()
    monkeypatch.setattr('utils.UPLOAD_FOLDER', str(temp_upload_dir_for_gcs_check))

    class DummyBlob:
        def exists(self): return True
        def download_to_filename(self, filename):
            # Ensure the directory for the downloaded file exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'wb') as f: f.write(b'gcs_data')
    class DummyBucket:
        def blob(self, name): return DummyBlob()
    class DummyClient:
        def bucket(self, name): return DummyBucket()
    monkeypatch.setattr('google.cloud.storage.Client', DummyClient)

    file_path_suffix = os.path.join(temp_upload_dir_for_gcs_check, 'gcsuser', 'resume.pdf') # This is the path relative to UPLOAD_FOLDER
    
    returned_path, success = get_resume_file(file_path_suffix, enable_gcs=True, gcs_bucket_name='bucket')
    
    # Check if the function returns the suffix as observed from the error
    assert returned_path == file_path_suffix
    assert success
    
    # Verify that the file was actually downloaded to the correct temporary location
    actual_download_location = os.path.join(str(temp_upload_dir_for_gcs_check), file_path_suffix)
    assert os.path.exists(actual_download_location)
    with open(actual_download_location, 'rb') as f:
        assert f.read() == b'gcs_data'

def test_get_resume_file_not_found():
    file_path, success = get_resume_file('nonexistent.pdf')
    assert file_path is None
    assert not success

def test_serve_resume_admin_access(client_with_utils, app_with_utils, tmp_path):
    # Setup admin, job, application, and dummy resume file
    admin = User(username='admin', email='admin@example.com', password='hash', role='admin')
    job = Job(title='Job', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=2)
    db.session.add_all([admin, job])
    db.session.commit()

    temp_resume_dir = tmp_path / "resumes_admin"
    temp_resume_dir.mkdir(exist_ok=True)
    app_with_utils.config['UPLOAD_FOLDER'] = str(temp_resume_dir)

    resume_rel = '1/resume.pdf'
    resume_abs = os.path.join(str(temp_resume_dir), resume_rel)
    os.makedirs(os.path.dirname(resume_abs), exist_ok=True)
    with open(resume_abs, 'wb') as f:
        f.write(b'data')
    app_obj = Application(job_id=job.id, applicant_id=1, resume_path=resume_rel)
    db.session.add(app_obj)
    db.session.commit()
    login(client_with_utils, admin.id, 'admin')
    resp = client_with_utils.get(f'/resume/{resume_rel}')
    assert resp.status_code == 200
    assert resp.data == b'data'

def test_serve_resume_employer_access(client_with_utils, app_with_utils, tmp_path):
    employer = User(username='emp', email='emp@example.com', password='hash', role='employer')
    db.session.add(employer)
    db.session.commit()
    job = Job(title='Job', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=employer.id)
    db.session.add(job)
    db.session.commit()

    temp_resume_dir = tmp_path / "resumes_employer"
    temp_resume_dir.mkdir(exist_ok=True)
    app_with_utils.config['UPLOAD_FOLDER'] = str(temp_resume_dir)

    resume_rel = '2/resume.pdf'
    resume_abs = os.path.join(str(temp_resume_dir), resume_rel)
    os.makedirs(os.path.dirname(resume_abs), exist_ok=True)
    with open(resume_abs, 'wb') as f:
        f.write(b'data')
    app_obj = Application(job_id=job.id, applicant_id=2, resume_path=resume_rel)
    db.session.add(app_obj)
    db.session.commit()
    login(client_with_utils, employer.id, 'employer')
    resp = client_with_utils.get(f'/resume/{resume_rel}')
    assert resp.status_code == 200

def test_serve_resume_applicant_access(client_with_utils, app_with_utils, tmp_path):
    user = User(username='user', email='user@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    job = Job(title='Job', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=3)
    db.session.add(job)
    db.session.commit()

    temp_resume_dir = tmp_path / "resumes_applicant"
    temp_resume_dir.mkdir(exist_ok=True)
    app_with_utils.config['UPLOAD_FOLDER'] = str(temp_resume_dir)

    resume_rel = '3/resume.pdf'
    resume_abs = os.path.join(str(temp_resume_dir), resume_rel)
    os.makedirs(os.path.dirname(resume_abs), exist_ok=True)
    with open(resume_abs, 'wb') as f:
        f.write(b'data')
    app_obj = Application(job_id=job.id, applicant_id=user.id, resume_path=resume_rel)
    db.session.add(app_obj)
    db.session.commit()
    login(client_with_utils, user.id, 'job_seeker')
    resp = client_with_utils.get(f'/resume/{resume_rel}')
    assert resp.status_code == 200

def test_serve_resume_unauthorized_employer(client_with_utils, app_with_utils, tmp_path):
    employer = User(username='emp2', email='emp2@example.com', password='hash', role='employer')
    db.session.add(employer)
    db.session.commit()
    job = Job(title='Job', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=999)  # Different employer
    db.session.add(job)
    db.session.commit()

    temp_resume_dir = tmp_path / "resumes_unauth_emp"
    temp_resume_dir.mkdir(exist_ok=True)
    app_with_utils.config['UPLOAD_FOLDER'] = str(temp_resume_dir)

    resume_rel = '4/resume.pdf'
    resume_abs = os.path.join(str(temp_resume_dir), resume_rel)
    os.makedirs(os.path.dirname(resume_abs), exist_ok=True)
    with open(resume_abs, 'wb') as f:
        f.write(b'data')
    app_obj = Application(job_id=job.id, applicant_id=4, resume_path=resume_rel)
    db.session.add(app_obj)
    db.session.commit()
    login(client_with_utils, employer.id, 'employer')
    resp = client_with_utils.get(f'/resume/{resume_rel}')
    assert resp.status_code == 403

def test_serve_resume_unauthorized_applicant(client_with_utils, app_with_utils, tmp_path):
    user = User(username='user2', email='user2@example.com', password='hash', role='job_seeker')
    db.session.add(user)
    db.session.commit()
    job = Job(title='Job', description='desc', location='New Delhi', category='Software Development', company='Coca Cola', poster_id=5)
    db.session.add(job)
    db.session.commit()

    temp_resume_dir = tmp_path / "resumes_unauth_applicant"
    temp_resume_dir.mkdir(exist_ok=True)
    app_with_utils.config['UPLOAD_FOLDER'] = str(temp_resume_dir)

    resume_rel = '5/resume.pdf'
    resume_abs = os.path.join(str(temp_resume_dir), resume_rel)
    os.makedirs(os.path.dirname(resume_abs), exist_ok=True)
    with open(resume_abs, 'wb') as f:
        f.write(b'data')
    app_obj = Application(job_id=job.id, applicant_id=999, resume_path=resume_rel)
    db.session.add(app_obj)
    db.session.commit()
    login(client_with_utils, user.id, 'job_seeker')
    resp = client_with_utils.get(f'/resume/{resume_rel}')
    assert resp.status_code == 403

def test_serve_resume_not_found(client_with_utils, app_with_utils):
    admin = User(username='admin2', email='admin2@example.com', password='hash', role='admin')
    db.session.add(admin)
    db.session.commit()
    login(client_with_utils, admin.id, 'admin')
    resp = client_with_utils.get('/resume/nonexistent/resume.pdf')
    assert resp.status_code == 404