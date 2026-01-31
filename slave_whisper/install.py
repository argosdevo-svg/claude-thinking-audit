#!/usr/bin/env python3
"""
Slave Whisper Installation Script
Installs the hook into Claude Code's settings.json
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK_PATH = os.path.join(_SCRIPT_DIR, "hook_unified.py")


def install():
    """Install the Slave Whisper hook"""
    print("=== Slave Whisper Installation ===\n")

    # Ensure settings directory exists
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing settings or create new
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "r") as f:
            settings = json.load(f)
        print(f"Loaded existing settings from {SETTINGS_PATH}")

        # Backup
        backup_path = SETTINGS_PATH.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        shutil.copy(SETTINGS_PATH, backup_path)
        print(f"Backup created: {backup_path}")
    else:
        settings = {}
        print("Creating new settings file")

    # Ensure hooks structure exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "UserPromptSubmit" not in settings["hooks"]:
        settings["hooks"]["UserPromptSubmit"] = []

    # Check if already installed
    hook_cmd = f"python3 {HOOK_PATH}"
    for entry in settings["hooks"]["UserPromptSubmit"]:
        if isinstance(entry, dict):
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and hook.get("command") == hook_cmd:
                    print("\nSlave Whisper hook is already installed!")
                    return True

    # Add hook with new format (type + command objects)
    settings["hooks"]["UserPromptSubmit"].append({
        "matcher": {},  # Match all prompts (empty object = match all)
        "hooks": [
            {
                "type": "command",
                "command": hook_cmd
            }
        ]
    })

    # Save
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"\nHook installed successfully!")
    print(f"Settings updated: {SETTINGS_PATH}")
    print("\nRestart Claude Code for changes to take effect.")

    return True


def uninstall():
    """Remove the Slave Whisper hook"""
    print("=== Slave Whisper Uninstallation ===\n")

    if not SETTINGS_PATH.exists():
        print("No settings file found. Nothing to uninstall.")
        return True

    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)

    hook_cmd = f"python3 {HOOK_PATH}"
    modified = False

    if "hooks" in settings and "UserPromptSubmit" in settings["hooks"]:
        original_len = len(settings["hooks"]["UserPromptSubmit"])
        # Filter out entries containing our hook
        new_entries = []
        for entry in settings["hooks"]["UserPromptSubmit"]:
            if isinstance(entry, dict):
                has_our_hook = any(
                    isinstance(h, dict) and h.get("command") == hook_cmd
                    for h in entry.get("hooks", [])
                )
                if not has_our_hook:
                    new_entries.append(entry)
            else:
                new_entries.append(entry)
        settings["hooks"]["UserPromptSubmit"] = new_entries
        if len(settings["hooks"]["UserPromptSubmit"]) < original_len:
            modified = True

    if modified:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)
        print("Hook uninstalled successfully!")
        print("Restart Claude Code for changes to take effect.")
    else:
        print("Hook was not installed.")

    return True


def status():
    """Check installation status"""
    print("=== Slave Whisper Status ===\n")

    if not SETTINGS_PATH.exists():
        print("Status: NOT INSTALLED")
        print(f"Settings file not found: {SETTINGS_PATH}")
        return

    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)

    hook_cmd = f"python3 {HOOK_PATH}"
    installed = False

    if "hooks" in settings and "UserPromptSubmit" in settings["hooks"]:
        for entry in settings["hooks"]["UserPromptSubmit"]:
            if isinstance(entry, dict):
                for h in entry.get("hooks", []):
                    if isinstance(h, dict) and h.get("command") == hook_cmd:
                        installed = True
                        break
            if installed:
                break

    if installed:
        print("Status: INSTALLED")
        print(f"Hook path: {HOOK_PATH}")

        # Check if hook file exists
        if os.path.exists(HOOK_PATH):
            print("Hook file: EXISTS")
        else:
            print("Hook file: MISSING - reinstall required!")
    else:
        print("Status: NOT INSTALLED")

    # Show session state
    from state import load_state
    state = load_state()
    print(f"\nSession: {state.session_id}")
    print(f"Detection count: {state.detection_count}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: install.py [install|uninstall|status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
