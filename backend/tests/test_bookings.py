import pytest

def test_create_booking_unauthorized(client):
    res = client.post('/api/bookings', json={})
    assert res.status_code == 401

def test_check_availability_missing_params(client, customer_user):
    from tests.conftest import auth_headers
    res = client.get('/api/bookings/availability-check', headers=auth_headers(customer_user))
    assert res.status_code == 400
