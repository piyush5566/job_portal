# /home/gagan/pF/job_portal/tests/test_celery.py

import pytest
import os
import sys
from unittest.mock import patch

# Ensure app directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import config
# Import the function that creates the Celery app instance
from celery_worker import make_celery

# --- Fixtures for different app configurations ---

@pytest.fixture
def app_gcs_enabled():
    """Flask app with GCS upload enabled and configured."""
    # Use a testing config that enables GCS
    app = create_app(config_class=config['dev_testing'])
    app.config.update(
        ENABLE_GCS_UPLOAD=True,
        GCS_BUCKET_NAME='my-test-bucket',
        SCHEDULER_INTERVAL_MINUTES=10 # Use a specific interval for testing
    )
    # Ensure Celery eager mode is set for consistency, though not strictly needed for this test
    app.config['task_always_eager'] = True
    return app

@pytest.fixture
def app_gcs_disabled():
    """Flask app with GCS upload disabled."""
    app = create_app(config_class=config['dev_testing'])
    app.config.update(
        ENABLE_GCS_UPLOAD=False,
        GCS_BUCKET_NAME='my-test-bucket', # Bucket name doesn't matter if disabled
        SCHEDULER_INTERVAL_MINUTES=10
    )
    app.config['task_always_eager'] = True
    return app

@pytest.fixture
def app_gcs_no_bucket():
    """Flask app with GCS upload enabled but no bucket name."""
    app = create_app(config_class=config['dev_testing'])
    app.config.update(
        ENABLE_GCS_UPLOAD=True,
        GCS_BUCKET_NAME=None, # Simulate missing bucket name
        SCHEDULER_INTERVAL_MINUTES=10
    )
    app.config['task_always_eager'] = True
    return app


# --- Test Cases ---

def test_celery_beat_schedule_when_gcs_enabled(app_gcs_enabled):
    """
    Verify the beat schedule includes the GCS task when enabled and configured.
    """
    # Create the Celery instance using the configured Flask app
    celery_instance = make_celery(app_gcs_enabled)

    # Check the beat schedule configuration
    schedule = celery_instance.conf.beat_schedule
    assert 'upload-resumes-every-interval' in schedule

    task_config = schedule['upload-resumes-every-interval']
    assert task_config['task'] == 'tasks.upload_resumes_to_gcs_task'
    # Check interval (make_celery sets it in seconds)
    assert task_config['schedule'] == 10 * 60.0
    # Check arguments passed to the task
    expected_upload_folder = app_gcs_enabled.config.get('UPLOAD_FOLDER')
    expected_bucket_name = 'my-test-bucket'
    assert task_config['args'] == (expected_upload_folder, expected_bucket_name)

def test_celery_beat_schedule_when_gcs_disabled(app_gcs_disabled):
    """
    Verify the beat schedule does NOT include the GCS task when disabled.
    """
    celery_instance = make_celery(app_gcs_disabled)
    schedule = celery_instance.conf.beat_schedule
    # The task should NOT be in the schedule
    assert 'upload-resumes-every-interval' not in schedule

def test_celery_beat_schedule_when_gcs_no_bucket(app_gcs_no_bucket):
    """
    Verify the beat schedule does NOT include the GCS task when enabled but
    GCS_BUCKET_NAME is not set.
    """
    celery_instance = make_celery(app_gcs_no_bucket)
    schedule = celery_instance.conf.beat_schedule
    # The task should NOT be in the schedule
    assert 'upload-resumes-every-interval' not in schedule

