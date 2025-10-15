import pytest
import json
from app import app, init_db

@pytest.fixture
def client():
    """Créer un client de test"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_health_endpoint(client):
    """Test de la route health"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_get_user(client):
    """Test de récupération d'un utilisateur"""
    response = client.get('/user/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'username' in data
    assert data['username'] == 'admin'

def test_get_all_users(client):
    """Test de récupération de tous les utilisateurs"""
    response = client.get('/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 2

def test_login_valid_credentials(client):
    """Test de connexion avec identifiants valides"""
    response = client.post('/login',
                          data=json.dumps({
                              'username': 'admin',
                              'password': 'admin123'
                          }),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

def test_login_invalid_credentials(client):
    """Test de connexion avec identifiants invalides"""
    response = client.post('/login',
                          data=json.dumps({
                              'username': 'admin',
                              'password': 'wrongpassword'
                          }),
                          content_type='application/json')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] == False

def test_search_endpoint(client):
    """Test de la recherche"""
    response = client.get('/search?q=test')
    assert response.status_code == 200
    assert b'test' in response.data

def test_calculate_endpoint(client):
    """Test du calculateur"""
    response = client.post('/calculate',
                          data=json.dumps({
                              'expression': '2+2'
                          }),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['result'] == 4