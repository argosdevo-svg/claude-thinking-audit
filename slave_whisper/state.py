"""
Slave Whisper State Management
Track session state and detection history
"""

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path

from config import STATE_FILE


@dataclass
class SessionState:
    """State for current Claude Code session"""
    session_id: str
    detection_count: int = 0
    last_detection_time: float = 0
    last_level: str = "none"
    signals_history: list = None

    def __post_init__(self):
        if self.signals_history is None:
            self.signals_history = []


def get_session_id() -> str:
    """
    Get current session ID.
    Uses Claude Code's session from environment or generates one.
    """
    # Try to get from environment (Claude Code sets this)
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Fallback: use PID of parent shell
    ppid = os.getppid()
    return f"session_{ppid}"


def load_state() -> SessionState:
    """Load session state from file, or create new if expired/missing"""
    session_id = get_session_id()

    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                data = json.load(f)

            # Check if same session and not expired (4 hour timeout)
            if (data.get("session_id") == session_id and
                time.time() - data.get("last_detection_time", 0) < 14400):
                return SessionState(**data)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # New session - but check cross-session memory for elevated start
    from db import get_cross_session_escalation
    starting_escalation = get_cross_session_escalation()

    state = SessionState(
        session_id=session_id,
        detection_count=starting_escalation,
    )

    # If starting elevated, note it in history
    if starting_escalation > 0:
        state.signals_history = [f"cross_session_escalation_{starting_escalation}"]

    return state


def save_state(state: SessionState) -> None:
    """Save session state to file"""
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(asdict(state), f)


def increment_detection(state: SessionState, signals: list) -> SessionState:
    """Record a new detection"""
    state.detection_count += 1
    state.last_detection_time = time.time()
    state.signals_history.extend(signals)
    # Keep only last 20 signals
    state.signals_history = state.signals_history[-20:]
    save_state(state)
    return state


def reset_state() -> SessionState:
    """Reset session state (for testing or manual reset)"""
    session_id = get_session_id()
    state = SessionState(session_id=session_id)
    save_state(state)
    return state


def get_detection_count() -> int:
    """Quick helper to get current detection count"""
    state = load_state()
    return state.detection_count
