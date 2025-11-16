"""
Structured logging utility for all agents.
Creates JSONL logs per session and keeps in-memory traces.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import threading

_LOCK = threading.Lock()


class Logger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.session_logs: Dict[str, List[Dict[str, Any]]] = {}

    # ---------------------------------------------------------
    # log_event()
    # ---------------------------------------------------------
    def log_event(
        self,
        agent: str,
        step: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:

        event = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "step": step,
            "data": data,
            "session_id": session_id
        }

        # in-memory
        if session_id:
            if session_id not in self.session_logs:
                self.session_logs[session_id] = []
            self.session_logs[session_id].append(event)

        # disk write
        with _LOCK:
            log_file = self.log_dir / f"{session_id or 'default'}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    # ---------------------------------------------------------
    def trace_session(self, session_id: str) -> List[Dict[str, Any]]:
        return self.session_logs.get(session_id, [])

    # ---------------------------------------------------------
    def get_all_sessions(self) -> List[str]:
        return list(self.session_logs.keys())


logger = Logger()
