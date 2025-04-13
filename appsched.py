"""Google Cloud Storage Scheduler Service.

This module handles periodic uploads of resume files to Google Cloud Storage.
It implements:
- Process-level locking to prevent duplicate scheduler initialization
- Periodic job execution
- Secure file uploads to GCS
- Comprehensive logging

Key Features:
- File locking mechanism using system temp directory
- Graceful shutdown handling
- Configurable upload intervals
- Error handling and logging

Configuration:
- Requires GCS_BUCKET_NAME in app config
- Uses UPLOAD_FOLDER from app config
- Lock file stored in system temp directory
"""

from apscheduler.schedulers.background import BackgroundScheduler
from google.cloud import storage
import os
import glob
from utils import logger
import atexit
import tempfile
import fcntl

# Define the lock file path using a fixed name in the system's temp directory
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'scheduler.lock')

scheduler = None


def init_scheduler(app, gcs_bucket_name):
    """Initialize and start the GCS upload scheduler with process locking.

    Args:
        app: Flask application instance
        gcs_bucket_name: Target GCS bucket name

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
    global scheduler
    # Open or create the lock file
    lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)

    try:
        # Attempt to acquire an exclusive, non-blocking lock
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # If lock acquisition fails, another process has the lock
        print("Scheduler already initialized by another process")
        os.close(lock_fd)
        return

    if scheduler is None:
        if not gcs_bucket_name or gcs_bucket_name == 'your-gcs-bucket-name':
            logger.warning(
                "Scheduler WARNING: GCS upload is enabled, but GCS_BUCKET_NAME is not set or is default.")
            return None
        logger.info(
            f"Scheduler: GCS Upload Feature ENABLED for bucket '{gcs_bucket_name}'")
        scheduler = BackgroundScheduler()

        def upload_resumes_to_gcs():
            """Upload new resume files to Google Cloud Storage and clean up local storage.

            Args:
                gcs_bucket_name (str): Target GCS bucket name
                local_resume_folder (str): Path to local resume files

            Side Effects:
                - Uploads files to GCS
                - Deletes local files after successful upload
                - Logs upload attempts and results
                - Maintains synchronization state
            """
            with app.app_context():
                logger.info("Scheduler: Checking resumes folder...")
                local_resume_folder = app.config['UPLOAD_FOLDER']
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
                                blob = bucket.blob(f"resumes/{relative_path}")

                                # Upload file
                                blob.upload_from_filename(local_file)
                                logger.info(
                                    f"Scheduler: Uploaded {local_file} to GCS")

                                # Verify upload was successful by checking if blob exists
                                if blob.exists():
                                    # Delete the local file
                                    os.remove(local_file)
                                    logger.info(
                                        f"Scheduler: Deleted local file {local_file}")

                                    # Remove empty parent directories if any
                                    parent_dir = os.path.dirname(local_file)
                                    while parent_dir and parent_dir.startswith(local_resume_folder):
                                        try:
                                            os.rmdir(parent_dir)
                                            logger.info(
                                                f"Scheduler: Removed empty directory {parent_dir}")
                                        except OSError:
                                            # Directory not empty or already removed
                                            break
                                        parent_dir = os.path.dirname(
                                            parent_dir)
                                else:
                                    logger.warning(
                                        f"Scheduler: Upload verification failed for {local_file}, keeping local copy")

                            except Exception as e:
                                logger.error(
                                    f"Scheduler: Error processing file {local_file}: {str(e)}")
                                continue

                        logger.info(
                            "Scheduler: Upload to GCS and local cleanup complete.")
                    except Exception as e:
                        logger.error(
                            f"Scheduler: ERROR during GCS upload - {str(e)}")
                else:
                    logger.info("Scheduler: No files found in resumes folder.")

        scheduler.add_job(func=upload_resumes_to_gcs,
                          trigger="interval", minutes=15)
        scheduler.start()
        # Shutdown scheduler gracefully when the app exits
        atexit.register(lambda: scheduler.shutdown())
        atexit.register(lambda: os.close(lock_fd))
