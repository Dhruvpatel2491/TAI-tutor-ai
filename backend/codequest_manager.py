"""CodeQuest Manager.

A lightweight JSON-backed "database" for:
- Challenge bank (per track / language)
- Per-user CodeQuest sessions
- Submissions, evaluation results, and progress tracking

Storage layout (default):
user_data/codequest/
  challenges.json
  sessions/<safe_user_id>/<session_id>.json

This mirrors the repo's chat history persistence approach.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    # When imported as `backend` package
    from backend.codequest_challenges import get_default_challenges
except Exception:
    # When running `python server.py` from the backend folder
    from codequest_challenges import get_default_challenges

logger = logging.getLogger("backend.codequest")

DEFAULT_CODEQUEST_STORE_DIR = os.environ.get(
    "CODEQUEST_STORE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data", "codequest"),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_user_dir_component(user_id: str) -> str:
    return user_id.replace("@", "__at__").replace(".", "__dot__")


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


@dataclass
class CodeQuestChallenge:
    id: str
    track: str
    language: str
    title: str
    prompt: str
    starter_code: str
    evaluator: str
    test_code: str

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "track": self.track,
            "language": self.language,
            "title": self.title,
            "prompt": self.prompt,
            "starter_code": self.starter_code,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "track": self.track,
            "language": self.language,
            "title": self.title,
            "prompt": self.prompt,
            "starter_code": self.starter_code,
            "evaluator": self.evaluator,
            "test_code": self.test_code,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeQuestChallenge":
        return cls(
            id=str(data.get("id")),
            track=str(data.get("track")),
            language=str(data.get("language")),
            title=str(data.get("title")),
            prompt=str(data.get("prompt")),
            starter_code=str(data.get("starter_code")),
            evaluator=str(data.get("evaluator")),
            test_code=str(data.get("test_code")),
        )


class CodeQuestManager:
    def __init__(self, store_dir: Optional[str] = None):
        self.store_dir = Path(store_dir or DEFAULT_CODEQUEST_STORE_DIR)
        self._lock = threading.Lock()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._challenges_path = self.store_dir / "challenges.json"
        self._sessions_dir = self.store_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CodeQuestManager initialized with store_dir: {self.store_dir}")

        # Ensure a challenge "DB section" exists.
        self._ensure_challenge_db()

    # ---------- Challenge store ----------
    def _ensure_challenge_db(self) -> None:
        if self._challenges_path.exists():
            return
        defaults = get_default_challenges()
        payload = {"version": 1, "created_at": _utc_now_iso(), "challenges": defaults}
        try:
            _atomic_write_json(self._challenges_path, payload)
            logger.info("Created default CodeQuest challenge DB")
        except Exception:
            logger.exception("Failed to create default challenge DB")

    def _load_challenges(self) -> List[CodeQuestChallenge]:
        try:
            if self._challenges_path.exists():
                with open(self._challenges_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw = data.get("challenges", []) if isinstance(data, dict) else []
                return [CodeQuestChallenge.from_dict(x) for x in raw]
        except Exception:
            logger.exception("Failed to load CodeQuest challenges; using defaults")
        return [CodeQuestChallenge.from_dict(x) for x in get_default_challenges()]

    def list_tracks(self) -> List[Dict[str, Any]]:
        challenges = self._load_challenges()
        tracks: Dict[str, Dict[str, Any]] = {}
        for ch in challenges:
            if ch.track not in tracks:
                tracks[ch.track] = {
                    "track": ch.track,
                    "languages": sorted({c.language for c in challenges if c.track == ch.track}),
                    "challenge_count": sum(1 for c in challenges if c.track == ch.track),
                }
        return sorted(tracks.values(), key=lambda t: t["track"].lower())

    def list_challenges(self, track: str) -> List[Dict[str, Any]]:
        challenges = self._load_challenges()
        return [c.to_public_dict() for c in challenges if c.track.lower() == track.lower()]

    def get_challenge(self, challenge_id: str) -> Optional[CodeQuestChallenge]:
        for c in self._load_challenges():
            if c.id == challenge_id:
                return c
        return None

    # ---------- Session store ----------
    def _get_user_dir(self, user_id: str) -> Path:
        return self._sessions_dir / _safe_user_dir_component(user_id)

    def _get_session_path(self, user_id: str, session_id: str) -> Path:
        return self._get_user_dir(user_id) / f"{session_id}.json"

    def _load_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        p = self._get_session_path(user_id, session_id)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Failed to load CodeQuest session")
            return None

    def _save_session(self, user_id: str, session: Dict[str, Any]) -> None:
        p = self._get_session_path(user_id, session["session_id"])
        _atomic_write_json(p, session)

    def create_session(self, user_id: str, track: str) -> Dict[str, Any]:
        with self._lock:
            all_ch = [c for c in self._load_challenges() if c.track.lower() == track.lower()]
            if not all_ch:
                raise ValueError("unknown track")

            session_id = str(uuid.uuid4())
            created_at = _utc_now_iso()
            session = {
                "session_id": session_id,
                "user_id": user_id,
                "track": all_ch[0].track,
                "language": all_ch[0].language,
                "created_at": created_at,
                "updated_at": created_at,
                "status": "active",
                "current_index": 0,
                "challenge_ids": [c.id for c in all_ch],
                "attempts": [],  # list of attempt dicts
                "results": {},  # challenge_id -> {passed: bool, last_submitted_at: str, attempts: int}
            }

            user_dir = self._get_user_dir(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            self._save_session(user_id, session)
            return session

    def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return []

        out: List[Dict[str, Any]] = []
        for p in sorted(user_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                out.append(
                    {
                        "session_id": s.get("session_id"),
                        "track": s.get("track"),
                        "language": s.get("language"),
                        "status": s.get("status"),
                        "created_at": s.get("created_at"),
                        "updated_at": s.get("updated_at"),
                        "current_index": s.get("current_index", 0),
                        "total_challenges": len(s.get("challenge_ids", []) or []),
                        "attempt_count": len(s.get("attempts", []) or []),
                    }
                )
            except Exception:
                logger.debug("Skipping unreadable session file %s", p)
        return out

    def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        return self._load_session(user_id, session_id)

    def get_current_challenge_public(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ids = session.get("challenge_ids") or []
        idx = int(session.get("current_index", 0))
        if idx < 0 or idx >= len(ids):
            return None
        ch = self.get_challenge(ids[idx])
        return ch.to_public_dict() if ch else None

    # ---------- Evaluation ----------
    def _run_python_unittest(self, student_code: str, test_code: str, timeout_s: int = 5) -> Tuple[bool, str, str, int]:
        with tempfile.TemporaryDirectory(prefix="codequest_py_") as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "student.py").write_text(student_code, encoding="utf-8")
            (tmp_path / "test_student.py").write_text(test_code, encoding="utf-8")

            cmd = [
                sys.executable,
                "-m",
                "unittest",
                "-q",
                "test_student",
            ]
            try:
                cp = subprocess.run(
                    cmd,
                    cwd=str(tmp_path),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                ok = cp.returncode == 0
                return ok, (cp.stdout or ""), (cp.stderr or ""), cp.returncode
            except subprocess.TimeoutExpired as e:
                return False, (e.stdout or ""), (e.stderr or "") + "\nTimed out.", 124

    def _run_node_assert(self, student_code: str, test_code: str, timeout_s: int = 5) -> Tuple[bool, str, str, int]:
        with tempfile.TemporaryDirectory(prefix="codequest_js_") as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "student.js").write_text(student_code, encoding="utf-8")
            (tmp_path / "test.js").write_text(test_code, encoding="utf-8")

            cmd = ["node", "test.js"]
            try:
                cp = subprocess.run(
                    cmd,
                    cwd=str(tmp_path),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                ok = cp.returncode == 0
                return ok, (cp.stdout or ""), (cp.stderr or ""), cp.returncode
            except FileNotFoundError:
                return False, "", "Node.js not available on server.", 127
            except subprocess.TimeoutExpired as e:
                return False, (e.stdout or ""), (e.stderr or "") + "\nTimed out.", 124

    def evaluate(self, challenge: CodeQuestChallenge, code: str) -> Dict[str, Any]:
        evaluator = (challenge.evaluator or "").strip().lower()
        if evaluator == "python_unittest":
            passed, stdout, stderr, rc = self._run_python_unittest(code, challenge.test_code)
        elif evaluator == "node_assert":
            passed, stdout, stderr, rc = self._run_node_assert(code, challenge.test_code)
        else:
            passed, stdout, stderr, rc = False, "", f"Unsupported evaluator: {challenge.evaluator}", 2

        # Truncate to keep responses small
        def _trunc(s: str, n: int = 8000) -> str:
            s = s or ""
            return s if len(s) <= n else (s[:n] + "\n...<truncated>...")

        return {
            "passed": bool(passed),
            "return_code": rc,
            "stdout": _trunc(stdout),
            "stderr": _trunc(stderr),
        }

    def submit_solution(self, user_id: str, session_id: str, challenge_id: str, code: str) -> Dict[str, Any]:
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                raise ValueError("session is not active")

            ids = session.get("challenge_ids") or []
            idx = int(session.get("current_index", 0))
            if idx < 0 or idx >= len(ids):
                raise ValueError("session has no current challenge")
            expected_id = ids[idx]
            if challenge_id != expected_id:
                raise ValueError("challenge_id does not match current challenge")

            ch = self.get_challenge(challenge_id)
            if not ch:
                raise ValueError("unknown challenge")

            started = datetime.now(timezone.utc)
            eval_result = self.evaluate(ch, code)
            ended = datetime.now(timezone.utc)
            duration_ms = int((ended - started).total_seconds() * 1000)

            attempt_id = str(uuid.uuid4())
            attempt = {
                "attempt_id": attempt_id,
                "challenge_id": challenge_id,
                "submitted_at": ended.isoformat(),
                "duration_ms": duration_ms,
                "passed": eval_result["passed"],
                "stdout": eval_result.get("stdout", ""),
                "stderr": eval_result.get("stderr", ""),
                "code": code,
            }
            session.setdefault("attempts", []).append(attempt)
            session["updated_at"] = _utc_now_iso()

            results = session.setdefault("results", {})
            prev = results.get(challenge_id) or {"attempts": 0, "passed": False}
            results[challenge_id] = {
                "attempts": int(prev.get("attempts", 0)) + 1,
                "passed": bool(prev.get("passed")) or bool(eval_result["passed"]),
                "last_submitted_at": attempt["submitted_at"],
            }

            # Advance if passed
            next_challenge: Optional[Dict[str, Any]] = None
            finished = False
            if eval_result["passed"]:
                session["current_index"] = idx + 1
                if session["current_index"] >= len(ids):
                    session["status"] = "completed"
                    session["completed_at"] = _utc_now_iso()
                    finished = True
                else:
                    next_challenge = self.get_current_challenge_public(session)

            self._save_session(user_id, session)

            return {
                "session_id": session_id,
                "track": session.get("track"),
                "status": session.get("status"),
                "current_index": session.get("current_index"),
                "total_challenges": len(ids),
                "challenge_id": challenge_id,
                "attempt_id": attempt_id,
                "passed": eval_result["passed"],
                "stdout": eval_result.get("stdout"),
                "stderr": eval_result.get("stderr"),
                "next_challenge": next_challenge,
                "finished": finished,
            }


_codequest_manager: Optional[CodeQuestManager] = None


def get_codequest_manager() -> CodeQuestManager:
    global _codequest_manager
    if _codequest_manager is None:
        _codequest_manager = CodeQuestManager()
    return _codequest_manager
