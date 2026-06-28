import pytest

def test_search_providers_public(client, provider_user):
    res = client.get('/api/providers/search?lat=19.0&lng=72.8&radius_km=20')
    assert res.status_code == 200
    assert res.json['success'] is True
