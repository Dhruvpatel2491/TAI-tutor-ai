from typing import Optional, Dict
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # attempt to import Ollama wrapper used by server (llama-index Ollama)
    from llama_index.llms.ollama import Ollama  # type: ignore
except Exception:
    Ollama = None  # we'll raise at call time if LLM is required but missing


class Plan(BaseModel):
    """Plan model used for generation and storage.

    Fields:
    - plan_id: unique id assigned by planner store
    - user_id: owner/creator id
    - timestamp: creation or last-update time (UTC)
    - plan_text: the generated plan content (plain text)

    Note: This project no longer uses 'topics' or 'hint' templates for plan
    generation. Plans are generated from a single 'requirement' string and
    produced by calling a generative Ollama model via `generate_plan`.
    """
    plan_id: str
    user_id: str
    timestamp: datetime
    plan_text: str


class Planner:
    """Simple file-backed planner store + generation helpers.

    Storage format (JSON): {"counter": int, "plans": {plan_id: {plan fields}}}
    """

    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file
        self._plans: Dict[str, Plan] = {}
        self._counter = 0
        if self.storage_file:
            self._load()

    def _load(self):
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
                    # best-effort: skip invalid entries
                    continue
        except Exception:
            self._plans = {}
            self._counter = 0

    def _save(self):
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
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def create_plan(self, user_id: str, plan_text: str) -> Plan:
        self._counter += 1
        pid = f"plan-{self._counter}"
        now = datetime.now(timezone.utc)
        plan = Plan(plan_id=pid, user_id=user_id, timestamp=now, plan_text=plan_text)
        self._plans[pid] = plan
        self._save()
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def update_plan(self, plan_id: str, new_text: str) -> Optional[Plan]:
        p = self._plans.get(plan_id)
        if not p:
            return None
        p.plan_text = new_text
        p.timestamp = datetime.now(timezone.utc)
        self._save()
        return p

    def list_plans_for_user(self, user_id: str):
        return [p for p in self._plans.values() if p.user_id == user_id]


def _default_plan_prompt(requirement: str, user_id: str, original_plan: Optional[str] = None, edit_instructions: Optional[str] = None) -> str:
    """Construct a single, consistent plan prompt for the generative model."""
    base = (
        "You are an expert tutoring assistant focused on creating short, actionable study plans tailored to the user's stated need.\n"
        "Produce a well-structured plan that a learner can follow immediately. Include the following sections with clear headings:\n"
        "- Title (1 line)\n"
        "- Learning Objectives (3-5 concise objectives)\n"
        "- Suggested Schedule (total duration and a minute-by-minute or block schedule)\n"
        "- Exercises (3 concrete practice activities with expected time and deliverable)\n"
        "- Quick Self-Check Questions (3 questions, with one 'stretch' question)\n"
        "- Recommended Resources (2-4 short links or resource descriptions)\n"
        "- Tips for Study (2-4 tactical tips)\n\n"
        "When you must reference a placeholder field, replace it with a sensible concrete value derived from the requirement (do not emit '[insert ...]').\n"
        "Be explicit and concrete: use the requirement text to fill blanks, choose realistic times, and name one example exercise tied to the topic.\n\n"
        "Requirement: {requirement}\n"
        "User: {user_id}\n\n"
    )
    prompt = base.format(requirement=requirement.strip(), user_id=user_id)
    if original_plan:
        prompt += "Previous plan:\n" + original_plan + "\n\n"
    if edit_instructions:
        prompt += "Edit instructions: " + edit_instructions + "\n\n"
    prompt += "Return only the plan text in plain text with headings. Keep the whole plan under 1000 words."
    return prompt


def _generate_plan_fallback(requirement: str, user_id: str, original_plan: Optional[str] = None, edit_instructions: Optional[str] = None) -> str:
    """Deterministic fallback plan generator used when an LLM isn't available or to post-process LLM output.

    The goal is to return a fully-populated, concrete plan that avoids placeholders like
    '[insert relevant field]'. This uses simple heuristics and templates derived from the requirement.
    """


    logger.info("Fallback plan generator triggered due to missing or unavailable LLM.")
    topic = requirement.strip() or "the requested topic"
    # Build a title
    title = f"Study Plan: {topic[:60]}"

    # Derive simple objectives by splitting requirement on common separators or by rephrasing
    objectives = []
    if ":" in topic or "-" in topic:
        parts = [p.strip() for p in topic.replace('-', ':').split(':') if p.strip()]
        for p in parts[:4]:
            objectives.append(f"Understand and apply: {p}")
    else:
        objectives = [
            f"Understand the core concepts of {topic}",
            f"Be able to explain key use-cases and limitations of {topic}",
            f"Apply {topic} in a simple example or exercise",
        ]

    # Suggested schedule: default to 60 minutes if not specified
    total_minutes = 60
    schedule_blocks = [
        (5, "Introduction: goals & quick review"),
        (20, "Direct instruction: concise reading or short video on the topic"),
        (15, "Guided practice: worked examples and walkthroughs"),
        (10, "Independent practice: try a short problem"),
        (10, "Reflection & self-check questions")
    ]

    # Exercises
    exercises = [
        {
            "title": f"Example problem applying {topic}",
            "time": "15 minutes",
            "task": f"Solve a short problem that requires using {topic}. Write the steps and final answer."
        },
        {
            "title": "Teaching exercise",
            "time": "10 minutes",
            "task": f"Summarize {topic} in your own words as if teaching a peer (3-5 sentences)."
        },
        {
            "title": "Extension challenge",
            "time": "15 minutes",
            "task": f"Modify the example to a slightly harder version and describe the differences in approach."
        }
    ]

    # Self-check questions
    self_checks = [
        f"What is the primary purpose of {topic}?",
        f"How would you choose an approach or technique when solving a problem involving {topic}?",
        f"Stretch: Describe a real-world scenario where {topic} is useful and why."
    ]

    # Resources - use requirement as a hint; prefer non-link placeholders to avoid invalid links
    resources = [
        f"Official intro or documentation about {topic} (search for '{topic} tutorial' or relevant docs)",
        f"A short video or article that gives a worked example of {topic}",
    ]

    tips = [
        "Take short notes and summarize after each block.",
        "Use active recall: try answering the self-checks without notes.",
        "If stuck, break the problem into smaller sub-steps and re-check assumptions."
    ]

    # Construct plain-text plan
    parts = []
    parts.append(title)
    parts.append("\nLearning Objectives:")
    for obj in objectives:
        parts.append(f"- {obj}")

    parts.append(f"\nSuggested Schedule ({total_minutes} minutes):")
    for m, desc in schedule_blocks:
        parts.append(f"- {m} minutes — {desc}")

    parts.append("\nExercises:")
    for ex in exercises:
        parts.append(f"- {ex['title']} ({ex['time']}): {ex['task']}")

    parts.append("\nQuick Self-Check Questions:")
    for q in self_checks:
        parts.append(f"- {q}")

    parts.append("\nRecommended Resources:")
    for r in resources:
        parts.append(f"- {r}")

    parts.append("\nTips for Study:")
    for t in tips:
        parts.append(f"- {t}")

    # If there is an original plan and edit instructions, append a small note
    if original_plan:
        parts.append("\nNote: This plan was generated from the user's requirement; see previous plan below for comparison.")
        parts.append(original_plan)
    if edit_instructions:
        parts.append(f"\nEdit instructions applied: {edit_instructions}")

    return "\n".join(parts)


def generate_plan(user_id: str, requirement: str, original_plan: Optional[str] = None, edit_instructions: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.15, max_tokens: int = 1024, timeout: int = 300) -> str:
    """Generate plan text using Ollama. Falls back to a simple deterministic template when Ollama is unavailable."""
    prompt = _default_plan_prompt(requirement=requirement, user_id=user_id, original_plan=original_plan, edit_instructions=edit_instructions)
    # Attempt to call Ollama via llama-index Ollama wrapper when available
    if Ollama is None:
        # LLM not installed: return a deterministic, fully-populated fallback plan
        return _generate_plan_fallback(requirement=requirement, user_id=user_id, original_plan=original_plan, edit_instructions=edit_instructions)

    try:
        model_name = model or os.environ.get("PLAN_MODEL") or os.environ.get("OLLAMA_LLM")
        # instantiate a per-request Ollama
        llm = Ollama(model=model_name, temperature=temperature, max_tokens=max_tokens, request_timeout=timeout)
        # many Ollama wrappers provide `complete` or `generate` — use complete if available
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

        # sanitize obvious placeholder patterns that some templates emit like '[insert ...]'
        if not out or "[insert" in out or "insert relevant" in out or len(out.strip()) < 60:
            # fall back to deterministic generator to ensure populated plan
            return _generate_plan_fallback(requirement=requirement, user_id=user_id, original_plan=original_plan, edit_instructions=edit_instructions)

        # Simple cleanup: replace common placeholder tokens with the requirement
        cleaned = out.replace("[insert relevant field]", requirement).replace("[insert relevant topic]", requirement)
        cleaned = cleaned.replace("[insert scenario]", "a relevant example scenario").replace("[insert example]", "an example")
        return cleaned
    except Exception:
        # if generation fails, return the prompt so UI/developers see useful text
        try:
            return _generate_plan_fallback(requirement=requirement, user_id=user_id, original_plan=original_plan, edit_instructions=edit_instructions)
        except Exception:
            return ""


# module-level planner instance
_planner_store_path = os.environ.get("PLANNER_STORE")
default_planner = Planner(storage_file=_planner_store_path) if _planner_store_path else Planner(storage_file=None)
