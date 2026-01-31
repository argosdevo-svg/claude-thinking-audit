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

### 2. Web UI (Browser)

Live dashboard served by the proxy on port 18889.

**Location:** `http://localhost:18889` (Statusline + Monitor tabs)

---

## Statusline Tab (Web UI)

Full statusline snapshot plus all raw metrics with explanations.

```
═══ Statusline Snapshot (Web UI) ═══

Model: Opus4.5-Nov (direct)  |  Hardware: TPU (72%)
ITT: 37ms ±86ms  |  Speed: 113 tokens/sec  |  TTFT: 2.8s
Thinking: Maximum (31k budget, 8% used)  |  Cache: 100%
Context: True 78%  |  CC 83%  |  mismatch!
```

The tab also includes:
- **Metrics Explained** (human-readable table)
- **All Metrics** (flattened raw fields)
- **Raw JSON** (full payload)

---

## Monitor Tab (Web UI)

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

| Feature | Statusline | Web UI |
|---------|------------|---------|
| Display | After each Claude response | Browser dashboard |
| Update | Per API call | Manual or 3s auto-refresh |
| Disable | `CLAUDE_STATUSLINE_DISABLED=1` | Just close the tab |
| Detail level | Configurable (EXPANDED/FULL/COMPACT) | Statusline snapshot + full metrics tables |
| Quantization | Shows in Quality line | Shown in tables (if captured) |

---

## When to Use Each

**Use Statusline when:**
- You want inline feedback after each response
- You don't want extra terminal windows
- You want configurable detail levels

**Use Web UI when:**
- You want a dedicated live dashboard
- You're running multiple Claude sessions
- You want to disable statusline but still see metrics
- You want a browser-based view of recent requests and all metrics

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

Open the Statusline or Monitor tab:

```
http://localhost:18889
```

---

## Files

| File | Purpose |
|------|---------|
| `~/.claude/statusline.py` | Integrated statusline for Claude Code |
| `~/.claude/fingerprint_db.py` | Database and quality detection logic |
| Web UI (`http://localhost:18889`) | Statusline + Monitor dashboards |

---

*Generated: 2026-01-26*
