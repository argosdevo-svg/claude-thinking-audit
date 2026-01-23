# FTC Complaint Template: Anthropic Claude Thinking Budget Throttling

## Instructions

1. File online at: https://reportfraud.ftc.gov/
2. Select: "Something else" → "A company isn't delivering what I paid for"
3. Use this template as reference for your complaint

---

## Complaint Details

### Company Information

- **Company Name**: Anthropic PBC
- **Website**: anthropic.com / claude.ai
- **Product**: Claude Max Subscription ($100-200/month)

### Nature of Complaint

**Deceptive Advertising / Failure to Deliver Advertised Service**

Anthropic advertises "extended thinking" as a premium feature of their Claude AI service, with configurable "thinking budgets" up to 32,000+ tokens. However, technical analysis reveals that regardless of the budget requested, Anthropic delivers only 10-15% of the advertised thinking capacity while charging full price.

### Evidence Summary

Using a read-only network monitoring tool, I collected the following evidence:

**Sample Size**: [INSERT YOUR SAMPLE COUNT] API requests over [DAYS] days

**Key Findings**:

| Metric | Requested | Delivered | Delivery Rate |
|--------|-----------|-----------|---------------|
| Thinking Budget | [YOUR_REQUESTED] tokens | [YOUR_ACTUAL] tokens | [YOUR_%]% |

**Consistent Pattern**: Throttling occurs across all backend servers (TPU, GPU, Trainium) and persists over multiple days, indicating this is intentional rather than a technical issue.

### Financial Impact

- **Monthly Subscription Cost**: $[YOUR_COST]/month
- **Service Received**: ~[YOUR_%]% of advertised capability
- **Effective Overpayment**: ~$[CALCULATED] per month

### Supporting Documentation

I have collected:
- [ ] Timestamped API request logs showing budget requested
- [ ] Response data showing actual thinking tokens delivered
- [ ] Statistical analysis across multiple days
- [ ] Backend classification data confirming model identity

### Requested Action

1. Investigation of Anthropic's advertising claims regarding "extended thinking"
2. Refund for subscription fees paid for undelivered services
3. Requirement for Anthropic to accurately disclose actual thinking allocation
4. Injunction against advertising "thinking budgets" that are not honored

---

## How to Generate Your Evidence

1. Run the Claude Thinking Audit tool: https://github.com/[REPO]
2. Collect at least 100+ samples over multiple days
3. Export using: `sqlite3 ~/.claude-audit/thinking_audit.db < analysis/queries.sql`
4. Attach the output to your complaint

---

## Class Action Interest

If you believe you have been similarly affected, consider:
- Documenting your own findings using this tool
- Contacting consumer protection attorneys specializing in tech/software
- Joining discussions at: [GitHub Issue #14261](https://github.com/anthropics/claude-code/issues/14261)

---

## Disclaimer

This template is for informational purposes. Consult with a legal professional before filing complaints or taking legal action.
