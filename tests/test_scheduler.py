import sys
import os
import pytest
from unittest.mock import patch, MagicMock, ANY # Import ANY
import fcntl
import tempfile # Import tempfile for LOCK_FILE definition consistency

# Ensure the app directory is in the path
# Consider using proper packaging or pytest config (pythonpath) instead
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import appsched # Import the module itself
from app import create_app # Import the app factory
from config import config # Import config

# --- Consistent App Fixture using create_app ---
@pytest.fixture
def app():
    """Provides a Flask app instance configured for testing."""
    # Use a specific testing configuration
    app_instance = create_app(config['dev_testing']) # Or another suitable test config
    app_instance.config.update(
        TESTING=True,
        SERVER_NAME='localhost', # Often useful for tests involving url_for
        UPLOAD_FOLDER='test_upload_dir', # Use a specific test upload dir
        GCS_BUCKET_NAME='test-bucket', # Test bucket name
        SCHEDULER_INTERVAL_MINUTES=1 # Use a short interval for testing if needed
    )
    # Reset scheduler state before each test
    appsched.scheduler = None
    appsched.lock_fd = None # Ensure lock fd is reset

    # Define lock file path consistently
    lock_file_path = os.path.join(tempfile.gettempdir(), 'scheduler.lock')

    # Clean up lock file if it exists from previous runs
    if os.path.exists(lock_file_path):
        try:
            # Attempt to remove lock file before test
            os.remove(lock_file_path)
        except OSError:
            pass # Ignore if removal fails (e.g., permissions, held by other process)

    yield app_instance

    # --- Cleanup after test ---
    # Ensure scheduler is shut down if it was started
    if appsched.scheduler and appsched.scheduler.running:
        appsched.shutdown_scheduler() # Use the proper shutdown function

    # Clean up lock file after test
    if os.path.exists(lock_file_path):
        # Close fd if held by this test's instance before removing
        if appsched.lock_fd is not None:
             try:
                 # Check if fd is valid before using fcntl (optional safety)
                 # if os.isatty(appsched.lock_fd): # This check might not be perfect for non-tty fds
                 fcntl.flock(appsched.lock_fd, fcntl.LOCK_UN)
                 os.close(appsched.lock_fd)
                 appsched.lock_fd = None
             except Exception:
                 # If closing/unlocking fails, reset fd anyway
                 appsched.lock_fd = None
                 pass # Ignore errors during cleanup
        try:
            os.remove(lock_file_path)
        except OSError:
            pass # Ignore if removal fails

# --- Mocks for File Locking ---
@pytest.fixture(autouse=True)
def mock_locking():
    """Mocks fcntl.flock and os.open to bypass file locking for tests."""
    original_os_open = os.open
    lock_file_path = os.path.join(tempfile.gettempdir(), 'scheduler.lock') # Define consistently

    # --- FIX: Accept 'mode' argument and pass it through ---
    # Accept the optional 'mode' argument with a default matching os.open's default
    def mock_os_open(path, flags, mode=0o777):
        if path == lock_file_path:
            # Still return the dummy fd for the lock file
            # print(f"DEBUG: Mocking os.open for LOCK_FILE: {path}") # Optional debug print
            return 99 # Use a distinct integer unlikely to be a real fd
        # Call the original os.open, passing all arguments through
        # print(f"DEBUG: Calling original os.open for: {path}, flags={flags}, mode={mode}") # Optional debug print
        return original_os_open(path, flags, mode)
    # --- END FIX ---

    # Patch os.open with the updated mock
    with patch('os.open', side_effect=mock_os_open), \
         patch('fcntl.flock') as mock_flock, \
         patch('os.close') as mock_os_close: # Also mock os.close for the dummy fd
        yield mock_flock, mock_os_close # Provide mocks if needed by tests


# ... (imports and fixtures) ...

# --- Test Cases ---

def test_init_scheduler_adds_job_and_starts(app, mock_locking):
    """Verify init_scheduler adds the job and starts the scheduler."""
    mock_flock, _ = mock_locking # Get the mock flock from the fixture

    # --- FIX: Reset mock after app creation, before explicit call ---
    # The app fixture calling create_app might have already called init_scheduler implicitly.
    # Reset the mock count so we only assert against the *explicit* call below.
    mock_flock.reset_mock()
    # --- END FIX ---

    # Patch BackgroundScheduler to check interactions
    with patch('appsched.BackgroundScheduler') as MockScheduler:
        mock_scheduler_instance = MockScheduler.return_value
        mock_scheduler_instance.running = False # Simulate scheduler not running initially

        # Reset scheduler state before calling init (still good practice)
        appsched.scheduler = None
        appsched.lock_fd = None

        # Call the function under test (this is the call we want to check)
        appsched.init_scheduler(app)

        # Assertions
        # Now this assertion checks only the call made by the line above
        mock_flock.assert_called_once_with(99, fcntl.LOCK_EX | fcntl.LOCK_NB) # Check lock attempt

        MockScheduler.assert_called_once_with(daemon=True) # Check scheduler instantiation
        mock_scheduler_instance.add_job.assert_called_once_with(
            func=appsched.upload_resumes_to_gcs, # Check correct function
            args=[app, 'test-bucket'],          # Check correct args
            trigger="interval",
            minutes=app.config['SCHEDULER_INTERVAL_MINUTES'],
            id='gcs_upload_job',
            replace_existing=True
        )
        mock_scheduler_instance.start.assert_called_once() # Check scheduler started
        assert appsched.scheduler == mock_scheduler_instance # Check module variable assignment

# Test for the case where GCS bucket is not configured
def test_init_scheduler_no_bucket(app, mock_locking):
    """Verify scheduler doesn't start if GCS_BUCKET_NAME is missing/default."""
    mock_flock, mock_os_close = mock_locking
    app.config['GCS_BUCKET_NAME'] = None # Simulate missing bucket name

    # --- FIX: Reset mock after app creation, before explicit call ---
    mock_flock.reset_mock()
    mock_os_close.reset_mock() # Also reset close mock if needed for assertions below
    # --- END FIX ---

    with patch('appsched.BackgroundScheduler') as MockScheduler:
        appsched.scheduler = None
        appsched.lock_fd = None

        appsched.init_scheduler(app) # Explicit call

        # Assertions against the explicit call
        mock_flock.assert_any_call(99, fcntl.LOCK_EX | fcntl.LOCK_NB) # Lock attempt
        MockScheduler.assert_not_called() # Scheduler should not be created
        assert appsched.scheduler is None # Module variable should remain None
        # Check that the lock was released (flock called with LOCK_UN) and fd closed
        mock_flock.assert_any_call(99, fcntl.LOCK_UN) # Check release call
        # Check close was called *at least once* for the dummy fd (might be called by implicit init too)
        mock_os_close.assert_any_call(99)
        # If you need to be more specific about calls *after* reset:
        # assert mock_os_close.call_args_list == [call(99)] # Example if only one call expected after reset


# Test for the case where lock is already held (simulated by raising IOError)
def test_init_scheduler_lock_held(app, mock_locking):
    """Verify scheduler doesn't start if lock is held by another process."""
    mock_flock, mock_os_close = mock_locking

    # --- FIX: Reset mock after app creation, before explicit call ---
    mock_flock.reset_mock()
    mock_os_close.reset_mock()
    # --- END FIX ---

    # Configure the mock flock to raise IOError *only for the explicit call*
    # The implicit call during app creation would have succeeded (or doesn't matter now)
    mock_flock.side_effect = IOError

    with patch('appsched.BackgroundScheduler') as MockScheduler:
        appsched.scheduler = None
        appsched.lock_fd = None

        appsched.init_scheduler(app) # Explicit call (this will now raise IOError via the mock)

        # Assertions against the explicit call
        mock_flock.assert_called_once_with(99, fcntl.LOCK_EX | fcntl.LOCK_NB) # Lock attempt failed
        MockScheduler.assert_not_called() # Scheduler should not be created
        assert appsched.scheduler is None # Module variable should remain None
        # Check os.close was called for the temporary fd when lock failed during the explicit call
        mock_os_close.assert_called_once_with(99)


# ... (rest of the tests for upload_resumes_to_gcs remain the same) ...


# --- Tests for the upload_resumes_to_gcs function logic ---

@pytest.fixture
def mock_gcs():
    """Provides mocks for GCS interactions."""
    with patch('google.cloud.storage.Client') as MockClient:
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        # Configure mock behaviors
        MockClient.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        # Simulate successful upload and existence check
        mock_blob.exists.return_value = True
        # Make reload do nothing for the mock
        mock_blob.reload = MagicMock()

        yield MockClient, mock_bucket, mock_blob

@pytest.fixture
def mock_os_ops():
    """Provides mocks for os file operations (excluding os.open/os.close)."""
    # Note: os.open and os.close are handled by mock_locking
    with patch('os.remove') as mock_remove, \
         patch('os.rmdir') as mock_rmdir, \
         patch('os.path.isfile', return_value=True) as mock_isfile, \
         patch('os.listdir', return_value=[]) as mock_listdir, \
         patch('glob.glob') as mock_glob: # Also mock glob
        yield mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob

@pytest.fixture
def mock_logger():
    """Mocks the logger used in appsched."""
    with patch('appsched.logger', MagicMock()) as logger_mock:
        yield logger_mock


def test_upload_resumes_to_gcs_uploads_and_deletes(
    app, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test successful upload and local file deletion."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob = mock_os_ops

    # Setup: Create dummy upload structure and file
    upload_dir = tmp_path / app.config['UPLOAD_FOLDER']
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')
    app.config['UPLOAD_FOLDER'] = str(upload_dir) # Point app config to temp dir

    # Configure glob mock to find the file
    mock_glob.return_value = [str(file_path)]
    # Configure listdir to return empty after file removal
    mock_listdir.side_effect = [[], []] # First call for user_dir, second for upload_dir (if checked)

    # Execute the function
    with app.app_context():
        appsched.upload_resumes_to_gcs(app, app.config['GCS_BUCKET_NAME'])

    # Assertions
    mock_glob.assert_called_once_with(os.path.join(str(upload_dir), '**', '*'), recursive=True)
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_called_once() # Verify reload was called before exists()
    mock_blob.exists.assert_called_once()
    mock_remove.assert_called_once_with(str(file_path))
    # Check if rmdir was called for the now-empty user directory
    mock_rmdir.assert_any_call(str(user_dir))
    mock_logger.info.assert_any_call(f"Scheduler: Deleted local file {str(file_path)}")
    mock_logger.info.assert_any_call(f"Scheduler: Removed empty directory {str(user_dir)}")


def test_upload_resumes_to_gcs_gcs_error_keeps_file(
    app, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test that local file is kept if GCS upload fails."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob = mock_os_ops

    # Setup: Create dummy file
    upload_dir = tmp_path / app.config['UPLOAD_FOLDER']
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')
    app.config['UPLOAD_FOLDER'] = str(upload_dir)

    # Configure mocks for failure
    mock_glob.return_value = [str(file_path)]
    mock_blob.upload_from_filename.side_effect = Exception("GCS Upload Failed")

    # Execute
    with app.app_context():
        appsched.upload_resumes_to_gcs(app, app.config['GCS_BUCKET_NAME'])

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_not_called() # Shouldn't reload if upload failed
    mock_blob.exists.assert_not_called() # Shouldn't check existence if upload failed
    mock_remove.assert_not_called() # File should NOT be removed
    mock_rmdir.assert_not_called() # Dir should NOT be removed
    mock_logger.error.assert_any_call(f"Scheduler: Error processing file {str(file_path)}: GCS Upload Failed")


def test_upload_resumes_to_gcs_verify_fail_keeps_file(
    app, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test that local file is kept if GCS verification (blob.exists) fails."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob = mock_os_ops

    # Setup: Create dummy file
    upload_dir = tmp_path / app.config['UPLOAD_FOLDER']
    user_dir = upload_dir / 'user123'
    user_dir.mkdir(parents=True)
    file_path = user_dir / 'resume.pdf'
    file_path.write_text('dummy resume data')
    app.config['UPLOAD_FOLDER'] = str(upload_dir)

    # Configure mocks for verification failure
    mock_glob.return_value = [str(file_path)]
    mock_blob.exists.return_value = False # Simulate verification failure

    # Execute
    with app.app_context():
        appsched.upload_resumes_to_gcs(app, app.config['GCS_BUCKET_NAME'])

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_called_once_with('resumes/user123/resume.pdf')
    mock_blob.upload_from_filename.assert_called_once_with(str(file_path))
    mock_blob.reload.assert_called_once() # Reload happens before exists
    mock_blob.exists.assert_called_once() # Exists check fails
    mock_remove.assert_not_called() # File should NOT be removed
    mock_rmdir.assert_not_called() # Dir should NOT be removed
    mock_logger.warning.assert_any_call(f"Scheduler: Upload verification failed for {str(file_path)} (gs://test-bucket/resumes/user123/resume.pdf), keeping local copy")


def test_upload_resumes_to_gcs_no_files(
    app, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test behavior when no files are found in the upload folder."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob = mock_os_ops

    # Setup: Ensure upload dir exists but is empty
    upload_dir = tmp_path / app.config['UPLOAD_FOLDER']
    upload_dir.mkdir(parents=True)
    app.config['UPLOAD_FOLDER'] = str(upload_dir)

    # Configure mocks for no files found
    mock_glob.return_value = [] # Glob finds nothing

    # Execute
    with app.app_context():
        appsched.upload_resumes_to_gcs(app, app.config['GCS_BUCKET_NAME'])

    # Assertions
    mock_glob.assert_called_once()
    mock_bucket.blob.assert_not_called() # No blob operations if no files
    mock_blob.upload_from_filename.assert_not_called()
    mock_remove.assert_not_called()
    mock_rmdir.assert_not_called()
    mock_logger.info.assert_any_call("Scheduler: No new files found in resumes folder.")
    mock_logger.error.assert_not_called() # No errors expected


def test_upload_resumes_to_gcs_upload_folder_missing(
    app, tmp_path, mock_gcs, mock_os_ops, mock_logger
):
    """Test behavior when the configured UPLOAD_FOLDER doesn't exist."""
    mock_client, mock_bucket, mock_blob = mock_gcs
    mock_remove, mock_rmdir, mock_isfile, mock_listdir, mock_glob = mock_os_ops

    # Setup: Point config to a non-existent directory
    non_existent_dir = tmp_path / "non_existent_uploads"
    app.config['UPLOAD_FOLDER'] = str(non_existent_dir)

    # Execute
    with app.app_context():
        appsched.upload_resumes_to_gcs(app, app.config['GCS_BUCKET_NAME'])

    # Assertions
    mock_logger.warning.assert_any_call(f"Scheduler: Local resume folder '{str(non_existent_dir)}' does not exist. Skipping.")
    mock_glob.assert_not_called() # Should not even call glob
    mock_bucket.blob.assert_not_called()
    mock_blob.upload_from_filename.assert_not_called()
    mock_remove.assert_not_called()
    mock_rmdir.assert_not_called()

