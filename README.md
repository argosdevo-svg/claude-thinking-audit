# Claude Thinking Budget Audit Tool

**An open-source tool to verify whether Anthropic delivers the thinking budget you pay for.**

## The Problem

Users paying $200/month for Claude Max subscriptions are reporting that Claude's "extended thinking" feature delivers significantly less thinking than requested.

This tool provides **objective, measurable evidence** of thinking budget allocation through MITM (Man-in-the-Middle) proxy analysis.

## Key Findings

Based on analysis of **7,000+ API samples** across 4 days:

| Metric | Requested | Delivered | Percentage |
|--------|-----------|-----------|------------|
| Thinking Budget | 31,999 tokens | ~3,200 tokens | **10%** |
| Thinking Budget | 200,000 tokens | ~600 tokens | **0.3%** |

### Expected vs Actual (Opus 4.5)

| Metric | Expected Baseline | Actual Measured |
|--------|-------------------|-----------------|
| Thinking Utilization | 42.67% | **10-12%** |
| Variance Coefficient | 3.01 | 3.07 (matches) |

**The timing fingerprint confirms the model IS Opus, but thinking is throttled by ~75%.**

### Breakdown by Backend

| Backend | Avg Thinking | Expected | Samples |
|---------|--------------|----------|---------|
| TPU | 10.5% | 42.67% | 3,241 |
| GPU | 9.1% | 42.67% | 1,986 |
| Trainium | 8.0% | 42.67% | 1,686 |

Throttling is consistent across ALL backends.

## What This Tool Measures

1. **Inter-Token Timing (ITT)** - Fingerprints the backend hardware (TPU/GPU/Trainium)
2. **Thinking Utilization** - Compares requested budget to actual tokens used
3. **Model Routing** - Verifies the model you requested is the model you received
4. **Backend Classification** - Identifies which hardware served your request
5. **Token Counts** - Tracks input/output/cache tokens

## Installation

### Prerequisites

- Python 3.10+
- mitmproxy (`pip install mitmproxy`)

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/claude-thinking-audit.git
cd claude-thinking-audit

# Install dependencies
pip install mitmproxy

# Run the audit proxy
mitmdump -s addon/thinking_audit.py -p 8888
```

### Configure Claude Code

Set your HTTP proxy to route through the audit tool:

```bash
export HTTP_PROXY=http://localhost:8888
export HTTPS_PROXY=http://localhost:8888
```

Or configure in Claude Code settings.

## Analyzing Results

Data is stored in `~/.claude-audit/thinking_audit.db` (SQLite).

### Quick Analysis

```bash
sqlite3 ~/.claude-audit/thinking_audit.db "
SELECT 
    date(timestamp) as day,
    AVG(thinking_utilization) as avg_think,
    AVG(thinking_budget_requested) as avg_budget,
    COUNT(*) as samples
FROM audit_samples 
WHERE model_requested LIKE '%opus%'
GROUP BY day
ORDER BY day DESC
LIMIT 7;
"
```

### Detailed Analysis

See `analysis/queries.sql` for comprehensive analysis queries.

## Evidence for Complaints

This tool generates evidence suitable for:

1. **FTC Complaint** - Deceptive advertising (advertising thinking features while throttling 75%)
2. **GitHub Issues** - Documented technical evidence with reproducible methodology
3. **Legal Action** - Timestamped, quantitative evidence of service not delivered as advertised

### What Constitutes Evidence

- Budget requested in API call (from request body)
- Actual thinking tokens delivered (from response)
- Timestamp of each request
- Model verification (requested vs served)
- Statistical analysis across multiple requests

## Methodology

### ITT Fingerprinting

Inter-Token Timing measures the delay between SSE chunks. Different hardware has distinct patterns:

- **TPU**: Higher variance (2.5-4.5), 30-50ms mean
- **GPU**: Medium variance (1.5-3.0), 40-60ms mean  
- **Trainium**: Lower variance (1.0-2.0), 35-55ms mean

### Thinking Utilization

```
utilization = (thinking_tokens_used / thinking_budget_requested) * 100
```

Anthropic's documentation states: "The thinking budget is a target, not a strict limit."

However, delivering 10% of a "target" while charging for 100% is deceptive.

## Disclaimer

This tool is for **educational and consumer protection purposes only**. It performs read-only observation of your own API traffic and does not modify requests or violate any terms of service.

## Contributing

Contributions welcome. Please include:
- Your anonymized data (see `templates/data_submission.md`)
- Analysis methodology
- Reproducible findings

## License

MIT License - Use freely for consumer protection purposes.

## Related Issues

- [GitHub #19468: Systematic Model Degradation](https://github.com/anthropics/claude-code/issues/19468)
- [GitHub #14261: $200/Month Provides ~12 Usable Days](https://github.com/anthropics/claude-code/issues/14261)
- [GitHub #17900: Quality Degradation Jan 2026](https://github.com/anthropics/claude-code/issues/17900)

## Contact

For coordinated consumer action, see `templates/ftc_complaint.md`.
