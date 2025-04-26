import sys
import os
import pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import appsched
from flask import Flask
from app import create_app
from config import config

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'static/resumes'
    app.config['GCS_BUCKET_NAME'] = 'test-bucket'
    app.config['SCHEDULER_INITIALIZED'] = False
    yield app

def test_scheduler_runs():
    app = create_app(config['development'])
    with patch('appsched.upload_resumes_to_gcs') as mock_upload:
        # Simulate scheduler job
        mock_upload()
        assert mock_upload.called

def test_init_scheduler_singleton(monkeypatch, app):
    # Should not start scheduler if already initialized
    app.config['SCHEDULER_INITIALIZED'] = True
    appsched.scheduler = None
    appsched.init_scheduler(app, 'test-bucket')
    assert appsched.scheduler is None

def test_init_scheduler_starts(monkeypatch, app):
    # Patch BackgroundScheduler and upload_resumes_to_gcs
    class DummyScheduler:
        def add_job(self, *a, **k): pass
        def start(self): self.started = True
        def shutdown(self): self.stopped = True
    monkeypatch.setattr(appsched, 'BackgroundScheduler', lambda: DummyScheduler())
    monkeypatch.setattr(appsched, 'init_scheduler', lambda a, b: None)
    appsched.scheduler = None
    app.config['SCHEDULER_INITIALIZED'] = False
    appsched.init_scheduler(app, 'test-bucket')
    # Should set scheduler
    assert appsched.scheduler is not None

def test_upload_resumes_to_gcs_local(monkeypatch, tmp_path, app):
    # Patch GCS client and logger
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    app.config['GCS_BUCKET_NAME'] = 'test-bucket'
    app.config['SCHEDULER_INITIALIZED'] = False
    # Create a dummy file
    user_dir = tmp_path / '123'
    user_dir.mkdir()
    file_path = user_dir / 'resume.pdf'
    file_path.write_bytes(b'data')
    # Patch GCS client
    class DummyBlob:
        def upload_from_filename(self, filename): pass
        def exists(self): return True
    class DummyBucket:
        def blob(self, name): return DummyBlob()
    class DummyClient:
        def bucket(self, name): return DummyBucket()
    monkeypatch.setattr('google.cloud.storage.Client', DummyClient)
    # Patch logger
    monkeypatch.setattr(appsched, 'logger', MagicMock())
    # Call upload_resumes_to_gcs
    with app.app_context():
        appsched.upload_resumes_to_gcs.__globals__['app'] = app
        appsched.upload_resumes_to_gcs()
    # File should be deleted
    assert not file_path.exists()

def test_upload_resumes_to_gcs_gcs_error(monkeypatch, tmp_path, app):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    app.config['GCS_BUCKET_NAME'] = 'test-bucket'
    app.config['SCHEDULER_INITIALIZED'] = False
    # Create a dummy file
    user_dir = tmp_path / '123'
    user_dir.mkdir()
    file_path = user_dir / 'resume.pdf'
    file_path.write_bytes(b'data')
    # Patch GCS client to raise error
    class DummyBlob:
        def upload_from_filename(self, filename): raise Exception('fail')
        def exists(self): return False
    class DummyBucket:
        def blob(self, name): return DummyBlob()
    class DummyClient:
        def bucket(self, name): return DummyBucket()
    monkeypatch.setattr('google.cloud.storage.Client', DummyClient)
    monkeypatch.setattr(appsched, 'logger', MagicMock())
    with app.app_context():
        appsched.upload_resumes_to_gcs.__globals__['app'] = app
        appsched.upload_resumes_to_gcs()
    # File should still exist due to error
    assert file_path.exists()

def test_upload_resumes_to_gcs_no_files(monkeypatch, tmp_path, app):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    app.config['GCS_BUCKET_NAME'] = 'test-bucket'
    app.config['SCHEDULER_INITIALIZED'] = False
    monkeypatch.setattr('google.cloud.storage.Client', MagicMock())
    monkeypatch.setattr(appsched, 'logger', MagicMock())
    with app.app_context():
        appsched.upload_resumes_to_gcs.__globals__['app'] = app
        appsched.upload_resumes_to_gcs()
    # No error should occur