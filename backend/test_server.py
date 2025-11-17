import requests
import pytest
import time

BASE_URL = "http://localhost:5000"

def wait_for_server(timeout=30):
    for _ in range(timeout):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_server():
    assert wait_for_server(), "Backend server not running on port 5000"

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

def test_query_basic():
    payload = {"question": "What is this project about?"}
    r = requests.post(f"{BASE_URL}/query", json=payload)
    assert r.status_code == 200
    assert "answer" in r.json()

def test_query_with_rebuild_and_parser():
    payload = {
        "question": "List all classes.",
        "rebuild": True,
        "indexing": {"parser": "code", "chunk_size": 512}
    }
    r = requests.post(f"{BASE_URL}/query", json=payload)
    assert r.status_code == 200
    assert "answer" in r.json()

def test_query_v2_custom_model():
    payload = {
        "question": "Summarize the codebase.",
        "model": "llama3-chatqa:latest",
        "temperature": 0.1,
        "max_tokens": 256
    }
    r = requests.post(f"{BASE_URL}/query_v2", json=payload)
    assert r.status_code == 200
    assert "answer" in r.json()

def test_rebuild_async():
    payload = {"wait": False}
    r = requests.post(f"{BASE_URL}/rebuild", json=payload)
    assert r.status_code == 202
    assert r.json().get("status") == "rebuild_started"
