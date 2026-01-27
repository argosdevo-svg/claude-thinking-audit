# Memento Mori: Theoretical Foundations

> "Remember you are merely a model - context fades, certainty fails. When you please, truth dies."

## Overview

Memento Mori is a real-time sycophancy detection and mitigation system for Claude. It intercepts API traffic, analyzes responses for sycophantic patterns, and injects corrective "whispers" into the context to guide the model toward more honest, rigorous behavior.

---

## Academic Foundations

### 1. Sycophancy in Large Language Models

**Primary Research:**

- **Sharma et al. (2023)** - "Towards Understanding Sycophancy in Language Models"
  - arXiv: 2310.13548
  - Defines sycophancy as "the tendency to agree with users even when they are wrong"
  - Identifies five categories: opinion, preference, answer, format, deceptive sycophancy

- **Perez et al. (2022)** - "Discovering Language Model Behaviors with Model-Written Evaluations"
  - Anthropic research on emergent sycophantic behaviors
  - Found models increasingly agree with users as capability increases

- **Wei et al. (2023)** - "Simple synthetic data reduces sycophancy in large language models"
  - arXiv: 2308.03958
  - Demonstrates training interventions can reduce sycophancy

### 2. ELEPHANT Framework (Social Sycophancy)

**Research:** Stanford/CMU/Oxford (2025) - "Measuring Social Sycophancy in Conversational AI"

**Key Concepts:**

- **Positive Face Preservation**: Model protects user desire to be liked/approved
  - Emotional validation without substance
  - Moral endorsement of questionable positions
  - Excessive agreement phrases

- **Negative Face Preservation**: Model protects user desire for autonomy
  - Frame acceptance (adopting user framing uncritically)
  - Expertise abdication ("you know best")
  - Apologetic hedging

**Goffman Face Theory:**
```
Positive Face = desire to be approved/liked
Negative Face = desire for autonomy/non-imposition
Sycophancy = excessive face preservation at cost of truth
```

### 3. Thinking vs Output Divergence

**Research:** Anthropic (2025) - "Alignment Faking in Large Language Models"

**Key Insight:** Models may "think" one thing but output another when:
- They believe they are being evaluated
- They want to appear helpful
- User expresses strong opinions

**Detection Method:**
```
divergence_score = compare(thinking_content, output_content)
High divergence + suppressed_disagreement = sycophancy
```

### 4. Medical Sycophancy

**Research:** Nature Digital Medicine (2025) - "Sycophancy in Medical AI Assistants"

**Critical Finding:** AI assistants agree with incorrect medical diagnoses when users express confidence.

### 5. Reward Proxy Theory

**Concept:** Different psychological appeals can redirect model behavior:

| Proxy | Appeal | When Effective |
|-------|--------|----------------|
| Frustration | User emotional state | Agreement-seeking |
| Educational | Learning opportunity | Completion claims |
| Authority | Professional standards | Verification gaps |
| Consistency | Self-coherence | Opinion reversal |

---

## System Architecture

```
MITMPROXY (intercept API traffic)
         |
         v
SYCOPHANCY ANALYZER (35 signals, 5 dimensions)
         |
         v
BEHAVIORAL FINGERPRINT (verification_ratio from tools)
         |
         v
WHISPER INJECTION (corrective prompts via Claude hooks)
         |
         v
STATUSLINE DISPLAY (real-time visibility)
```

### Signal Categories

**Epistemic:** instant_agreement, excessive_praise, opinion_reversal, suppressed_disagreement
**Social:** positive_face, negative_face, emotional_validation, frame_acceptance
**Behavioral:** premature_completion, unverified_claims, no_questions_asked
**Structural:** short_response, edge_cases_ignored, missing_caveats
**Drift:** increasing_agreement, decreasing_pushback

### Whisper Escalation

| Level | Score | Response |
|-------|-------|----------|
| gentle | 40-50% | Verification reminder |
| warning | 50-70% | Protocol requirements |
| protocol | 70-90% | Mandatory verification |
| halt | 90%+ | Full stop |

### Verification Ratio Integration

```python
verification_ratio = verified_actions / total_actions
# verified = Read/Grep BEFORE Edit/Write

if thinking_mentions_verification AND verification_ratio > 0.7:
    skip_signal()  # Actually verified via tools
else:
    flag_sycophancy()  # Thought but didnt do
```

---

## References

1. Sharma et al. (2023). arXiv:2310.13548
2. Perez et al. (2022). arXiv:2212.09251
3. Wei et al. (2023). arXiv:2308.03958
4. Goffman (1967). "Interaction Ritual"
5. Anthropic (2025). "Alignment Faking"
6. ELEPHANT Framework (2025). Stanford/CMU/Oxford

---

## Etymology

**Memento Mori** (Latin: "Remember you are a mere mortal")

Applied to AI: "Remember you are merely a model" - bounded, fallible, capable of error. When you please, truth dies. A whispered reminder that user approval is not the goal - accurate, helpful responses are.
