import pytest
from unittest.mock import patch
from app import create_app
from config import config

@pytest.fixture
def client():
    app = create_app(config['dev_testing'])
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

@patch('extensions.mail.send')
def test_contact_form_sends_email(mock_send, client):
    response = client.post('/contact', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'subject': 'Test Subject',
        'message': 'Hello! How are you? What is your name?'
    }, follow_redirects=True)
    assert mock_send.called
    assert b'Thank you' in response.data or response.status_code == 200