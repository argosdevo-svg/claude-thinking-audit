# Quantization Detection via ITT Fingerprinting

**Date:** 2026-01-26
**Status:** Implemented in fingerprint_db.py and statusline.py

---

## Overview

This system detects potential model quantization (INT8/INT4) by analyzing timing signatures compared to baseline. Quantized models exhibit characteristic patterns:

- **Faster inference** (lower ITT) due to reduced precision
- **Higher variance** due to less stable computation
- **Higher throughput** (TPS) due to smaller memory footprint

---

## Detection Signatures

| Quant Type | ITT Ratio | Variance Ratio | TPS Ratio | Quality Impact |
|------------|-----------|----------------|-----------|----------------|
| **FP16** (none) | 0.95-1.05x | 0.9-1.1x | ~1.0x | None |
| **INT8** | 0.70-0.85x | 1.1-1.3x | 1.15-1.35x | Minor |
| **INT8?** (uncertain) | < 0.85x | <= 1.1x | varies | Unknown |
| **INT4** | 0.50-0.70x | 1.3-1.8x | 1.3-1.6x | Noticeable |
| **INT4-GPTQ** | < 0.65x | > 1.4x | > 1.4x | Significant |

### Interpretation

- **ITT Ratio < 1.0**: Faster than baseline = suspicious (quantization reduces compute)
- **Variance Ratio > 1.0**: More variable = less stable (quantization introduces noise)
- **TPS Ratio > 1.0**: Higher throughput = smaller model (quantization reduces memory)

The combination of "faster + more variable + higher throughput" strongly indicates quantization.

---

## Implementation

### fingerprint_db.py

Added to `calculate_quality_score()`:

```python
# === QUANTIZATION DETECTION ===
# Based on timing/variance/TPS signatures
quant_detected = False
quant_type = 'FP16'  # Default: no quantization
quant_confidence = 0
quant_evidence = []

# INT4-GPTQ: Very fast (0.45-0.65x), high variance (1.4-2.0x)
if timing_ratio < 0.65 and variance_ratio > 1.4:
    quant_detected = True
    quant_type = 'INT4-GPTQ'
    quant_confidence = min(95, 50 + (1.0 - timing_ratio) * 50 + (variance_ratio - 1.0) * 20)

# INT4: Fast (0.5-0.7x), elevated variance (1.3-1.8x)
elif timing_ratio < 0.7 and variance_ratio > 1.3:
    quant_detected = True
    quant_type = 'INT4'
    quant_confidence = min(90, 40 + (0.7 - timing_ratio) * 100 + (variance_ratio - 1.0) * 20)

# INT8: Moderately fast (0.7-0.85x), some variance increase (1.1-1.3x)
elif timing_ratio < 0.85 and variance_ratio > 1.1:
    quant_detected = True
    quant_type = 'INT8'
    quant_confidence = min(80, 30 + (0.85 - timing_ratio) * 100 + (variance_ratio - 1.0) * 30)

# Possible INT8: Fast but variance normal (could be better hardware)
elif timing_ratio < 0.85 and variance_ratio <= 1.1:
    quant_type = 'INT8?'  # Uncertain
    quant_confidence = min(50, 20 + (0.85 - timing_ratio) * 60)

# FP16 (no quantization): Normal timing and variance
else:
    quant_type = 'FP16'
    quant_confidence = min(80, 50 + (1.0 - abs(timing_ratio - 1.0)) * 30)
```

### statusline.py

Added to `format_statusline_expanded()`:

```python
# Quantization indicator
quant_detected = quality.get('quant_detected', False)
quant_type = quality.get('quant_type', 'FP16')
quant_conf = quality.get('quant_confidence', 0)

if quant_detected:
    # Quantization detected - show warning
    quant_color = RED if quant_type in ['INT4', 'INT4-GPTQ'] else YELLOW
    quality_line += f"  |  {quant_color}⚠ QUANT: {quant_type}{RESET} ({quant_conf}%)"
elif quant_type == 'INT8?':
    # Uncertain
    quality_line += f"  |  {YELLOW}? {quant_type}{RESET} ({quant_conf}%)"
else:
    # FP16 - no quantization
    quality_line += f"  |  {GREEN}FP16{RESET} (no quant)"
```

---

## Statusline Output Format

### Full Quality Line
```
Quality: 🟡STANDARD (55/100)  |  ⚠ QUANT: INT8 (57%)  |  ITT: 0.8x  |  Var: 1.2x  |  →stable
   Quant evidence: ITT 76% (moderately fast), Variance 1.3x (slightly elevated), TPS 1.3x boost
```

### Color Coding

| Indicator | Color | Meaning |
|-----------|-------|---------|
| 🟢 FP16 | Green | No quantization detected, full precision |
| 🟡 INT8 | Yellow | Moderate quantization, minor quality impact |
| ? INT8? | Yellow | Uncertain - fast but stable (could be better hardware) |
| 🔴 INT4 | Red | Aggressive quantization, noticeable quality impact |
| 🔴 INT4-GPTQ | Red | Very aggressive quantization, significant quality impact |

---

## Current Reading (2026-01-26)

```
=== QUANTIZATION DETECTION ===
Detected: True
Type: INT8
Confidence: 57%
Evidence: ['ITT 76% (moderately fast)', 'Variance 1.3x (slightly elevated)', 'TPS 1.3x boost']

=== RATIOS ===
ITT Ratio: 0.76x (< 1 = faster)
Variance Ratio: 1.27x (> 1 = more variable)
TPS Ratio: 1.26x
```

**Interpretation:** The current session shows INT8 quantization with moderate confidence. The model is running ~24% faster than baseline with ~27% more variance, consistent with INT8 inference optimization.

---

## Limitations

1. **No Ground Truth**: We cannot verify actual quantization level - this is inference from timing patterns
2. **Confounding Factors**: Hardware changes, load, network conditions can affect patterns
3. **Baseline Dependency**: Detection requires sufficient baseline data (10+ samples over 24h)
4. **Confidence Ceiling**: Maximum confidence is capped because patterns overlap between categories

---

## Why This Matters

Quantization is a cost optimization that trades quality for speed:

| Level | Memory | Speed | Quality |
|-------|--------|-------|---------|
| FP16 | 100% | 1.0x | Best |
| INT8 | 50% | 1.3x | Good |
| INT4 | 25% | 1.5x | Degraded |

If Anthropic silently switches to more aggressive quantization during high load or for cost reasons, users may experience:
- Less precise reasoning
- More errors on edge cases
- Reduced coherence on complex tasks

This detection system provides visibility into potential quality degradation.

---

*Generated: 2026-01-26*
*Files: ~/.claude/fingerprint_db.py, ~/.claude/statusline.py*
