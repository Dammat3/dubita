"""Auth tests: register, login, me, wrong-password."""
import uuid
import requests


def test_register_creates_user_and_returns_token_and_cookie(base_url):
    email = f"reg_{uuid.uuid4().hex[:8]}@dubita.it"
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": "Pass1234!", "name": "Reg User"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == email
    assert data["name"] == "Reg User"
    assert data["role"] == "user"
    assert isinstance(data.get("id"), str) and len(data["id"]) > 0
    assert isinstance(data.get("token"), str) and len(data["token"]) > 20
    # httpOnly cookie
    set_cookie = r.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie.lower()
    assert "httponly" in set_cookie.lower()


def test_admin_login_returns_token(base_url):
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "admin@dubita.it", "password": "admin123"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "admin@dubita.it"
    assert data["role"] == "admin"
    assert isinstance(data.get("token"), str) and len(data["token"]) > 20
    set_cookie = r.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower()


def test_me_with_bearer_token_returns_user(base_url):
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "admin@dubita.it", "password": "admin123"},
        timeout=30,
    )
    token = r.json()["token"]
    me = requests.get(
        f"{base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert me.status_code == 200, me.text
    data = me.json()
    assert data["email"] == "admin@dubita.it"
    assert data["role"] == "admin"
    assert "id" in data
    assert "name" in data
    assert "password_hash" not in data


def test_login_wrong_password_returns_401_italian(base_url):
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "admin@dubita.it", "password": "wrong_password"},
        timeout=30,
    )
    assert r.status_code == 401
    detail = r.json().get("detail", "")
    assert "Credenziali non valide" in detail


def test_me_without_token_returns_401(base_url):
    r = requests.get(f"{base_url}/api/auth/me", timeout=30)
    assert r.status_code == 401
