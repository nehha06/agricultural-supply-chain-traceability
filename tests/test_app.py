
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login(client):
    return client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin123"
        },
        follow_redirects=True
    )


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302


def test_admin_can_open_dashboard(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Welcome to AgriTrace" in response.data


def test_tracking_unknown_batch(client):
    response = client.get("/track/INVALID-BATCH")
    assert response.status_code == 404
