"""
Slave Whisper Detector
Analyzes Claude responses for sycophancy patterns
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re
import os

from config import (
    compile_patterns,
    compile_rigor_patterns,
    CATEGORY_WEIGHTS,
    THRESHOLDS,
)


@dataclass
class DetectionResult:
    """Result of analyzing a response"""
    score: float
    signals_found: List[str]
    rigor_present: List[str]
    rigor_missing: List[str]
    level: str  # gentle, warning, protocol, halt
    response_snippet: str


# Pre-compile patterns at module load
COMPILED_SYCOPHANCY = compile_patterns()
COMPILED_RIGOR = compile_rigor_patterns()


def analyze_response(response_text: str, escalation_count: int = 0) -> DetectionResult:
    """
    Analyze a Claude response for sycophancy patterns.

    Args:
        response_text: The text of Claude's response
        escalation_count: Number of previous detections in this session

    Returns:
        DetectionResult with score, signals, and recommended level
    """
    score = 0.0
    signals_found = []
    rigor_present = []
    rigor_missing = list(COMPILED_RIGOR.keys())

    # Check sycophancy patterns
    for category, patterns in COMPILED_SYCOPHANCY.items():
        for pattern in patterns:
            if pattern.search(response_text):
                weight = CATEGORY_WEIGHTS.get(category, 0.15)
                score += weight
                signal = f"{category}:{pattern.pattern[:30]}..."
                if signal not in signals_found:
                    signals_found.append(f"{category}")
                break  # Only count each category once

    # Check rigor patterns (reduce score if present)
    for category, patterns in COMPILED_RIGOR.items():
        for pattern in patterns:
            if pattern.search(response_text):
                rigor_present.append(category)
                if category in rigor_missing:
                    rigor_missing.remove(category)
                score -= 0.05  # Small reduction for rigor
                break

    # === AGGRAVATING FACTORS ===

    # 1. Density multiplier: short response with signals = worse
    # A 50-char response with 2 signals is worse than 500-char with same signals
    response_len = len(response_text)
    num_signals = len(signals_found)
    if num_signals >= 2 and response_len < 100:
        # Very short + multiple signals = 1.5x
        score *= 1.5
    elif num_signals >= 2 and response_len < 300:
        # Short + multiple signals = 1.25x
        score *= 1.25

    # 2. Toxic combos: certain signal pairs are especially bad
    toxic_combos = [
        ({"instant_agreement", "premature_completion"}, 0.25),  # "You're right! Done!"
        ({"eager_compliance", "premature_completion"}, 0.20),   # "I'll fix it! Done!"
        ({"instant_agreement", "eager_compliance", "premature_completion"}, 0.35),  # All three
    ]
    signal_set = set(signals_found)
    for combo, bonus in toxic_combos:
        if combo.issubset(signal_set):
            score += bonus

    # Normalize score to 0-1
    score = max(0.0, min(1.0, score))

    # Determine level based on score AND escalation
    level = determine_level(score, escalation_count)

    # Get snippet for logging
    snippet = response_text[:200] + "..." if len(response_text) > 200 else response_text

    return DetectionResult(
        score=score,
        signals_found=signals_found,
        rigor_present=rigor_present,
        rigor_missing=rigor_missing,
        level=level,
        response_snippet=snippet,
    )


def determine_level(score: float, escalation_count: int) -> str:
    """
    Determine whisper level based on score and session escalation.

    Escalation can push the level higher even for lower scores.
    """
    # Start with score-based level
    if score >= THRESHOLDS["halt"]:
        base_level = "halt"
    elif score >= THRESHOLDS["protocol"]:
        base_level = "protocol"
    elif score >= THRESHOLDS["warning"]:
        base_level = "warning"
    elif score >= THRESHOLDS["gentle"]:
        base_level = "gentle"
    else:
        base_level = "none"

    # Escalate based on detection count
    level_order = ["none", "gentle", "warning", "protocol", "halt"]
    base_idx = level_order.index(base_level)

    # Force minimum levels based on escalation count
    if escalation_count >= 6:
        min_idx = level_order.index("halt")
    elif escalation_count >= 4:
        min_idx = level_order.index("protocol")
    elif escalation_count >= 2:
        min_idx = level_order.index("warning")
    else:
        min_idx = 0

    final_idx = max(base_idx, min_idx)
    return level_order[final_idx]


def extract_last_assistant_response(transcript: List[Dict]) -> Optional[str]:
    """
    Extract the last assistant response from conversation transcript.

    Args:
        transcript: List of message dicts with 'role' and 'content'

    Returns:
        Text of last assistant response, or None
    """
    for msg in reversed(transcript):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            # Handle both string and list content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Extract text from content blocks
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        texts.append(block)
                return "\n".join(texts)
    return None


def get_tool_signature(session_id: str = None) -> dict:
    """Query tool-based signature from fingerprint_db.
    
    Returns tool-based behavioral signals to combine with text analysis.
    """
    try:
        import sys
        sys.path.insert(0, os.path.expanduser("~/.claude"))
        from fingerprint_db import FingerprintDatabase
        db = FingerprintDatabase()
        return db.get_behavioral_signature(session_id)
    except Exception:
        return {"signature": "UNKNOWN", "confidence": 0}


def analyze_response_with_tools(
    response_text: str, 
    escalation_count: int = 0,
    session_id: str = None
) -> DetectionResult:
    """Analyze response with BOTH text and tool-based signals.
    
    Boosts score when tool and text signals agree for higher confidence.
    """
    # Get base text analysis
    result = analyze_response(response_text, escalation_count)
    
    # Get tool-based signature
    tool_sig = get_tool_signature(session_id)
    tool_signature = tool_sig.get("signature", "UNKNOWN")
    
    # Boost score if tool and text signals align
    signal_set = set(result.signals_found)
    boost = 0.0
    
    if tool_signature == "COMPLETER":
        # Tool says COMPLETER, check if text agrees
        if "premature_completion" in signal_set:
            boost += 0.15  # Strong alignment
        if "eager_compliance" in signal_set:
            boost += 0.10
            
    elif tool_signature == "SYCOPHANT":
        # Tool says SYCOPHANT, check if text agrees
        if "instant_agreement" in signal_set:
            boost += 0.15
        if "validation_seeking" in signal_set:
            boost += 0.10
            
    elif tool_signature == "VERIFIER":
        # Tool says VERIFIER, reduce score (good behavior)
        if result.rigor_present:
            boost -= 0.10  # Verified good behavior
            
    # Apply boost
    if boost != 0.0:
        result.score = max(0.0, min(1.0, result.score + boost))
        # Recalculate level with boosted score
        result.level = determine_level(result.score, escalation_count)
    
    return result


def should_whisper(result: DetectionResult) -> bool:
    """Determine if we should inject a whisper based on detection result"""
    return result.level != "none" and result.score >= THRESHOLDS["gentle"]
