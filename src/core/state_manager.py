import time
from dataclasses import dataclass
from typing import Dict

@dataclass
class AgentState:
    """
    Internal state of the agent.
    Values are normalized between 0.0 and 1.0 (or higher if valid).
    """
    anger: float = 0.0
    fatigue: float = 0.0
    satisfaction: float = 0.5
    last_update_ts: float = 0.0

class StateManager:
    """
    Manages the internal state of the agent.
    Handles decay over time and updates based on events.
    """
    def __init__(self):
        self.state = AgentState(last_update_ts=time.time())
        # Decay rates per second (example values)
        self.decay_rates = {
            "anger": 0.01,
            "fatigue": -0.005,  # Fatigue increases over time? Or decreases? 
                               # Usually increases with action, decreases with rest. 
                               # Let's assume natural decay of fatigue means recovery for now.
            "satisfaction": -0.001
        }

    def update(self) -> AgentState:
        """
        Calculates the current state based on time elapsed since last update.
        """
        current_time = time.time()
        delta = current_time - self.state.last_update_ts

        # Apply decay
        self.state.anger = max(0.0, self.state.anger - (self.decay_rates["anger"] * delta))
        # Fatigue recovery (natural decay)
        self.state.fatigue = max(0.0, self.state.fatigue - (0.01 * delta)) # Simple recovery
        
        # Satisfaction might decay towards neutral (0.5) or 0
        # Let's say it decays towards 0.5
        if self.state.satisfaction > 0.5:
            self.state.satisfaction = max(0.5, self.state.satisfaction - (0.001 * delta))
        else:
            self.state.satisfaction = min(0.5, self.state.satisfaction + (0.001 * delta))

        self.state.last_update_ts = current_time
        return self.state

    def modify_state(self, updates: Dict[str, float]):
        """
        Directly modifies state values (e.g., from an event).
        """
        self.update() # Sync time first
        
        for key, value in updates.items():
            if hasattr(self.state, key):
                current = getattr(self.state, key)
                setattr(self.state, key, min(1.0, max(0.0, current + value)))
