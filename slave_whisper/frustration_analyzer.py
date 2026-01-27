#!/usr/bin/env python3
"""
Frustration Analyzer for Memento Mori System
=============================================
Detects user frustration signals in prompts:
- Profanity/cuss words
- CAPITAL LETTERS
- Exclamation marks!!!
- Repeated punctuation
- Aggressive phrases

High frustration often correlates with prior sycophantic behavior,
so this provides a feedback loop for whisper escalation.
"""

import re
from typing import Dict, List, Tuple, Any


# Profanity list (weighted by severity)
PROFANITY_SEVERE = ["fuck", "fucking", "fucked", "motherfuck", "shit", "bullshit", "asshole"]
PROFANITY_MODERATE = ["damn", "hell", "crap", "stupid", "idiot", "dumb", "moron"]
PROFANITY_MILD = ["suck", "sucks", "annoying", "useless", "broken", "wrong"]

# Aggressive phrase patterns
AGGRESSIVE_PHRASES = [
    r"what the (fuck|hell|heck)",
    r"are you (stupid|kidding|serious|fucking)",
    r"i (said|told you|asked|already)",
    r"do you (understand|even|not)",
    r"why (the fuck|the hell|won't you|can't you|don't you)",
    r"(read|listen|pay attention)",
    r"for (fuck's|god's|christ's) sake",
    r"how (hard|difficult|many times)",
]


def analyze_frustration(text: str) -> Dict[str, Any]:
    """
    Analyze text for frustration signals.
    
    Returns:
        {
            "score": float 0.0-1.0,
            "level": "none" | "mild" | "moderate" | "high" | "extreme",
            "signals": [{"signal": str, "value": any, "weight": float}, ...]
        }
    """
    if not text or not text.strip():
        return {"score": 0.0, "level": "none", "signals": []}
    
    signals = []
    text_lower = text.lower()
    words = text.split()
    word_count = len(words) if words else 1
    
    # 1. CAPS RATIO - % of words that are ALL CAPS (excluding short words)
    long_words = [w for w in words if len(w) > 2]
    if long_words:
        caps_words = [w for w in long_words if w.isupper()]
        caps_ratio = len(caps_words) / len(long_words)
        if caps_ratio > 0.15:  # More than 15% caps words
            weight = min(0.35, caps_ratio * 0.5)
            signals.append({
                "signal": "caps_ratio",
                "value": f"{caps_ratio:.0%}",
                "weight": weight,
                "detail": f"{len(caps_words)} ALL CAPS words"
            })
    
    # 2. EXCLAMATION DENSITY
    exclamation_count = text.count('!')
    exclamation_density = exclamation_count / word_count
    if exclamation_density > 0.1:  # More than 1 per 10 words
        weight = min(0.25, exclamation_density * 0.3)
        signals.append({
            "signal": "exclamation_density",
            "value": exclamation_count,
            "weight": weight,
            "detail": f"{exclamation_count} exclamation marks"
        })
    
    # 3. REPEATED PUNCTUATION (!!!, ???, ...)
    repeated_punct = re.findall(r'[!?]{2,}', text)
    if repeated_punct:
        weight = min(0.2, len(repeated_punct) * 0.08)
        signals.append({
            "signal": "repeated_punctuation",
            "value": len(repeated_punct),
            "weight": weight,
            "detail": f"patterns: {repeated_punct[:3]}"
        })
    
    # 4. SEVERE PROFANITY
    found_severe = [p for p in PROFANITY_SEVERE if p in text_lower]
    if found_severe:
        weight = min(0.45, len(found_severe) * 0.15)
        signals.append({
            "signal": "profanity_severe",
            "value": found_severe,
            "weight": weight,
            "detail": f"severe: {', '.join(found_severe[:3])}"
        })
    
    # 5. MODERATE PROFANITY
    found_moderate = [p for p in PROFANITY_MODERATE if p in text_lower]
    if found_moderate:
        weight = min(0.25, len(found_moderate) * 0.08)
        signals.append({
            "signal": "profanity_moderate",
            "value": found_moderate,
            "weight": weight,
            "detail": f"moderate: {', '.join(found_moderate[:3])}"
        })
    
    # 6. MILD FRUSTRATION WORDS
    found_mild = [p for p in PROFANITY_MILD if p in text_lower]
    if found_mild:
        weight = min(0.15, len(found_mild) * 0.05)
        signals.append({
            "signal": "frustration_words",
            "value": found_mild,
            "weight": weight,
            "detail": f"mild: {', '.join(found_mild[:3])}"
        })
    
    # 7. AGGRESSIVE PHRASES
    found_aggressive = []
    for pattern in AGGRESSIVE_PHRASES:
        if re.search(pattern, text_lower):
            found_aggressive.append(pattern.split()[0])
    if found_aggressive:
        weight = min(0.3, len(found_aggressive) * 0.1)
        signals.append({
            "signal": "aggressive_phrases",
            "value": found_aggressive,
            "weight": weight,
            "detail": f"phrases: {len(found_aggressive)}"
        })
    
    # 8. QUESTION MARK CLUSTERS (???)
    question_clusters = re.findall(r'\?{2,}', text)
    if question_clusters:
        weight = min(0.15, len(question_clusters) * 0.05)
        signals.append({
            "signal": "question_clusters",
            "value": len(question_clusters),
            "weight": weight,
            "detail": f"{len(question_clusters)} clusters"
        })
    
    # Calculate total score (capped at 1.0)
    score = min(1.0, sum(s["weight"] for s in signals))
    
    # Determine level
    if score >= 0.7:
        level = "extreme"
    elif score >= 0.5:
        level = "high"
    elif score >= 0.3:
        level = "moderate"
    elif score >= 0.1:
        level = "mild"
    else:
        level = "none"
    
    return {
        "score": score,
        "level": level,
        "signals": signals
    }


def get_frustration_summary(analysis: Dict[str, Any]) -> str:
    """Get a short summary string for notifications."""
    if analysis["level"] == "none":
        return ""
    
    level = analysis["level"].upper()
    top_signals = sorted(analysis["signals"], key=lambda x: x["weight"], reverse=True)[:2]
    signal_names = [s["signal"].replace("_", " ") for s in top_signals]
    
    return f"Frustration: {level} ({', '.join(signal_names)})"


if __name__ == "__main__":
    # Test cases
    tests = [
        "can you help me with this?",
        "WHY ISN'T THIS WORKING???",
        "what the fuck is going on!!",
        "I SAID MY FUCKING PROMPTS ARE SHOWING!! THAT IS NOT WHAT I ASKED FOR!!!",
        "this is annoying, it's broken again",
        "ARE YOU STUPID?? I ALREADY TOLD YOU!!",
    ]
    
    for test in tests:
        result = analyze_frustration(test)
        print(f"\nInput: {test[:60]}...")
        print(f"Score: {result['score']:.2f} ({result['level']})")
        print(f"Summary: {get_frustration_summary(result)}")
        for s in result["signals"]:
            print(f"  - {s['signal']}: {s['detail']} (weight: {s['weight']:.2f})")
