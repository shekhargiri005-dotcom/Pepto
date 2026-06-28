import pytest

def test_register_success(client):
    res = client.post('/api/auth/register', json={
        "email": "newuser@test.com",
        "password": "Password123!",
        "full_name": "New User"
    })
    assert res.status_code == 201
    assert res.json['success'] is True

def test_login_success(client, customer_user):
    res = client.post('/api/auth/login', json={
        "email": "customer@test.com",
        "password": "Password123!"
    })
    assert res.status_code == 200
    assert 'access_token' in res.json['data']

def test_get_current_user(client, customer_user):
    from tests.conftest import auth_headers
    res = client.get('/api/auth/me', headers=auth_headers(customer_user))
    assert res.status_code == 200
    assert res.json['data']['email'] == "customer@test.com"
