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

def test_my_applications_requires_login(client):
    response = client.get('/my_applications', follow_redirects=True)
    assert b'Login' in response.data or response.status_code == 403
