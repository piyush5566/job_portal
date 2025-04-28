"""
Utility functions for the Job Portal application.

This module provides various utility functions used throughout the application:
- File handling (uploads, validation, retrieval)
- Image processing
- Path management
- Google Cloud Storage integration

It also defines important constants for file paths and allowed file extensions.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import logging
from flask import current_app
from google.cloud import storage
import io # Needed for BytesIO in serve_resume later

# Configuration constants
UPLOAD_FOLDER = 'static/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
PROFILE_UPLOAD_FOLDER = 'static/img/profiles'
ALLOWED_PIC_EXTENSIONS = {'png', 'jpg', 'jpeg'}
COMPANY_LOGOS_FOLDER = 'static/img/company_logos'

# Logger
logger = logging.getLogger('job_portal')

# Utility functions
def allowed_file(filename, allowed_extensions):
    """
    Check if a file has an allowed extension.
    
    Args:
        filename (str): The name of the file to check
        allowed_extensions (set): Set of allowed file extensions
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions

# --- NEW: Function to upload directly to GCS ---
def upload_to_gcs(file_storage, user_id, gcs_bucket_name):
    """
    Uploads a file directly to Google Cloud Storage.

    Args:
        file_storage (FileStorage): The file object from the request.
        user_id (int): The ID of the user uploading the file.
        gcs_bucket_name (str): The name of the target GCS bucket.

    Returns:
        str: The GCS object name (e.g., 'resumes/123/filename.pdf') if successful,
             None otherwise.
    """
    if not file_storage or not gcs_bucket_name:
        logger.warning("upload_to_gcs: Missing file_storage or bucket name.")
        return None

    if not allowed_file(file_storage.filename, ALLOWED_RESUME_EXTENSIONS):
        logger.warning(f"upload_to_gcs: Invalid file type attempted: {file_storage.filename}")
        return None

    try:
        filename = secure_filename(file_storage.filename)
        # Construct the object name/path within GCS
        gcs_object_name = f"resumes/{user_id}/{filename}"

        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(gcs_object_name)

        # Rewind the file stream before uploading
        file_storage.seek(0)

        # Upload the file stream
        blob.upload_from_file(file_storage)

        logger.info(f"Successfully uploaded {filename} to GCS bucket {gcs_bucket_name} as {gcs_object_name} for user {user_id}")
        return gcs_object_name # Return the GCS path

    except Exception as e:
        logger.error(f"Error uploading {file_storage.filename} to GCS for user {user_id}: {str(e)}")
        # Optionally re-raise or handle specific GCS exceptions
        return None
    
    
# def save_resume(resume_file, user_id):
#     """
#     Save a resume file to the appropriate directory.
    
#     Creates a user-specific directory if it doesn't exist and
#     saves the resume file with a secure filename.
    
#     Args:
#         resume_file (FileStorage): The resume file to save
#         user_id (int): The ID of the user uploading the resume
        
#     Returns:
#         str: The relative path to the saved resume file
        
#     Raises:
#         Exception: If there's an error saving the file
#     """
#     try:
#         if resume_file and allowed_file(resume_file.filename, ALLOWED_RESUME_EXTENSIONS):
#             filename = secure_filename(resume_file.filename)
#             # Create user-specific directory
#             user_dir = os.path.join(UPLOAD_FOLDER, str(user_id))
#             if not os.path.exists(user_dir):
#                 os.makedirs(user_dir)
#                 logger.info(f"Created resume directory for user {user_id}")
            
#             filepath = os.path.join(user_dir, filename)
#             resume_file.save(filepath)
#             logger.info(f"Resume saved successfully: {filepath}")
#             return f"static/resumes/{user_id}/{filename}"
#     except Exception as e:
#         logger.error(f"Error saving resume for user {user_id}: {str(e)}")
#         raise

def save_company_logo(file):
    """
    Save a company logo with a unique filename.
    
    Generates a UUID-based filename to prevent collisions and
    saves the image to the company logos directory.
    
    Args:
        file (FileStorage): The company logo file to save
        
    Returns:
        str: The unique filename of the saved logo, or None if saving failed
    """
    if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        try:
            filename = secure_filename(file.filename)
            unique_filename = str(
                uuid.uuid4().hex[:16]) + os.path.splitext(filename)[1]
            logo_path = os.path.join(
                COMPANY_LOGOS_FOLDER, unique_filename)
            file.save(logo_path)
            logger.info(f"Company logo saved successfully: {unique_filename}")
            return unique_filename
        except Exception as e:
            logger.error(f"Error saving company logo: {str(e)}")
            return None
    logger.warning(f"Invalid company logo file type attempted")
    return None

def save_profile_picture(picture_file):
    """
    Save and resize a user profile picture.
    
    Generates a UUID-based filename, saves the image, and resizes it
    to a standard size (300x300) if it's larger.
    
    Args:
        picture_file (FileStorage): The profile picture file to save
        
    Returns:
        str: The relative path to the saved profile picture,
             or the default profile picture path if saving failed
    """
    if not picture_file or not allowed_file(picture_file.filename, ALLOWED_PIC_EXTENSIONS):
         logger.warning(f"Invalid profile picture file type attempted or file missing.")
         return 'img/profiles/default.jpg' # Return default if invalid
    try:
        filename = secure_filename(picture_file.filename)
        unique_filename = str(uuid.uuid4().hex[:16]) + os.path.splitext(filename)[1]
        picture_path = os.path.join(PROFILE_UPLOAD_FOLDER, unique_filename)
        
        # Save the file
        picture_file.save(picture_path)
        
        # Resize the image to a standard size
        img = Image.open(picture_path)
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(picture_path)
            
        return f'img/profiles/{unique_filename}'
    except Exception as e:
        logger.error(f"Error saving profile picture: {str(e)}")
        return 'img/profiles/default.jpg'

def get_resume_file(resume_path, enable_gcs=False, gcs_bucket_name=None):
    """
    Get a resume file from either local storage or Google Cloud Storage.
    
    First checks if the file exists locally. If not and GCS is enabled,
    attempts to retrieve it from GCS and save it locally.
    
    Args:
        resume_path (str): The path to the resume file
        enable_gcs (bool): Whether to try retrieving from GCS if not found locally
        gcs_bucket_name (str): The name of the GCS bucket to retrieve from
        
    Returns:
        tuple: (file_path, success_flag) where file_path is the path to the file
               if found, or None if not found, and success_flag is a boolean
               indicating whether the file was successfully retrieved
    """
    # First check if file exists locally
    if os.path.exists(resume_path):
        return resume_path, True

    # If not found locally and GCS is enabled, try to get from GCS
    if enable_gcs:
        try:
            from google.cloud import storage
            # Get relative path for GCS object name
            relative_path = os.path.relpath(
                resume_path, start=UPLOAD_FOLDER)
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(gcs_bucket_name)
            blob = bucket.blob(f"resumes/{relative_path}")
            
            # Check if blob exists
            if blob.exists():
                # Create local directory if it doesn't exist
                os.makedirs(os.path.dirname(resume_path), exist_ok=True)
                
                # Download file
                blob.download_to_filename(resume_path)
                return resume_path, True
        except Exception as e:
            logger.error(f"Error retrieving file from GCS: {str(e)}")
    
    return None, False
