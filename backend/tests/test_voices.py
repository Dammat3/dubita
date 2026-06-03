"""Voices endpoint test."""
import requests


def test_voices_returns_list(base_url):
    r = requests.get(f"{base_url}/api/voices", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "voices" in data
    voices = data["voices"]
    assert isinstance(voices, list)
    assert len(voices) >= 5
    for v in voices:
        assert "id" in v
        assert "label" in v
    ids = {v["id"] for v in voices}
    assert "alloy" in ids
