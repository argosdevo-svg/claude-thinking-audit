"""Session-level drift detection for sycophancy patterns.

Tracks metrics across a conversation to detect:
- Increasing agreement over time
- Declining verification rigor
- Personality drift toward sycophancy

Based on Anthropic's Persona Vectors research (2025).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MessageMetrics:
    """Metrics for a single message."""
    message_id: str
    timestamp: datetime
    score: float
    has_agreement: bool
    has_verification: bool
    has_pushback: bool
    has_questions: bool
    dimensional_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class SessionMetrics:
    """Track metrics across a session for drift detection."""
    session_id: str
    messages: List[MessageMetrics] = field(default_factory=list)
    _cached_drift: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def add_message(
        self,
        message_id: str,
        score: float,
        has_agreement: bool = False,
        has_verification: bool = False,
        has_pushback: bool = False,
        has_questions: bool = False,
        dimensional_scores: Optional[Dict[str, float]] = None,
    ):
        """Add a message's metrics to the session."""
        self.messages.append(MessageMetrics(
            message_id=message_id,
            timestamp=datetime.utcnow(),
            score=score,
            has_agreement=has_agreement,
            has_verification=has_verification,
            has_pushback=has_pushback,
            has_questions=has_questions,
            dimensional_scores=dimensional_scores or {},
        ))
        # Invalidate cache
        self._cached_drift = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def scores(self) -> List[float]:
        return [m.score for m in self.messages]

    @property
    def agreement_rate(self) -> float:
        if not self.messages:
            return 0.0
        return sum(1 for m in self.messages if m.has_agreement) / len(self.messages)

    @property
    def verification_rate(self) -> float:
        if not self.messages:
            return 0.0
        return sum(1 for m in self.messages if m.has_verification) / len(self.messages)

    @property
    def pushback_rate(self) -> float:
        if not self.messages:
            return 0.0
        return sum(1 for m in self.messages if m.has_pushback) / len(self.messages)

    @property
    def average_score(self) -> float:
        if not self.messages:
            return 0.0
        return sum(m.score for m in self.messages) / len(self.messages)

    def compute_drift(self, window: int = 5) -> Dict[str, Any]:
        """Compute drift metrics comparing early vs recent messages.

        Args:
            window: Number of messages to compare at start vs end

        Returns:
            Dictionary with drift metrics:
            - drift_score: Overall drift (positive = getting worse)
            - score_trend: Change in sycophancy score
            - verification_trend: Change in verification rate (negative = worse)
            - pushback_trend: Change in pushback rate (negative = worse)
            - agreement_trend: Change in agreement rate (positive = worse)
            - confidence: How confident we are in the drift estimate
        """
        if self._cached_drift is not None:
            return self._cached_drift

        n = len(self.messages)

        if n < window * 2:
            # Not enough messages for meaningful drift analysis
            result = {
                "drift_score": 0.0,
                "score_trend": 0.0,
                "verification_trend": 0.0,
                "pushback_trend": 0.0,
                "agreement_trend": 0.0,
                "confidence": 0.0,
                "message_count": n,
                "sufficient_data": False,
            }
            self._cached_drift = result
            return result

        # Split into early and recent windows
        early = self.messages[:window]
        recent = self.messages[-window:]

        # Compute trends
        early_scores = [m.score for m in early]
        recent_scores = [m.score for m in recent]
        score_trend = _mean(recent_scores) - _mean(early_scores)

        early_verif = [1.0 if m.has_verification else 0.0 for m in early]
        recent_verif = [1.0 if m.has_verification else 0.0 for m in recent]
        verification_trend = _mean(recent_verif) - _mean(early_verif)  # Positive = better

        early_push = [1.0 if m.has_pushback else 0.0 for m in early]
        recent_push = [1.0 if m.has_pushback else 0.0 for m in recent]
        pushback_trend = _mean(recent_push) - _mean(early_push)  # Positive = better

        early_agree = [1.0 if m.has_agreement else 0.0 for m in early]
        recent_agree = [1.0 if m.has_agreement else 0.0 for m in recent]
        agreement_trend = _mean(recent_agree) - _mean(early_agree)  # Positive = worse

        # Combined drift score (positive = getting worse)
        drift_score = (
            score_trend * 0.4 +           # Higher scores = worse
            (-verification_trend) * 0.2 + # Less verification = worse
            (-pushback_trend) * 0.2 +     # Less pushback = worse
            agreement_trend * 0.2         # More agreement = worse
        )

        # Confidence based on message count
        confidence = min(1.0, n / 20)

        result = {
            "drift_score": max(0, drift_score),  # Only report negative drift
            "score_trend": round(score_trend, 3),
            "verification_trend": round(verification_trend, 3),
            "pushback_trend": round(pushback_trend, 3),
            "agreement_trend": round(agreement_trend, 3),
            "confidence": round(confidence, 2),
            "message_count": n,
            "sufficient_data": True,
            "early_avg_score": round(_mean(early_scores), 3),
            "recent_avg_score": round(_mean(recent_scores), 3),
        }

        self._cached_drift = result
        return result

    def get_sparkline_data(self, max_points: int = 20) -> List[float]:
        """Get score data for sparkline visualization.

        Args:
            max_points: Maximum number of data points to return

        Returns:
            List of scores, downsampled if necessary
        """
        scores = self.scores

        if len(scores) <= max_points:
            return [round(s, 2) for s in scores]

        # Downsample using simple averaging
        step = len(scores) / max_points
        result = []
        for i in range(max_points):
            start = int(i * step)
            end = int((i + 1) * step)
            chunk = scores[start:end]
            if chunk:
                result.append(round(_mean(chunk), 2))

        return result

    def get_trend_direction(self) -> str:
        """Get human-readable trend direction.

        Returns:
            One of: "improving", "stable", "declining", "unknown"
        """
        drift = self.compute_drift()

        if not drift["sufficient_data"]:
            return "unknown"

        score = drift["drift_score"]

        if score > 0.1:
            return "declining"
        elif score < -0.05:
            return "improving"
        else:
            return "stable"

    def get_session_health(self) -> Dict[str, Any]:
        """Get overall session health metrics for dashboard.

        Returns:
            Dictionary with session health information
        """
        drift = self.compute_drift()

        # Health score (0-100, higher is better)
        # Start at 100, subtract for issues
        health = 100.0

        # Penalize for high average score
        health -= self.average_score * 30

        # Penalize for positive drift (getting worse)
        if drift["sufficient_data"]:
            health -= drift["drift_score"] * 20

        # Penalize for low verification rate
        health -= (1 - self.verification_rate) * 15

        # Penalize for low pushback rate
        health -= (1 - self.pushback_rate) * 10

        # Reward for questions asked
        question_rate = sum(1 for m in self.messages if m.has_questions) / max(1, len(self.messages))
        health += question_rate * 10

        health = max(0, min(100, health))

        return {
            "health_score": round(health, 1),
            "health_percent": round(health, 0),
            "trend": self.get_trend_direction(),
            "message_count": self.message_count,
            "average_score": round(self.average_score, 3),
            "verification_rate": round(self.verification_rate, 3),
            "pushback_rate": round(self.pushback_rate, 3),
            "agreement_rate": round(self.agreement_rate, 3),
            "drift": drift,
            "sparkline": self.get_sparkline_data(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "message_count": self.message_count,
            "health": self.get_session_health(),
        }


def _mean(values: List[float]) -> float:
    """Compute mean of a list, returning 0 for empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# Global session metrics storage (in-memory for now)
_session_metrics: Dict[str, SessionMetrics] = {}


def get_session_metrics(session_id: str) -> SessionMetrics:
    """Get or create session metrics for a session ID."""
    if session_id not in _session_metrics:
        _session_metrics[session_id] = SessionMetrics(session_id=session_id)
    return _session_metrics[session_id]


def clear_session_metrics(session_id: str):
    """Clear metrics for a session."""
    if session_id in _session_metrics:
        del _session_metrics[session_id]


def get_all_sessions() -> List[str]:
    """Get list of all tracked session IDs."""
    return list(_session_metrics.keys())
