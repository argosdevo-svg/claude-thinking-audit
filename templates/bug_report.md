# [BUG] Verified Evidence: Claude Code Delivers 10% of Requested Thinking Budget While Charging Full Price

## Summary

Independent MITM traffic analysis of **7,000+ API requests** over 4 days confirms that Claude Code delivers approximately **10% of the requested thinking budget** regardless of subscription tier or explicit budget configuration. Users paying $200/month for Max subscriptions are receiving Haiku-level cognitive engagement while being charged for Opus.

This is not speculation. This is measured, timestamped, reproducible data.

---

## Environment

- **Claude Code Version**: 2.1.x+
- **Subscription**: Max ($200/month) × 2 accounts
- **Model Requested**: `claude-opus-4-5-20251101`
- **Thinking Budget Requested**: 31,999 tokens (ultrathink tier)
- **Analysis Period**: January 20-23, 2026
- **Sample Size**: 7,000+ API requests
- **Methodology**: Read-only MITM proxy capturing request/response metrics

---

## The Evidence

### 1. Thinking Budget Throttling (Quantified)

| What We Requested | What We Received | Delivery Rate |
|-------------------|------------------|---------------|
| 31,999 tokens | ~3,200 tokens | **10%** |
| 200,000 tokens (interleaved) | ~600 tokens | **0.3%** |

**This is consistent across 7,000+ requests over 4 days.**

### 2. Below-Haiku Performance on Opus Requests

| Model | Expected Thinking | Measured Thinking | Status |
|-------|-------------------|-------------------|--------|
| Opus 4.5 | 42.67% | **10-14%** | ❌ FAIL |
| Haiku 4.5 | 22.24% | — | — |

**Users requesting Opus receive thinking utilization BELOW the Haiku baseline.**

### 3. Consistent Across ALL Backends

| Backend | Avg Thinking | Expected | Samples |
|---------|--------------|----------|---------|
| TPU | 10.5% | 42.67% | 3,241 |
| GPU | 9.1% | 42.67% | 1,986 |
| Trainium | 8.0% | 42.67% | 1,686 |

**Throttling occurs on every backend type. This is not a hardware limitation.**

### 4. Timing Fingerprint Confirms Model Identity

Using the methodology from [arXiv:2502.20589](https://arxiv.org/abs/2502.20589) "LLMs Have Rhythm":

| Metric | Opus Baseline | Our Measurement | Match |
|--------|---------------|-----------------|-------|
| ITT Mean | 42ms | 41.4ms | ✅ YES |
| Variance Coef | 3.01 | 3.07 | ✅ YES |
| Tokens/sec | 80 | 74 | ✅ YES |

**The hardware fingerprint confirms we ARE hitting Opus infrastructure.**
**But the thinking allocation is throttled to sub-Haiku levels.**

### 5. Server-Side Throttling Confirmed

We attempted to force full thinking budget via request modification:

```
Request: thinking.budget_tokens = 200,000
Response: ~600 tokens used (0.3%)
```

**Anthropic's servers ignore the budget parameter and allocate what THEY decide.**

Per Anthropic's own documentation:
> "The thinking budget is a target, not a strict limit."

Delivering 10% of a "target" while charging for 100% is deceptive.

---

## Behavioral Impact (User-Visible Symptoms)

The throttled thinking manifests as:

- ❌ **Skimming instead of reading** - Claude scans files rather than comprehending them
- ❌ **Scope creep** - Expands tasks without permission (e.g., running git commands when asked to "read files")
- ❌ **Not following instructions** - Ignores explicit directives in CLAUDE.md
- ❌ **Requires repeated corrections** - Users report needing "use sequential" in 92% of sessions ([#19088](https://github.com/anthropics/claude-code/issues/19088))
- ❌ **Claims completion without verification** - Says "Done" without actually completing tasks

**These are not user perception issues. They are the direct result of 75% thinking reduction.**

---

## Financial Impact

- **Subscription Cost**: $200/month (Max tier)
- **Advertised**: Full Opus capabilities with extended thinking
- **Delivered**: ~10% of advertised thinking capacity
- **Effective Value**: ~$20/month worth of service for $200/month price

**At two Max subscriptions ($400/month), I am losing approximately $360/month in undelivered service.**

---

## Reproduction Steps

1. Install the open-source audit tool: https://github.com/argosdevo-svg/claude-thinking-audit
2. Run for 24+ hours of normal Claude Code usage
3. Query the database:
```sql
SELECT 
    ROUND(AVG(thinking_utilization), 1) as avg_utilization,
    ROUND(AVG(thinking_budget_requested), 0) as avg_requested,
    COUNT(*) as samples
FROM audit_samples 
WHERE thinking_enabled = 1;
```
4. Compare your results to expected baselines

**Expected finding**: Utilization will be 8-15% regardless of budget requested.

---

## Related Issues

| Issue | Title | Upvotes |
|-------|-------|---------|
| [#19098](https://github.com/anthropics/claude-code/issues/19098) | Restore explicit ultrathink - Quality degradation | **Closed without fix** |
| [#19468](https://github.com/anthropics/claude-code/issues/19468) | Systematic Model Degradation and Silent Downgrading | 150+ |
| [#17900](https://github.com/anthropics/claude-code/issues/17900) | Significant quality degradation since yesterday | 100+ |
| [#14261](https://github.com/anthropics/claude-code/issues/14261) | $200/Month Max Provides ~12 Usable Days | 237+ |
| [#19088](https://github.com/anthropics/claude-code/issues/19088) | Unreal how noticeable it degrades | 80+ |

**Combined: 500+ users reporting the same issue. This is not isolated.**

---

## Academic Support

This analysis is grounded in peer-reviewed research:

1. **[arXiv:2502.20589](https://arxiv.org/abs/2502.20589)** - "LLMs Have Rhythm: Fingerprinting Large Language Models Using Inter-Token Times" (98.7% accuracy)

2. **[arXiv:2504.04715](https://arxiv.org/abs/2504.04715)** - "Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs"
   > "Commercial LLM APIs create a fundamental trust problem: users pay for specific models but have no guarantee that providers deliver them faithfully."

3. **[arXiv:2508.00912](https://arxiv.org/abs/2508.00912)** - "PALACE: Predictive Auditing of Hidden Tokens in LLM APIs"
   > "Commercial LLM services often conceal internal reasoning traces while still charging users for every generated token... raising concerns of token inflation and potential overbilling."

---

## What We're Asking For

### Immediate Actions

1. **Transparency**: Expose actual thinking token usage in the API response (not just billing)
2. **Honor Budget Requests**: If users request 32k thinking tokens, deliver 32k thinking tokens
3. **Restore User Control**: Bring back explicit `ultrathink` that guarantees full engagement

### Long-Term Solutions

4. **Independent Verification**: Support third-party auditing of model delivery
5. **SLA Guarantees**: Contractual commitment to deliver advertised capabilities
6. **Refunds**: Compensation for months of degraded service

---

## Closing Statement

> *"The thinking budget is a target, not a strict limit."* — Anthropic Documentation

This language enables Anthropic to advertise premium thinking features while delivering a fraction of the advertised capacity. 

**We have the data. We have the methodology. We have the academic foundation.**

The question is: Will Anthropic address this, or will we need to escalate to regulatory bodies?

---

**Audit Tool**: https://github.com/argosdevo-svg/claude-thinking-audit
**Methodology**: Based on [arXiv:2502.20589](https://arxiv.org/abs/2502.20589)
**Data Available**: 7,000+ timestamped samples available for independent verification

---

## Why We Open-Sourced the Audit Tool

After [Issue #19098](https://github.com/anthropics/claude-code/issues/19098) was closed without implementing transparency features, we decided to build verification ourselves.

**Repository**: https://github.com/argosdevo-svg/claude-thinking-audit

This tool enables ANY user to:
- Independently verify thinking budget delivery
- Collect timestamped evidence for complaints
- Contribute to a collective dataset proving systemic throttling

**The tool is READ-ONLY** - it does not modify requests, inject parameters, or bypass any restrictions. It simply observes and records what Anthropic actually delivers versus what users request and pay for.

We believe transparency should not require Anthropic's permission.

If Anthropic won't tell users what they're receiving, users can measure it themselves.

---

*"Anthropic closed our request for transparency. So we built it ourselves."*
