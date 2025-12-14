"""LLM helpers for CodeQuest.

This module centralizes interactions with local Ollama models for:
- Generating CodeQuest challenge sets
- Evaluating submissions

Design notes:
- All functions are best-effort: callers should treat failures as non-fatal and
    fall back to deterministic (non-executing) checks.
- This project does not execute user code or expose test cases/stdout/stderr.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import re
import ast

logger = logging.getLogger("backend.llm_codequest")

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
            logger.error(
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
        logger.debug("Direct json.loads failed: %s", e1)
        # 2) try to extract json block
        candidate = _extract_json_block(raw)
        if candidate:
            try:
                parsed = json.loads(candidate)
            except Exception as e2:
                logger.debug("json.loads on extracted block failed: %s", e2)
                # 3) try cleaning trailing commas
                try:
                    cleaned = _remove_trailing_commas(candidate)
                    parsed = json.loads(cleaned)
                except Exception as e3:
                    logger.debug("json.loads after removing trailing commas failed: %s", e3)
                    # 4) try ast.literal_eval after small replacements (null/true/false)
                    try:
                        alt = candidate.replace("null", "None").replace("true", "True").replace("false", "False")
                        parsed = ast.literal_eval(alt)
                    except Exception as e4:
                        logger.debug("ast.literal_eval fallback failed: %s", e4)
        else:
            logger.debug("No JSON block found in LLM output to attempt recovery")

    if parsed is None:
        # Provide some context in the error to help debugging LLM outputs (truncate raw)
        sample = (raw or "")[:4000]
        raise ValueError(f"LLM did not return valid JSON after recovery attempts. Raw output (truncated): {sample}")

    # If parsed is a string (e.g., the LLM returned a quoted JSON blob), try to
    # extract JSON from that string and parse again.
    if isinstance(parsed, str):
        logger.debug("Parsed value is a string; attempting to extract JSON from it")
        candidate = _extract_json_block(parsed)
        if candidate:
            try:
                parsed = json.loads(candidate)
                logger.debug("Successfully parsed JSON extracted from string")
            except Exception as e:
                logger.debug("Failed to json.loads extracted candidate from parsed string: %s", e)
                try:
                    cleaned = _remove_trailing_commas(candidate)
                    parsed = json.loads(cleaned)
                    logger.debug("Successfully parsed JSON after cleaning trailing commas")
                except Exception:
                    try:
                        alt = candidate.replace("null", "None").replace("true", "True").replace("false", "False")
                        parsed = ast.literal_eval(alt)
                        logger.debug("Successfully parsed JSON via ast.literal_eval fallback")
                    except Exception:
                        logger.debug("All fallbacks failed for parsed string candidate")

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
                logger.debug("Coerced list-of-strings into list-of-dicts with %d items", len(coerced))
                parsed = coerced

    # If the model returned a dict that wraps the list, try to find the list inside.
    if not isinstance(parsed, list) or not parsed:
        # log raw output for debugging (truncated)
        logger.debug("Parsed LLM output is not a list. Type=%s", type(parsed))
        try:
            sample_raw = (raw or "")[:2000]
            logger.debug("LLM raw output (truncated 2k): %s", sample_raw)
        except Exception:
            pass

        # If parsed is a dict, try to locate a list value that looks like challenges
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    logger.debug("Found list under key '%s' in dict-wrapped response; using it.", k)
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
        logger.exception("LLM evaluation failed")
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
