"""Shared pytest fixtures for backend tests."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://audio-italiano-2.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@dubita.it", "password": "admin123"},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    })
    return s


@pytest.fixture(scope="session")
def fresh_user():
    """Register a new fresh user for the session."""
    email = f"test_user_{uuid.uuid4().hex[:8]}@dubita.it"
    password = "Test1234!"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": "Test User"},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"User registration failed: {r.status_code} {r.text}")
    data = r.json()
    return {"email": email, "password": password, "token": data["token"], "id": data["id"]}


@pytest.fixture
def user_client(fresh_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {fresh_user['token']}",
    })
    return s
