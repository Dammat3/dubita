"""Project lifecycle tests including the full YouTube dubbing pipeline."""
import time
import uuid
import requests
import pytest


SHORT_YT = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" 19s


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_create_youtube_project_returns_queued(base_url, fresh_user):
    r = requests.post(
        f"{base_url}/api/projects/youtube",
        json={"youtube_url": SHORT_YT, "voice": "alloy", "title": "TEST_YT_Quick"},
        headers=_auth_headers(fresh_user["token"]),
        timeout=30,
    )
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "queued"
    assert doc["voice"] == "alloy"
    assert doc["source_type"] == "youtube"
    assert doc["user_id"] == fresh_user["id"]
    assert "id" in doc
    # Persist for later test usage
    pytest.shared_project_id = doc["id"]


def test_invalid_youtube_url_returns_400(base_url, fresh_user):
    r = requests.post(
        f"{base_url}/api/projects/youtube",
        json={"youtube_url": "not-a-url", "voice": "alloy"},
        headers=_auth_headers(fresh_user["token"]),
        timeout=30,
    )
    assert r.status_code == 400


def test_unauthenticated_create_returns_401(base_url):
    r = requests.post(
        f"{base_url}/api/projects/youtube",
        json={"youtube_url": SHORT_YT, "voice": "alloy"},
        timeout=30,
    )
    assert r.status_code == 401


def test_list_projects_for_user_isolation(base_url, fresh_user):
    # the first test created a project for this user
    r = requests.get(
        f"{base_url}/api/projects",
        headers=_auth_headers(fresh_user["token"]),
        timeout=30,
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(p["id"] == getattr(pytest, "shared_project_id", None) for p in items)

    # Create a second user, verify they DO NOT see the first user's project
    email2 = f"isol_{uuid.uuid4().hex[:8]}@dubita.it"
    reg = requests.post(
        f"{base_url}/api/auth/register",
        json={"email": email2, "password": "Pass1234!", "name": "Other"},
        timeout=30,
    )
    assert reg.status_code == 200
    token2 = reg.json()["token"]
    r2 = requests.get(
        f"{base_url}/api/projects",
        headers=_auth_headers(token2),
        timeout=30,
    )
    assert r2.status_code == 200
    items2 = r2.json()
    pid = getattr(pytest, "shared_project_id", None)
    assert all(p["id"] != pid for p in items2)

    # Cross-user GET single -> 404
    r3 = requests.get(
        f"{base_url}/api/projects/{pid}",
        headers=_auth_headers(token2),
        timeout=30,
    )
    assert r3.status_code == 404


def test_youtube_pipeline_completes(base_url, fresh_user):
    """Long-running test: poll until project is done (max 6 min)."""
    pid = getattr(pytest, "shared_project_id", None)
    if not pid:
        pytest.skip("No project created in earlier test")

    deadline = time.time() + 360  # 6 minutes
    last = None
    while time.time() < deadline:
        r = requests.get(
            f"{base_url}/api/projects/{pid}",
            headers=_auth_headers(fresh_user["token"]),
            timeout=30,
        )
        assert r.status_code == 200
        last = r.json()
        st = last.get("status")
        if st == "done":
            break
        if st == "error":
            pytest.fail(f"Pipeline failed: status=error, error={last.get('error')}, doc={last}")
        time.sleep(5)
    assert last is not None
    assert last.get("status") == "done", f"Pipeline did not finish in time, last={last}"
    assert last.get("progress") == 100
    segments = last.get("segments")
    assert isinstance(segments, list) and len(segments) > 0
    seg0 = segments[0]
    assert "text" in seg0
    assert "text_it" in seg0
    assert last.get("dubbed_video_path")

    # GET dubbed video
    r = requests.get(
        f"{base_url}/api/projects/{pid}/video/dubbed",
        headers=_auth_headers(fresh_user["token"]),
        timeout=60,
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("video/mp4")
    assert len(r.content) > 1000  # has bytes


def test_delete_project(base_url, fresh_user):
    pid = getattr(pytest, "shared_project_id", None)
    if not pid:
        pytest.skip("No project to delete")
    r = requests.delete(
        f"{base_url}/api/projects/{pid}",
        headers=_auth_headers(fresh_user["token"]),
        timeout=30,
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True
    # Now GET -> 404
    r2 = requests.get(
        f"{base_url}/api/projects/{pid}",
        headers=_auth_headers(fresh_user["token"]),
        timeout=30,
    )
    assert r2.status_code == 404
