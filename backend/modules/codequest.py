"""
CodeQuest module for TAI Tutor AI.

This module handles CodeQuest challenge management, sessions, and evaluation.
Uses file-backed storage and LLM for challenge generation and evaluation.

Storage layout:
user_data/codequest/
  challenges.json
  sessions/<safe_user_id>/<session_id>.json
"""

import json
import logging
import os
import threading
import uuid
import re
import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import with fallback for running as script
try:
    from config import CODEQUEST_STORE_DIR
    from prompts.codequest_prompts import get_default_challenges
except ImportError:
    from config import CODEQUEST_STORE_DIR
    from prompts.codequest_prompts import get_default_challenges

logger = logging.getLogger("backend.modules.codequest")


def _utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _safe_user_dir_component(user_id: str) -> str:
    """Sanitize user ID for filesystem usage."""
    return user_id.replace("@", "__at__").replace(".", "__dot__")


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON atomically using temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


# =============================================================================
# LLM Helper Implementation (embedded from OLD BACKEND/llm_codequest.py)
# Provides: generate_challenge_set, generate_reference_solution,
#           evaluate_submission_with_llm and LLM_AVAILABLE flag.
# This is best-effort and will silently disable itself if Ollama or
# environment flags are not present.
# =============================================================================

llm_logger = logging.getLogger("backend.llm_codequest")

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover
    ollama = None


CODEQUEST_GENERATOR_MODEL = os.environ.get("CODEQUEST_GENERATOR_MODEL", "codellama:34b ")
CODEQUEST_SUBMIT_MODEL = os.environ.get("CODEQUEST_SUBMIT_MODEL", "gpt-oss:20b")

CODEQUEST_LLM_ENABLED = os.environ.get("CODEQUEST_LLM_ENABLED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _ensure_available() -> None:
    if not CODEQUEST_LLM_ENABLED:
        raise RuntimeError("CODEQUEST_LLM_ENABLED is false")
    if ollama is None:
        raise RuntimeError("Ollama python package is not available")


def _chat(model: str, system: str, user: str, *, temperature: float = 0.1) -> str:
    _ensure_available()
    try:
        resp = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options={"temperature": float(temperature)},
        )
    except Exception as e:  # pragma: no cover - defensive error handling
        # Provide a clearer error when Ollama returns an unauthorized response.
        msg = str(e or "")
        status = getattr(e, "status_code", None)
        if status == 401 or "unauthorized" in msg.lower():
            llm_logger.error(
                "Ollama API returned 401 Unauthorized. If your Ollama server requires an API key, set the OLLAMA_API_KEY environment variable (export OLLAMA_API_KEY=...) or configure Ollama server auth.")
            # Raise a readable error for callers which already handle failures and fallbacks
            raise RuntimeError(
                "Ollama returned 401 Unauthorized. Set OLLAMA_API_KEY or check Ollama server authentication."
            ) from e
        # Re-raise other exceptions
        raise

    try:
        return (resp or {}).get("message", {}).get("content", "") or ""
    except Exception:
        return ""


def generate_challenge_set(
    *,
    title: str,
    language: str,
    difficulty: str,
    concepts: Optional[List[str]] = None,
    num_challenges: int = 5,
    description: str = "",
    plan_text: str = "",
) -> List[Dict[str, Any]]:
    """Generate a list of challenges as JSON dictionaries.

    Returns a list of dicts with keys:
    id, track, language, title, prompt, starter_code

    The generator MAY also include:
    - solution: a reference solution (code) for the challenge
    """
    lang = (language or "").strip().lower()
    track = "Python" if "python" in lang else ("JavaScript" if "javascript" in lang or lang == "js" else language)
    system = (
        "You generate programming challenges for an educational product called CodeQuest. "
        "Return ONLY valid JSON. Do not include markdown fences."
    )

    user = {
        "task": "Generate a CodeQuest challenge set",
        "constraints": {
            "num_challenges": int(num_challenges),
            "difficulty": str(difficulty),
            "language": lang,
            "track": track,
            "ids": "ids must be unique, lowercase, and URL-safe",
            "starter_code": "include minimal starter_code with TODOs but syntactically valid",
            "solution": "include a correct reference solution as code (no markdown fences)",
        },
        "inputs": {
            "title": str(title),
            "description": str(description or ""),
            "concepts": [str(c) for c in (concepts or [])],
            "plan_text": str(plan_text or ""),
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "track", "language", "title", "prompt", "starter_code"],
                "optional": ["solution"],
            },
        },
    }

    raw = _chat(
        CODEQUEST_GENERATOR_MODEL,
        system,
        json.dumps(user, ensure_ascii=False),
        temperature=0.2,
    )

    def _extract_json_block(s: str) -> Optional[str]:
        """Try to extract the first JSON object/array block from s.

        Returns the substring if found, else None.
        This is a lightweight parser that respects double-quoted strings.
        """
        if not s:
            return None
        # find first opening brace or bracket
        idx_br = s.find("[")
        idx_bc = s.find("{")
        if idx_br == -1 and idx_bc == -1:
            return None
        if idx_br == -1:
            start = idx_bc
            open_ch = "{"
            close_ch = "}"
        elif idx_bc == -1:
            start = idx_br
            open_ch = "["
            close_ch = "]"
        else:
            # choose the earliest
            if idx_br < idx_bc:
                start = idx_br
                open_ch = "["
                close_ch = "]"
            else:
                start = idx_bc
                open_ch = "{"
                close_ch = "}"

        in_str = False
        esc = False
        depth = 0
        for i in range(start, len(s)):
            ch = s[i]
            if ch == '"' and not esc:
                in_str = not in_str
            if ch == "\\" and not esc:
                esc = True
                continue
            esc = False

            if in_str:
                continue

            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        return None

    def _remove_trailing_commas(s: str) -> str:
        # remove trailing commas before } or ]
        s = re.sub(r",\s*(?=[}\]])", "", s)
        return s

    parsed = None
    # 1) Try direct parse
    try:
        parsed = json.loads(raw)
    except Exception as e1:
        llm_logger.debug("Direct json.loads failed: %s", e1)
        # 2) try to extract json block
        candidate = _extract_json_block(raw)
        if candidate:
            try:
                parsed = json.loads(candidate)
            except Exception as e2:
                llm_logger.debug("json.loads on extracted block failed: %s", e2)
                # 3) try cleaning trailing commas
                try:
                    cleaned = _remove_trailing_commas(candidate)
                    parsed = json.loads(cleaned)
                except Exception as e3:
                    llm_logger.debug("json.loads after removing trailing commas failed: %s", e3)
                    # 4) try ast.literal_eval after small replacements (null/true/false)
                    try:
                        alt = candidate.replace("null", "None").replace("true", "True").replace("false", "False")
                        parsed = ast.literal_eval(alt)
                    except Exception as e4:
                        llm_logger.debug("ast.literal_eval fallback failed: %s", e4)
        else:
            llm_logger.debug("No JSON block found in LLM output to attempt recovery")

    if parsed is None:
        # Provide some context in the error to help debugging LLM outputs (truncate raw)
        sample = (raw or "")[:4000]
        raise ValueError(f"LLM did not return valid JSON after recovery attempts. Raw output (truncated): {sample}")

    # If parsed is a string (e.g., the LLM returned a quoted JSON blob), try to
    # extract JSON from that string and parse again.
    if isinstance(parsed, str):
        llm_logger.debug("Parsed value is a string; attempting to extract JSON from it")
        candidate = _extract_json_block(parsed)
        if candidate:
            try:
                parsed = json.loads(candidate)
                llm_logger.debug("Successfully parsed JSON extracted from string")
            except Exception as e:
                llm_logger.debug("Failed to json.loads extracted candidate from parsed string: %s", e)
                try:
                    cleaned = _remove_trailing_commas(candidate)
                    parsed = json.loads(cleaned)
                    llm_logger.debug("Successfully parsed JSON after cleaning trailing commas")
                except Exception:
                    try:
                        alt = candidate.replace("null", "None").replace("true", "True").replace("false", "False")
                        parsed = ast.literal_eval(alt)
                        llm_logger.debug("Successfully parsed JSON via ast.literal_eval fallback")
                    except Exception:
                        llm_logger.debug("All fallbacks failed for parsed string candidate")

    # If parsed is a list but contains non-dict items (e.g., strings), try to coerce
    # them into minimal challenge dicts so downstream code can proceed.
    if isinstance(parsed, list) and parsed:
        if not all(isinstance(x, dict) for x in parsed):
            # If items are strings, convert to dicts with title=id
            if all(isinstance(x, str) for x in parsed):
                def _slug(s: str) -> str:
                    s2 = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")
                    return s2.lower() or "challenge"

                coerced: List[Dict[str, Any]] = []
                seen_ids = set()
                for idx, title in enumerate(parsed):
                    base = _slug(title)
                    cid = base
                    # ensure uniqueness
                    i = 1
                    while cid in seen_ids:
                        i += 1
                        cid = f"{base}-{i}"
                    seen_ids.add(cid)
                    coerced.append(
                        {
                            "id": cid,
                            "track": track,
                            "language": lang,
                            "title": title,
                            "prompt": title,
                            "starter_code": "",
                        }
                    )
                llm_logger.debug("Coerced list-of-strings into list-of-dicts with %d items", len(coerced))
                parsed = coerced

    # If the model returned a dict that wraps the list, try to find the list inside.
    if not isinstance(parsed, list) or not parsed:
        # log raw output for debugging (truncated)
        llm_logger.debug("Parsed LLM output is not a list. Type=%s", type(parsed))
        try:
            sample_raw = (raw or "")[:2000]
            llm_logger.debug("LLM raw output (truncated 2k): %s", sample_raw)
        except Exception:
            pass

        # If parsed is a dict, try to locate a list value that looks like challenges
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    llm_logger.debug("Found list under key '%s' in dict-wrapped response; using it.", k)
                    parsed = v
                    break

    if not isinstance(parsed, list) or not parsed:
        raise ValueError("LLM returned empty/non-list challenge set")

    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        cleaned.append(
            {
                "id": cid,
                "track": str(item.get("track") or track),
                "language": str(item.get("language") or lang),
                "title": str(item.get("title") or cid),
                "prompt": str(item.get("prompt") or ""),
                "starter_code": str(item.get("starter_code") or ""),
                "solution": str(item.get("solution") or ""),
            }
        )

    if len(cleaned) == 0:
        raise ValueError("LLM returned no valid challenges")

    return cleaned[: int(num_challenges)]


def generate_reference_solution(*, language: str, prompt: str, starter_code: str = "") -> str:
    """Generate a reference solution (code only) for a given challenge.

    Best-effort; callers should fall back gracefully if generation fails.
    """
    system = (
        "You write correct reference solutions for programming challenges. "
        "Return ONLY the solution code. Do not include markdown fences, explanations, or extra text."
    )
    user = (
        f"Language: {language}\n\n"
        f"Challenge prompt:\n{prompt}\n\n"
        f"Starter code (if any):\n{starter_code}\n\n"
        "Write a clean, correct solution that satisfies the prompt."
    )
    raw = _chat(CODEQUEST_GENERATOR_MODEL, system, user, temperature=0.0)
    return (raw or "").strip()


def evaluate_submission_with_llm(*, language: str, prompt: str, code: str, solution: str = "") -> Dict[str, Any]:
    """Ask the LLM to evaluate the submission and return a structured result.

    Returns a dict with keys: passed: bool, reason: str (optional), feedback: str (optional)
    This is best-effort; callers should treat failures as non-fatal and fall back.
    """
    system = (
        "You are an automated grader. Return only JSON with keys: "
        "passed (bool), reason (string, short), feedback (string, optional)."
    )
    user = (
        f"Language: {language}\n\n"
        f"Challenge prompt:\n{prompt}\n\n"
        f"Reference solution (for comparison):\n{solution}\n\n"
        f"Student submission:\n{code}\n\n"
        "Evaluate whether the submission correctly satisfies the prompt requirements. "
        "If it fails, provide a concise reason (one sentence) and an optional short feedback. "
        "Return only a JSON object."
    )
    raw = ""
    try:
        raw = _chat(CODEQUEST_SUBMIT_MODEL, system, user, temperature=0.0)
    except Exception:
        llm_logger.exception("LLM evaluation failed")
        raise

    # Attempt to extract a JSON object from the LLM reply
    try:
        # Allow for cases where the model returns code fences or surrounding text
        import re

        m = re.search(r"\{[\s\S]*\}", raw)
        json_text = m.group(0) if m else raw
        return json.loads(json_text)
    except Exception:
        # As a last resort, return a conservative failure with the raw text as reason/feedback
        return {"passed": False, "reason": "llm_parse_error", "feedback": (raw or "")}


# Flag for other code to check if LLM helpers are usable
LLM_AVAILABLE = bool(CODEQUEST_LLM_ENABLED and (ollama is not None))


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CodeQuestChallenge:
    """Represents a single CodeQuest challenge."""
    id: str
    track: str
    language: str
    title: str
    prompt: str
    starter_code: str
    solution: str = ""

    def to_public_dict(self, *, include_solution: bool = False) -> Dict[str, Any]:
        """Return public-facing dictionary (optionally with solution)."""
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
        """Return full dictionary including solution."""
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
        """Create instance from dictionary."""
        return cls(
            id=str(data.get("id")),
            track=str(data.get("track")),
            language=str(data.get("language")),
            title=str(data.get("title")),
            prompt=str(data.get("prompt")),
            starter_code=str(data.get("starter_code")),
            solution=str(data.get("solution") or ""),
        )


# =============================================================================
# CodeQuest Manager
# =============================================================================

class CodeQuestManager:
    """
    Manages CodeQuest challenges, sessions, and submissions.
    
    Uses file-backed storage with one file per session.
    """

    def __init__(self, store_dir: Optional[str] = None):
        self.store_dir = Path(store_dir or CODEQUEST_STORE_DIR)
        self._lock = threading.Lock()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._challenges_path = self.store_dir / "challenges.json"
        self._sessions_dir = self.store_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CodeQuestManager initialized with store_dir: {self.store_dir}")
        self._ensure_challenge_db()

    # -------------------------------------------------------------------------
    # Challenge Database
    # -------------------------------------------------------------------------

    def _ensure_challenge_db(self) -> None:
        """Ensure challenge database exists with defaults."""
        if self._challenges_path.exists():
            return
        defaults = get_default_challenges()
        payload = {"version": 2, "created_at": _utc_now_iso(), "challenges": defaults}
        try:
            _atomic_write_json(self._challenges_path, payload)
            logger.info("Created default CodeQuest challenge DB")
        except Exception:
            logger.exception("Failed to create default challenge DB")

    def _load_challenges(self) -> List[CodeQuestChallenge]:
        """Load all challenges from database."""
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
        """List available tracks with their languages and challenge counts."""
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
        """List challenges for a specific track."""
        challenges = self._load_challenges()
        return [c.to_public_dict() for c in challenges if c.track.lower() == track.lower()]

    def get_challenge(self, challenge_id: str) -> Optional[CodeQuestChallenge]:
        """Get a challenge by ID."""
        for c in self._load_challenges():
            if c.id == challenge_id:
                return c
        return None

    # -------------------------------------------------------------------------
    # Session Storage
    # -------------------------------------------------------------------------

    def _get_user_dir(self, user_id: str) -> Path:
        """Get user's session directory."""
        return self._sessions_dir / _safe_user_dir_component(user_id)

    def _get_session_path(self, user_id: str, session_id: str) -> Path:
        """Get path to session file."""
        return self._get_user_dir(user_id) / f"{session_id}.json"

    def _load_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from disk."""
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
        """Save session to disk."""
        p = self._get_session_path(user_id, session["session_id"])
        _atomic_write_json(p, session)

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

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
        """Create a new CodeQuest session."""
        with self._lock:
            track_clean = str(track or "").strip()
            all_ch = [c for c in self._load_challenges() if c.track.lower() == track_clean.lower()]

            session_challenges: Dict[str, Dict[str, Any]] = {}
            
            # Try LLM generation if enabled
            if use_llm_generator and LLM_AVAILABLE and generate_challenge_set is not None:
                try:
                    language = (
                        "python"
                        if track_clean.lower() == "python"
                        else ("javascript" if track_clean.lower() in ("javascript", "js") else track_clean.lower())
                    )
                    n = int(num_challenges) if isinstance(num_challenges, int) and num_challenges > 0 else 5
                    title_seed = (description or track_clean).strip() or track_clean
                    generated = generate_challenge_set(
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

            # Fallback to challenge bank
            if not session_challenges:
                if not all_ch:
                    raise ValueError("unknown track")
                if isinstance(num_challenges, int) and num_challenges > 0:
                    all_ch = all_ch[:int(num_challenges)]
                all_ids = [c.id for c in all_ch]
                session_challenges = {c.id: c.to_dict() for c in all_ch}

            # Ensure solutions exist
            if isinstance(session_challenges, dict) and LLM_AVAILABLE and generate_reference_solution is not None:
                for cid in list(all_ids or []):
                    raw = session_challenges.get(cid) or {}
                    if str(raw.get("solution") or "").strip():
                        continue
                    try:
                        session_challenges[cid] = dict(raw)
                        session_challenges[cid]["solution"] = generate_reference_solution(
                            language=str(raw.get("language") or ""),
                            prompt=str(raw.get("prompt") or ""),
                            starter_code=str(raw.get("starter_code") or ""),
                        )
                    except Exception:
                        session_challenges[cid] = dict(raw)
                        session_challenges[cid]["solution"] = ""

            # Build session metadata
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
                "attempts": [],
                "results": {},
                "drafts": {},
                "session_challenges": session_challenges or {},
            }

            user_dir = self._get_user_dir(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            self._save_session(user_id, session)
            return session

    def _get_challenge_for_session(
        self, session: Dict[str, Any], challenge_id: str
    ) -> Optional[CodeQuestChallenge]:
        """Get challenge from session or global bank."""
        session_bank = session.get("session_challenges") if isinstance(session, dict) else None
        if isinstance(session_bank, dict) and challenge_id in session_bank:
            try:
                return CodeQuestChallenge.from_dict(session_bank[challenge_id])
            except Exception:
                return None
        return self.get_challenge(challenge_id)

    def _challenge_is_submitted(self, session: Dict[str, Any], challenge_id: str) -> bool:
        """Check if challenge has been submitted."""
        try:
            results = (session or {}).get("results", {}) or {}
            r = results.get(challenge_id) or {}
            return int(r.get("attempts", 0) or 0) > 0
        except Exception:
            return False

    def _ensure_session_challenges(self, user_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure session has challenge definitions with solutions."""
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

            # Ensure solution exists
            try:
                existing_solution = str((bank.get(cid) or {}).get("solution") or "")
            except Exception:
                existing_solution = ""

            if not existing_solution and LLM_AVAILABLE and generate_reference_solution is not None:
                try:
                    bank[cid]["solution"] = generate_reference_solution(
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
        """List all sessions for a user."""
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return []

        out: List[Dict[str, Any]] = []
        for p in sorted(user_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                out.append({
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
                })
            except Exception:
                logger.debug("Skipping unreadable session file %s", p)
        return out

    def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID with hydrated challenges."""
        session = self._load_session(user_id, session_id)
        if not session:
            return None
        return self._ensure_session_challenges(user_id, session)

    def get_current_challenge_public(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current challenge for session (public view)."""
        ids = session.get("challenge_ids") or []
        idx = int(session.get("current_index", 0))
        if idx < 0 or idx >= len(ids):
            return None
        ch = self._get_challenge_for_session(session, ids[idx])
        return ch.to_public_dict(include_solution=False) if ch else None

    def get_challenges_public(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all challenges for session (public view)."""
        ids = session.get("challenge_ids") or []
        out: List[Dict[str, Any]] = []
        for cid in ids:
            ch = self._get_challenge_for_session(session, str(cid))
            if ch:
                out.append(ch.to_public_dict(include_solution=False))
            else:
                out.append({
                    "id": str(cid),
                    "title": str(cid),
                    "prompt": "",
                    "starter_code": "",
                    "language": session.get("language"),
                    "track": session.get("track")
                })
        return out

    def get_solution_map(
        self, user_id: str, session: Dict[str, Any], *, include_all: bool = False
    ) -> Dict[str, str]:
        """Get challenge ID to solution mapping."""
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

    def save_draft(
        self, user_id: str, session_id: str, challenge_id: str, code: str
    ) -> Dict[str, Any]:
        """Save code draft for a challenge."""
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

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def compute_user_question_stats(self, user_id: str) -> Dict[str, int]:
        """Compute aggregate question stats for a user."""
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

    # -------------------------------------------------------------------------
    # Submission & Evaluation
    # -------------------------------------------------------------------------

    def submit_solution(
        self, user_id: str, session_id: str, challenge_id: str, code: str
    ) -> Dict[str, Any]:
        """Submit a solution for evaluation."""
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

            # Infer expected symbol from starter code
            def _infer_expected_symbol(challenge: CodeQuestChallenge) -> Optional[str]:
                import re
                sc = challenge.starter_code or ""
                m = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", sc)
                if m:
                    return m.group(1)
                m = re.search(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", sc)
                if m:
                    return m.group(1)
                m = re.search(r"module\.exports\s*=\s*\{\s*([A-Za-z_][A-Za-z0-9_]*)", sc)
                if m:
                    return m.group(1)
                return None

            expected = _infer_expected_symbol(ch)
            ended = datetime.now(timezone.utc)

            attempt_id = str(uuid.uuid4())
            attempt = {
                "attempt_id": attempt_id,
                "challenge_id": challenge_id,
                "submitted_at": ended.isoformat(),
                "duration_ms": 0,
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

            # Try LLM evaluation
            llm_result = None
            if LLM_AVAILABLE and evaluate_submission_with_llm is not None:
                try:
                    llm_result = evaluate_submission_with_llm(
                        language=str(ch.language or ""),
                        prompt=str(ch.prompt or ""),
                        code=str(code or ""),
                        solution=str(getattr(ch, "solution", "") or ""),
                    )
                except Exception:
                    logger.exception("LLM evaluation failed; falling back to static checks")
                    llm_result = None

            # Static symbol check fallback
            missing_symbol = False
            if expected and not llm_result:
                try:
                    if ch.language and "python" in (ch.language or ""):
                        if f"def {expected}(" not in code:
                            missing_symbol = True
                    else:
                        if f"function {expected}(" not in code and expected not in code:
                            missing_symbol = True
                except Exception:
                    missing_symbol = False

            # Build result
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
                    passed_flag = True
                    new_status = "passed"
                    feedback = "Submission recorded. (Auto-pass: expected function detected.)"

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
                "next_challenge": None,
                "finished": False,
                "user_code": str(code or ""),
                "solution": str(getattr(ch, "solution", "") or ""),
            }

            if reason:
                out["reason"] = reason
            if feedback:
                out["feedback"] = feedback

            return out

    def finish_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Finish session by submitting all remaining challenges."""
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
                if LLM_AVAILABLE and evaluate_submission_with_llm is not None:
                    try:
                        llm_result = evaluate_submission_with_llm(
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
        """Exit session and mark status based on progress."""
        with self._lock:
            session = self._load_session(user_id, session_id)
            if not session:
                raise FileNotFoundError("session not found")
            if session.get("status") != "active":
                return session

            ids = session.get("challenge_ids") or []
            all_submitted = all(self._challenge_is_submitted(session, str(cid)) for cid in ids)
            session["status"] = "completed" if all_submitted else "incomplete"
            session["exited_at"] = _utc_now_iso()
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)
            return session

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def navigate_session(
        self,
        user_id: str,
        session_id: str,
        *,
        index: Optional[int] = None,
        direction: Optional[str] = None,
        challenge_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Navigate to a different challenge in the session."""
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
                elif d in ("prev", "previous"):
                    next_index = current - 1
                else:
                    raise ValueError("unsupported direction")

            next_index = max(0, min(len(ids) - 1, int(next_index)))
            session["current_index"] = next_index
            session["updated_at"] = _utc_now_iso()
            self._save_session(user_id, session)
            return session


# =============================================================================
# Module-level Singleton
# =============================================================================

_codequest_manager: Optional[CodeQuestManager] = None


def get_codequest_manager() -> CodeQuestManager:
    """Get the global CodeQuestManager singleton."""
    global _codequest_manager
    if _codequest_manager is None:
        _codequest_manager = CodeQuestManager()
    return _codequest_manager
