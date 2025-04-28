import os
from celery import Celery
from celery.schedules import crontab # Or timedelta
from app import create_app # Import the Flask app factory
from config import config

# Determine the config name (e.g., 'development', 'production')
# Celery might run in a different context, so be explicit or use env vars
config_class = config[os.getenv('APP_ENV', 'development')]

# Create a Flask app instance contextually for config loading
flask_app = create_app(config_class=config_class)

def make_celery(app):
    """Configure Celery instance using Flask app config."""
    # Use Redis as broker and result backend (adjust URL as needed)
    broker_url = app.config.get('broker_url', 'redis://localhost:6379/0')
    result_backend_url = app.config.get('result_backend', 'redis://localhost:6379/1')

    celery = Celery(
        app.import_name,
        broker=broker_url,
        backend=result_backend_url,
        include=['tasks'] # List of modules where tasks are defined
    )
    celery.conf.update(app.config)

    # --- Celery Beat Schedule ---
    # Get config values needed for the task arguments
    upload_folder = app.config.get('UPLOAD_FOLDER', 'static/resumes')
    gcs_bucket_name = app.config.get('GCS_BUCKET_NAME')
    interval_minutes = app.config.get('SCHEDULER_INTERVAL_MINUTES', 15)
    enable_gcs = app.config.get('ENABLE_GCS_UPLOAD', False)

    beat_schedule = {}
    # Only schedule the job if GCS is enabled and configured
    # if enable_gcs and gcs_bucket_name and gcs_bucket_name != 'your-gcs-bucket-name':
    #     print(f"Celery Beat: Scheduling 'upload_resumes_to_gcs_task' every {interval_minutes} minutes.")
    #     beat_schedule['upload-resumes-every-interval'] = {
    #         'task': 'tasks.upload_resumes_to_gcs_task', # Path to the task function
    #         'schedule': interval_minutes * 60.0, # Schedule in seconds (or use crontab)
    #         # 'schedule': crontab(minute=f'*/{interval_minutes}'), # Alternative using crontab
    #         'args': (upload_folder, gcs_bucket_name), # Arguments for the task
    #     }
    # else:
    #      print("Celery Beat: GCS upload not enabled or bucket not configured. Task 'upload_resumes_to_gcs_task' not scheduled.")

    celery.conf.beat_schedule = beat_schedule
    # --------------------------

    # Subclass Task to automatically push/pop Flask app context if needed
    # Not strictly required here since we pass config directly, but good practice
    # if tasks interact with Flask extensions like db.session
    class ContextTask(celery.Task):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Create the Celery instance using the factory
celery = make_celery(flask_app)

