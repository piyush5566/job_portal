"""Google Cloud Storage Scheduler Service.
# ... (rest of the docstring) ...
"""

from apscheduler.schedulers.background import BackgroundScheduler
from google.cloud import storage
import os
import glob
from utils import logger
import atexit
import tempfile
import fcntl
import time # Import time

# Define the lock file path using a fixed name in the system's temp directory
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'scheduler.lock')

scheduler = None
lock_fd = None # Keep track of the lock file descriptor

# --- Function moved to module level ---
def upload_resumes_to_gcs(app, gcs_bucket_name):
    """Upload new resume files to Google Cloud Storage and clean up local storage.

    Args:
        app: Flask application instance (needed for context and config)
        gcs_bucket_name (str): Target GCS bucket name

    Side Effects:
        - Uploads files to GCS
        - Deletes local files after successful upload
        - Logs upload attempts and results
        - Maintains synchronization state
    """
    with app.app_context():
        logger.info("Scheduler: Checking resumes folder...")
        local_resume_folder = app.config.get('UPLOAD_FOLDER', 'static/resumes') # Use .get with default
        if not os.path.exists(local_resume_folder):
             logger.warning(f"Scheduler: Local resume folder '{local_resume_folder}' does not exist. Skipping.")
             return

        # Use glob to find all files recursively within the UPLOAD_FOLDER
        all_files = glob.glob(os.path.join(
            local_resume_folder, '**', '*'), recursive=True)
        # Filter out directories, keep only files
        local_files = [f for f in all_files if os.path.isfile(f)]

        if local_files:
            logger.info(
                f"Scheduler: Found {len(local_files)} files. Uploading to GCS bucket '{gcs_bucket_name}'...")
            try:
                # Initialize GCS client
                storage_client = storage.Client()
                bucket = storage_client.bucket(gcs_bucket_name)

                # Upload each file and track successful uploads
                for local_file in local_files:
                    try:
                        # Get relative path for GCS object name
                        relative_path = os.path.relpath(
                            local_file, start=local_resume_folder)
                        # Ensure consistent path separators for GCS
                        gcs_path = f"resumes/{relative_path.replace(os.sep, '/')}"
                        blob = bucket.blob(gcs_path)

                        # Upload file
                        logger.info(f"Scheduler: Attempting to upload {local_file} to gs://{gcs_bucket_name}/{gcs_path}")
                        blob.upload_from_filename(local_file)
                        logger.info(
                            f"Scheduler: Uploaded {local_file} to GCS")

                        # Verify upload was successful by checking if blob exists
                        # Reload metadata to ensure exists() is accurate after upload
                        blob.reload()
                        if blob.exists():
                            # Delete the local file
                            os.remove(local_file)
                            logger.info(
                                f"Scheduler: Deleted local file {local_file}")

                            # Remove empty parent directories if any
                            parent_dir = os.path.dirname(local_file)
                            # Check parent_dir is not empty and is within local_resume_folder
                            while parent_dir and parent_dir != local_resume_folder and parent_dir.startswith(local_resume_folder):
                                try:
                                    if not os.listdir(parent_dir): # Check if directory is empty
                                        os.rmdir(parent_dir)
                                        logger.info(
                                            f"Scheduler: Removed empty directory {parent_dir}")
                                        parent_dir = os.path.dirname(parent_dir) # Move up
                                    else:
                                        break # Stop if directory is not empty
                                except OSError as e:
                                    logger.warning(f"Scheduler: Could not remove directory {parent_dir}: {e}")
                                    break # Stop if error occurs
                        else:
                            logger.warning(
                                f"Scheduler: Upload verification failed for {local_file} (gs://{gcs_bucket_name}/{gcs_path}), keeping local copy")

                    except Exception as e:
                        logger.error(
                            f"Scheduler: Error processing file {local_file}: {str(e)}")
                        # Optionally add traceback: import traceback; logger.error(traceback.format_exc())
                        continue # Continue with the next file

                logger.info(
                    "Scheduler: Upload to GCS and local cleanup complete.")
            except Exception as e:
                logger.error(
                    f"Scheduler: ERROR during GCS upload task setup or client initialization - {str(e)}")
                # Optionally add traceback: import traceback; logger.error(traceback.format_exc())
        else:
            logger.info("Scheduler: No new files found in resumes folder.")


def init_scheduler(app):
    """Initialize and start the GCS upload scheduler with process locking.

    Args:
        app: Flask application instance

    Returns:
        None: Initializes scheduler as a side effect

    Side Effects:
        - Creates lock file
        - Starts background scheduler
        - Configures graceful shutdown
        - Logs initialization status

    Process Safety:
        - Uses file locking to prevent duplicate initialization
        - Only one process can acquire the lock
    """
    global scheduler, lock_fd
    gcs_bucket_name = app.config.get('GCS_BUCKET_NAME')

    # Check if already initialized in this process
    if scheduler is not None:
        logger.info("Scheduler already initialized in this process.")
        return

    # Open or create the lock file
    try:
        # Use 'a' mode which creates if not exists, and allows reading/writing
        # Use os.open for lower-level control needed by fcntl
        lock_fd_temp = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
    except OSError as e:
        logger.error(f"Scheduler: Failed to open or create lock file {LOCK_FILE}: {e}")
        return # Cannot proceed without lock file

    try:
        # Attempt to acquire an exclusive, non-blocking lock
        fcntl.flock(lock_fd_temp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Lock acquired, store the file descriptor
        lock_fd = lock_fd_temp
        logger.info(f"Scheduler lock acquired by process {os.getpid()}.")

    except IOError:
        # If lock acquisition fails, another process has the lock
        logger.info(f"Scheduler lock file {LOCK_FILE} is held by another process. Scheduler not starting in process {os.getpid()}.")
        os.close(lock_fd_temp) # Close the descriptor, we didn't get the lock
        return # Do not initialize scheduler in this process

    # --- Lock acquired, proceed with initialization ---

    if not gcs_bucket_name or gcs_bucket_name == 'your-gcs-bucket-name':
        logger.warning(
            "Scheduler WARNING: GCS upload feature intended, but GCS_BUCKET_NAME is not set or is default. Scheduler not started.")
        # Release lock and close file descriptor if scheduler not started
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            lock_fd = None
        return

    logger.info(
        f"Scheduler: Initializing GCS Upload Feature for bucket '{gcs_bucket_name}'")
    scheduler = BackgroundScheduler(daemon=True) # Use daemon=True for background thread

    # Pass app and bucket name to the job function
    scheduler.add_job(
        func=upload_resumes_to_gcs,
        args=[app, gcs_bucket_name], # Pass app instance and bucket name
        trigger="interval",
        minutes=app.config.get('SCHEDULER_INTERVAL_MINUTES', 15), # Make interval configurable
        id='gcs_upload_job', # Give the job an ID
        replace_existing=True # Replace if job with same ID exists
    )

    try:
        scheduler.start()
        logger.info(f"Scheduler started successfully in process {os.getpid()}.")
        # --- FIX: Only register atexit handler if NOT in testing mode ---
        if not app.config.get('TESTING'):
            logger.info("Registering scheduler shutdown hook with atexit.")
            atexit.register(shutdown_scheduler)
        else:
            logger.info("Skipping atexit registration for scheduler shutdown in TESTING mode.")
        # --- END FIX ---
        
    except Exception as e:
        logger.error(f"Scheduler: Failed to start - {str(e)}")
        # Clean up lock if start fails
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                lock_fd = None
            except Exception as cleanup_e:
                logger.error(f"Scheduler: Error during cleanup after failed start: {cleanup_e}")
        scheduler = None # Ensure scheduler is None if start failed


def shutdown_scheduler():
    """Shutdown the scheduler and release the lock file."""
    global scheduler, lock_fd
    logger.info(f"Scheduler: Shutting down in process {os.getpid()}...")
    if scheduler is not None and scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Scheduler shut down gracefully.")
        except Exception as e:
            logger.error(f"Scheduler: Error during shutdown - {str(e)}")
    else:
        logger.info("Scheduler was not running or not initialized in this process.")

    # Release the lock and close the file descriptor if this process held it
    if lock_fd is not None:
        logger.info(f"Scheduler: Releasing lock file {LOCK_FILE} from process {os.getpid()}.")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            lock_fd = None # Reset fd
            # Optionally remove the lock file on clean shutdown
            # try:
            #     os.remove(LOCK_FILE)
            #     logger.info(f"Scheduler: Removed lock file {LOCK_FILE}.")
            # except OSError as e:
            #     logger.warning(f"Scheduler: Could not remove lock file {LOCK_FILE}: {e}")
        except Exception as e:
            logger.error(f"Scheduler: Error releasing lock file - {str(e)}")

# Register the shutdown function specifically for exit
# atexit.register(shutdown_scheduler) # Moved registration to init_scheduler after successful start
