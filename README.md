
<img width="1119" height="343" alt="claude-detector2" src="https://github.com/user-attachments/assets/71805db2-47ac-4a50-bec0-fb7e7a214306" />


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

**One command to get what you pay for:**
```bash
BLOCK_NON_OPUS=1 FORCE_THINKING_BUDGET=31999 mitmdump -s mitm_itt_addon.py -p 18888
```

### 👁️ VISIBILITY - See What's Really Happening

| Feature | What You See |
|---------|--------------|
| **Real Model** | Detect if you're getting Opus or secretly served Haiku |
| **Real Thinking** | Actual tokens delivered vs requested (spoiler: ~10%) |
| **Quantization** | Detect INT8/INT4 compressed models (faster but dumber) |
| **Backend Hardware** | Trainium/TPU/GPU classification with confidence % |
| **Subagent Delegation** | How many calls secretly go to Haiku (spoiler: 99%) |
| **UI vs API Mismatch** | Claude Code shows 83% context, API shows 5% |

### 📊 TWO DISPLAY OPTIONS

| Option | Description | Usage |
|--------|-------------|-------|
| **Statusline** | Integrated into Claude Code output after each response | Enabled by default |
| **Terminal Monitor** | Standalone live dashboard (refreshes every 2s) | `./claude-monitor` |

**Statusline Output:**
```
Model: Opus4.5-Nov25 (direct)  |  Hardware: Google TPU (72%)
ITT: 37ms ±86ms  |  Speed: 113 tokens/sec  |  TTFT: 2.8s
Thinking: 🔴Maximum (31k budget, 8% used)  |  Cache: 100%
Quality: 🟡STANDARD (55/100)  |  ⚠ QUANT: INT8 (57%)  |  ITT: 0.8x baseline
```

**Terminal Monitor Output:**
```
═══ Claude ITT Fingerprint Monitor ═══

Model: claude-opus-4-5-20251101
Backend: tpu (72%)
ITT: 37ms ±86ms  |  TPS: 113  |  TTFT: 2.8s

─── Quality Analysis ───
ITT Ratio: 0.76x baseline  |  Variance: 1.27x
Quantization: INT8 (57%)

─── Session ───
Samples: 14000 total, 185 last hour
Backends: gpu:42, tpu:110, trainium:33
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

# Optional: Start terminal monitor (Terminal 2)
./claude-monitor

# Run Claude Code through proxy (Terminal 3)
export HTTPS_PROXY=http://127.0.0.1:18888
claude
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `BLOCK_NON_OPUS` | `0` | Set to `1` to block Haiku/Sonnet requests (returns 403) |
| `FORCE_THINKING_MODE` | `0` | Set to `1` to force thinking enabled on all requests |
| `FORCE_THINKING_BUDGET` | - | Force specific budget (e.g., `31999`). Set to `0` to disable. |
| `FORCE_INTERLEAVED` | `0` | Set to `1` to enable interleaved thinking with 200k budget |
| `CLAUDE_STATUSLINE_DISABLED` | `0` | Set to `1` to disable integrated statusline |

### Usage Examples

```bash
# Default: Monitoring only (read-only, no modifications)
mitmdump -s mitm_itt_addon.py -p 18888

# RECOMMENDED: Block cheap models + force maximum thinking
BLOCK_NON_OPUS=1 FORCE_THINKING_BUDGET=31999 mitmdump -s mitm_itt_addon.py -p 18888

# Force interleaved thinking (200k budget)
FORCE_INTERLEAVED=1 mitmdump -s mitm_itt_addon.py -p 18888

# Full protection: Block non-Opus + Force thinking + Interleaved
BLOCK_NON_OPUS=1 FORCE_THINKING_MODE=1 FORCE_INTERLEAVED=1 mitmdump -s mitm_itt_addon.py -p 18888

# Use terminal monitor instead of statusline
CLAUDE_STATUSLINE_DISABLED=1 mitmdump -s mitm_itt_addon.py -p 18888
# Then in another terminal: ./claude-monitor
```

### File Locations

| File | Purpose |
|------|---------|
| `mitm_itt_addon.py` | Main mitmproxy addon |
| `claude-monitor` | Standalone terminal monitor |
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

### Discovery #3: UI vs API Context Mismatch

| Metric | Claude Code UI | Actual API | Phantom Usage |
|--------|---------------|------------|---------------|
| Context Usage | 21% | 0% | **21% phantom** |
| Context Usage | 83% | 5% | **78% phantom** |
| Context Usage | 74% | 0% | **74% phantom** |

The UI shows inflated context that doesn't match API reality.

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

See `PRECISE_INSTRUCTIONS_ANALYSIS.md` for full analysis.

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

### 7. Full Metrics (45+ fields per sample)

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

**The issue was closed without implementing the requested transparency features.**

Rather than accept opaque "automatic thinking allocation" that users cannot verify, we built this tool.

### Timeline

| Date | Event |
|------|-------|
| Nov 2025 | Claude Code v2.0.x deprecates explicit thinking triggers |
| Dec 2025 | Users report quality degradation, [#14261](https://github.com/anthropics/claude-code/issues/14261) filed |
| Jan 12, 2026 | [#17900](https://github.com/anthropics/claude-code/issues/17900) - "Significant quality degradation" |
| Jan 18, 2026 | [#19098](https://github.com/anthropics/claude-code/issues/19098) - Feature request for ultrathink restoration |
| Jan 20, 2026 | [#19468](https://github.com/anthropics/claude-code/issues/19468) - "Systematic Model Degradation" |
| Jan 23, 2026 | Issue #19098 closed without transparency features |
| Jan 23, 2026 | **This tool released** |
| Jan 24, 2026 | [**Bug Report #20350**](https://github.com/anthropics/claude-code/issues/20350) filed with evidence |
| Jan 26, 2026 | **v3.4 Released** - Quantization detection, terminal monitor, optional statusline |

### Related GitHub Issues

| Issue | Title | Status |
|-------|-------|--------|
| [#20350](https://github.com/anthropics/claude-code/issues/20350) | Verified Evidence: Claude Code Delivers 10% of Requested Thinking Budget | **Our Report** |
| [#19098](https://github.com/anthropics/claude-code/issues/19098) | Restore explicit ultrathink keyword | **Closed** |
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

## FILES IN THIS REPOSITORY

| File | Purpose |
|------|---------|
| `mitm_itt_addon.py` | Main mitmproxy addon |
| `claude-monitor` | Standalone terminal monitor |
| `setup.sh` | Installation script |
| `README.md` | This file |
| `QUANTIZATION_DETECTION.md` | INT8/INT4 detection methodology |
| `PRECISE_INSTRUCTIONS_ANALYSIS.md` | "Precise instructions" blame-shifting analysis |
| `DISPLAY_OPTIONS.md` | Statusline vs terminal monitor docs |
| `ARXIV_PAPER.md` | Research paper draft |

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

- GitHub Issues: [claude-thinking-audit](https://github.com/anthropics/claude-thinking-audit/issues)
- Related Discussion: [anthropics/claude-code#19098](https://github.com/anthropics/claude-code/issues/19098)

---

*"The thinking budget is a target, not a strict limit."* — Anthropic Documentation

*"Delivering 10% of a 'target' while charging for 100% is deceptive."* — This Tool

*"Faster inference + higher variance = quantized model = cheaper for them, worse for you."* — Quantization Detection
