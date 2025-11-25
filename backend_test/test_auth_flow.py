import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend import auth


def test_register_and_verify(tmp_path):
    # Use a unique temporary user directory by monkeypatching the module path
    # Create a temp dir and point auth._ROOT_USER_DIR to it
    tmp_user_dir = tmp_path / "login_register"
    auth._ROOT_USER_DIR = tmp_user_dir
    email = "testuser@example.com"
    password = "s3cret-P@ss"

    # Ensure user does not exist
    assert not auth.user_exists(email)

    # Register user
    meta = auth.register_user(email, password)
    assert meta.get("email") == email
    assert auth.user_exists(email)

    # Verify correct password
    assert auth.verify_user(email, password) is True

    # Wrong password fails
    assert auth.verify_user(email, "wrong") is False
