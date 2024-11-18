import pytest
from app import app

@pytest.fixture
def client():
    app.testing = True
    return app.test_client()

def test_get_books(client):
    response = client.get('/books')
    assert response.status_code == 200
    assert isinstance(response.json, list)
