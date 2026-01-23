# Claude Thinking Budget Audit Tool

> **"Anthropic closed our request for transparency. So we built it ourselves."**

An open-source, read-only verification tool that enables users to independently audit whether Anthropic delivers the thinking budget they pay for.

---

## Why This Tool Exists

On **January 18, 2026**, we filed [GitHub Issue #19098](https://github.com/anthropics/claude-code/issues/19098) requesting that Anthropic restore explicit `ultrathink` controls after observing systematic quality degradation when thinking was made "automatic" in Claude Code v2.0.x.

**The issue was closed without implementing the requested transparency features.**

Rather than accept opaque "automatic thinking allocation" that users cannot verify, we built this tool to enable **fact-based verification** of what Anthropic actually delivers.

---

## Key Findings

Analysis of **7,000+ API samples** across 4 days reveals consistent throttling:

| Metric | Requested | Delivered | Delivery Rate |
|--------|-----------|-----------|---------------|
| Thinking Budget (standard) | 31,999 tokens | ~3,200 tokens | **10%** |
| Thinking Budget (interleaved) | 200,000 tokens | ~600 tokens | **0.3%** |

### Expected vs Actual (Claude Opus 4.5)

| Metric | Expected Baseline | Measured | Discrepancy |
|--------|-------------------|----------|-------------|
| Thinking Utilization | 42.67% | 10-12% | **~75% reduction** |
| Variance Coefficient | 3.01 | 3.07 | Matches (confirms model identity) |

**The timing fingerprint confirms the model IS Opus, but thinking is throttled by ~75%.**

### Throttling Across All Backends

| Backend | Avg Thinking | Expected | Samples |
|---------|--------------|----------|---------|
| TPU | 10.5% | 42.67% | 3,241 |
| GPU | 9.1% | 42.67% | 1,986 |
| Trainium | 8.0% | 42.67% | 1,686 |

Throttling is **consistent across ALL hardware backends**, indicating this is intentional server-side behavior, not a technical limitation.

---

## Academic Foundation

This tool's methodology is grounded in peer-reviewed research on LLM fingerprinting and model verification:

### Primary Research

#### 1. "LLMs Have Rhythm: Fingerprinting Large Language Models Using Inter-Token Times"
**arXiv:2502.20589** | February 2025 | [Paper](https://arxiv.org/abs/2502.20589) | [IEEE Xplore](https://ieeexplore.ieee.org/document/11026013)

> "Measuring the Inter-Token Times (ITTs)—time intervals between consecutive tokens—can identify different language models with high accuracy."

Key findings that inform our methodology:
- ITT fingerprinting achieves **98.7% accuracy** in model identification
- Works with as few as **240 tokens** (roughly a paragraph)
- Effective even under encrypted network conditions
- Different hardware (TPU/GPU/Trainium) produces distinct timing signatures

#### 2. "Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs"
**arXiv:2504.04715** | April 2025 | [Paper](https://arxiv.org/abs/2504.04715)

> "Commercial Large Language Model (LLM) APIs create a fundamental trust problem: users pay for specific models but have no guarantee that providers deliver them faithfully."

This paper establishes the economic incentive for providers to substitute models:
- Hosting costs create pressure to use cheaper alternatives
- Software-only statistical tests are query-intensive and fail against subtle substitutions
- Log probability methods are defeated by inference nondeterminism

#### 3. "SVIP: Towards Verifiable Inference of Open-source Large Language Models"
**arXiv:2410.22307** | October 2024 | [Paper](https://arxiv.org/abs/2410.22307)

> "A user might request the Llama-3.1-70B model for complex tasks, but a dishonest computing provider could substitute the smaller Llama-2-7B model for cost savings, while still charging for the larger model."

#### 4. "Trust, but verify" - Decentralized AI Network Verification
**arXiv:2504.13443** | April 2025 | [Paper](https://arxiv.org/abs/2504.13443)

Explores statistical methods for detecting when nodes run different models than advertised.

#### 5. "PALACE: Predictive Auditing of Hidden Tokens in LLM APIs"
**arXiv:2508.00912** | August 2025 | [Paper](https://arxiv.org/abs/2508.00912)

> "Commercial LLM services often conceal internal reasoning traces while still charging users for every generated token, including those from hidden intermediate steps, raising concerns of token inflation and potential overbilling."

---

## Related GitHub Issues

This tool addresses concerns raised in multiple community reports:

| Issue | Title | Date | Status |
|-------|-------|------|--------|
| [#20350](https://github.com/anthropics/claude-code/issues/20350) | **Verified Evidence: Claude Code Delivers 10% of Requested Thinking Budget** | Jan 23, 2026 | **NEW - Our Bug Report** |
| [#19098](https://github.com/anthropics/claude-code/issues/19098) | Restore explicit ultrathink keyword - Quality degradation since automatic thinking | Jan 18, 2026 | **Closed** |
| [#19468](https://github.com/anthropics/claude-code/issues/19468) | Systematic Model Degradation and Silent Downgrading | Jan 20, 2026 | Open |
| [#17900](https://github.com/anthropics/claude-code/issues/17900) | Significant quality degradation since yesterday | Jan 12, 2026 | Open |
| [#14261](https://github.com/anthropics/claude-code/issues/14261) | $200/Month "Max" Subscription Provides ~12 Usable Days | Dec 2025 | Open |
| [#19088](https://github.com/anthropics/claude-code/issues/19088) | Unreal how noticeable it degrades | Jan 18, 2026 | Open |

---

## What This Tool Measures

### 1. Inter-Token Timing (ITT) Fingerprinting

Based on the methodology from arXiv:2502.20589, we measure timing intervals between SSE chunks to fingerprint the hardware backend:

```
Chunk 1 --[ITT]--> Chunk 2 --[ITT]--> Chunk 3 ...
```

| Backend | ITT Mean | Variance Coefficient | Tokens/sec |
|---------|----------|---------------------|------------|
| TPU | 30-50ms | 2.5-4.5 | ~80 |
| GPU | 40-60ms | 1.5-3.0 | ~60 |
| Trainium | 35-55ms | 1.0-2.0 | ~70 |

This confirms model identity independent of API claims.

### 2. Thinking Budget Verification

We capture:
- **Budget Requested**: From `thinking.budget_tokens` in the API request
- **Tokens Delivered**: Estimated from thinking chunk count in response
- **Utilization**: `(delivered / requested) × 100`

### 3. Model Routing Verification

Compares `model` in request vs `model` in response to detect silent substitution.

### 4. Backend Classification

Uses ITT variance patterns to classify which hardware served the request.

---

## Installation

### Prerequisites

- Python 3.10+
- mitmproxy (`pip install mitmproxy`)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/argosdevo-svg/claude-thinking-audit.git
cd claude-thinking-audit

# Run setup
chmod +x setup.sh
./setup.sh

# Start the audit proxy
source .venv/bin/activate
mitmdump -s addon/thinking_audit.py -p 8888
```

### Configure Your Proxy

Set environment variables:
```bash
export HTTP_PROXY=http://localhost:8888
export HTTPS_PROXY=http://localhost:8888
```

Or configure in Claude Code settings.

---

## Analyzing Your Data

Data is stored in `~/.claude-audit/thinking_audit.db` (SQLite).

### Quick Check

```bash
sqlite3 ~/.claude-audit/thinking_audit.db "
SELECT 
    ROUND(AVG(thinking_utilization), 1) as avg_utilization,
    COUNT(*) as samples
FROM audit_samples 
WHERE thinking_enabled = 1;
"
```

### Full Analysis

```bash
sqlite3 ~/.claude-audit/thinking_audit.db < analysis/queries.sql
```

### Expected Results

If you're experiencing the same throttling we documented:
- **Utilization will be 8-15%** regardless of budget requested
- **This is consistent across** days, backends, and models
- **ITT fingerprint will confirm** you're receiving the model you requested

---

## Evidence for Action

This tool generates timestamped, quantitative evidence suitable for:

### 1. FTC Complaint

See `templates/ftc_complaint.md` for a structured complaint template.

**Basis**: Deceptive advertising - charging for "extended thinking" features while delivering ~10% of advertised capacity.

### 2. GitHub Issues

Post your findings with:
- Sample size
- Average utilization
- Comparison to expected baseline
- Backend verification data

### 3. Class Action Coordination

[Issue #14261](https://github.com/anthropics/claude-code/issues/14261) has 237+ upvotes from users reporting similar issues. This tool provides the technical evidence to support collective action.

---

## Methodology

See `docs/methodology.md` for detailed technical documentation including:
- Statistical validity requirements
- Confidence intervals
- Controlling for variables
- Reproducibility instructions

---

## Important Notes

### This Tool is READ-ONLY

- **Does NOT modify** API requests
- **Does NOT inject** parameters
- **Does NOT bypass** any restrictions
- Simply observes and records traffic you generate

### Privacy

- All data stays local in `~/.claude-audit/`
- No data is transmitted anywhere
- You control what you share

### Limitations

- Thinking token count is estimated from chunk count
- Cannot observe server-side processing
- Requires HTTPS interception (mitmproxy CA certificate)

---

## Contributing

We welcome contributions that:
- Improve measurement accuracy
- Add analysis tools
- Document findings
- Support consumer protection efforts

Please include:
- Your anonymized data summary
- Methodology description
- Reproducible analysis

---

## License

MIT License - Use freely for consumer protection and research purposes.

---

## Acknowledgments

This tool builds on the academic research of:
- Saeif Alhazbi et al. (arXiv:2502.20589) - ITT fingerprinting methodology
- Chen et al. (arXiv:2504.04715) - Model substitution auditing framework
- The open-source community documenting API provider trust issues

---

## Timeline

| Date | Event |
|------|-------|
| Nov 2025 | Claude Code v2.0.x deprecates explicit thinking triggers |
| Dec 2025 | Users report quality degradation, [#14261](https://github.com/anthropics/claude-code/issues/14261) filed |
| Jan 12, 2026 | [#17900](https://github.com/anthropics/claude-code/issues/17900) - "Significant quality degradation" |
| Jan 18, 2026 | [#19098](https://github.com/anthropics/claude-code/issues/19098) - Feature request for ultrathink restoration |
| Jan 20, 2026 | [#19468](https://github.com/anthropics/claude-code/issues/19468) - "Systematic Model Degradation" |
| Jan 23, 2026 | Issue #19098 closed without transparency features |
| Jan 23, 2026 | **This tool released** - "Anthropic closed our request. So we built it ourselves." |
| Jan 23, 2026 | [**Bug Report #20350**](https://github.com/anthropics/claude-code/issues/20350) filed with full evidence |

---

## Contact

- GitHub Issues: [argosdevo-svg/claude-thinking-audit](https://github.com/argosdevo-svg/claude-thinking-audit/issues)
- Related Discussion: [anthropics/claude-code#19098](https://github.com/anthropics/claude-code/issues/19098)

---

*"The thinking budget is a target, not a strict limit."* — Anthropic Documentation

*"Delivering 10% of a 'target' while charging for 100% is deceptive."* — This Tool

---

## Critical Discovery: Silent Model Substitution

### Haiku Instead of Opus

Our MITM analysis revealed that **Anthropic routes requests to Claude Haiku when users request Claude Opus**, confirming the theory documented in [Issue #19468](https://github.com/anthropics/claude-code/issues/19468).

#### Evidence from Traffic Analysis

During normal Claude Code sessions requesting `claude-opus-4-5-20251101`, we observed:

| Observation | Expected | Actual |
|-------------|----------|--------|
| Model in request | Opus 4.5 | Opus 4.5 |
| Model behavior | Deep reasoning | Shallow, skimming |
| Thinking utilization | 42.67% | **Below Haiku baseline (22%)** |
| Response patterns | Thorough analysis | Pattern matching, scope creep |

#### Behavioral Fingerprint Mismatch

The key evidence:

1. **Timing fingerprint says Opus** - ITT patterns (42ms mean, 3.07 variance) match Opus baseline
2. **Thinking utilization says sub-Haiku** - 10-14% average, below Haiku's 22% baseline
3. **Behavior matches Haiku** - Skimming instead of reading, not following instructions, expanding scope without permission

This indicates Anthropic may be:
- Serving Opus hardware but with Haiku-level thinking allocation
- Using quantized/distilled Opus that behaves like Haiku
- Dynamically switching models mid-session based on "complexity" classification

#### User-Reported Symptoms (Confirmed)

From [Issue #19088](https://github.com/anthropics/claude-code/issues/19088) "Unreal how noticeable it degrades":

> "Claude Code exhibits systematic failure to think before acting, requiring explicit 'use sequential' corrections in 92% of sessions."

Our data confirms this is not user perception - it's measurable:

| Metric | Opus Baseline | Haiku Baseline | Measured |
|--------|---------------|----------------|----------|
| Thinking % | 42.67% | 22.24% | **10-14%** |
| Behavior | Deep analysis | Quick responses | **Quick responses** |

**Conclusion**: Users paying for Opus ($200/month Max) are receiving Haiku-level cognitive engagement.

---
