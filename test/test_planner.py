import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.planner import Planner


def test_planner_create_and_get():
    p = Planner()
    plan = p.create_plan(user_id="u1", topics=["python", "lists"], notes="start easy")
    assert plan.id.startswith("plan-")
    got = p.get_plan(plan.id)
    assert got is not None
    assert got.user_id == "u1"


def test_list_plans_for_user():
    p = Planner()
    p.create_plan(user_id="u2", topics=["a"])
    p.create_plan(user_id="u2", topics=["b"])
    plans = p.list_plans_for_user("u2")
    assert len(plans) == 2
