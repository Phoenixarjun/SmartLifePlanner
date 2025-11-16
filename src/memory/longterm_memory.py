"""
Long-term memory using JSON file storage.
Stores persistent user preferences and historical data.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional


class LongTermMemory:
    """
    Long-term memory storage using JSON file.
    """
    
    def __init__(self, memory_file: str = "data/longterm_memory.json"):
        """
        Initialize long-term memory.
        
        Args:
            memory_file: Path to JSON file for storage
        """
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self._memory: Dict[str, Any] = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"preferences": {}, "history": [], "patterns": {}}
        return {"preferences": {}, "history": [], "patterns": {}}
    
    def _save_memory(self) -> None:
        """Save memory to file."""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._memory, f, indent=2, ensure_ascii=False)
    
    def read_memory(self, key: Optional[str] = None) -> Any:
        """
        Read memory data.
        
        Args:
            key: Optional key to read specific value
            
        Returns:
            Memory data (full dict if key is None, else specific value)
        """
        if key is None:
            return self._memory.copy()
        keys = key.split(".")
        value = self._memory
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
    
    def write_memory(self, key: str, value: Any) -> None:
        """
        Write to memory.
        
        Args:
            key: Dot-separated key path (e.g., "preferences.diet")
            value: Value to store
        """
        keys = key.split(".")
        target = self._memory
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save_memory()
    
    def clear_memory(self, key: Optional[str] = None) -> None:
        """
        Clear memory.
        
        Args:
            key: Optional key to clear specific value (clears all if None)
        """
        if key is None:
            self._memory = {"preferences": {}, "history": [], "patterns": {}}
        else:
            keys = key.split(".")
            target = self._memory
            for k in keys[:-1]:
                if k in target and isinstance(target[k], dict):
                    target = target[k]
                else:
                    return
            if keys[-1] in target:
                del target[keys[-1]]
        self._save_memory()
    
    def add_history(self, entry: Dict[str, Any]) -> None:
        """Add an entry to history."""
        if "history" not in self._memory:
            self._memory["history"] = []
        self._memory["history"].append(entry)
        # Keep only last 100 entries
        if len(self._memory["history"]) > 100:
            self._memory["history"] = self._memory["history"][-100:]
        self._save_memory()


# Global long-term memory instance
longterm_memory = LongTermMemory()

