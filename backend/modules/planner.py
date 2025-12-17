"""
Planner module for TAI Tutor AI.

This module handles learning plan generation and storage.
Uses file-backed storage and Ollama LLM for plan generation.
"""

import os
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

# Import with fallback for running as script
try:
    from config import (
        PLAN_MODEL,
        PLAN_TEMPERATURE,
        PLAN_MAX_TOKENS,
        PLANNER_STORE,
        DEFAULT_TIMEOUT,
    )
    from prompts.planner_prompts import build_plan_prompt, generate_fallback_plan
except ImportError:
    from config import (
        PLAN_MODEL,
        PLAN_TEMPERATURE,
        PLAN_MAX_TOKENS,
        PLANNER_STORE,
        DEFAULT_TIMEOUT,
    )
    from prompts.planner_prompts import build_plan_prompt, generate_fallback_plan

logger = logging.getLogger("backend.modules.planner")

# Try to import Ollama
try:
    from llama_index.llms.ollama import Ollama
except ImportError:
    Ollama = None


class Plan(BaseModel):
    """
    Plan model used for generation and storage.
    
    Attributes:
        plan_id: Unique identifier
        user_id: Owner/creator id
        timestamp: Creation or last-update time (UTC)
        plan_text: The generated plan content (plain text)
    """
    plan_id: str
    user_id: str
    timestamp: datetime
    plan_text: str


class Planner:
    """
    Simple file-backed planner store with generation helpers.
    
    Storage format (JSON): {"counter": int, "plans": {plan_id: {plan fields}}}
    """

    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file
        self._plans: Dict[str, Plan] = {}
        self._counter = 0
        if self.storage_file:
            self._load()

    def _load(self):
        """Load plans from storage file."""
        try:
            p = Path(self.storage_file)
            if not p.exists():
                return
            raw = json.loads(p.read_text(encoding="utf-8"))
            self._counter = int(raw.get("counter", 0) or 0)
            plans = raw.get("plans", {}) or {}
            for pid, pdata in plans.items():
                try:
                    self._plans[pid] = Plan.parse_obj(pdata)
                except Exception:
                    continue
        except Exception:
            self._plans = {}
            self._counter = 0

    def _save(self):
        """Save plans to storage file."""
        if not self.storage_file:
            return
        try:
            p = Path(self.storage_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {"counter": self._counter, "plans": {}}
            for pid, plan in self._plans.items():
                try:
                    data["plans"][pid] = plan.model_dump()
                except Exception:
                    data["plans"][pid] = getattr(plan, "__dict__", {})
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def create_plan(self, user_id: str, plan_text: str) -> Plan:
        """Create a new plan."""
        self._counter += 1
        pid = f"plan-{self._counter}"
        now = datetime.now(timezone.utc)
        plan = Plan(plan_id=pid, user_id=user_id, timestamp=now, plan_text=plan_text)
        self._plans[pid] = plan
        self._save()
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def update_plan(self, plan_id: str, new_text: str) -> Optional[Plan]:
        """Update a plan's text."""
        p = self._plans.get(plan_id)
        if not p:
            return None
        p.plan_text = new_text
        p.timestamp = datetime.now(timezone.utc)
        self._save()
        return p

    def list_plans_for_user(self, user_id: str) -> List[Plan]:
        """List all plans for a user."""
        return [p for p in self._plans.values() if p.user_id == user_id]


def generate_plan(
    user_id: str,
    requirement: str,
    original_plan: Optional[str] = None,
    edit_instructions: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = PLAN_TEMPERATURE,
    max_tokens: int = PLAN_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT
) -> str:
    """
    Generate plan text using Ollama.
    
    Falls back to a deterministic template when Ollama is unavailable.
    
    Args:
        user_id: User identifier
        requirement: Learning requirement/goal
        original_plan: Previous plan for iteration
        edit_instructions: Specific editing instructions
        model: Ollama model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens
        timeout: Request timeout
    
    Returns:
        Generated plan text
    """
    prompt = build_plan_prompt(
        requirement=requirement,
        user_id=user_id,
        original_plan=original_plan,
        edit_instructions=edit_instructions
    )
    
    # Fallback if Ollama not available
    if Ollama is None:
        logger.info("Ollama not available, using fallback plan generator")
        return generate_fallback_plan(
            requirement=requirement,
            user_id=user_id,
            original_plan=original_plan,
            edit_instructions=edit_instructions
        )

    try:
        model_name = model or PLAN_MODEL
        llm = Ollama(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=timeout
        )
        
        # Call LLM
        if hasattr(llm, "complete"):
            resp = llm.complete(prompt)
            out = str(resp)
        elif hasattr(llm, "generate"):
            resp = llm.generate(prompt)
            out = str(resp)
        elif callable(llm):
            out = str(llm(prompt))
        else:
            out = ""

        # Sanitize placeholder patterns
        if not out or "[insert" in out or "insert relevant" in out or len(out.strip()) < 60:
            return generate_fallback_plan(
                requirement=requirement,
                user_id=user_id,
                original_plan=original_plan,
                edit_instructions=edit_instructions
            )

        # Simple cleanup
        cleaned = out.replace("[insert relevant field]", requirement)
        cleaned = cleaned.replace("[insert relevant topic]", requirement)
        cleaned = cleaned.replace("[insert scenario]", "a relevant example scenario")
        cleaned = cleaned.replace("[insert example]", "an example")
        
        return cleaned
    except Exception:
        logger.exception("Plan generation failed, using fallback")
        return generate_fallback_plan(
            requirement=requirement,
            user_id=user_id,
            original_plan=original_plan,
            edit_instructions=edit_instructions
        )


# Module-level planner instance
default_planner = Planner(storage_file=PLANNER_STORE) if PLANNER_STORE else Planner(storage_file=None)
