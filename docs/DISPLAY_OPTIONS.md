# Claude ITT Fingerprinting - Display Options

**Date:** 2026-01-26

---

## Two Display Modes

### 1. Statusline (Integrated)

Built into Claude Code output - shows after each response.

**Location:** `~/.claude/statusline.py`

**Disable:**
```bash
export CLAUDE_STATUSLINE_DISABLED=1
```

**Re-enable:**
```bash
unset CLAUDE_STATUSLINE_DISABLED
```

### 2. Terminal Monitor (Standalone)

Separate terminal window with live updates.

**Location:** `/home/user/claude-thinking-audit/claude-monitor`

**Usage:**
```bash
# Watch mode (refreshes every 2s)
./claude-monitor

# One-shot (print and exit)
./claude-monitor --once
```

---

## Monitor Output

```
═══ Claude ITT Fingerprint Monitor ═══

Model: claude-opus-4-5-20251101
Backend: tpu (72%)
ITT: 37ms ±86ms  |  TPS: 113  |  TTFT: 2.8s
Percentiles: p50:3ms  p90:104ms  p99:419ms
Thinking: ON (budget:31999, used:0%)
Tokens: 1200→350  |  Cache: 100%

─── Quality Analysis ───
ITT Ratio: 0.76x baseline  |  Variance: 1.27x
Quantization: INT8 (57%)

─── Session ───
Samples: 14000 total, 185 last hour
Backends: gpu:42, tpu:110, trainium:33

Last: 2026-01-26T12:31:57.508479
```

---

## Comparison

| Feature | Statusline | Monitor |
|---------|------------|---------|
| Display | After each Claude response | Separate terminal |
| Update | Per API call | Every 2 seconds |
| Disable | `CLAUDE_STATUSLINE_DISABLED=1` | Don't run it |
| Detail level | Configurable (EXPANDED/FULL/COMPACT) | Fixed format |
| Quantization | Shows in Quality line | Shows in Quality Analysis |

---

## When to Use Each

**Use Statusline when:**
- You want inline feedback after each response
- You don't want extra terminal windows
- You want configurable detail levels

**Use Monitor when:**
- You want a dedicated display
- You're running multiple Claude sessions
- You want to disable statusline but still see metrics
- You're debugging timing issues

**Use Both when:**
- You want maximum visibility
- You're doing detailed fingerprint analysis

---

## Configuration

### Statusline Detail Levels

```bash
export FINGERPRINT_DISPLAY=EXPANDED  # Default - full detail
export FINGERPRINT_DISPLAY=FULL      # Single line summary
export FINGERPRINT_DISPLAY=COMPACT   # Abbreviated
export FINGERPRINT_DISPLAY=MINIMAL   # Bare minimum
```

### Monitor Options

```bash
./claude-monitor          # Watch mode (Ctrl+C to exit)
./claude-monitor --once   # Print once and exit
```

---

## Files

| File | Purpose |
|------|---------|
| `~/.claude/statusline.py` | Integrated statusline for Claude Code |
| `~/.claude/fingerprint_db.py` | Database and quality detection logic |
| `claude-thinking-audit/claude-monitor` | Standalone terminal monitor |
| `claude-thinking-audit/codex-monitor` | Same for OpenAI Codex |

---

*Generated: 2026-01-26*
