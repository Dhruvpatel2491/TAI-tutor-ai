import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import auth


def test_create_and_verify_jwt():
    token = auth.create_jwt_for_user("test-user-1", exp_seconds=60)
    assert isinstance(token, str) and len(token) > 0
    payload = auth.verify_jwt(token)
    assert payload is not None
    assert payload.get("sub") == "test-user-1"
