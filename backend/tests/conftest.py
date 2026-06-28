import pytest
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
