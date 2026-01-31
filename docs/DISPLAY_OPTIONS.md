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

### 2. Web UI Monitor (Browser)

Live dashboard served by the proxy on port 18889.

**Location:** `http://localhost:18889` (Monitor tab)

---

## Monitor Output (Web UI)

```
═══ Live Request Monitor (Web UI) ═══

Model: claude-opus-4-5-20251101
Backend: tpu (72%)
ITT: 37ms ±86ms  |  TPS: 113  |  TTFT: 2.8s
Thinking: ON (budget:31999)
Tokens: 1200  |  Cache: 100%
5h/7d Quota: 40% / 10%  |  Status: allowed
Location: AMS
```

---

## Comparison

| Feature | Statusline | Web UI Monitor |
|---------|------------|---------|
| Display | After each Claude response | Browser dashboard |
| Update | Per API call | Manual or 3s auto-refresh |
| Disable | `CLAUDE_STATUSLINE_DISABLED=1` | Just close the tab |
| Detail level | Configurable (EXPANDED/FULL/COMPACT) | Table + badges |
| Quantization | Shows in Quality line | Shown in table (if captured) |

---

## When to Use Each

**Use Statusline when:**
- You want inline feedback after each response
- You don't want extra terminal windows
- You want configurable detail levels

**Use Web UI Monitor when:**
- You want a dedicated live dashboard
- You're running multiple Claude sessions
- You want to disable statusline but still see metrics
- You want a browser-based view of recent requests

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

### Web UI

Open the Monitor tab:

```
http://localhost:18889
```

---

## Files

| File | Purpose |
|------|---------|
| `~/.claude/statusline.py` | Integrated statusline for Claude Code |
| `~/.claude/fingerprint_db.py` | Database and quality detection logic |
| Web UI (`http://localhost:18889`) | Monitor dashboard |

---

*Generated: 2026-01-26*
