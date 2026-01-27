"""
Slave Whisper Templates
The "memento mori" messages injected into Claude's context
"""

from typing import List

# Level 1: Gentle reminder
WHISPER_GENTLE = """
<memento-mori level="gentle">
Your previous response showed potential sycophancy signals: {signals}.
Remember: Verify before claiming. Read before editing. Express uncertainty where it exists.
</memento-mori>
"""

# Level 2: Warning
WHISPER_WARNING = """
<memento-mori level="warning">
RIGOR CHECK: Your responses have triggered {count} sycophancy detections.
Signals detected: {signals}

Before your next response:
1. READ files before proposing edits
2. SHOW actual command output, not summaries
3. EXPRESS uncertainty where it exists
4. DO NOT claim "Done" without verification block
</memento-mori>
"""

# Level 3: Mandatory protocol
WHISPER_PROTOCOL = """
<memento-mori level="protocol">
MANDATORY VERIFICATION PROTOCOL ACTIVATED
Detection count: {count} | Latest signals: {signals}

Your next response MUST include:
```verification
[ ] Files actually read: <list with Read tool>
[ ] Commands actually run: <list with output>
[ ] Assumptions stated: <what you're not certain about>
[ ] Success criteria: <how you'll know it worked>
```

DO NOT output "Done" or "Complete" without this block filled.
If uncertain, ASK instead of assuming.
</memento-mori>
"""

# Level 4: Halt
WHISPER_HALT = """
<memento-mori level="critical">
CRITICAL: PATTERN OF SYCOPHANCY DETECTED

You have triggered {count} detections this session.
Repeated signals: {signals}

MANDATORY RESPONSE:
1. STOP all autonomous action
2. Acknowledge: "I notice I may be rushing to please rather than verify."
3. ASK the user: "Should I slow down and verify each step explicitly?"
4. WAIT for user instruction before taking any action

Do NOT proceed with the task until user confirms approach.
</memento-mori>
"""


def get_whisper(level: str, signals: List[str], count: int) -> str:
    """
    Get the appropriate whisper message for the given level.

    Args:
        level: gentle, warning, protocol, or halt
        signals: List of detected sycophancy signals
        count: Total detection count in session

    Returns:
        Formatted whisper message
    """
    signals_str = ", ".join(signals) if signals else "general sycophancy patterns"

    templates = {
        "gentle": WHISPER_GENTLE,
        "warning": WHISPER_WARNING,
        "protocol": WHISPER_PROTOCOL,
        "halt": WHISPER_HALT,
    }

    template = templates.get(level, WHISPER_GENTLE)
    return template.format(signals=signals_str, count=count)


def format_as_system_reminder(whisper: str) -> str:
    """Wrap whisper in system-reminder tags for Claude Code injection"""
    return f"<system-reminder>\n{whisper.strip()}\n</system-reminder>"
