"""
Scheduler Agent - Combines task/meal outputs and resolves conflicts.
Robust ADK-compatible scheduler with internal fallback when calendar_tool is not fully featured.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.utils.logger import logger

# try to import calendar_tool; use None if not present
try:
    from src.tools.calendar_tool import calendar_tool
except Exception:
    calendar_tool = None

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def time_str_to_minutes(t: str) -> int:
    try:
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def minutes_to_time_str(m: int) -> str:
    h = (m // 60) % 24
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def overlap(a_start: int, a_dur: int, b_start: int, b_dur: int) -> bool:
    a_end = a_start + a_dur
    b_end = b_start + b_dur
    return (a_start < b_end) and (b_start < a_end)


class SchedulerAgent:
    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.tool = calendar_tool
        self.time_map = {
            "morning": "09:00",
            "afternoon": "14:00",
            "evening": "18:00",
            "breakfast": "08:00",
            "lunch": "12:30",
            "dinner": "19:00"
        }

    def _suggest_time_slot(self, day: str, duration_minutes: int, preferred_time: Optional[str] = None) -> str:
        if preferred_time and ":" in preferred_time:
            return preferred_time
        if preferred_time and preferred_time in self.time_map:
            return self.time_map[preferred_time]
        idx = DAYS.index(day) if day in DAYS else 0
        base_hour = 9 + (idx % 3) * 2
        return f"{base_hour:02d}:00"

    def _detect_conflicts(self, schedule_for_day: List[Dict[str, Any]], start_time: str, duration_minutes: int) -> List[Dict[str, Any]]:
        conflicts = []
        s_min = time_str_to_minutes(start_time)
        for ev in schedule_for_day:
            ev_start = time_str_to_minutes(ev.get("start_time", "00:00"))
            ev_dur = int(ev.get("duration_minutes", 0))
            if overlap(s_min, duration_minutes, ev_start, ev_dur):
                conflicts.append(ev)
        return conflicts

    def _create_event_local(self, title: str, start_time: str, duration_minutes: int, day: str, event_type: str) -> Dict[str, Any]:
        return {
            "title": title,
            "start_time": start_time,
            "duration_minutes": int(duration_minutes),
            "day": day,
            "type": event_type
        }

    def create_schedule(self, tasks: List[Dict[str, Any]], meal_plan: List[Dict[str, Any]], plan_days: int = 7) -> Dict[str, Any]:
        logger.log_event("SchedulerAgent", "create_schedule_start",
                         {"task_count": len(tasks), "meal_days": len(meal_plan), "plan_days": plan_days}, self.session_id)

        # limit to 7 days only
        days = DAYS[:max(1, min(7, plan_days))]
        schedule: Dict[str, List[Dict[str, Any]]] = {d: [] for d in days}
        conflicts_resolved = 0

        # Normalize tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            task_list = tasks.get("tasks", [])
        elif isinstance(tasks, list):
            task_list = tasks
        else:
            task_list = []

        # Normalize meals
        if isinstance(meal_plan, dict) and "meal_plan" in meal_plan:
            meal_days = meal_plan.get("meal_plan", [])
        elif isinstance(meal_plan, list):
            meal_days = meal_plan
        else:
            meal_days = []

        # Schedule tasks
        if task_list:
            n_tasks = len(task_list)
            per_day = n_tasks // len(days)
            remainder = n_tasks % len(days)
            t_idx = 0

            for i, day in enumerate(days):
                count = per_day + (1 if i < remainder else 0)
                for _ in range(count):
                    if t_idx >= n_tasks:
                        break
                    t = task_list[t_idx]
                    t_idx += 1

                    preferred_block = t.get("preferred_time_block", "morning")
                    preferred_start = self.time_map.get(
                        preferred_block,
                        self._suggest_time_slot(day, t.get("duration_minutes", 60), preferred_block)
                    )
                    duration = int(t.get("duration_minutes", 60))

                    conflicts = self._detect_conflicts(schedule[day], preferred_start, duration)
                    if conflicts:
                        start_minutes = time_str_to_minutes(preferred_start)
                        shifted = False
                        for shift in range(1, 6):
                            cand = minutes_to_time_str(start_minutes + shift * 60)
                            if not self._detect_conflicts(schedule[day], cand, duration):
                                preferred_start = cand
                                shifted = True
                                conflicts_resolved += 1
                                break
                        if not shifted:
                            conflicts_resolved += len(conflicts)

                    event = self._create_event_local(
                        t.get("title", "Task"),
                        preferred_start,
                        duration,
                        day,
                        "task"
                    )
                    schedule[day].append(event)

        # Schedule meals
        for md in meal_days:
            # Resolve day name
            day = md.get("day") or md.get("day_name")
            if not day:
                idx = md.get("day_index", 1)
                if isinstance(idx, int) and 1 <= idx <= len(days):
                    day = days[idx - 1]
                else:
                    day = days[0]

            meals = md.get("meals", []) or []
            for meal in meals:
                m_type = meal.get("type", "dinner")
                start_time = self.time_map.get(m_type, "19:00")
                duration = int(meal.get("duration_minutes", 30)) if meal.get("duration_minutes") else 30

                conflicts = self._detect_conflicts(schedule[day], start_time, duration)
                if conflicts:
                    base = time_str_to_minutes(start_time)
                    shifted = False
                    for shift in [30, -30, 60, -60]:
                        cand = minutes_to_time_str(base + shift)
                        if not self._detect_conflicts(schedule[day], cand, duration):
                            start_time = cand
                            conflicts_resolved += 1
                            shifted = True
                            break
                    if not shifted:
                        conflicts_resolved += len(conflicts)

                event = self._create_event_local(
                    f"{meal.get('name','Meal')} ({m_type})",
                    start_time,
                    duration,
                    day,
                    "meal"
                )
                schedule[day].append(event)

        # Sort events
        for day in schedule:
            schedule[day].sort(key=lambda e: time_str_to_minutes(e.get("start_time", "00:00")))

        total_events = sum(len(ev) for ev in schedule.values())

        logger.log_event("SchedulerAgent", "schedule_created",
                         {"total_events": total_events, "conflicts_resolved": conflicts_resolved}, self.session_id)

        # IMPORTANT: Return FLAT structure!
        return {
            "schedule": schedule,
            "conflicts_resolved": conflicts_resolved,
            "total_events": total_events
        }

    def process(self, task_data: Any, meal_data: Any, intent_data: Any) -> Dict[str, Any]:

        tasks = task_data.get("tasks") if isinstance(task_data, dict) else []
        meal_plan = meal_data.get("meal_plan") if isinstance(meal_data, dict) else []

        if isinstance(intent_data, dict) and "intent" in intent_data:
            intent = intent_data["intent"]
        else:
            intent = {}

        plan_days = int(intent.get("plan_duration_days") or intent.get("plan_days") or 7)

        result = self.create_schedule(tasks, meal_plan, plan_days)

        # FINAL FIX: Flatten output
        return {
            "schedule": result["schedule"],
            "conflicts_resolved": result["conflicts_resolved"],
            "total_events": result["total_events"],
            "agent": "SchedulerAgent",
            "status": "success"
        }
