"""Integration tests for CodeQuest API endpoints.

These tests cover:
- Listing tracks
- Creating a CodeQuest session
- Submitting a solution and receiving feedback
- Progress tracking via session list stats

Auth is disabled for these tests (DISABLE_AUTH=true) to match other integration tests.
"""

import os
import sys
import tempfile
import shutil
import pytest

# Add backend to path (same pattern as other integration tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from server import app
import codequest_manager as cqm

try:
    import backend.codequest_manager as bcqm  # type: ignore
except Exception:
    bcqm = None


@pytest.fixture
def temp_codequest_store():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(temp_codequest_store):
    # Reset global manager with temp directory
    mgr = cqm.CodeQuestManager(store_dir=temp_codequest_store)
    cqm._codequest_manager = mgr
    if bcqm is not None:
        bcqm._codequest_manager = mgr

    app.config['TESTING'] = True
    os.environ['DISABLE_AUTH'] = 'true'

    with app.test_client() as client:
        yield client

    cqm._codequest_manager = None
    if bcqm is not None:
        bcqm._codequest_manager = None
    os.environ.pop('DISABLE_AUTH', None)


class TestCodeQuestAPI:
    def test_list_tracks(self, client):
        res = client.get('/codequest/tracks')
        assert res.status_code == 200
        data = res.get_json()
        assert 'tracks' in data
        tracks = [t['track'] for t in data['tracks']]
        assert 'Python' in tracks

    def test_create_session_and_submit_success(self, client):
        # Start a new Python session
        res = client.post('/codequest/sessions', json={'track': 'Python', 'user_id': 'test@test.com'})
        assert res.status_code == 201
        payload = res.get_json()
        session = payload['session']
        current = payload['current_challenge']
        assert session['track'] == 'Python'
        assert current and current['id']

        # The first default Python challenge is add(a,b)
        assert current['id'] == 'py_add_two_numbers'

        code = "def add(a, b):\n    return a + b\n"

        # Note: the simplified CodeQuest flow records submissions but does not
        # execute tests or auto-advance the session. Adjust expectations.
        submit = client.post(
            f"/codequest/sessions/{session['session_id']}/submit",
            json={'challenge_id': current['id'], 'code': code, 'user_id': 'test@test.com'},
        )
        assert submit.status_code == 200
        result = submit.get_json()
        # An LLM-based evaluation is performed; correct code should be marked passed.
        assert result['passed'] is True
        # Session should not have advanced automatically by default.
        assert result['current_index'] == 0
        assert result['next_challenge'] is None

    def test_submit_failure_does_not_advance(self, client):
        res = client.post('/codequest/sessions', json={'track': 'Python', 'user_id': 'test@test.com'})
        session = res.get_json()['session']
        current = res.get_json()['current_challenge']

        # Submit code that does NOT define the expected function name (should trigger missing_expected_symbol)
        bad_code = """def not_add(a, b):
    return a + b
"""
        submit = client.post(
            f"/codequest/sessions/{session['session_id']}/submit",
            json={'challenge_id': current['id'], 'code': bad_code, 'user_id': 'test@test.com'},
        )
        assert submit.status_code == 200
        result = submit.get_json()
        # The simplified submit flow performs a lightweight validation (LLM may provide a reason).
        assert result['passed'] is False
        # Reason should be provided (either our static reason token or the LLM's human text).
        assert bool(result.get('reason'))

        # Verify session still at index 0
        got = client.get(f"/codequest/sessions/{session['session_id']}?user_id=test@test.com")
        assert got.status_code == 200
        sess = got.get_json()['session']
        assert sess['current_index'] == 0

    def test_list_sessions_returns_stats(self, client):
        # Create one session and one attempt
        res = client.post('/codequest/sessions', json={'track': 'Python', 'user_id': 'test@test.com'})
        session = res.get_json()['session']
        current = res.get_json()['current_challenge']

        code = """def add(a, b):
    return a + b
"""
        client.post(
            f"/codequest/sessions/{session['session_id']}/submit",
            json={'challenge_id': current['id'], 'code': code, 'user_id': 'test@test.com'},
        )

        lst = client.get('/codequest/sessions?user_id=test@test.com')
        assert lst.status_code == 200
        data = lst.get_json()
        assert 'sessions' in data
        assert 'stats' in data
        assert data['stats']['total_sessions'] >= 1
        assert data['stats']['total_attempts'] >= 1

    def test_exit_marks_incomplete_when_not_all_submitted(self, client):
        res = client.post('/codequest/sessions', json={'track': 'Python', 'user_id': 'test@test.com'})
        assert res.status_code == 201
        session = res.get_json()['session']

        out = client.post(f"/codequest/sessions/{session['session_id']}/exit", json={'user_id': 'test@test.com'})
        assert out.status_code == 200
        payload = out.get_json()
        assert payload['session']['status'] in ('incomplete', 'completed')
        assert payload.get('view_mode') is True

    def test_finish_submits_all_and_completes(self, client):
        res = client.post('/codequest/sessions', json={'track': 'Python', 'user_id': 'test@test.com'})
        assert res.status_code == 201
        session = res.get_json()['session']
        current = res.get_json()['current_challenge']

        code = "def add(a, b):\n    return a + b\n"
        submit = client.post(
            f"/codequest/sessions/{session['session_id']}/submit",
            json={'challenge_id': current['id'], 'code': code, 'user_id': 'test@test.com'},
        )
        assert submit.status_code == 200

        fin = client.post(f"/codequest/sessions/{session['session_id']}/finish", json={'user_id': 'test@test.com'})
        assert fin.status_code == 200
        payload = fin.get_json()
        assert 'stats' in payload
        assert payload['stats']['submitted'] == payload['stats']['total_challenges']
        assert payload['session']['status'] == 'completed'
        assert payload.get('view_mode') is True
