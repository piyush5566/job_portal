import io
import pytest
from app import create_app
from config import config

@pytest.fixture
def client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_resume_upload_requires_login(client):
    data = {
        'resume': (io.BytesIO(b'my resume'), 'resume.pdf')
    }
    response = client.post('/jobs/apply/1', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'Login' in response.data or response.status_code in (302, 403)