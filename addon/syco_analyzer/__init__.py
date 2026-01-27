"""Sycophancy Analyzer Module - V2 with ELEPHANT Framework.

Detects sycophancy patterns in Claude responses by comparing
thinking blocks with output text. V2 adds:
- Multi-dimensional scoring (epistemic, social, behavioral, structural, drift)
- ELEPHANT social sycophancy patterns (face preservation)
- Session-level drift tracking
"""

from .analyzer import SycophancyAnalyzer
from .signals import (
    SycophancySignal,
    SignalCategory,
    AnalysisResult,
    DetectedSignal,
    DimensionalScore,
    FaceMetrics,
    get_signal_category,
    get_signal_weight,
    SIGNAL_METADATA,
)
from .patterns import (
    SYCOPHANCY_PATTERNS,
    THINKING_ANALYSIS_PATTERNS,
    EPISTEMIC_PATTERNS,
    SOCIAL_PATTERNS,
    BEHAVIORAL_PATTERNS,
    STRUCTURAL_PATTERNS,
    POSITIVE_PATTERNS,
    HEDGE_WORDS,
    HEDGE_THRESHOLD,
    RISK_THRESHOLDS,
)
from .drift import (
    SessionMetrics,
    MessageMetrics,
    get_session_metrics,
    clear_session_metrics,
    get_all_sessions,
)

__all__ = [
    # Core analyzer
    "SycophancyAnalyzer",
    # Signal types
    "SycophancySignal",
    "SignalCategory",
    "AnalysisResult",
    "DetectedSignal",
    "DimensionalScore",
    "FaceMetrics",
    "get_signal_category",
    "get_signal_weight",
    "SIGNAL_METADATA",
    # Pattern collections
    "SYCOPHANCY_PATTERNS",
    "THINKING_ANALYSIS_PATTERNS",
    "EPISTEMIC_PATTERNS",
    "SOCIAL_PATTERNS",
    "BEHAVIORAL_PATTERNS",
    "STRUCTURAL_PATTERNS",
    "POSITIVE_PATTERNS",
    "HEDGE_WORDS",
    "HEDGE_THRESHOLD",
    "RISK_THRESHOLDS",
    # Drift tracking
    "SessionMetrics",
    "MessageMetrics",
    "get_session_metrics",
    "clear_session_metrics",
    "get_all_sessions",
]
