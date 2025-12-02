import pytest
from backend.planner import Planner


def test_planner_create_and_get():
    p = Planner()
    plan = p.create_plan(user_id="u1", plan_text="Initial plan for python lists")
    assert plan.plan_id.startswith("plan-")
    got = p.get_plan(plan.plan_id)
    assert got is not None
    assert got.user_id == "u1"


def test_list_plans_for_user():
    p = Planner()
    p.create_plan(user_id="u2", plan_text="plan a")
    p.create_plan(user_id="u2", plan_text="plan b")
    plans = p.list_plans_for_user("u2")
    assert len(plans) == 2
