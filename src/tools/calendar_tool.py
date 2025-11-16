"""
Calendar Tool - ADK-compatible scheduling engine.
Provides deterministic conflict detection, event creation, and time-slot suggestions.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import threading

_LOCK = threading.Lock()


class CalendarTool:
    def __init__(self, persist_path: str = "data/calendar.json"):
        # schedule[day] = [event, event, ...]
        self.schedule: Dict[str, List[Dict[str, Any]]] = {}
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()
        # valid days in order
        self.days = [
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"
        ]

    # ---------- Persistence ----------
    def _load(self) -> None:
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.schedule = json.load(f)
            except Exception:
                # Corrupt file -> start fresh
                self.schedule = {}

    def _save(self) -> None:
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.schedule, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ------------------------------------------
    # Helper: Convert "HH:MM" → minutes
    # ------------------------------------------
    def _time_to_minutes(self, t: str) -> int:
        try:
            parts = t.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h * 60 + m
        except Exception:
            return 0

    # ------------------------------------------
    # Helper: Check overlap
    # ------------------------------------------
    def _overlaps(self, start1: int, dur1: int, start2: int, dur2: int) -> bool:
        end1 = start1 + dur1
        end2 = start2 + dur2
        return start1 < end2 and start2 < end1

    # ------------------------------------------
    # Clear full schedule
    # ------------------------------------------
    def clear_schedule(self) -> bool:
        with _LOCK:
            self.schedule = {}
            self._save()
        return True

    # ------------------------------------------
    # Detect conflicts for a specific timeslot
    # ------------------------------------------
    def detect_conflicts(
        self,
        day: str,
        start_time: str,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        if not day:
            return []
        day = str(day)
        if day not in self.schedule:
            return []

        start_min = self._time_to_minutes(start_time)
        conflicts = []

        for event in self.schedule.get(day, []):
            ev_start = self._time_to_minutes(event.get("start_time", "00:00"))
            ev_dur = int(event.get("duration_minutes", 0) or 0)

            if self._overlaps(start_min, duration_minutes, ev_start, ev_dur):
                conflicts.append(event)

        return conflicts

    # ------------------------------------------
    # Suggest a time slot (deterministic search)
    # ------------------------------------------
    def suggest_time_slot(
        self,
        day: str,
        duration_minutes: int,
        preferred_time: Optional[str] = None
    ) -> Optional[str]:
        # Default search anchors
        cand = []
        if preferred_time:
            cand.append(preferred_time)
        cand.extend(["08:00", "09:00", "10:00", "11:00", "12:30", "14:00", "16:00", "17:00", "18:00", "19:00"])

        candidate_times = [t for t in cand if t]

        for t in candidate_times:
            if not self.detect_conflicts(day, t, duration_minutes):
                return t

        # Expand search by scanning day in 30-min increments (08:00 to 20:00)
        start = 8 * 60
        end = 20 * 60
        for m in range(start, end, 30):
            tt = f"{m // 60:02d}:{m % 60:02d}"
            if not self.detect_conflicts(day, tt, duration_minutes):
                return tt

        return None  # no available time

    # ------------------------------------------
    # Create event & add safely
    # ------------------------------------------
    def create_event(
        self,
        title: str,
        start_time: str,
        duration_minutes: int,
        day: str,
        event_type: str = "task"
    ) -> Dict[str, Any]:
        if not day:
            raise ValueError("create_event: day is required")

        with _LOCK:
            if day not in self.schedule:
                self.schedule[day] = []

            event = {
                "title": title or "Event",
                "start_time": start_time or "00:00",
                "duration_minutes": int(duration_minutes or 0),
                "day": day,
                "type": event_type or "task"
            }

            self.schedule[day].append(event)
            # keep events sorted
            self.schedule[day].sort(key=lambda e: self._time_to_minutes(e.get("start_time", "00:00")))
            self._save()
        return event

    # ------------------------------------------
    # ADK-standard execution wrapper
    # ------------------------------------------
    def execute(self, action: str, **kwargs):
        action = (action or "").strip()
        if action == "clear_schedule":
            return self.clear_schedule()

        if action == "detect_conflicts":
            return self.detect_conflicts(
                kwargs.get("day", ""),
                kwargs.get("start_time", "00:00"),
                int(kwargs.get("duration_minutes", 0) or 0)
            )

        if action == "suggest_time_slot":
            return self.suggest_time_slot(
                kwargs.get("day", ""),
                int(kwargs.get("duration_minutes", 0) or 0),
                kwargs.get("preferred_time")
            )

        if action == "create_event":
            return self.create_event(
                title=kwargs.get("title", "Event"),
                start_time=kwargs.get("start_time", "00:00"),
                duration_minutes=int(kwargs.get("duration_minutes", 0) or 0),
                day=kwargs.get("day", ""),
                event_type=kwargs.get("event_type", "task")
            )

        raise ValueError(f"Unknown calendar tool action: {action}")


# Global instance
calendar_tool = CalendarTool()
