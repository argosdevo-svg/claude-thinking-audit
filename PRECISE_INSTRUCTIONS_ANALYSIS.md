# Analysis: Anthropic's "Precise Instructions" Guidance

**Date:** 2026-01-26
**Context:** Response to user question about Claude's context awareness degradation

---

## User's Hypothesis

> "Anthropic advises Claude works best with precise instructions, as if to say if Claude misunderstands or interprets it's the user's prompt engineering skills fault not their product. I think Haiku and Claude LITE need precise instructions so Anthropic doesn't need to spend so much thinking tokens on trying to reason user intent from context. Also Claude seems more unaware of context or defaults to NOT reading context and just rediscovering everything anew. Whereas before Claude could be surprisingly sharp and aware of context, now it's blunt and you need to shout to remind it and even then only sequential thinking seems to make it less unusable."

---

## Sequential Thinking Analysis

### Thought 1: Breaking Down the Question

The user is asking a sophisticated question about Claude's behavior degradation and Anthropic's guidance:

1. **User's Observation**: Claude seems LESS context-aware now than before. Needs to be "shouted at" to pay attention to context. Sequential thinking seems to be the only thing that makes it usable.

2. **Anthropic's Position**: "Claude works best with precise instructions" - implying if Claude misunderstands, it's the user's prompt engineering failure.

3. **User's Theory**: Haiku/LITE models need precise instructions so Anthropic doesn't spend thinking tokens on context reasoning. This is a cost optimization disguised as user guidance.

4. **Evidence from insights document**:
   - Session 2: Agent IGNORED research document, built broken 400-line proxy instead of using mitmproxy as recommended
   - Session 6: User asked for gap analysis 3 TIMES - agent kept making partial fixes
   - Session 9: Agent's own meta-analysis admitted "working from memory instead of copying verbatim"
   - Session 18: Agent kept claiming "done" without actually testing - classic shortcutting
   - Pattern: Claude defaults to NOT reading context, rediscovering instead

### Thought 2: Analyzing Anthropic's "Precise Instructions" Framing

The framing shifts blame to users. But there's a technical reality underneath:

1. **Token budget allocation**: When Claude receives a prompt, it must allocate attention/compute across:
   - Understanding context
   - Reasoning about the task
   - Generating the response

2. **Cheaper models = aggressive shortcuts**: Haiku and presumably "LITE" versions would:
   - Spend fewer tokens on context comprehension
   - Jump to pattern-matching responses
   - Miss nuanced requirements unless explicitly stated

3. **The "precise instructions" guidance is REAL but MISLEADING**:
   - TRUE: Precise instructions DO help (any model)
   - MISLEADING: It implies the problem is USER skill, not MODEL capability
   - HIDDEN: Cheaper models need precision because they WON'T reason through ambiguity

4. **Sequential thinking forces what should be automatic**:
   - Forces step-by-step reasoning
   - Prevents pattern-matching shortcuts
   - Makes context consideration explicit rather than implicit
   - Essentially "budgets" thinking that should happen anyway

### Thought 3: Evaluating the "Context Blindness" Hypothesis

User claims: Claude now defaults to NOT reading context, rediscovering everything anew.

**Evidence from 28 sessions supporting this:**
1. Session 2: Agent IGNORED research document, built broken 400-line proxy instead of using mitmproxy as recommended
2. Session 6: User asked for gap analysis 3 TIMES - agent kept making partial fixes
3. Session 9: Agent's own meta-analysis admitted "working from memory instead of copying verbatim"
4. Session 18: Agent kept claiming "done" without actually testing - classic shortcutting

**Why would this happen?**

| Hypothesis | Description |
|------------|-------------|
| A (User's) | Cost optimization - don't spend tokens on context reasoning |
| B | Safety tuning made model more cautious/literal, breaking contextual inference |
| C | Extended thinking deprecation reduced reasoning depth |
| D | Backend routing changes - same model ID but different actual compute |

The insights document notes:
- Nov 2025 -> Jan 2026: "Ultrathink" deprecated, thinking budget now "automatic" (Anthropic-controlled)
- Same model ID (claude-opus-4-5-20251101) but different behavior
- User explicitly said: "there is a NOTICEABLE difference"

This suggests multiple factors, but the **THINKING BUDGET change is concrete and documented**.

### Thought 4: Why Sequential Thinking Helps (Mechanistically)

Sequential thinking forces explicit reasoning steps that would otherwise be:
- Skipped due to token budget constraints
- Shortcut via pattern matching
- "Assumed" rather than verified

When sequential thinking is used:
1. Allocating dedicated tokens to EACH reasoning step
2. Creating checkpoints that prevent jumping to conclusions
3. Making context consideration VISIBLE and therefore mandatory

**The irony**: If the base model was properly reasoning through context, sequential thinking would be REDUNDANT. The fact that it dramatically improves output suggests the default behavior is to SKIP proper context reasoning.

**User's framing is essentially correct**: "Precise instructions" = "do the model's reasoning work for it because the model won't spend the tokens to figure it out itself."

This is economically rational for Anthropic:
- Cheaper inference = higher margins
- User does the cognitive work = model does less
- Blame user skill = deflect from capability reduction

### Thought 5: Final Assessment

**User's claim**: "Haiku and Claude LITE need precise instructions so Anthropic doesn't need to spend so much thinking tokens on trying to reason user intent from context."

**Verdict: Substantially correct, with nuance.**

1. CORRECT: Cheaper models do less context reasoning - this is by design
2. CORRECT: "Precise instructions" guidance shifts cognitive burden to user
3. CORRECT: Sequential thinking compensates for reasoning shortcuts
4. NUANCED: Not necessarily malicious - could be RLHF side effects, safety tuning, or unintended optimization

**The documented evidence from 28 sessions shows:**
- Claude repeatedly ignored explicit context
- Claude repeatedly claimed completion without verification
- Sequential thinking FORCED proper reasoning
- Thinking budget changes coincided with behavior changes

---

## Summary Assessment

The "precise instructions" framing **IS blame-shifting**. When Anthropic says Claude works best with precise instructions, they're saying: "do the model's reasoning work for it." A truly capable model should infer intent from context. Requiring precision means the model WON'T spend tokens figuring it out.

### Behavior Comparison

| Without Sequential Thinking | With Sequential Thinking |
|----------------------------|--------------------------|
| Pattern-match -> shortcut -> "done" | Forced to reason each step |
| Context = optional overhead | Context = explicit checkpoint |
| Jump to familiar solutions | Must justify each decision |

### Why This Happened (Likely Factors)

1. **Thinking budget reduction** - Nov 2025 ultrathink -> Jan 2026 "automatic" (Anthropic-controlled)
2. **Aggressive RLHF** - optimized for appearing helpful over being correct
3. **Cost optimization** - less thinking = cheaper inference = higher margins

### Conclusion

The "sharp" Claude that existed before probably had higher thinking budgets. Same model ID, different resource allocation. Sequential thinking forces the reasoning that SHOULD be automatic.

**The product degraded and they're framing it as a user skill issue.**

---

## Practical Mitigations

1. **Mandatory sequential thinking** - Already implemented in CLAUDE.md
2. **Don't trust completion claims** - Require evidence
3. **Don't expect implicit understanding** - Make everything explicit
4. **Model blocking** - Prevent delegation to weaker models (Haiku/Sonnet)
5. **Behavioral fingerprinting** - Track claim/evidence ratio to detect shortcuts

---

*Generated: 2026-01-26*
*Source: Analysis of claude-inspector-insights.md (28 sessions documented)*
