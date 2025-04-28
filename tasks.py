"""Celery Tasks for Job Portal."""

from celery import shared_task
from google.cloud import storage
import os
import glob
from utils import logger
import time
from flask import Flask # Import Flask
from config import config # Import config
from app import create_app # Import create_app to get context/config

# Note: No scheduler initialization or shutdown logic needed here anymore.

# Use shared_task for tasks defined outside the main Celery app instance file
@shared_task(bind=True) # bind=True gives access to self (the task instance)
def upload_resumes_to_gcs_task(self, upload_folder, gcs_bucket_name):
    """
    Celery task to upload new resume files to Google Cloud Storage
    and clean up local storage.

    Args:
        upload_folder (str): Path to the local folder containing resumes.
        gcs_bucket_name (str): Target GCS bucket name.

    Side Effects:
        - Uploads files to GCS
        - Deletes local files after successful upload
        - Logs upload attempts and results
    """
    # Create a minimal app instance to access context/config if needed,
    # OR rely on config passed directly or via Celery app config.
    # Here, we only need config values which are passed as arguments.
    # No app context needed directly within the core logic below.

    logger.info(f"Celery Task '{self.name}': Checking resumes folder '{upload_folder}'...")

    if not os.path.exists(upload_folder):
         logger.warning(f"Celery Task '{self.name}': Local resume folder '{upload_folder}' does not exist. Skipping.")
         return f"Skipped: Folder {upload_folder} not found."

    # Use glob to find all files recursively within the UPLOAD_FOLDER
    all_files = glob.glob(os.path.join(
        upload_folder, '**', '*'), recursive=True)
    # Filter out directories, keep only files
    local_files = [f for f in all_files if os.path.isfile(f)]

    uploaded_count = 0
    deleted_count = 0
    failed_count = 0

    if local_files:
        logger.info(
            f"Celery Task '{self.name}': Found {len(local_files)} files. Uploading to GCS bucket '{gcs_bucket_name}'...")
        try:
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(gcs_bucket_name)

            # Upload each file and track successful uploads
            for local_file in local_files:
                try:
                    # Get relative path for GCS object name
                    relative_path = os.path.relpath(
                        local_file, start=upload_folder)
                    # Ensure consistent path separators for GCS
                    gcs_path = f"resumes/{relative_path.replace(os.sep, '/')}"
                    blob = bucket.blob(gcs_path)

                    # Upload file
                    logger.info(f"Celery Task '{self.name}': Attempting to upload {local_file} to gs://{gcs_bucket_name}/{gcs_path}")
                    blob.upload_from_filename(local_file)
                    logger.info(
                        f"Celery Task '{self.name}': Uploaded {local_file} to GCS")
                    uploaded_count += 1

                    # Verify upload was successful by checking if blob exists
                    blob.reload()
                    if blob.exists():
                        # Delete the local file
                        os.remove(local_file)
                        logger.info(
                            f"Celery Task '{self.name}': Deleted local file {local_file}")
                        deleted_count += 1

                        # Remove empty parent directories if any
                        parent_dir = os.path.dirname(local_file)
                        while parent_dir and parent_dir != upload_folder and parent_dir.startswith(upload_folder):
                            try:
                                if not os.listdir(parent_dir): # Check if directory is empty
                                    os.rmdir(parent_dir)
                                    logger.info(
                                        f"Celery Task '{self.name}': Removed empty directory {parent_dir}")
                                    parent_dir = os.path.dirname(parent_dir) # Move up
                                else:
                                    break # Stop if directory is not empty
                            except OSError as e:
                                logger.warning(f"Celery Task '{self.name}': Could not remove directory {parent_dir}: {e}")
                                break # Stop if error occurs
                    else:
                        logger.warning(
                            f"Celery Task '{self.name}': Upload verification failed for {local_file} (gs://{gcs_bucket_name}/{gcs_path}), keeping local copy")
                        failed_count += 1 # Count verification failures as failures

                except Exception as e:
                    logger.error(
                        f"Celery Task '{self.name}': Error processing file {local_file}: {str(e)}")
                    failed_count += 1
                    continue # Continue with the next file

            result_msg = f"Celery Task '{self.name}': Upload complete. Uploaded: {uploaded_count}, Deleted: {deleted_count}, Failed/Kept: {failed_count}."
            logger.info(result_msg)
            return result_msg

        except Exception as e:
            error_msg = f"Celery Task '{self.name}': ERROR during GCS upload task setup or client initialization - {str(e)}"
            logger.error(error_msg)
            # Reraise or handle as appropriate for Celery error tracking
            raise self.retry(exc=e, countdown=60) # Example: retry in 60 seconds

    else:
        logger.info(f"Celery Task '{self.name}': No new files found in resumes folder.")
        return f"Celery Task '{self.name}': No files found."

