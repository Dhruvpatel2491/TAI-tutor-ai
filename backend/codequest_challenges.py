"""DEPRECATED: CodeQuest challenge bank.

This file is intentionally kept as a tiny stub to avoid import errors in
environments that still reference it. The CodeQuest default challenge bank now
lives in `backend/codequest_manager.py`.

TODO: remove this file from the repository when safe.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_default_challenges() -> List[Dict[str, Any]]:
    # Legacy compatibility shim.
    return []
