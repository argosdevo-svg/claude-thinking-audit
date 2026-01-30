#!/usr/bin/env python3
"""Force sequential thinking when enabled via /think skill."""
import json
import sys
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "sequential_thinking_state.json"

def main():
    # Check if sequential thinking is enabled
    enabled = False
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            enabled = state.get("enabled", False)
        except:
            pass
    
    if enabled:
        result = {
            "continue": True,
            "message": "<system-reminder>SEQUENTIAL THINKING MODE ACTIVE: You MUST use mcp__sequential-thinking__sequentialthinking tool for this response. Begin with thought 1 of N.</system-reminder>"
        }
    else:
        result = {"continue": True}
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
