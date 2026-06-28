import os

BACKEND_TESTS = r"c:\PROJECT\PEPto\backend\tests"

files = {
    "conftest.py": """import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.provider import ProviderProfile
from app.models.service import Service
from app.models.booking import Booking

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def customer_user(app):
    user = User(
        email="customer@test.com",
        full_name="Test Customer",
        role="customer",
        is_verified=True,
        is_active=True
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def provider_user(app):
    user = User(
        email="provider@test.com",
        full_name="Test Provider",
        role="provider",
        is_verified=True,
        is_active=True
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    
    profile = ProviderProfile(
        user_id=user.id,
        business_name="Test Vet Clinic",
        slug="test-vet-clinic",
        is_verified_business=True,
        city="Mumbai",
        state="MH",
        latitude=19.0760,
        longitude=72.8777
    )
    db.session.add(profile)
    db.session.commit()
    return user

def auth_headers(user):
    from app.services.auth_service import AuthService
    tokens = AuthService().generate_tokens(str(user.id), user.role.name)
    return {'Authorization': f"Bearer {tokens['access_token']}"}
""",
    "test_auth.py": """import pytest

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
""",
    "test_bookings.py": """import pytest

def test_create_booking_unauthorized(client):
    res = client.post('/api/bookings', json={})
    assert res.status_code == 401

def test_check_availability_missing_params(client, customer_user):
    from tests.conftest import auth_headers
    res = client.get('/api/bookings/availability-check', headers=auth_headers(customer_user))
    assert res.status_code == 400
""",
    "test_search.py": """import pytest

def test_search_providers_public(client, provider_user):
    res = client.get('/api/providers/search?lat=19.0&lng=72.8&radius_km=20')
    assert res.status_code == 200
    assert res.json['success'] is True
"""
}

os.makedirs(BACKEND_TESTS, exist_ok=True)
for filepath, content in files.items():
    full_path = os.path.join(BACKEND_TESTS, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Backend pytest suite generated successfully.")
