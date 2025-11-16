"""
Session memory using ADK-compatible InMemorySessionService pattern.
Stores user preferences, queries, and in-progress plan states.
"""
from typing import Any, Dict, Optional
from datetime import datetime


class InMemorySessionService:
    """
    ADK-compatible session service for storing session state.
    """
    
    def __init__(self):
        """Initialize session storage."""
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "user_preferences": {},
                "queries": [],
                "plan_states": {},
                "context": {}
            }
        return self.sessions[session_id]
    
    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update session data.
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to merge
        """
        session = self.get_session(session_id)
        session.update(updates)
        session["updated_at"] = datetime.now().isoformat()
    
    def add_query(self, session_id: str, query: str) -> None:
        """Add a user query to session history."""
        session = self.get_session(session_id)
        session["queries"].append({
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
    
    def set_preference(self, session_id: str, key: str, value: Any) -> None:
        """Set a user preference."""
        session = self.get_session(session_id)
        session["user_preferences"][key] = value
    
    def get_preference(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        session = self.get_session(session_id)
        return session["user_preferences"].get(key, default)
    
    def save_plan_state(self, session_id: str, state_name: str, state: Dict[str, Any]) -> None:
        """Save an intermediate plan state."""
        session = self.get_session(session_id)
        session["plan_states"][state_name] = state
    
    def get_plan_state(self, session_id: str, state_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved plan state."""
        session = self.get_session(session_id)
        return session["plan_states"].get(state_name)
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


# Global session service instance
session_service = InMemorySessionService()

