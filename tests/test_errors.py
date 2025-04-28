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

def test_404_handler(client):
    response = client.get('/nonexistentpage')
    assert response.status_code == 404
    assert b'404' in response.data or b'Not Found' in response.data