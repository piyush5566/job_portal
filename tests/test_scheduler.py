import sys
import os
import pytest
from unittest.mock import patch, MagicMock, ANY
import tempfile

# Ensure the app directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the task function directly
from tasks import upload_resumes_to_gcs_task
from app import create_app
from config import config

# --- Fixture for App Context (needed if task uses current_app) ---
# Although our refactored task doesn't strictly need it,
# it's good practice if tasks *might* use app context later.
@pytest.fixture
def app_context():
    """Provides a Flask app instance configured for testing."""
    app_instance = create_app(config_class=config['dev_testing']) # Use test config
    app_instance.config.update(
        TESTING=True,
        SERVER_NAME='localhost',
        UPLOAD_FOLDER='test_upload_dir_celery', # Use a specific test upload dir
        GCS_BUCKET_NAME='test-bucket-celery', # Test bucket name
        ENABLE_GCS_UPLOAD=True # Ensure GCS is enabled for testing the task
    )
    with app_instance.app_context():
        yield app_instance # Yield app inside context

# --- Mocks for External Services ---
@pytest.fixture
def mock_gcs():
    """Provides mocks for GCS interactions."""
    with patch('google.cloud.storage.Client') as MockClient:
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        MockClient.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.exists.return_value = True
        mock_blob.reload = MagicMock()
        yield MockClient, mock_bucket, mock_blob

@pytest.fixture
def mock_os_ops():
    """Provides mocks for os file operations."""
    with patch('os.remove') as mock_remove, \
         patch('os.rmdir') as mock_rmdir, \
         patch('os.path.isfile', return_value=True) as mock_isfile, \
         patch('os.path.exists') as mock_exists, \
         patch('os.listdir', return_value=[]) as mock_listdir, \
         patch('glob.glob') as mock_glob:
         # Make os.path.exists return True by default for the upload folder check
         # Specific tests can override this behavior if needed
         mock_exists.return_value = True
         yield mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob

@pytest.fixture
def mock_logger():
    """Mocks the logger used in tasks."""
    # Assuming logger is imported as 'logger' in tasks.py
    with patch('tasks.logger', MagicMock()) as logger_mock:
        yield logger_mock

# --- Tests for the upload_resumes_to_gcs_task logic ---
# Note: We call the task function directly. Celery's eager mode handles this in tests.

def test_upload_task_uploads_and_deletes(
    app_context, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test successful upload and local file deletion by the Celery task."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob = mock_os_ops

    # Use the app_context fixture to get config values
    upload_dir_name = app_context.config['UPLOAD_FOLDER']
    gcs_bucket_name = app_context.config['GCS_BUCKET_NAME']

    # Setup: Create dummy upload structure and file in tmp_path
    upload_dir = tmp_path / upload_dir_name
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')

    # Configure mocks
    mock_glob.return_value = [str(file_path)]
    mock_listdir.side_effect = [[], []] # Empty after file removal

    # Execute the task function directly
    # Pass config values as arguments
    result = upload_resumes_to_gcs_task(str(upload_dir), gcs_bucket_name)

    # Assertions
    mock_exists.assert_called_with(str(upload_dir)) # Check folder existence check
    mock_glob.assert_called_once_with(os.path.join(str(upload_dir), '**', '*'), recursive=True)
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_called_once()
    mock_blob.exists.assert_called_once()
    mock_remove.assert_called_once_with(str(file_path))
    mock_rmdir.assert_any_call(str(user_dir))
    mock_logger.info.assert_any_call(f"Celery Task 'tasks.upload_resumes_to_gcs_task': Deleted local file {str(file_path)}")
    assert "Uploaded: 1" in result
    assert "Deleted: 1" in result

def test_upload_task_gcs_error_keeps_file(
    app_context, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test that local file is kept if GCS upload fails."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob = mock_os_ops

    upload_dir_name = app_context.config['UPLOAD_FOLDER']
    gcs_bucket_name = app_context.config['GCS_BUCKET_NAME']
    upload_dir = tmp_path / upload_dir_name
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')

    # Configure mocks for failure
    mock_glob.return_value = [str(file_path)]
    mock_blob.upload_from_filename.side_effect = Exception("GCS Upload Failed")

    # Execute
    result = upload_resumes_to_gcs_task(str(upload_dir), gcs_bucket_name)

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_not_called()
    mock_blob.exists.assert_not_called()
    mock_remove.assert_not_called() # File should NOT be removed
    mock_rmdir.assert_not_called()
    mock_logger.error.assert_any_call(f"Celery Task 'tasks.upload_resumes_to_gcs_task': Error processing file {str(file_path)}: GCS Upload Failed")
    assert "Failed/Kept: 1" in result

def test_upload_task_verify_fail_keeps_file(
    app_context, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test that local file is kept if GCS verification (blob.exists) fails."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob = mock_os_ops

    upload_dir_name = app_context.config['UPLOAD_FOLDER']
    gcs_bucket_name = app_context.config['GCS_BUCKET_NAME']
    upload_dir = tmp_path / upload_dir_name
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')

    # Configure mocks for verification failure
    mock_glob.return_value = [str(file_path)]
    mock_blob.exists.return_value = False # Simulate verification failure

    # Execute
    result = upload_resumes_to_gcs_task(str(upload_dir), gcs_bucket_name)

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_called_once()
    mock_blob.exists.assert_called_once()
    mock_remove.assert_not_called() # File should NOT be removed
    mock_rmdir.assert_not_called()
    mock_logger.warning.assert_any_call(f"Celery Task 'tasks.upload_resumes_to_gcs_task': Upload verification failed for {str(file_path)} (gs://{gcs_bucket_name}/resumes/user123/resume.pdf), keeping local copy")
    assert "Failed/Kept: 1" in result

def test_upload_task_no_files(
    app_context, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test behavior when no files are found in the upload folder."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob = mock_os_ops

    upload_dir_name = app_context.config['UPLOAD_FOLDER']
    gcs_bucket_name = app_context.config['GCS_BUCKET_NAME']
    upload_dir = tmp_path / upload_dir_name
    upload_dir.mkdir(parents=True)

    # Configure mocks for no files found
    mock_glob.return_value = [] # Glob finds nothing

    # Execute
    result = upload_resumes_to_gcs_task(str(upload_dir), gcs_bucket_name)

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_not_called()
    mock_blob.upload_from_filename.assert_not_called()
    mock_remove.assert_not_called()
    mock_rmdir.assert_not_called()
    mock_logger.info.assert_any_call(f"Celery Task 'tasks.upload_resumes_to_gcs_task': No new files found in resumes folder.")
    assert "No files found" in result

def test_upload_task_upload_folder_missing(
    app_context, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test behavior when the configured UPLOAD_FOLDER doesn't exist."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_exists, mock_listdir, mock_glob = mock_os_ops

    # Setup: Point config to a non-existent directory
    non_existent_dir_name = "non_existent_uploads_celery"
    non_existent_dir = tmp_path / non_existent_dir_name
    gcs_bucket_name = app_context.config['GCS_BUCKET_NAME']

    # Configure os.path.exists mock to return False for this specific path
    mock_exists.side_effect = lambda p: False if p == str(non_existent_dir) else True

    # Execute
    result = upload_resumes_to_gcs_task(str(non_existent_dir), gcs_bucket_name)

    # Assertions
    mock_exists.assert_called_with(str(non_existent_dir))
    mock_logger.warning.assert_any_call(f"Celery Task 'tasks.upload_resumes_to_gcs_task': Local resume folder '{str(non_existent_dir)}' does not exist. Skipping.")
    mock_glob.assert_not_called() # Should not even call glob
    mock_bucket.blob.assert_not_called()
    mock_blob.upload_from_filename.assert_not_called()
    assert "Skipped: Folder" in result
