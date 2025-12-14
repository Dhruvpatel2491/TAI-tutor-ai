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
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_default_challenges() -> List[Dict[str, Any]]:
    """Built-in fallback challenge bank.

    This intentionally lives in this module so the backend doesn't depend on
    `backend/codequest_challenges.py`.

    Schema:
    - id: str
    - track: str
    - language: str
    - title: str
    - prompt: str
    - starter_code: str
    """

    return [
        {
            "id": "py_add_two_numbers",
            "track": "Python",
            "language": "python",
            "title": "Add Two Numbers",
            "prompt": "Write a function `add(a, b)` that returns the sum of `a` and `b`.\n\nRequirements:\n- Must return an int/float numeric sum\n- Do not print; just return",
            "starter_code": "def add(a, b):\n    # TODO: implement\n    pass\n",
            "solution": "def add(a, b):\n    return a + b\n",
        },
        {
            "id": "py_reverse_string",
            "track": "Python",
            "language": "python",
            "title": "Reverse a String",
            "prompt": "Write a function `reverse_string(s)` that returns the reverse of the input string `s`.\n\nExamples:\n- reverse_string('abc') -> 'cba'\n- reverse_string('') -> ''",
            "starter_code": "def reverse_string(s: str) -> str:\n    # TODO: implement\n    pass\n",
            "solution": "def reverse_string(s: str) -> str:\n    return s[::-1]\n",
        },
        {
            "id": "js_fizzbuzz",
            "track": "JavaScript",
            "language": "javascript",
            "title": "FizzBuzz",
            "prompt": "Write a function `fizzBuzz(n)` that returns an array of length `n` with values from 1..n using the classic FizzBuzz rules:\n- 'Fizz' for multiples of 3\n- 'Buzz' for multiples of 5\n- 'FizzBuzz' for multiples of both\n- otherwise the number itself\n\nExample: fizzBuzz(5) -> [1,2,'Fizz',4,'Buzz']",
            "starter_code": "function fizzBuzz(n) {\n  // TODO: implement\n}\n\nmodule.exports = { fizzBuzz };\n",
            "solution": "function fizzBuzz(n) {\n  const out = [];\n  for (let i = 1; i <= n; i++) {\n    const fizz = i % 3 === 0;\n    const buzz = i % 5 === 0;\n    if (fizz && buzz) out.push('FizzBuzz');\n    else if (fizz) out.push('Fizz');\n    else if (buzz) out.push('Buzz');\n    else out.push(i);\n  }\n  return out;\n}\n\nmodule.exports = { fizzBuzz };\n",
        },
        {
            "id": "js_is_palindrome",
            "track": "JavaScript",
            "language": "javascript",
            "title": "Palindrome Check",
            "prompt": "Write a function `isPalindrome(s)` that returns true if `s` reads the same backwards. Treat the string exactly as-is (case-sensitive, spaces count).\n\nExamples:\n- isPalindrome('racecar') -> true\n- isPalindrome('Racecar') -> false\n- isPalindrome('a b a') -> true",
            "starter_code": "function isPalindrome(s) {\n  // TODO: implement\n}\n\nmodule.exports = { isPalindrome };\n",
            "solution": "function isPalindrome(s) {\n  const rev = s.split('').reverse().join('');\n  return s === rev;\n}\n\nmodule.exports = { isPalindrome };\n",
        },
    ]

try:
    # When imported as `backend` package
    from backend import llm_codequest
except Exception:
    try:
        import llm_codequest  # type: ignore
    except Exception:
        llm_codequest = None

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
    solution: str = ""

    def to_public_dict(self, *, include_solution: bool = False) -> Dict[str, Any]:
        out = {
            "id": self.id,
            "track": self.track,
            "language": self.language,
            "title": self.title,
            "prompt": self.prompt,
            "starter_code": self.starter_code,
        }
        if include_solution:
            out["solution"] = self.solution
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "track": self.track,
            "language": self.language,
            "title": self.title,
            "prompt": self.prompt,
            "starter_code": self.starter_code,
            "solution": self.solution,
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
            solution=str(data.get("solution") or ""),
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
        defaults = _get_default_challenges()
        payload = {"version": 2, "created_at": _utc_now_iso(), "challenges": defaults}
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
        return [CodeQuestChallenge.from_dict(x) for x in _get_default_challenges()]

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

    def create_session(
        self,
        user_id: str,
        track: str,
        *,
        description: Optional[str] = None,
        plan_reference: Optional[str] = None,
        difficulty: Optional[str] = None,
        concepts: Optional[List[str]] = None,
        num_challenges: Optional[int] = None,
        use_llm_generator: bool = False,
        plan_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            track_clean = str(track or "").strip()
            all_ch = [c for c in self._load_challenges() if c.track.lower() == track_clean.lower()]

            # Optional: generate a per-session set using the LLM.
            session_challenges: Dict[str, Dict[str, Any]] = {}
            if bool(use_llm_generator) and llm_codequest is not None:
                try:
                    # Derive language from track when possible.
                    language = (
                        "python"
                        if track_clean.lower() == "python"
                        else ("javascript" if track_clean.lower() in ("javascript", "js") else track_clean.lower())
                    )
                    n = int(num_challenges) if isinstance(num_challenges, int) and num_challenges > 0 else 5
                    title_seed = (description or track_clean).strip() or track_clean
                    generated = llm_codequest.generate_challenge_set(
                        title=title_seed,
                        language=language,
                        difficulty=(difficulty or "medium"),
                        concepts=concepts or [],
                        num_challenges=n,
                        description=(description or ""),
                        plan_text=(plan_text or ""),
                    )
                    for g in generated:
                        session_challenges[str(g.get("id"))] = dict(g)
                    all_ids = list(session_challenges.keys())
                except Exception:
                    logger.exception("LLM CodeQuest generation failed; falling back to default challenge bank")
                    session_challenges = {}
                    all_ids = []
            else:
                all_ids = []

            # Fallback to challenge bank.
            if not session_challenges:
                if not all_ch:
                    raise ValueError("unknown track")
                # Deterministic subset selection (keeps legacy ordering for tests)
                if isinstance(num_challenges, int) and num_challenges > 0:
                    all_ch = all_ch[: int(num_challenges)]
                all_ids = [c.id for c in all_ch]
                # Persist per-session challenge definitions (including solutions).
                session_challenges = {c.id: c.to_dict() for c in all_ch}

            # Best-effort: ensure each per-session challenge has a solution.
            if isinstance(session_challenges, dict):
                for cid in list(all_ids or []):
                    raw = session_challenges.get(cid) or {}
                    if str(raw.get("solution") or "").strip():
                        continue
                    if llm_codequest is not None:
                        try:
                            session_challenges[cid] = dict(raw)
                            session_challenges[cid]["solution"] = llm_codequest.generate_reference_solution(
                                language=str(raw.get("language") or ""),
                                prompt=str(raw.get("prompt") or ""),
                                starter_code=str(raw.get("starter_code") or ""),
                            )
                        except Exception:
                            # Keep empty solution if LLM is unavailable or fails.
                            session_challenges[cid] = dict(raw)
                            session_challenges[cid]["solution"] = ""

            desc = (description or "").strip()
            session_track = (
                str(track_clean)
                if str(track_clean).strip()
                else (all_ch[0].track if all_ch else "CodeQuest")
            )
            if session_challenges:
                try:
                    first_id = all_ids[0]
                    session_language = str((session_challenges.get(first_id) or {}).get("language") or "")
                except Exception:
                    session_language = ""
            else:
                session_language = all_ch[0].language if all_ch else ""

            title = desc[:50] + ("..." if len(desc) > 50 else "") if desc else session_track
            diff = (difficulty or "").strip().lower() or "medium"
            if diff not in ("easy", "medium", "hard"):
                diff = "medium"
            concept_list = [str(c).strip() for c in (concepts or []) if str(c).strip()]

            session_id = str(uuid.uuid4())
            created_at = _utc_now_iso()
            session = {
                "session_id": session_id,
                "user_id": user_id,
                "track": session_track,
                "language": session_language or session_track,
                "title": title,
                "description": desc,
                "difficulty": diff,
                "concepts": concept_list,
                "plan_reference": (plan_reference or "").strip() or None,
                "created_at": created_at,
                "updated_at": created_at,
                "status": "active",
                "current_index": 0,
                "challenge_ids": all_ids,
                "attempts": [],  # list of attempt dicts
                "results": {},  # challenge_id -> {passed: bool, last_submitted_at: str, attempts: int}
                "drafts": {},  # challenge_id -> code
                "session_challenges": session_challenges or {},  # per-session challenge defs (includes solutions)
            }

            user_dir = self._get_user_dir(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            self._save_session(user_id, session)
            return session

    def _get_challenge_for_session(self, session: Dict[str, Any], challenge_id: str) -> Optional[CodeQuestChallenge]:
        """Resolve a challenge either from session-specific challenges or the global bank."""
        session_bank = session.get("session_challenges") if isinstance(session, dict) else None
        if isinstance(session_bank, dict) and challenge_id in session_bank:
            try:
                return CodeQuestChallenge.from_dict(session_bank[challenge_id])
            except Exception:
                return None
        return self.get_challenge(challenge_id)

    def _challenge_is_submitted(self, session: Dict[str, Any], challenge_id: str) -> bool:
        try:
            results = (session or {}).get("results", {}) or {}
            r = results.get(challenge_id) or {}
            return int(r.get("attempts", 0) or 0) > 0
        except Exception:
            return False

    def _ensure_session_challenges(self, user_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure `session['session_challenges']` exists and contains reference solutions.

        Older sessions may not have `session_challenges` at all, and challenge definitions
        from the global bank may not include `solution`. We hydrate and persist the
        session-level bank so the frontend can display solutions for submitted/old sessions.
        """
        if not isinstance(session, dict):
            return session
        bank = session.get("session_challenges")
        ids = session.get("challenge_ids") or []
        changed = False

        if not isinstance(bank, dict):
            bank = {}
            changed = True

        for cid in ids:
            cid = str(cid)
            if cid not in bank:
                ch = self.get_challenge(cid)
                if ch:
                    bank[cid] = ch.to_dict()
                    changed = True
                else:
                    bank[cid] = {
                        "id": cid,
                        "track": session.get("track"),
                        "language": session.get("language"),
                        "title": cid,
                        "prompt": "",
                        "starter_code": "",
                        "solution": "",
                    }
                    changed = True

            # Ensure solution exists.
            try:
                existing_solution = str((bank.get(cid) or {}).get("solution") or "")
            except Exception:
                existing_solution = ""

            if not existing_solution:
                # Best-effort: generate a solution via LLM if available.
                if llm_codequest is not None:
                    try:
                        bank[cid]["solution"] = llm_codequest.generate_reference_solution(
                            language=str((bank[cid] or {}).get("language") or session.get("language") or ""),
                            prompt=str((bank[cid] or {}).get("prompt") or ""),
                            starter_code=str((bank[cid] or {}).get("starter_code") or ""),
                        )
                        changed = True
                    except Exception:
                        logger.debug("Failed to generate reference solution for %s", cid)
                        bank[cid]["solution"] = ""
                        changed = True

        session["session_challenges"] = bank
        if changed:
            session["updated_at"] = _utc_now_iso()
            try:
                self._save_session(user_id, session)
            except Exception:
                logger.debug("Failed to persist hydrated session_challenges")
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
                        "title": s.get("title"),
                        "difficulty": s.get("difficulty"),
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
        session = self._load_session(user_id, session_id)
        if not session:
            return None
        # Hydrate and persist missing session_challenges/solutions for legacy sessions.
        return self._ensure_session_challenges(user_id, session)

    def get_current_challenge_public(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ids = session.get("challenge_ids") or []
        idx = int(session.get("current_index", 0))
        if idx < 0 or idx >= len(ids):
            return None
        ch = self._get_challenge_for_session(session, ids[idx])
        return ch.to_public_dict(include_solution=False) if ch else None

    def get_challenges_public(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the ordered list of challenges for the session (public schema)."""
        ids = session.get("challenge_ids") or []
        out: List[Dict[str, Any]] = []
        for cid in ids:
            ch = self._get_challenge_for_session(session, str(cid))
            if ch:
                out.append(ch.to_public_dict(include_solution=False))
            else:
                out.append({"id": str(cid), "title": str(cid), "prompt": "", "starter_code": "", "language": session.get("language"), "track": session.get("track")})
        return out

    def get_solution_map(self, user_id: str, session: Dict[str, Any], *, include_all: bool = False) -> Dict[str, str]:
        """Return challenge_id -> solution for the session.

        If include_all is False, only includes solutions for challenges that have been submitted.
        """
        session = self._ensure_session_challenges(user_id, session)
        bank = session.get("session_challenges") if isinstance(session, dict) else None
        if not isinstance(bank, dict):
            return {}
        out: Dict[str, str] = {}
        for cid, raw in bank.items():
            cid = str(cid)
            if not include_all and not self._challenge_is_submitted(session, cid):
                continue
            try:
                out[cid] = str((raw or {}).get("solution") or "")
            except Exception:
                out[cid] = ""
        return out

    def save_draft(self, user_id: str, session_id: str, challenge_id: str, code: str) -> Dict[str, Any]:
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                raise ValueError(f"session is not active (status={session.get('status')})")
            ids = session.get("challenge_ids") or []
            if challenge_id not in ids:
                raise ValueError("unknown challenge")
            session.setdefault("drafts", {})[challenge_id] = str(code)
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)
            return {
                "session_id": session_id,
                "challenge_id": challenge_id,
                "saved": True,
                "updated_at": session.get("updated_at"),
            }

    # ---------- Dashboard stats ----------
    def compute_user_question_stats(self, user_id: str) -> Dict[str, int]:
        """Compute aggregate question stats across all sessions for a user.

        Counts are based on `session['results']` entries.
        - answered: any challenge with a result entry
        - correct: result passed True OR status == 'passed'
        - incorrect: answered - correct
        - total_questions: sum of total challenges across sessions
        """
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return {
                "total_questions": 0,
                "answered_questions": 0,
                "correct_answers": 0,
                "incorrect_answers": 0,
            }

        total_questions = 0
        answered_questions = 0
        correct_answers = 0
        incorrect_answers = 0

        for p in user_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                ids = s.get("challenge_ids", []) or []
                total_questions += len(ids)
                results = s.get("results", {}) or {}
                for cid in ids:
                    r = results.get(cid)
                    if not r:
                        continue
                    answered_questions += 1
                    status = str(r.get("status") or "").strip().lower()
                    passed = r.get("passed")
                    is_correct = (status == "passed") or (passed is True)
                    if is_correct:
                        correct_answers += 1
                    else:
                        incorrect_answers += 1
            except Exception:
                logger.debug("Skipping unreadable session file %s", p)

        return {
            "total_questions": int(total_questions),
            "answered_questions": int(answered_questions),
            "correct_answers": int(correct_answers),
            "incorrect_answers": int(incorrect_answers),
        }

    def submit_solution(self, user_id: str, session_id: str, challenge_id: str, code: str) -> Dict[str, Any]:
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                raise ValueError(f"session is not active (status={session.get('status')})")

            session = self._ensure_session_challenges(user_id, session)

            ids = session.get("challenge_ids") or []
            idx = int(session.get("current_index", 0))
            if idx < 0 or idx >= len(ids):
                raise ValueError("session has no current challenge")
            expected_id = ids[idx]
            if challenge_id != expected_id:
                raise ValueError("challenge_id does not match current challenge")

            ch = self._get_challenge_for_session(session, challenge_id)
            if not ch:
                raise ValueError("unknown challenge")
            # Basic static validation: we cannot execute user code in the backend.
            # Instead, perform lightweight checks (e.g., ensure the submitted code defines
            # the expected symbol/function) and update status accordingly.
            def _infer_expected_symbol(challenge: CodeQuestChallenge) -> Optional[str]:
                # Prefer to inspect starter_code for a clear function name.
                try:
                    sc = (challenge.starter_code or "")
                    # Python: def name(
                    import re

                    m = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", sc)
                    if m:
                        return m.group(1)
                    # JS: function name(
                    m = re.search(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", sc)
                    if m:
                        return m.group(1)
                    # JS common export pattern: module.exports = { name }
                    m = re.search(r"module\.exports\s*=\s*\{\s*([A-Za-z_][A-Za-z0-9_]*)", sc)
                    if m:
                        return m.group(1)
                except Exception:
                    return None
                return None

            expected = _infer_expected_symbol(ch)

            ended = datetime.now(timezone.utc)
            duration_ms = 0

            attempt_id = str(uuid.uuid4())
            attempt = {
                "attempt_id": attempt_id,
                "challenge_id": challenge_id,
                "submitted_at": ended.isoformat(),
                "duration_ms": duration_ms,
                "passed": False,
                "code": code,
                "reason": None,
                "feedback": None,
            }
            session.setdefault("attempts", []).append(attempt)
            session.setdefault("drafts", {})[challenge_id] = code
            session["updated_at"] = _utc_now_iso()

            results = session.setdefault("results", {})
            prev = results.get(challenge_id) or {"attempts": 0, "passed": False}

            # Prefer LLM-based evaluation if available. This is best-effort; on any
            # failure we fall back to the simple static symbol check above.
            llm_result = None
            try:
                if llm_codequest is not None:
                    try:
                        llm_result = llm_codequest.evaluate_submission_with_llm(
                            language=str(ch.language or ""),
                            prompt=str(ch.prompt or ""),
                            code=str(code or ""),
                            solution=str(getattr(ch, "solution", "") or ""),
                        )
                    except Exception:
                        logger.exception("LLM evaluation failed; falling back to static checks")
                        llm_result = None
            except Exception:
                llm_result = None

            missing_symbol = False
            if expected and not llm_result:
                try:
                    if ch.language and "python" in (ch.language or ""):
                        if f"def {expected}(" not in code:
                            missing_symbol = True
                    else:
                        # heuristics for JS
                        if f"function {expected}(" not in code and expected not in code:
                            missing_symbol = True
                except Exception:
                    missing_symbol = False

            # Build result entry
            passed_flag = False
            new_status = "submitted"
            reason = None
            feedback = None

            if llm_result and isinstance(llm_result, dict):
                passed_flag = bool(llm_result.get("passed"))
                reason = llm_result.get("reason")
                feedback = llm_result.get("feedback")
                new_status = "passed" if passed_flag else "failed"
            else:
                if missing_symbol:
                    passed_flag = False
                    new_status = "failed"
                    reason = "missing_expected_symbol"
                else:
                    # Deterministic fallback: if the expected symbol exists, treat as a pass.
                    # This keeps CodeQuest usable even without an LLM, while still enforcing
                    # a minimal requirement (the correct function/module export is present).
                    passed_flag = True
                    new_status = "passed"
                    feedback = "Submission recorded. (Auto-pass: expected function detected.)"

                    # Persist per-attempt result fields (used by feedback UI).
                    attempt["passed"] = bool(passed_flag)
                    attempt["reason"] = reason
                    attempt["feedback"] = feedback

            results[challenge_id] = {
                "attempts": int(prev.get("attempts", 0)) + 1,
                "passed": bool(prev.get("passed", False)) or bool(passed_flag),
                "last_submitted_at": attempt["submitted_at"],
                "status": new_status,
                "reason": reason,
                "feedback": feedback,
                "manual": False,
            }

            # We do not auto-advance the session because no evaluation occurs here.
            next_challenge: Optional[Dict[str, Any]] = None
            finished = False

            self._save_session(user_id, session)

            out = {
                "session_id": session_id,
                "track": session.get("track"),
                "status": session.get("status"),
                "current_index": session.get("current_index"),
                "total_challenges": len(ids),
                "challenge_id": challenge_id,
                "attempt_id": attempt_id,
                "passed": True if results[challenge_id].get("passed") else False,
                "next_challenge": next_challenge,
                "finished": finished,
                "user_code": str(code or ""),
                "solution": str(getattr(ch, "solution", "") or ""),
            }

            # Include reason/feedback when available
            if reason:
                out["reason"] = reason
            if feedback:
                out["feedback"] = feedback

            return out

    def finish_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Submit/evaluate all remaining (unsubmitted) challenges and complete the session."""
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                raise ValueError(f"session is not active (status={session.get('status')})")

            session = self._ensure_session_challenges(user_id, session)
            ids = session.get("challenge_ids") or []
            results = session.setdefault("results", {})

            for cid in ids:
                cid = str(cid)
                if self._challenge_is_submitted(session, cid):
                    continue
                ch = self._get_challenge_for_session(session, cid)
                if not ch:
                    continue
                code = str((session.get("drafts", {}) or {}).get(cid) or ch.starter_code or "")

                attempt_id = str(uuid.uuid4())
                ended = datetime.now(timezone.utc)
                attempt = {
                    "attempt_id": attempt_id,
                    "challenge_id": cid,
                    "submitted_at": ended.isoformat(),
                    "duration_ms": 0,
                    "passed": False,
                    "code": code,
                    "reason": None,
                    "feedback": None,
                }
                session.setdefault("attempts", []).append(attempt)
                session.setdefault("drafts", {})[cid] = code

                llm_result = None
                if llm_codequest is not None:
                    try:
                        llm_result = llm_codequest.evaluate_submission_with_llm(
                            language=str(ch.language or ""),
                            prompt=str(ch.prompt or ""),
                            code=str(code or ""),
                            solution=str(getattr(ch, "solution", "") or ""),
                        )
                    except Exception:
                        llm_result = None

                passed_flag = False
                reason = None
                feedback = None
                status = "submitted"
                if isinstance(llm_result, dict):
                    passed_flag = bool(llm_result.get("passed"))
                    reason = llm_result.get("reason")
                    feedback = llm_result.get("feedback")
                    status = "passed" if passed_flag else "failed"
                else:
                    # Conservative fallback for bulk finish: if no LLM, don't auto-pass.
                    passed_flag = False
                    status = "failed"
                    reason = "llm_unavailable"

                attempt["passed"] = bool(passed_flag)
                attempt["reason"] = reason
                attempt["feedback"] = feedback

                prev = results.get(cid) or {"attempts": 0, "passed": False}
                results[cid] = {
                    "attempts": int(prev.get("attempts", 0)) + 1,
                    "passed": bool(prev.get("passed", False)) or bool(passed_flag),
                    "last_submitted_at": attempt["submitted_at"],
                    "status": status,
                    "reason": reason,
                    "feedback": feedback,
                    "manual": False,
                }

            # Completed iff all challenges have been submitted at least once.
            all_submitted = all(self._challenge_is_submitted(session, str(cid)) for cid in ids)
            if all_submitted:
                session["status"] = "completed"
                session["completed_at"] = _utc_now_iso()
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)

            passed_count = sum(1 for cid in ids if bool((results.get(str(cid)) or {}).get("passed")))
            submitted_count = sum(1 for cid in ids if self._challenge_is_submitted(session, str(cid)))
            failed_count = submitted_count - passed_count

            return {
                "session_id": session_id,
                "status": session.get("status"),
                "total_challenges": len(ids),
                "submitted": int(submitted_count),
                "passed": int(passed_count),
                "failed": int(failed_count),
                "completed": bool(session.get("status") == "completed"),
            }

    def exit_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Mark a session as completed/incomplete based on submission coverage."""
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                # idempotent: return current state
                return session

            ids = session.get("challenge_ids") or []
            all_submitted = all(self._challenge_is_submitted(session, str(cid)) for cid in ids)
            session["status"] = "completed" if all_submitted else "incomplete"
            session["exited_at"] = _utc_now_iso()
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)
            return session

    # ---------- Navigation / Progress ----------
    def navigate_session(self, user_id: str, session_id: str, *, index: Optional[int] = None, direction: Optional[str] = None, challenge_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            ids = session.get("challenge_ids") or []
            if not ids:
                raise ValueError("session has no challenges")

            current = int(session.get("current_index", 0))
            next_index = current
            if isinstance(index, int):
                next_index = index
            elif challenge_id:
                try:
                    next_index = ids.index(challenge_id)
                except ValueError:
                    raise ValueError("unknown challenge_id")
            elif direction:
                d = str(direction).strip().lower()
                if d == "next":
                    next_index = current + 1
                elif d == "prev" or d == "previous":
                    next_index = current - 1
                else:
                    raise ValueError("unsupported direction")

            next_index = max(0, min(len(ids) - 1, int(next_index)))
            session["current_index"] = next_index
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)
            return session


_codequest_manager: Optional[CodeQuestManager] = None


def get_codequest_manager() -> CodeQuestManager:
    global _codequest_manager
    if _codequest_manager is None:
        _codequest_manager = CodeQuestManager()
    return _codequest_manager
