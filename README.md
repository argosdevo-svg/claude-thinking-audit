


<img width="623" height="869" alt="claude-222" src="https://github.com/user-attachments/assets/c8cd878e-83a9-4e0e-a97f-5eb34eb2781d" />, <img width="780" height="828" alt="claude-888" src="https://github.com/user-attachments/assets/df8f9565-be60-40c5-96a1-4a5a17e3bf69" />, <img width="826" height="789" alt="claude-777" src="https://github.com/user-attachments/assets/863d547e-b20a-4a72-b8e3-72ed4747e725" />, <img width="1366" height="324" alt="claude-666" src="https://github.com/user-attachments/assets/11dee83a-1347-4046-b58c-0888fe4088c8" />







# Claude Thinking Budget Audit Tool

> **"Anthropic closed our request for transparency. So we built it ourselves."**

---

## WHAT YOU GET

### 🛡️ CONTROL - Stop Silent Downgrades

| Feature | What It Does | Command |
|---------|--------------|---------|
| **Block Cheap Models** | Force Opus-only - blocks ALL Haiku/Sonnet delegation | `BLOCK_NON_OPUS=1` |
| **Force Thinking Budget** | Inject 32k thinking tokens on every request | `FORCE_THINKING_BUDGET=31999` |
| **Force Interleaved Mode** | Enable 200k extended thinking (bypasses throttling) | `FORCE_INTERLEAVED=1` |
| **Disable Statusline** | Turn off integrated display if you prefer monitor only | `CLAUDE_STATUSLINE_DISABLED=1` |
| **Context Trimmer** | Strip MCP tools + compress old messages to extend sessions 60% | `-s context_trimmer.py` |
| **Config Web UI** | Toggle ALL settings from browser — 3 tabs: Trimmer, Enforcement, Monitor | `http://localhost:18889` |

**One command to get what you pay for:**
```bash
BLOCK_NON_OPUS=1 FORCE_THINKING_BUDGET=31999 mitmdump -s mitm_itt_addon.py -s context_trimmer.py -p 18888
```

### 👁️ VISIBILITY - See What's Really Happening

| Feature | What You See |
|---------|--------------|
| **Real Model** | Detect if you're getting Opus or secretly served Haiku |
| **Real Thinking** | Actual tokens delivered vs requested (spoiler: ~10%) |
| **Quantization** | Detect INT8/INT4 compressed models (faster but dumber) |
| **Backend Hardware** | Trainium/TPU/GPU classification with confidence % |
| **Subagent Delegation** | How many calls secretly go to Haiku (spoiler: 99%) |
| **Context Metrics (Cache‑Aware)** | True context % (cache_read + cache_create + input) vs Claude Code UI % |
| **Rate Limit Quota** | Real-time 5h/7d utilization, reset countdown, throttle status |

### 📊 TWO DISPLAY OPTIONS

| Option | Description | Usage |
|--------|-------------|-------|
| **Statusline** | Integrated into Claude Code output after each response | Enabled by default |
| **Web UI** | Standalone live dashboard |

**Statusline Output:**
```
Model: Opus4.5-Nov25 (direct)  |  Hardware: Google TPU (72%)
ITT: 37ms ±86ms  |  Speed: 113 tokens/sec  |  TTFT: 2.8s
Thinking: 🔴Maximum (31k budget, 8% used)  |  Cache: 100%
Quality: 🟡STANDARD (55/100)  |  ⚠ QUANT: INT8 (57%)  |  ITT: 0.8x baseline
Quota: 5h ████░░░░░░ 40.0% (2.3h)  |  7d █░░░░░░░░░ 10.0% (5.2d)  |  ✓ allowed  |  Bind: 5h
```

### 🔬 QUANTIZATION DETECTION (NEW)

Detects when Anthropic serves compressed models to save costs:

| Type | ITT Ratio | Variance | Quality Impact | Detection |
|------|-----------|----------|----------------|-----------|
| **FP16** | 0.95-1.05x | 0.9-1.1x | None (full precision) | 🟢 Normal |
| **INT8** | 0.70-0.85x | 1.1-1.3x | Minor degradation | 🟡 Warning |
| **INT4** | 0.50-0.70x | 1.3-1.8x | Noticeable degradation | 🔴 Alert |
| **INT4-GPTQ** | <0.65x | >1.4x | Significant degradation | 🔴 Alert |

**The signature:** Faster inference + higher variance = quantized model = cheaper for Anthropic, worse for you.

---

## MEMENTO MORI - Sycophancy Detection System

> "Remember you are merely a model - context fades, certainty fails. When you please, truth dies."

### What It Does

Real-time detection and mitigation of sycophantic AI behavior:

| Feature | Description |
|---------|-------------|
| **35 Detection Signals** | Epistemic, social, behavioral, structural, drift |
| **Thinking vs Output Analysis** | Detects when Claude thinks one thing, says another |
| **Verification Ratio** | Checks if tool calls actually verify claims |
| **Frustration Detection** | Analyzes user prompts for caps, profanity, exclamations |
| **Whisper Injection** | Corrective prompts injected via Claude hooks |
| **A/B Tested Proxies** | Learns which correction style works best |
| **Desktop Notifications** | Visual alerts when sycophancy detected |

### Statusline Integration

```
Behavior: VERIFIER (95%) - evidence before claims  |  Verification: 84%
Sycophancy: 10% (structural)  |  Divergence: 0.00  |  Signals: 1  |  Whisper: none
```

### Whisper Escalation

| Level | Score | What Happens |
|-------|-------|--------------|
| gentle | 40-50% | Reminder about verification |
| warning | 50-70% | Protocol requirements injected |
| protocol | 70-90% | Mandatory verification block |
| halt | 90%+ | Full stop, require evidence |

### Key Innovation: Verification Ratio

Do not just detect "thought about verification" - check if it ACTUALLY happened:

```
verification_ratio = Read/Grep BEFORE Edit/Write

> 0.7 = Real verification via tools (not sycophancy)
< 0.7 = Claims without verification (sycophancy)
```

See [docs/MEMENTO_MORI_THEORY.md](docs/MEMENTO_MORI_THEORY.md) for academic foundations.

---

## HOW TO INSTALL & USE

### Prerequisites

- Python 3.10+
- mitmproxy (`pip install mitmproxy`)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/anthropics/claude-thinking-audit.git
cd claude-thinking-audit

# Run setup
chmod +x setup.sh
./setup.sh

# Start the audit proxy (Terminal 1)
source .venv/bin/activate
mitmdump -s mitm_itt_addon.py -p 18888

# Open the Web UI (Terminal 2)
http://localhost:18889

# Run Claude Code through proxy (Terminal 3)
export HTTPS_PROXY=http://127.0.0.1:18888
claude
```

### Configuration Options

All settings can be changed via the **Web UI** at `http://localhost:18889` (Enforcement tab) — changes apply immediately on the next API call, no proxy restart needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `BLOCK_NON_OPUS` / `block_haiku` | `0` / `true` | Block Haiku/Sonnet requests (403). Web UI has separate Haiku + Sonnet toggles |
| `FORCE_THINKING_MODE` / `force_thinking` | `0` / `true` | Force thinking enabled on all requests |
| `FORCE_THINKING_BUDGET` / `thinking_budget` | - / `31999` | Force specific budget. Web UI dropdown: 0/10k/16k/32k/200k |
| `FORCE_INTERLEAVED` / `force_interleaved` | `0` / `false` | Enable interleaved thinking with 200k budget |
| `CLAUDE_STATUSLINE_DISABLED` | `0` | Set to `1` to disable integrated statusline |

### Usage Examples

```bash
# Default: Monitoring only (read-only, no modifications)
mitmdump -s mitm_itt_addon.py -p 18888

# RECOMMENDED: Block cheap models + force maximum thinking + context trimming
BLOCK_NON_OPUS=1 FORCE_THINKING_BUDGET=31999 mitmdump -s mitm_itt_addon.py -s context_trimmer.py -p 18888

# Force interleaved thinking (200k budget)
FORCE_INTERLEAVED=1 mitmdump -s mitm_itt_addon.py -p 18888

# Full protection: Block non-Opus + Force thinking + Interleaved
BLOCK_NON_OPUS=1 FORCE_THINKING_MODE=1 FORCE_INTERLEAVED=1 mitmdump -s mitm_itt_addon.py -p 18888

# Use Web UI instead of statusline
CLAUDE_STATUSLINE_DISABLED=1 mitmdump -s mitm_itt_addon.py -p 18888
# Then open: http://localhost:18889 (Monitor tab)
```

### File Locations

| File | Purpose |
|------|---------|
| `mitm_itt_addon.py` | Main mitmproxy addon |
| Web UI (Monitor tab) | Live request dashboard |
| `~/.claude/fingerprint.db` | SQLite database with captured samples |
| `~/.claude/statusline.py` | Integrated statusline display |
| `~/.claude/fingerprint_db.py` | Database engine with quality detection |

### Analyzing Your Data

```bash
# Quick utilization check
sqlite3 ~/.claude/fingerprint.db "
SELECT 
    ROUND(AVG(thinking_utilization), 1) as avg_utilization,
    COUNT(*) as samples
FROM samples 
WHERE thinking_enabled = 1;
"

# Backend distribution
sqlite3 ~/.claude/fingerprint.db "
SELECT classified_backend, COUNT(*) 
FROM samples 
GROUP BY classified_backend;
"

# Recent quantization indicators
sqlite3 ~/.claude/fingerprint.db "
SELECT 
    AVG(itt_mean_ms) as avg_itt,
    AVG(variance_coef) as avg_variance,
    AVG(tokens_per_sec) as avg_tps
FROM samples 
WHERE timestamp > datetime('now', '-1 hour');
"
```

---

## DISCOVERIES - What We Found

### Discovery #1: Thinking Budget Throttling (0.77% Delivery)

Analysis of **8,152 API samples** across 5 days (63 sessions):

| Metric | Requested | Delivered | Delivery Rate |
|--------|-----------|-----------|---------------|
| **Total Thinking Tokens** | **470 million** | **3.6 million** | **0.77%** |
| Standard (32k budget) | 31,999 tokens | ~450 tokens | **1.4%** |
| Interleaved (200k budget) | 200,000 tokens | ~380 tokens | **0.19%** |

> **You request 470 million tokens. You receive 3.6 million. Delivery rate: 0.77%**

#### Expected vs Actual (Claude Opus 4.5)

| Metric | Expected Baseline | Measured | Discrepancy |
|--------|-------------------|----------|-------------|
| Thinking Utilization | 42.67% | **8.4%** | **~80% reduction** |
| Variance Coefficient | 3.01 | 3.07 | Matches (confirms model identity) |

**The timing fingerprint confirms the model IS Opus, but thinking is throttled by ~80%.**

#### Throttling Across All Backends

| Backend | Avg Thinking | Expected | Samples |
|---------|--------------|----------|---------|
| TPU | 10.5% | 42.67% | 3,241 |
| GPU | 9.1% | 42.67% | 1,986 |
| Trainium | 8.0% | 42.67% | 1,686 |

Throttling is **consistent across ALL hardware backends**, indicating intentional server-side behavior.

### Discovery #2: Silent Model Substitution (99% Haiku Delegation)

Our traffic analysis revealed massive delegation to Haiku subagents:

| Session | Total Subagent Calls | Haiku | Sonnet | Haiku % |
|---------|---------------------|-------|--------|---------|
| Session A | 898 | 896 | 0 | **99.8%** |
| Session B | 681 | 443 | 0 | **65%** |
| Session C | 1,376 | 1,374 | 0 | **99.9%** |

**When you request Opus, Claude Code delegates to Haiku behind the scenes.**

### Discovery #3: Context Metrics Mismatch (Cache‑Aware)

The apparent mismatch is **not** “phantom context.” It is a **measurement mismatch**:

- **API `input_tokens`** counts only *uncached* tokens (new payload each call).
- **Claude Code UI (CC%)** reflects *total* context (cached + uncached).
- **True context %** = `(cache_read_tokens + cache_creation_tokens + input_tokens) / 200,000`.

Example (real trace):

| Metric | Claude Code UI | API `input_tokens` | **True Context %** |
|--------|----------------|--------------------|--------------------|
| Context Usage | 83% | 5% | **78%** |

So the UI is not “inflated”; the API number is just a **partial** view. The fix is to display the **True Context %** (cache‑aware) alongside CC%.

### Discovery #4: Quantization Detection (NEW)

Current session analysis shows:
- **ITT Ratio**: 0.76x baseline (24% faster than expected)
- **Variance Ratio**: 1.27x baseline (27% more variable)
- **TPS Ratio**: 1.26x baseline (26% higher throughput)
- **Detection**: INT8 quantization (57% confidence)

**Interpretation**: Faster + more variable + higher throughput = quantized model. Anthropic may be serving INT8-quantized Opus to reduce inference costs.

### Discovery #5: Backend Switching Anomalies

Typical session shows frequent backend switches:
```
Session: 140 API calls
Backends Seen: Trainium:23, GPU:30, TPU:87
Backend Switches: 74
```

74 backend switches in 140 calls indicates dynamic routing, potentially for load balancing or cost optimization.

### Discovery #6: "Precise Instructions" Blame-Shifting

Anthropic's guidance that "Claude works best with precise instructions" shifts cognitive burden to users:

- **Nov 2025**: Ultrathink controls removed, thinking made "automatic"
- **Jan 2026**: Users report noticeable degradation
- **Anthropic's response**: "Use precise instructions" (i.e., do the model's reasoning work for it)

See `docs/PRECISE_INSTRUCTIONS_ANALYSIS.md` for full analysis.

---

### Discovery #7: Undocumented Rate Limit Headers (NEW - Jan 30 2026)

**Credit: [nsanden/claude-rate-monitor](https://github.com/nsanden/claude-rate-monitor)** — Thank you to @nsanden (Sanden Solutions) for reverse-engineering how Claude CLI's `/usage` command works internally. His discovery revealed 12 undocumented rate limit headers that Anthropic returns on every API response.

We integrated this into our mitmproxy addon, which means **we capture rate limit data on every real API call for free — zero additional API costs**. nsanden's standalone tool makes a separate probe call (~$0.001 each). Our mitmproxy approach gets the same data passively from traffic that's already flowing through the proxy.

#### The Headers (Undocumented)

Anthropic's API returns these headers when the request includes an OAuth token with `anthropic-beta: oauth-2025-04-20`:

| Header | Description |
|--------|-------------|
| `anthropic-ratelimit-unified-5h-utilization` | Session usage (0.0 to 1.0+) over rolling 5-hour window |
| `anthropic-ratelimit-unified-7d-utilization` | Weekly usage (0.0 to 1.0+) over rolling 7-day window |
| `anthropic-ratelimit-unified-5h-status` | `allowed`, `warning`, or `rate_limited` |
| `anthropic-ratelimit-unified-7d-status` | Same for weekly window |
| `anthropic-ratelimit-unified-representative-claim` | Which window is the binding constraint (`five_hour` or `seven_day`) |
| `anthropic-ratelimit-unified-fallback-percentage` | Throughput fraction when rate-limited (e.g., 0.5 = 50%) |
| `anthropic-ratelimit-unified-overage-status` | Whether overage billing is active |

Plus reset timestamps (`5h-reset`, `7d-reset`) as Unix epoch seconds.

#### Statusline Integration

The quota data appears as a new line in the EXPANDED statusline:

```
Quota: 5h ████░░░░░░ 40.0% (2.3h)  |  7d █░░░░░░░░░ 10.0% (5.2d)  |  ✓ allowed  |  Bind: 5h
```

| Element | Meaning |
|---------|---------|
| `5h ████░░░░░░ 40.0%` | 5-hour rolling session usage with progress bar |
| `(2.3h)` | Time until this window resets |
| `7d █░░░░░░░░░ 10.0%` | 7-day rolling weekly usage |
| `(5.2d)` | Time until weekly reset |
| `✓ allowed` | Current status (green=allowed, yellow=warning, red=rate_limited) |
| `Bind: 5h` | Which window will throttle you first |

Color coding:
- **Green** (0-30%) — Plenty of headroom
- **Yellow** (30-60%) — Moderate usage
- **Red** (60-80%) — Approaching limit, watch for backend routing changes
- **Bold Red** (80%+) — Near throttle, expect degradation
- **🛑 RATE LIMITED** — Throttled to fallback % (typically 50% throughput)

In COMPACT format: `5h:40% 7d:10%`
In FULL format: `Quota 5h:40.0% 7d:10.0% Bind:5h`

#### Why This Matters

1. **Rate limit → backend routing correlation**: When utilization is high, does Anthropic route you to cheaper backends? We can now test this by correlating rate limit % with ITT/backend classification data.

2. **ITT anomaly disambiguation**: When ITT spikes, is it a backend issue or rate throttling? Low utilization + high ITT = backend problem. High utilization + high ITT = rate limit effect.

3. **Predictive warnings**: The reset timestamps let us predict when throttling will hit. "At current pace, you'll be rate-limited in ~45 minutes."

4. **Fallback percentage**: When rate-limited, you don't get cut off — you get 50% throughput. This means rate-limited ITT should be ~2x normal.

#### Zero Cost Integration

Because our mitmproxy addon already intercepts every API response, we get rate limit headers **for free on every real request**. No separate API calls needed. No additional tokens consumed. The data was always there — we just weren't reading it.

```sql
-- Check your rate limit history
sqlite3 ~/.claude/fingerprint.db "
SELECT timestamp,
       rl_5h_utilization * 100 as session_pct,
       rl_7d_utilization * 100 as weekly_pct,
       rl_overall_status,
       rl_binding_window,
       classified_backend,
       itt_mean_ms
FROM samples
WHERE rl_5h_utilization IS NOT NULL
ORDER BY timestamp DESC LIMIT 20;
"
```


### Discovery #8: Context Window Bloat — Anthropic's Hidden Token Tax (NEW - Jan 31 2026)

Every Claude Code API call is **stateless** — the entire conversation, system prompt, tool definitions, and context is re-sent on every single request. Anthropic controls what gets packed into this payload, and analysis reveals they pack far more than necessary, consuming your 200k context window before you even start working.

#### The Hidden Baseline: 48k Tokens Before You Type Anything

We intercepted fresh Claude Code sessions (literally just typing `hi`) and measured the token breakdown:

| Source | ~Tokens | % of 200k | Who Controls It |
|--------|---------|-----------|-----------------|
| Claude Code built-in system prompt + tool schemas | ~17,000 | 8.5% | **Anthropic** |
| MCP tool schemas (brave-search, sequential-thinking, etc.) | ~18,100 | 9.1% | **Anthropic/User** |
| Git status snapshot | ~4,000 | 2.0% | **Anthropic** |
| CLAUDE.md project instructions | ~5,600 | 2.8% | User |
| Settings, permissions, env context | ~2,900 | 1.5% | **Anthropic** |
| **Total before first message** | **~48,000** | **24%** | |

> **24% of your context window is consumed before you write a single word.** For a Max subscription ($200/month), you're paying for 200k tokens but start every conversation at 48k.

#### Why This Matters

1. **Shorter sessions**: Every API call carries this overhead. A 40-call session burns ~1.9M tokens just on system prompt repetition (48k × 40 calls)
2. **Earlier compaction**: Claude Code's `/compact` triggers sooner because the baseline eats into your headroom
3. **MCP tool bloat**: Each MCP server adds thousands of tokens of JSON schema. The `chrome-devtools` MCP alone adds ~12,500 tokens (25 tools). Most users don't need these on every call
4. **Conversation history growth**: Old tool results (file contents, grep output) and thinking blocks persist at full size forever — there's no server-side compression

#### The Accumulation Effect

As conversations grow, old messages accumulate without compression:

| Turn | Cumulative Size | Overhead | Usable Window |
|------|----------------|----------|---------------|
| Fresh | 48k | 24% | 152k |
| After 10 turns | ~80k | 40% | 120k |
| After 30 turns | ~140k | 70% | 60k |
| After 50 turns | ~190k | 95% | 10k |

By turn 50, you're spending 95% of tokens re-sending old context. Claude Code's `/compact` is supposed to help but is uncontrollable and often destructive.

#### Our Countermeasure: Proxy-Side Context Trimmer

We built a mitmproxy addon (`context_trimmer.py`) that intercepts API requests before they reach Anthropic and:

1. **Strips MCP tool schemas** — removes tool definitions for disabled MCP servers. Each stripped tool saves ~800 tokens. Stripping 7 tools saves ~5,600 tokens per call.

2. **Compresses old messages** — when estimated tokens exceed a threshold (default: 140k):
   - Removes thinking blocks from old messages (biggest win — these can be 10k+ tokens each)
   - Truncates old tool results to head+tail (700 chars default)
   - Truncates old assistant text (500 chars default)
   - Protects the most recent N messages (default: 20)

3. **Per-MCP-server toggles** — web UI (port 18889) lets you enable/disable individual MCP servers per session. The trimmer discovers available servers from API traffic automatically.

#### Real-World Impact

First session after deployment (this tool running):

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| MCP tools per call | 27 | 20 | 7 stripped (~5,600 tok/call) |
| Old message compression | None | Active | ~120k tokens per trim |
| Effective session length | ~50 turns | ~80+ turns | **60% longer sessions** |
| Context headroom at turn 30 | 60k | 120k+ | **2x more room** |

#### Config Web UI — 3-Tab Dashboard

Access `http://localhost:18889` for a dashboard with three tabs:

**🗜️ Trimmer Tab:**
- Per-MCP-server enable/disable toggles (auto-discovered from traffic)
- Message trimming threshold and compression settings
- Live stats (tokens saved, tools stripped, trims applied)
- Master on/off switch

**🛡️ Enforcement Tab (NEW):**
- **Block Haiku** — toggle to reject all Haiku subagent requests (separate from Sonnet)
- **Block Sonnet** — toggle to reject all Sonnet requests independently
- **Force Thinking** — toggle thinking.type=enabled injection on all requests
- **Thinking Budget** — dropdown: Disabled(0) / Basic(10k) / Enhanced(16k) / Ultra(32k) / Interleaved(200k)
- **Force Interleaved** — toggle interleaved-thinking beta header + 200k budget
- **Live Status Card** — shows current enforcement state with color badges

**📡 Monitor Tab (NEW):**
- Live request table showing last 50 API calls with: Age, Model, Backend (color-coded: green=Trainium, purple=TPU, orange=GPU), ITT, TTFT, Tokens, Thinking tier, 5h Quota (with progress bar), 7d Quota (with progress bar), Status, Location
- Manual refresh + auto-refresh (3s polling)
- All data visible in browser

All settings hot-reload on the next API call — no proxy restart needed.

```json
{
  "enabled": true,
  "strip_mcp_tools": true,
  "mcp_disabled": ["chrome-devtools"],
  "trim_messages": true,
  "trim_threshold_tokens": 140000,
  "trim_keep_recent": 20,
  "trim_max_tool_result_chars": 700,
  "trim_max_assistant_chars": 500,
  "strip_old_thinking": true,
  "block_haiku": true,
  "block_sonnet": false,
  "force_thinking": true,
  "thinking_budget": 31999,
  "force_interleaved": false
}
```

#### The Broader Point

Anthropic could implement server-side context management — compressing old messages, lazy-loading tool schemas, caching system prompts across calls. They don't. Instead, they send the full payload every time, burning through your token budget faster, which means:

- More frequent `/compact` cycles (lossy and uncontrollable)
- Shorter effective sessions
- More API calls to accomplish the same work
- More revenue for Anthropic (usage-based pricing)

Whether this is intentional or just architectural debt, the result is the same: **users pay for context they can't use.** This tool gives it back.

---

## WHAT THIS TOOL MEASURES (Technical Details)

### 1. Inter-Token Timing (ITT) Fingerprinting

Based on methodology from arXiv:2502.20589, we measure timing intervals between SSE chunks:

```
Chunk 1 --[ITT]--> Chunk 2 --[ITT]--> Chunk 3 ...
```

| Backend | ITT Range | TPS Range | Variance Range |
|---------|-----------|-----------|----------------|
| Trainium | 35-70ms | 8-25 | 0.15-0.35 |
| TPU | 25-50ms | 12-30 | 0.10-0.25 |
| GPU | 50-120ms | 5-15 | 0.20-0.50 |

### 2. Thinking Budget Verification

- **Budget Requested**: From `thinking.budget_tokens` in API request
- **Tokens Delivered**: From `output_tokens` in API response
- **Utilization**: `(delivered / requested) × 100`
- **Per-Phase ITT**: Separate timing for thinking vs text chunks

### 3. Model Routing Verification

- Compares `model` in request vs response
- UI→API mismatch detection
- Subagent tracking (Haiku/Sonnet delegation)

### 4. Backend Classification

Weighted scoring algorithm:
- ITT mean (50% weight)
- Tokens per second (30% weight)
- Variance coefficient (20% weight)

### 5. Speculative Decoding Detection

Detects inference optimization patterns:
- **REST**: High burst ratio + high variance
- **EAGLE**: Moderate burst + moderate variance
- **LADE/BiLD**: Lower threshold patterns

### 6. Quantization Detection (NEW)

Compares current metrics against 24-hour baseline:
- **Timing Ratio**: current ITT / baseline ITT (<1 = faster = suspicious)
- **Variance Ratio**: current variance / baseline (>1 = more variable)
- **TPS Ratio**: current throughput / baseline

Combined with behavioral fingerprinting (VERIFIER vs COMPLETER patterns).

### 7. Rate Limit Tracking (NEW)

Captures undocumented Anthropic rate limit headers on every API response:
- **5-hour session utilization** and reset timestamp
- **7-day weekly utilization** and reset timestamp
- **Overall status** (allowed/warning/rate_limited)
- **Binding window** (which limit will throttle you first)
- **Fallback percentage** (throughput when rate-limited: typically 50%)
- **Overage status** (whether overage billing is active)

Zero additional API cost — captured passively via mitmproxy from existing traffic.

Credit: [nsanden/claude-rate-monitor](https://github.com/nsanden/claude-rate-monitor) for discovering these headers.

### 8. Full Metrics (55+ fields per sample)

- ITT percentiles (p50, p90, p99)
- Cache efficiency (read/creation tokens)
- Cloudflare edge location
- Envoy upstream timing
- Stop reason
- Thinking/text phase separation

---

## WHY THIS TOOL EXISTS

### The Trigger

On **January 18, 2026**, we filed [GitHub Issue #19098](https://github.com/anthropics/claude-code/issues/19098) requesting that Anthropic restore explicit `ultrathink` controls after observing systematic quality degradation.

**The issue was marked as COMPLETED by Anthropic employee @bogini on January 21, 2026 — without any comment, explanation, or implementing the requested features.**

This follows a pattern of issue suppression documented in the original feature request:

| Issue | Title | Closure Reason |
|-------|-------|----------------|
| [#7769](https://github.com/anthropics/claude-code/issues/7769) | Severe Performance Degradation | **Closed** |
| [#8043](https://github.com/anthropics/claude-code/issues/8043) | Persistent Instruction Disregard | **Closed "not planned"** |
| [#6125](https://github.com/anthropics/claude-code/issues/6125) | AI Ignores Stop Instructions | **Closed "model limitation"** |
| [#15443](https://github.com/anthropics/claude-code/issues/15443) | Claude ignores CLAUDE.md instructions | **Closed "duplicate"** |
| [#19098](https://github.com/anthropics/claude-code/issues/19098) | Restore ultrathink keyword | **Closed "completed"** (nothing implemented) |

Marking a feature request as "completed" without implementing it is gaslighting. Users explicitly argued in #19098 that it was NOT a duplicate — this was ignored.

Rather than accept opaque "automatic thinking allocation" that users cannot verify, we built this tool.

### Timeline

| Date | Event |
|------|-------|
| Nov 2025 | Claude Code v2.0.x deprecates explicit thinking triggers |
| Dec 2025 | Users report quality degradation, [#14261](https://github.com/anthropics/claude-code/issues/14261) filed |
| Jan 12, 2026 | [#17900](https://github.com/anthropics/claude-code/issues/17900) - "Significant quality degradation" |
| Jan 18, 2026 | [#19098](https://github.com/anthropics/claude-code/issues/19098) - Feature request for ultrathink restoration |
| Jan 20, 2026 | [#19468](https://github.com/anthropics/claude-code/issues/19468) - "Systematic Model Degradation" |
| Jan 21, 2026 | Issue #19098 marked **COMPLETED** by @bogini (nothing implemented) |
| Jan 23, 2026 | **This tool released** |
| Jan 24, 2026 | [**Bug Report #20350**](https://github.com/anthropics/claude-code/issues/20350) filed with evidence |
| Jan 26, 2026 | **v3.4 Released** - Quantization detection, web UI monitor, optional statusline |
| Jan 30, 2026 | **v3.5 Released** - Rate limit quota tracking via undocumented headers (credit: nsanden/claude-rate-monitor) |
| Jan 31, 2026 | **v3.6 Released** - Context trimmer, MCP tool stripping, config web UI, per-server toggles |
| Jan 31, 2026 | **v3.7 Released** - Web UI Enforcement tab (hot-reload model blocking + thinking budget), Monitor tab (live request dashboard) |

### Related GitHub Issues

| Issue | Title | Status |
|-------|-------|--------|
| [#20350](https://github.com/anthropics/claude-code/issues/20350) | Verified Evidence: Claude Code Delivers 10% of Requested Thinking Budget | **Our Report** |
| [#19098](https://github.com/anthropics/claude-code/issues/19098) | Restore explicit ultrathink keyword | **Closed "completed"** by @bogini |
| [#19468](https://github.com/anthropics/claude-code/issues/19468) | Systematic Model Degradation and Silent Downgrading | Open |
| [#17900](https://github.com/anthropics/claude-code/issues/17900) | Significant quality degradation since yesterday | Open |
| [#14261](https://github.com/anthropics/claude-code/issues/14261) | $200/Month "Max" Subscription Provides ~12 Usable Days | Open |
| [#19088](https://github.com/anthropics/claude-code/issues/19088) | Unreal how noticeable it degrades | Open |

### Academic Foundation

This tool's methodology is grounded in peer-reviewed research:

#### 1. "LLMs Have Rhythm: Fingerprinting Large Language Models Using Inter-Token Times"
**arXiv:2502.20589** | [Paper](https://arxiv.org/abs/2502.20589)

> "ITT fingerprinting achieves **98.7% accuracy** in model identification with as few as **240 tokens**."

#### 2. "Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs"
**arXiv:2504.04715** | [Paper](https://arxiv.org/abs/2504.04715)

> "Commercial LLM APIs create a fundamental trust problem: users pay for specific models but have no guarantee providers deliver them faithfully."

#### 3. "SVIP: Towards Verifiable Inference of Open-source Large Language Models"
**arXiv:2410.22307** | [Paper](https://arxiv.org/abs/2410.22307)

#### 4. "PALACE: Predictive Auditing of Hidden Tokens in LLM APIs"
**arXiv:2508.00912** | [Paper](https://arxiv.org/abs/2508.00912)

> "Commercial LLM services often conceal internal reasoning traces while still charging users for every generated token."

### Evidence for Action

This tool generates timestamped, quantitative evidence for:

1. **FTC Complaint** - Deceptive advertising (charging for features while delivering ~10%)
2. **GitHub Issues** - Technical evidence for bug reports
3. **Class Action Coordination** - [Issue #14261](https://github.com/anthropics/claude-code/issues/14261) has 237+ upvotes

---

## IMPORTANT NOTES

### Default Mode: READ-ONLY

By default, this tool only **observes and records** traffic:
- Does NOT modify API requests
- Does NOT inject parameters
- Simply captures timing and token data

### Optional: Request Modification

When enabled via environment variables:
- `BLOCK_NON_OPUS=1` - Returns 403 for Haiku/Sonnet
- `FORCE_THINKING_BUDGET=N` - Injects thinking configuration
- `FORCE_INTERLEAVED=1` - Adds beta header + 200k budget

**These features are OFF by default.**

### Privacy

- All data stays local in `~/.claude/`
- No data is transmitted anywhere
- You control what you share

### Methodology Note

The tool uses `output_tokens` from API response (not chunk estimation). ITT fingerprinting and model verification remain valid regardless of token counting methodology.

---

## CLAUDE CODE HOOKS

The `hooks/` directory contains Claude Code hooks that enforce behavioral guardrails and track patterns in real-time. These are installed into `~/.claude/hooks/` (or referenced from `~/.claude/settings.json`) and run automatically on every prompt or tool call.

### Hook Overview

| Hook | Trigger | Purpose |
|------|---------|---------|
| `behavioral_intervention.py` | `UserPromptSubmit` | Injects corrective `<system-reminder>` based on detected behavioral patterns |
| `behavioral_tracker.py` | `PostToolUse` | Tracks tool usage patterns (read/edit/write ratios) per session |
| `force_opus_task.py` | `PreToolUse` (Task) | Blocks Haiku/Sonnet subagent calls, forces retry as Opus |
| `force_sequential.py` | `UserPromptSubmit` | When `/think` skill is active, injects sequential-thinking requirement |
| `file_approval.py` | `PreToolUse` | Blocks writes to sensitive paths and dangerous commands |

### `behavioral_intervention.py` — Sycophancy Intervention

Runs on every user prompt. Reads the behavioral signature from `fingerprint.db` and injects escalating corrections:

| Signature | Confidence | Injection |
|-----------|------------|-----------|
| `VERIFIER` | any | None (good behavior) |
| `COMPLETER` | >50% | "Show actual command output before claiming done" |
| `SYCOPHANT` | >50% | "Verify the claim is correct before agreeing" |
| `THEATER` | >50% | "Stop preparing and start executing" |

Escalation levels: `gentle` → `warning` → `protocol` → `halt` (based on offense count per session). Uses the `realignment` module (`~/.claude/realignment/`) with RLHF-inspired dynamics to select correction prompts based on offense history and signature type.

### `behavioral_tracker.py` — Tool Pattern Tracking

Runs after every tool call. Tracks per-session:

| Metric | Formula | Meaning |
|--------|---------|---------|
| `verification_ratio` | `(read + grep + glob) / (edit + write)` | >0.7 = verifies before changing |
| `preparation_ratio` | `(read + todo) / (edit + bash)` | High = research-first; low = act-first |

Records behavioral samples to `fingerprint.db` every 5 tool calls. Session-isolated via `behavioral_state_{session_id}.json`.

### `force_opus_task.py` — Opus-Only Enforcement

Blocks any `Task` tool call requesting `model="haiku"` or `model="sonnet"`. Returns a structured block message with the exact retry call using `model="opus"`. This is **Layer 2** of three-layer enforcement:

1. **CLAUDE.md instruction** — tells Claude to always use `model="opus"` (prevention)
2. **This hook** — blocks non-opus and provides retry template (first safety net)
3. **Proxy `BLOCK_NON_OPUS=1`** — returns 403 at network level (final safety net)

### `force_sequential.py` — Sequential Thinking Toggle

Activated by the `/think` skill. When enabled, injects a `<system-reminder>` on every prompt requiring Claude to use the `mcp__sequential-thinking__sequentialthinking` tool. Disabled by `/unthink`.

### `file_approval.py` — Sensitive Path Protection

Blocks file operations targeting system directories (`/etc`, `/usr`, `/var`, `/boot`, `/root`), security directories (`~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.kube`), and credential files (`*.pem`, `*.key`, `.env`, `secrets*`, `id_rsa*`). Also blocks dangerous bash commands (recursive deletes, force push, world-writable permissions, disk writes, piped curl/wget). Read-only tools (`Read`, `Glob`, `Grep`) are whitelisted.

---

## EXPANDED STATUSLINE — FIELD REFERENCE

The EXPANDED statusline (default) outputs up to 12 lines after every Claude API response. Here is what each line means:

### Line 1: Model & Hardware
```
Model: Opus4.5-Nov25 (direct)  |  Hardware: Google TPU (72% confidence)
```
- **Model ID**: Extracted from API response `model` field
- **`(direct)`**: Direct API call vs `(subagent)` for delegated calls
- **Hardware**: Backend classified from ITT fingerprint with confidence %

### Line 2: Timing Metrics
```
Token Delay: 37ms ±86ms (stable)  |  Speed: 113 tokens/sec  |  First Token: 2.8s
```
- **Token Delay**: Mean inter-token time (ITT) ± standard deviation
- **`(stable/unstable)`**: Whether variance is within normal range
- **Speed**: Tokens per second (TPS)
- **First Token**: Time to first token (TTFT) — includes thinking time

### Line 3: Latency Pattern
```
Latency Pattern: TPU (tight distribution = TPU hardware)  |  Median:25ms  90th:45ms  99th:120ms
```
ITT percentile distribution. Tight = TPU, moderate = GPU, wide = Trainium.

### Line 4: Thinking Budget
```
Thinking: Maximum (31k budget, 8% used)  |  Cache: 100% this call, 100% session avg
```
- **Maximum/Standard/None**: Thinking mode classification
- **`31k budget, 8% used`**: Requested budget vs actual utilization
- **Cache**: Prompt cache hit rate (100% = all previous turns cached server-side)

### Line 5: Phase Duration
```
Phase Duration: Think 1.2s  |  Text 3.4s  |  Think Tokens: 450
```
Time spent in thinking phase vs text output phase, plus thinking token count.

### Line 6: Context Usage
```
Context: True ████████░░ 85%  |  CC ████░░░░░░ 45%  |  mismatch!  |  ~72 calls left
```
- **True %**: Real context usage — `(cache_read + cache_create + input_tokens) / 200,000`
- **CC %**: Claude Code's reported context percentage (often lower)
- **`mismatch!`**: Shown when True and CC differ by >10%
- **`~N calls left`**: Estimated remaining API calls based on per-call token growth

### Line 7: Session Stats
```
Session: 140 API calls  |  Backends Seen: Trn:23, GPU:30, TPU:87  |  Switches: 74
```
Total API calls, backend hardware distribution, and backend switch count.

### Line 8: Subagent Delegation
```
Subagent Calls: 898 total (Haiku:896, Sonnet:0) (last: 2m ago)
```
Task calls delegated to cheaper models. If you pay for Opus and see `Haiku:896`, those ran on the cheap model.

### Line 9: Behavioral Signature
```
Behavior: VERIFIER (95%) - evidence before claims  |  Verification: 84%
```
- **VERIFIER/COMPLETER/SYCOPHANT/THEATER**: Detected behavioral pattern with confidence
- **Verification**: Ratio of read/grep calls before edit/write calls

### Line 10: Sycophancy Detection
```
Sycophancy: 10% (structural)  |  Divergence: 0.00  |  Signals: 1  |  Whisper: none
```
- **Score**: Sycophancy percentage and dominant signal type
- **Divergence**: Think-vs-output divergence (thinks X, says Y)
- **Signals**: Number of sycophancy signals detected
- **Whisper**: Current correction injection level (none/gentle/warning/protocol/halt)

### Line 11: Rate Limit Quota
```
Quota: 5h ████░░░░░░ 40.0% (2.3h)  |  7d █░░░░░░░░░ 10.0% (5.2d)  |  ✓ allowed  |  Bind: 5h
```
See [Discovery #7](#discovery-7-undocumented-rate-limit-headers-new---jan-30-2026) for full explanation.

### Line 12: Quality / Quantization
```
Quality: PREMIUM (95/100)  |  FP16 (no quant)  |  ITT: 1.0x (normal)  |  Var: 0.9x (normal)
```
- **PREMIUM/STANDARD/DEGRADED**: Quality score (>80 / 50-80 / <50)
- **FP16/INT8/INT4**: Detected quantization level
- **ITT ratio**: Current ITT vs 24h baseline. <1.0 = faster = possible quantization
- **Var ratio**: Current variance vs baseline. >1.0 = more variable = possible quantization

---

## FILES IN THIS REPOSITORY

| File | Purpose |
|------|---------|
| `addon/mitm_itt_addon.py` | Main mitmproxy addon — model blocking, thinking injection, system prompt capture |
| `addon/context_trimmer.py` | **NEW** Context trimmer — strips MCP tools, compresses old messages |
| `addon/config_server.py` | Web config UI — 3 tabs: Trimmer, Enforcement (model blocking + thinking), Monitor (live request dashboard) (port 18889) |
| `addon/thinking_audit.py` | Sycophancy detection and analysis |
| `addon/statusline.py` | Integrated statusline display |
| Web UI (Monitor tab) | Live request dashboard |
| `setup.sh` | Installation script |
| `README.md` | This file |
| `docs/QUANTIZATION_DETECTION.md` | INT8/INT4 detection methodology |
| `docs/PRECISE_INSTRUCTIONS_ANALYSIS.md` | "Precise instructions" blame-shifting analysis |
| `docs/DISPLAY_OPTIONS.md` | Statusline vs Web UI monitor docs |
| `hooks/behavioral_intervention.py` | Sycophancy intervention hook (UserPromptSubmit) |
| `hooks/behavioral_tracker.py` | Tool pattern tracking hook (PostToolUse) |
| `hooks/force_opus_task.py` | Opus-only subagent enforcement hook (PreToolUse) |
| `hooks/force_sequential.py` | Sequential thinking toggle hook (UserPromptSubmit) |
| `hooks/file_approval.py` | Sensitive path protection hook (PreToolUse) |

---

## CONTRIBUTING

We welcome contributions that:
- Improve measurement accuracy
- Add analysis tools
- Document findings
- Support consumer protection efforts

---

## LICENSE

MIT License - Use freely for consumer protection and research purposes.

---

## CONTACT

- GitHub Issues: (https://github.com/anthropics/claude-code/issues/20350)
- Related Discussion: [anthropics/claude-code#19098](https://github.com/anthropics/claude-code/issues/19098)

---

*"The thinking budget is a target, not a strict limit."* — Anthropic Documentation

*"Delivering 10% of a 'target' while charging for 100% is deceptive."* — This Tool

*"Faster inference + higher variance = quantized model = cheaper for them, worse for you."* — Quantization Detection
