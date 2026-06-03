"""Upload-based dubbing pipeline test using a tiny mp4 with English speech.

This test is used because the YouTube downloader path is failing due to
YouTube's bot detection (HTTP 403 Forbidden) in this cloud environment.
"""
import os
import time
import requests
import pytest

SAMPLE_MP4 = "/tmp/test_sample.mp4"


@pytest.fixture(scope="module")
def upload_user_token(base_url):
    import uuid
    email = f"upl_{uuid.uuid4().hex[:8]}@dubita.it"
    r = requests.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": "Pass1234!", "name": "Upload User"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_upload_pipeline_completes(base_url, upload_user_token):
    if not os.path.exists(SAMPLE_MP4):
        pytest.skip(f"sample file missing: {SAMPLE_MP4}")

    with open(SAMPLE_MP4, "rb") as f:
        files = {"file": ("test_sample.mp4", f, "video/mp4")}
        data = {"voice": "alloy", "title": "TEST_Upload_Sample"}
        r = requests.post(
            f"{base_url}/api/projects/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {upload_user_token}"},
            timeout=60,
        )
    assert r.status_code == 200, r.text
    doc = r.json()
    pid = doc["id"]
    assert doc["status"] == "queued"
    assert doc["source_type"] == "upload"

    # Poll until done
    deadline = time.time() + 360  # 6 min
    last = None
    while time.time() < deadline:
        rr = requests.get(
            f"{base_url}/api/projects/{pid}",
            headers={"Authorization": f"Bearer {upload_user_token}"},
            timeout=30,
        )
        assert rr.status_code == 200
        last = rr.json()
        st = last.get("status")
        if st == "done":
            break
        if st == "error":
            pytest.fail(f"Upload pipeline failed: error={last.get('error')}, doc={last}")
        time.sleep(5)

    assert last is not None
    assert last.get("status") == "done", f"Pipeline did not finish: {last}"
    assert last.get("progress") == 100
    segs = last.get("segments")
    assert isinstance(segs, list) and len(segs) > 0
    assert "text" in segs[0]
    assert "text_it" in segs[0]
    assert last.get("dubbed_video_path")

    # Dubbed video
    v = requests.get(
        f"{base_url}/api/projects/{pid}/video/dubbed",
        headers={"Authorization": f"Bearer {upload_user_token}"},
        timeout=60,
    )
    assert v.status_code == 200
    assert v.headers.get("content-type", "").startswith("video/mp4")
    assert len(v.content) > 1000

    # Cleanup
    d = requests.delete(
        f"{base_url}/api/projects/{pid}",
        headers={"Authorization": f"Bearer {upload_user_token}"},
        timeout=30,
    )
    assert d.status_code == 200
