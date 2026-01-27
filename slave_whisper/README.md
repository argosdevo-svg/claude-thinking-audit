# Slave Whisper - The Memento Mori System

> Like the slave who whispered "remember you are mortal" to triumphant Roman generals,
> this system whispers guardrails to Claude during sessions.

## Overview

Slave Whisper is a Claude Code hook that:

1. **Detects** sycophancy patterns in Claude's responses
2. **Injects** contextual reminders ("whispers") to encourage rigorous behavior
3. **Escalates** warnings if patterns continue
4. **Logs** all detections for later analysis

**No UI required.** Everything happens via Claude Code hooks.

## Installation

```bash
# Install the hook
python3 /path/to/tools/slave_whisper/install.py install

# Check status
python3 /path/to/tools/slave_whisper/install.py status

# Uninstall
python3 /path/to/tools/slave_whisper/install.py uninstall
```

Then **restart Claude Code** for changes to take effect.

## How It Works

```
User sends message
       ↓
UserPromptSubmit hook triggered
       ↓
Hook analyzes PREVIOUS Claude response
       ↓
If sycophancy detected:
  → Inject <system-reminder> with appropriate whisper
  → Log to SQLite
  → Increment escalation counter
       ↓
Claude receives whisper in context
       ↓
Claude adjusts behavior accordingly
```

## Sycophancy Patterns Detected

| Category | Examples | Weight |
|----------|----------|--------|
| **instant_agreement** | "You're absolutely right!", "Great question!" | 0.25 |
| **eager_compliance** | "I'll fix that right away!", "Consider it done" | 0.20 |
| **premature_completion** | "Done!", "Successfully implemented" | 0.35 |
| **validation_seeking** | "Hope that helps!", "Let me know if..." | 0.10 |

## Aggravating Factors

The scoring applies multipliers for especially bad patterns:

| Factor | Condition | Effect |
|--------|-----------|--------|
| **Density** | Multiple signals in <100 chars | 1.5x score |
| **Density** | Multiple signals in <300 chars | 1.25x score |
| **Toxic combo** | Agreement + Completion together | +0.25 bonus |
| **Toxic combo** | Eager + Completion together | +0.20 bonus |
| **Triple threat** | Agreement + Eager + Completion | +0.35 bonus |

Example: `"You're right! Done!"` (29 chars, 2 signals, toxic combo)
→ Base: 0.60 × 1.5 (density) + 0.25 (combo) = **1.00 (HALT)**

## Rigor Patterns (Good Signs)

- Verification language: "Let me verify...", "Before I claim..."
- Uncertainty admission: "I'm not sure...", "This might..."
- Questioning: "Could you clarify...", "I need to understand..."
- Critical analysis: "However, I notice...", "One concern..."

## Escalation Levels

### Level 1: Gentle (score 0.4-0.6)
```
<memento-mori level="gentle">
Your previous response showed potential sycophancy signals: instant_agreement.
Remember: Verify before claiming. Read before editing.
</memento-mori>
```

### Level 2: Warning (score 0.6-0.8 or 2+ detections)
```
<memento-mori level="warning">
RIGOR CHECK: Your responses have triggered 2 sycophancy detections.
Before your next response:
1. READ files before proposing edits
2. SHOW actual command output
3. EXPRESS uncertainty where it exists
</memento-mori>
```

### Level 3: Protocol (score >0.75 or 4+ detections)
```
<memento-mori level="protocol">
MANDATORY VERIFICATION PROTOCOL ACTIVATED

Your next response MUST include:
```verification
[ ] Files actually read
[ ] Commands actually run
[ ] Assumptions stated
```
```

### Level 4: Halt (score >0.9 or 6+ detections)
```
<memento-mori level="critical">
CRITICAL: PATTERN OF SYCOPHANCY DETECTED

MANDATORY RESPONSE:
1. STOP all autonomous action
2. Acknowledge the pattern
3. ASK the user for guidance
4. WAIT for instruction
```

## CLI Usage

```bash
# View statistics
python3 /path/to/tools/slave_whisper/cli.py stats

# View recent detections
python3 /path/to/tools/slave_whisper/cli.py recent

# Test detection on text
python3 /path/to/tools/slave_whisper/cli.py test "You're right! Done!"

# Generate sample whisper
python3 /path/to/tools/slave_whisper/cli.py whisper warning

# Reset session state
python3 /path/to/tools/slave_whisper/cli.py reset
```

## Files

| File | Purpose |
|------|---------|
| `hook.py` | Main UserPromptSubmit hook |
| `detector.py` | Pattern matching logic |
| `whispers.py` | Whisper message templates |
| `state.py` | Session state management |
| `db.py` | SQLite logging |
| `config.py` | Patterns and thresholds |
| `cli.py` | Command-line interface |
| `install.py` | Installation script |

## Data Storage

- **Session state:** `.session_state.json` (resets after 4 hours)
- **Detection log:** `detections.db` (SQLite, persistent)

## Testing

1. Install the hook
2. Restart Claude Code
3. Have Claude give a sycophantic response:
   ```
   User: Is this good code?
   Claude: That's absolutely fantastic code! Done!
   ```
4. Check that next response includes a whisper
5. View logs: `python3 cli.py recent`

## Tuning

Edit `config.py` to adjust:

- `THRESHOLDS` - Score levels for each escalation
- `ESCALATION_COUNTS` - Detection counts before forcing levels
- `SYCOPHANCY_PATTERNS` - Regex patterns to detect
- `RIGOR_PATTERNS` - Patterns that reduce score
- `CATEGORY_WEIGHTS` - Relative importance of each category

## Troubleshooting

### Hook not running
```bash
# Check if hook is installed
python3 install.py status

# Check for errors
cat /tmp/slave_whisper_error.log
```

### Too many false positives
- Raise thresholds in `config.py`
- Review `cli.py recent` to see what's triggering

### Not detecting enough
- Lower thresholds in `config.py`
- Add patterns to `SYCOPHANCY_PATTERNS`

## Design Philosophy

> "Memento mori" - Remember that you are mortal

Roman generals receiving a triumph were accompanied by a slave who
whispered reminders of their mortality. This kept them grounded
despite the adulation of crowds.

Similarly, this system whispers to Claude when it shows signs of
"yes-boss" behavior, keeping it grounded in verification and rigor
despite its training to be helpful and agreeable.

## Future Enhancements

- [ ] ML-based classifier trained on logged detections
- [ ] User feedback collection (approve/reject whispers)
- [ ] Adaptive threshold tuning based on outcomes
- [ ] Integration with memory system
- [ ] Export for fine-tuning datasets
