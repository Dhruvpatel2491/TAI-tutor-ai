from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class Plan(BaseModel):
    id: str
    user_id: str
    topics: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None



class Planner:
    """A planner for adaptive learning plans.

    By default this stores plans in-memory. If `storage_file` is provided,
    plans will be persisted to that JSON file on each write. The on-disk
    format is simple: {"counter": int, "plans": {id: plan_dict}}.
    """

    def __init__(self, storage_file: Optional[str] = None):
        self._store: Dict[str, Plan] = {}
        self._counter = 0
        self.storage_file = storage_file
        if self.storage_file:
            self._load()

    def _load(self):
        try:
            import json
            from pathlib import Path
            p = Path(self.storage_file)
            if not p.exists():
                return
            raw = json.loads(p.read_text(encoding="utf-8"))
            self._counter = int(raw.get("counter", 0))
            plans = raw.get("plans", {})
            for pid, pdata in plans.items():
                self._store[pid] = Plan.parse_obj(pdata)
        except Exception:
            # if loading fails, keep in-memory empty store
            self._store = {}
            self._counter = 0

    def _save(self):
        try:
            import json
            from pathlib import Path
            # Prefer Pydantic v2 `model_dump()` but fall back to `.dict()` for compatibility.
            plans_data = {}
            for pid, p in self._store.items():
                try:
                    plans_data[pid] = p.model_dump()
                except Exception:
                    # fallback to instance __dict__ to avoid direct `.dict()` usage
                    plans_data[pid] = getattr(p, "__dict__", {})
            data = {"counter": self._counter, "plans": plans_data}
            p = Path(self.storage_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            # non-fatal: persist best-effort
            pass

    def create_plan(self, user_id: str, topics: List[str], notes: Optional[str] = None) -> Plan:
        self._counter += 1
        pid = f"plan-{self._counter}"
        plan = Plan(id=pid, user_id=user_id, topics=topics, notes=notes)
        self._store[pid] = plan
        if self.storage_file:
            self._save()
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._store.get(plan_id)

    def list_plans_for_user(self, user_id: str) -> List[Plan]:
        return [p for p in self._store.values() if p.user_id == user_id]


# simple module-level planner instance for quick use in server prototypes
import os

# Default planner: use file-backed store if PLANNER_STORE env var provided; otherwise in-memory
_planner_store_path = os.environ.get("PLANNER_STORE")
default_planner = Planner(storage_file=_planner_store_path) if _planner_store_path else Planner()
