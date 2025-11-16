"""
Plan Evaluator – deterministic scoring for final plan.
Used by Verifier/Coordinator to provide quality metrics.
"""

from typing import Dict, Any, List


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default


def evaluate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    goals = plan.get("goals", []) or []
    tasks = plan.get("tasks", []) or []
    meal_days = plan.get("meals", []) or []
    constraints = plan.get("constraints", {}) or {}
    schedule = plan.get("schedule", {}) or {}
    budget_info = plan.get("budget", {}) or {}

    trace = {}

    # --------------------------------------------------------
    # 1. Goal satisfaction
    # --------------------------------------------------------
    hits = 0
    for g in goals:
        g = g.lower()
        task_match = any(g in (t.get("title", "").lower()) for t in tasks)
        meal_match = any(g in m.get("name", "").lower() for d in meal_days for m in d.get("meals", []))
        if task_match or meal_match:
            hits += 1

    goal_score = hits / len(goals) if goals else 0.5
    goal_score = max(0.0, min(1.0, goal_score))
    trace["goal_satisfaction"] = goal_score

    # --------------------------------------------------------
    # 2. Budget compliance
    # --------------------------------------------------------
    limit = _safe_float(constraints.get("max_budget"), None)
    actual = _safe_float(budget_info.get("total"), 0)

    if limit:
        deviation = max(0, actual - limit)
        compliance = 1.0 if deviation <= 0 else max(0.0, 1.0 - min(1.0, deviation / limit))
    else:
        deviation = 0
        compliance = 1.0

    trace["budget_deviation"] = deviation
    trace["budget_compliance"] = compliance

    # --------------------------------------------------------
    # 3. Constraint compliance
    # --------------------------------------------------------
    issues = []

    if not meal_days:
        issues.append("no meals")
    if isinstance(schedule, dict):
        has_events = any(len(v) > 0 for v in schedule.values())
    else:
        inner = schedule.get("schedule", {})
        has_events = any(len(v) > 0 for v in inner.values())

    if not has_events:
        issues.append("no events")

    if not issues:
        constraint_score = 1.0
    elif len(issues) == 1:
        constraint_score = 0.7
    else:
        constraint_score = 0.4

    trace["issues"] = issues
    trace["constraint_compliance"] = constraint_score

    # --------------------------------------------------------
    # 4. Overall score
    # --------------------------------------------------------
    overall = (
        goal_score * 0.5 +
        constraint_score * 0.3 +
        compliance * 0.2
    )
    overall = max(0.0, min(1.0, overall))

    return {
        "goal_satisfaction_score": goal_score,
        "constraint_compliance": constraint_score,
        "budget_deviation": deviation,
        "issues": issues,
        "overall_score": round(overall * 100, 2),
        "trace": trace,
    }
