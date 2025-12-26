import json
import os
import sys
import pytest

# Ensure repository root is on sys.path so imports work when tests
# are executed directly.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(ROOT, 'backend')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import LLM helper functions from codequest module
# (these are embedded in modules.codequest now)
from modules import codequest as lc


VALID_ITEM = {
    "id": "sample-challenge",
    "track": "Python",
    "language": "python",
    "title": "Sample Challenge",
    "prompt": "Do something",
    "starter_code": "",
}


@pytest.mark.parametrize(
    "raw",
    [
        # clean JSON array
        json.dumps([VALID_ITEM]),
        # dict-wrapped response
        json.dumps({"challenges": [VALID_ITEM]}),
        # trailing commas (common LLM mistake)
        '[{"id":"sample-challenge","track":"Python","language":"python","title":"Sample Challenge","prompt":"Do something","starter_code":"",},]',
        # JSON inside a quoted string
        '"' + json.dumps([VALID_ITEM]).replace('"', '\\"') + '"',
        # markdown fences around JSON
        '```json\n' + json.dumps([VALID_ITEM]) + '\n```',
        # list of strings -> should coerce into minimal dicts
        json.dumps(["One", "Two"]),
    ],
)
def test_generate_challenge_set_recovers(raw, monkeypatch):
    """Ensure generate_challenge_set can handle several malformed LLM outputs."""

    def fake_chat(model, system, user, *, temperature=0.1):
        return raw

    monkeypatch.setattr(lc, "_chat", fake_chat)

    out = lc.generate_challenge_set(title="T", language="python", difficulty="easy", num_challenges=2)

    assert isinstance(out, list)
    assert len(out) >= 1
    # each item must contain required keys
    for item in out:
        assert isinstance(item, dict)
        for k in ("id", "title", "prompt", "starter_code"):
            assert k in item
