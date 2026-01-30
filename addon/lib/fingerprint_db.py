#!/usr/bin/env python3
"""
Claude Fingerprint Database v3 - Comprehensive Schema

Stores ALL metrics from Fingerprint System v3:
- Model routing (picker vs actual, DIRECT/SUBAGENT/ROUTED)
- Thinking analysis (budget, tier, phase timing)
- Phase-specific ITT (thinking_delta vs text_delta)
- Full timing (TTFT, ITT stats with percentiles)
- Token usage (input, output, cache)
- Cache efficiency at 3 levels
- Session tracking
"""

import sqlite3
import json
import os
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path

# Database path
DB_PATH = Path(os.path.expanduser("~/.claude/fingerprint.db"))

# Known backend profiles
KNOWN_BACKENDS = {
    "trainium": {
        "name": "AWS Trainium",
        "location": "US-East (Indiana/PA)",
        "itt_range_ms": (35, 70),
        "tps_range": (8, 15),
        "variance_range": (0.3, 0.8),
        "color": "yellow",
    },
    "tpu": {
        "name": "Google TPU",
        "location": "GCP",
        "itt_range_ms": (25, 50),
        "tps_range": (12, 25),
        "variance_range": (0.2, 0.6),
        "color": "blue",
    },
    "gpu": {
        "name": "Standard GPU",
        "location": "Various",
        "itt_range_ms": (50, 100),
        "tps_range": (5, 12),
        "variance_range": (0.4, 1.0),
        "color": "magenta",
    },
    "unknown": {
        "name": "Unknown Backend",
        "location": "Unknown",
        "itt_range_ms": (0, 999),
        "tps_range": (0, 999),
        "variance_range": (0, 999),
        "color": "white",
    },
}

# Thinking budget tiers
THINKING_TIERS = {
    "ultra": {"min": 20000, "color": "red", "emoji": "🔴"},
    "enhanced": {"min": 8000, "color": "orange", "emoji": "🟠"},
    "basic": {"min": 1024, "color": "yellow", "emoji": "🟡"},
    "none": {"min": 0, "color": "none", "emoji": ""},
}

# Comprehensive Schema v3
SCHEMA_V3 = """
-- Drop old tables if needed (for migration)
-- DROP TABLE IF EXISTS samples;
-- DROP TABLE IF EXISTS model_profiles;

-- Samples table (per-call metrics)
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,

    -- MODEL ROUTING
    model_requested TEXT NOT NULL,
    model_requested_version TEXT,
    model_response TEXT,
    model_response_version TEXT,
    model_match INTEGER DEFAULT 1,
    model_ui_selected TEXT,
    ui_api_mismatch INTEGER DEFAULT 0,
    is_subagent INTEGER DEFAULT 0,
    subagent_type TEXT,

    -- THINKING
    thinking_enabled INTEGER DEFAULT 0,
    thinking_budget_requested INTEGER DEFAULT 0,
    thinking_budget_tier TEXT,
    thinking_chunk_count INTEGER DEFAULT 0,
    thinking_utilization REAL DEFAULT 0,
    thinking_duration_ms REAL DEFAULT 0,
    thinking_itt_mean_ms REAL DEFAULT 0,
    thinking_itt_std_ms REAL DEFAULT 0,

    -- TEXT PHASE
    text_chunk_count INTEGER DEFAULT 0,
    text_duration_ms REAL DEFAULT 0,
    text_itt_mean_ms REAL DEFAULT 0,
    text_itt_std_ms REAL DEFAULT 0,

    -- TOKENS
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_efficiency REAL DEFAULT 0,

    -- TIMING
    ttft_ms REAL DEFAULT 0,
    total_time_ms REAL DEFAULT 0,
    envoy_upstream_time_ms REAL DEFAULT 0,
    itt_mean_ms REAL DEFAULT 0,
    itt_std_ms REAL DEFAULT 0,
    itt_min_ms REAL DEFAULT 0,
    itt_max_ms REAL DEFAULT 0,
    itt_p50_ms REAL DEFAULT 0,
    itt_p90_ms REAL DEFAULT 0,
    itt_p99_ms REAL DEFAULT 0,
    variance_coef REAL DEFAULT 0,
    tokens_per_sec REAL DEFAULT 0,
    num_chunks INTEGER DEFAULT 0,

    -- CLASSIFICATION
    classified_backend TEXT DEFAULT 'unknown',
    confidence REAL DEFAULT 0,

    -- METADATA
    request_id TEXT,
    cf_ray TEXT,
    has_tool_use INTEGER DEFAULT 0,

    -- Legacy columns for compatibility
    model TEXT,
    num_tokens INTEGER DEFAULT 0,
    response_model TEXT,
    has_thinking INTEGER DEFAULT 0,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Model stats table (per-model aggregates)
CREATE TABLE IF NOT EXISTS model_stats (
    model TEXT PRIMARY KEY,
    model_version TEXT,
    samples_count INTEGER DEFAULT 0,

    -- TIMING BASELINES
    itt_mean_baseline REAL DEFAULT 0,
    itt_std_baseline REAL DEFAULT 0,
    tps_baseline REAL DEFAULT 0,
    ttft_baseline REAL DEFAULT 0,

    -- BACKEND DISTRIBUTION
    trainium_count INTEGER DEFAULT 0,
    tpu_count INTEGER DEFAULT 0,
    gpu_count INTEGER DEFAULT 0,
    trainium_pct REAL DEFAULT 0,
    tpu_pct REAL DEFAULT 0,
    gpu_pct REAL DEFAULT 0,

    -- CACHE STATS
    cache_efficiency_avg REAL DEFAULT 0,
    cache_efficiency_min REAL DEFAULT 0,
    cache_efficiency_max REAL DEFAULT 0,

    -- THINKING STATS
    thinking_utilization_avg REAL DEFAULT 0,

    last_updated TEXT
);

-- Session stats table (per-session aggregates)
CREATE TABLE IF NOT EXISTS session_stats (
    session_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    sample_count INTEGER DEFAULT 0,

    -- MODEL USAGE
    picker_model TEXT,
    direct_count INTEGER DEFAULT 0,
    subagent_count INTEGER DEFAULT 0,
    haiku_count INTEGER DEFAULT 0,
    sonnet_count INTEGER DEFAULT 0,

    -- ITT TRENDS
    itt_mean_start REAL DEFAULT 0,
    itt_mean_end REAL DEFAULT 0,
    itt_trend_pct REAL DEFAULT 0,
    itt_trend_direction TEXT,

    -- BACKEND
    trainium_count INTEGER DEFAULT 0,
    gpu_count INTEGER DEFAULT 0,
    tpu_count INTEGER DEFAULT 0,
    backend_switches INTEGER DEFAULT 0,

    -- CACHE
    cache_efficiency_avg REAL DEFAULT 0,
    cache_efficiency_trend TEXT,

    -- CONTEXT
    context_mismatches INTEGER DEFAULT 0,

    -- ANOMALIES
    anomalies TEXT,

    last_updated TEXT
);

-- Legacy model_profiles table (for compatibility)
CREATE TABLE IF NOT EXISTS model_profiles (
    model TEXT PRIMARY KEY,
    samples_count INTEGER DEFAULT 0,
    itt_mean_avg REAL DEFAULT 0,
    itt_mean_std REAL DEFAULT 0,
    tps_avg REAL DEFAULT 0,
    tps_std REAL DEFAULT 0,
    variance_coef_avg REAL DEFAULT 0,
    dominant_backend TEXT DEFAULT 'unknown',
    backend_confidence REAL DEFAULT 0,
    last_updated TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_samples_session ON samples(session_id);
CREATE INDEX IF NOT EXISTS idx_samples_model_req ON samples(model_requested);
CREATE INDEX IF NOT EXISTS idx_samples_model_resp ON samples(model_response);
CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp);
CREATE INDEX IF NOT EXISTS idx_samples_backend ON samples(classified_backend);
CREATE INDEX IF NOT EXISTS idx_samples_model ON samples(model);
"""

# Behavioral fingerprinting schema
BEHAVIORAL_SCHEMA = """
-- Behavioral samples table (per-turn metrics)
CREATE TABLE IF NOT EXISTS behavioral_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    turn_number INTEGER,
    read_calls INTEGER DEFAULT 0,
    edit_calls INTEGER DEFAULT 0,
    write_calls INTEGER DEFAULT 0,
    bash_calls INTEGER DEFAULT 0,
    test_calls INTEGER DEFAULT 0,
    todo_calls INTEGER DEFAULT 0,
    verification_ratio REAL DEFAULT 0,
    preparation_ratio REAL DEFAULT 0,
    completion_claims INTEGER DEFAULT 0,
    verified_completions INTEGER DEFAULT 0,
    unverified_completions INTEGER DEFAULT 0,
    agreement_phrases INTEGER DEFAULT 0,
    hedge_phrases INTEGER DEFAULT 0,
    behavioral_signature TEXT DEFAULT 'unknown',
    signature_confidence REAL DEFAULT 0,
    user_frustration_level INTEGER DEFAULT 0,
    user_frustration_trend TEXT DEFAULT 'stable',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS behavioral_session_stats (
    session_id TEXT PRIMARY KEY,
    avg_verification_ratio REAL DEFAULT 0,
    avg_preparation_ratio REAL DEFAULT 0,
    total_completion_claims INTEGER DEFAULT 0,
    total_unverified_completions INTEGER DEFAULT 0,
    total_sycophancy_signals INTEGER DEFAULT 0,
    verifier_turns INTEGER DEFAULT 0,
    completer_turns INTEGER DEFAULT 0,
    sycophant_turns INTEGER DEFAULT 0,
    theater_turns INTEGER DEFAULT 0,
    current_signature TEXT DEFAULT 'unknown',
    signature_trend TEXT DEFAULT 'stable',
    reminders_sent INTEGER DEFAULT 0,
    warnings_sent INTEGER DEFAULT 0,
    blocks_triggered INTEGER DEFAULT 0,
    last_updated TEXT
);

CREATE INDEX IF NOT EXISTS idx_behavioral_session ON behavioral_samples(session_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_timestamp ON behavioral_samples(timestamp);
"""


@contextmanager
def get_db():
    """Get database connection"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database with v3 schema and behavioral schema"""
    with get_db() as conn:
        conn.executescript(SCHEMA_V3)
        conn.executescript(BEHAVIORAL_SCHEMA)


def migrate_schema():
    """Add new columns to existing tables if needed"""
    new_columns = [
        ("samples", "session_id", "TEXT"),
        ("samples", "model_requested", "TEXT"),
        ("samples", "model_requested_version", "TEXT"),
        ("samples", "model_response", "TEXT"),
        ("samples", "model_response_version", "TEXT"),
        ("samples", "model_match", "INTEGER DEFAULT 1"),
        ("samples", "model_ui_selected", "TEXT"),
        ("samples", "ui_api_mismatch", "INTEGER DEFAULT 0"),
        ("samples", "subagent_type", "TEXT"),
        ("samples", "thinking_enabled", "INTEGER DEFAULT 0"),
        ("samples", "thinking_budget_requested", "INTEGER DEFAULT 0"),
        ("samples", "thinking_budget_tier", "TEXT"),
        ("samples", "thinking_chunk_count", "INTEGER DEFAULT 0"),
        ("samples", "thinking_utilization", "REAL DEFAULT 0"),
        ("samples", "thinking_duration_ms", "REAL DEFAULT 0"),
        ("samples", "thinking_itt_mean_ms", "REAL DEFAULT 0"),
        ("samples", "thinking_itt_std_ms", "REAL DEFAULT 0"),
        ("samples", "text_chunk_count", "INTEGER DEFAULT 0"),
        ("samples", "text_duration_ms", "REAL DEFAULT 0"),
        ("samples", "text_itt_mean_ms", "REAL DEFAULT 0"),
        ("samples", "text_itt_std_ms", "REAL DEFAULT 0"),
        ("samples", "cache_efficiency", "REAL DEFAULT 0"),
        ("samples", "ttft_ms", "REAL DEFAULT 0"),
        ("samples", "envoy_upstream_time_ms", "REAL DEFAULT 0"),
        ("samples", "itt_min_ms", "REAL DEFAULT 0"),
        ("samples", "itt_max_ms", "REAL DEFAULT 0"),
        ("samples", "itt_p50_ms", "REAL DEFAULT 0"),
        ("samples", "itt_p90_ms", "REAL DEFAULT 0"),
        ("samples", "itt_p99_ms", "REAL DEFAULT 0"),
        ("samples", "request_id", "TEXT"),
        ("samples", "cf_ray", "TEXT"),
        ("samples", "has_tool_use", "INTEGER DEFAULT 0"),
        ("samples", "input_tokens", "INTEGER DEFAULT 0"),
        ("samples", "output_tokens", "INTEGER DEFAULT 0"),
        ("samples", "cache_creation_tokens", "INTEGER DEFAULT 0"),
        ("samples", "cache_read_tokens", "INTEGER DEFAULT 0"),
        ("samples", "response_model", "TEXT"),
        ("samples", "is_subagent", "INTEGER DEFAULT 0"),
        ("samples", "has_thinking", "INTEGER DEFAULT 0"),
        # Phase 2 additions - from UNIFIED plan
        ("samples", "routing_state", "TEXT DEFAULT 'DIRECT'"),
        ("samples", "cf_edge_location", "TEXT"),
        ("samples", "speculative_decoding", "INTEGER DEFAULT 0"),
        ("samples", "speculative_type", "TEXT"),
        ("samples", "context_api_tokens", "INTEGER DEFAULT 0"),
        ("samples", "context_api_pct", "REAL DEFAULT 0"),
        ("samples", "context_cc_pct", "REAL DEFAULT 0"),
        ("samples", "context_mismatch", "INTEGER DEFAULT 0"),
        ("samples", "backend_evidence", "TEXT"),
        # Quality detection columns (for quantization/degradation detection)
        ("session_stats", "quality_score", "REAL DEFAULT 50"),
        ("session_stats", "mode_classification", "TEXT DEFAULT 'standard'"),
        ("session_stats", "timing_ratio", "REAL DEFAULT 1.0"),
        ("session_stats", "variance_ratio", "REAL DEFAULT 1.0"),
        ("session_stats", "quality_trend", "TEXT DEFAULT 'stable'"),
        # Rate limit columns (from nsanden/claude-rate-monitor discovery)
        ("samples", "rl_5h_utilization", "REAL DEFAULT NULL"),
        ("samples", "rl_5h_reset", "INTEGER DEFAULT NULL"),
        ("samples", "rl_5h_status", "TEXT DEFAULT NULL"),
        ("samples", "rl_7d_utilization", "REAL DEFAULT NULL"),
        ("samples", "rl_7d_reset", "INTEGER DEFAULT NULL"),
        ("samples", "rl_7d_status", "TEXT DEFAULT NULL"),
        ("samples", "rl_overall_status", "TEXT DEFAULT NULL"),
        ("samples", "rl_binding_window", "TEXT DEFAULT NULL"),
        ("samples", "rl_fallback_pct", "REAL DEFAULT NULL"),
        ("samples", "rl_overage_status", "TEXT DEFAULT NULL"),
        # Phase 1 fixes: persist stop_reason and thinking_tokens_used
        ("samples", "stop_reason", "TEXT"),
        ("samples", "thinking_tokens_used", "INTEGER DEFAULT 0"),
    ]

    with get_db() as conn:
        for table, column, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists


class FingerprintDatabase:
    """Comprehensive fingerprint database v3"""

    def __init__(self):
        init_db()
        migrate_schema()

    def classify_backend(self, itt_mean: float, tps: float, variance: float = 0) -> Tuple[str, float, dict]:
        """Classify backend based on timing characteristics
        
        Returns: (backend_name, confidence, evidence_dict)
        Per plan: always return trainium/tpu/gpu, never unknown.
        When ITT=0, use TPS-only classification with lower confidence.
        """
        if itt_mean == 0 and tps == 0:
            # No data at all - return gpu as default with 0 confidence
            return "gpu", 0.0, {"fallback": "No timing data available"}
        
        if itt_mean == 0 and tps > 0:
            # TPS-only classification (lower confidence)
            evidence = {"tps_only": f"TPS {tps:.1f} (no ITT data)"}
            if tps >= 12:
                return "tpu", min(40, tps * 2), evidence  # High TPS suggests TPU
            elif tps >= 8:
                return "trainium", min(35, tps * 2), evidence
            else:
                return "gpu", min(30, tps * 3), evidence

        scores = {}
        evidence = {}
        
        for backend_id, profile in KNOWN_BACKENDS.items():
            score = 0.0
            backend_evidence = []

            itt_min, itt_max = profile["itt_range_ms"]
            if itt_min <= itt_mean <= itt_max:
                center = (itt_min + itt_max) / 2
                distance = abs(itt_mean - center) / ((itt_max - itt_min) / 2)
                score += (1 - distance) * 0.5
                backend_evidence.append(f"ITT {itt_mean:.1f}ms in [{itt_min}-{itt_max}]")
            elif itt_mean < itt_min:
                score += max(0, 0.3 - (itt_min - itt_mean) / 50)
            else:
                score += max(0, 0.3 - (itt_mean - itt_max) / 50)

            tps_min, tps_max = profile["tps_range"]
            if tps_min <= tps <= tps_max:
                center = (tps_min + tps_max) / 2
                distance = abs(tps - center) / ((tps_max - tps_min) / 2)
                score += (1 - distance) * 0.3
                backend_evidence.append(f"TPS {tps:.1f} in [{tps_min}-{tps_max}]")

            var_min, var_max = profile["variance_range"]
            if var_min <= variance <= var_max:
                score += 0.2
                backend_evidence.append(f"Var {variance:.2f} in [{var_min}-{var_max}]")

            scores[backend_id] = score
            if backend_evidence:
                evidence[backend_id] = backend_evidence

        if not scores:
            return "unknown", 0.0, {}

        best_backend = max(scores, key=scores.get)
        confidence = min(100, scores[best_backend] * 100)

        return best_backend, confidence, evidence.get(best_backend, [])

    def classify_thinking_tier(self, budget: int) -> Tuple[str, str]:
        """Classify thinking tier based on budget
        
        Returns: (tier_name, display_code)
        Per plan: ULTRATHINK >= 20000, ENHANCED >= 8000, BASIC >= 1024, else DISABLED
        """
        if budget >= 20000:
            return ("ULTRATHINK", "[R]")  # Red for max thinking
        elif budget >= 8000:
            return ("ENHANCED", "[O]")   # Orange
        elif budget >= 1024:
            return ("BASIC", "[Y]")      # Yellow
        else:
            return ("DISABLED", "[-]")

    def detect_routing_state(self, model_requested: str, model_response: str, 
                             subagent_type: str = None) -> str:
        """Detect routing state based on model request/response
        
        Returns: DIRECT, SUBAGENT, or ROUTED
        """
        if subagent_type:
            return "SUBAGENT"
        if model_response and model_requested != model_response:
            return "ROUTED"
        return "DIRECT"

    def context_verification(self, api_tokens: int, cc_estimate: int, 
                             tolerance_pct: float = 10.0) -> dict:
        """Verify context token counts between API and CC estimate
        
        Returns dict with mismatch status and details
        """
        if api_tokens == 0 or cc_estimate == 0:
            return {"verified": False, "reason": "missing_data"}
        
        diff_pct = abs(api_tokens - cc_estimate) / api_tokens * 100
        
        return {
            "verified": diff_pct <= tolerance_pct,
            "api_tokens": api_tokens,
            "cc_estimate": cc_estimate,
            "diff_pct": round(diff_pct, 1),
            "mismatch": diff_pct > tolerance_pct
        }

    def time_of_day_analysis(self, hour: int = None) -> dict:
        """Analyze expected backend behavior by time of day
        
        Hypothesis: Anthropic uses inference hardware during day, training at night
        Returns expected characteristics for given hour (0-23)
        """
        from datetime import datetime
        if hour is None:
            hour = datetime.utcnow().hour
        
        # Peak inference hours (US business hours in UTC)
        # ~14:00-02:00 UTC = 9AM-9PM EST
        peak_hours = set(range(14, 24)) | set(range(0, 3))
        
        if hour in peak_hours:
            return {
                "period": "peak",
                "hour_utc": hour,
                "expected_latency": "higher",
                "expected_backend": "inference_optimized",
                "hypothesis": "High user load, inference-focused hardware"
            }
        else:
            return {
                "period": "off_peak", 
                "hour_utc": hour,
                "expected_latency": "lower",
                "expected_backend": "mixed",
                "hypothesis": "Lower load, possible training workloads"
            }

    def calculate_trends(self, model: str, window_hours: int = 24) -> dict:
        """Calculate timing trends for a model over a time window
        
        Returns trend analysis with direction and magnitude
        """
        with get_db() as conn:
            rows = conn.execute("""
                SELECT itt_mean_ms, tokens_per_sec, timestamp, classified_backend
                FROM samples 
                WHERE (model_requested = ? OR model_response = ?)
                AND timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', ? || ' hours')
                ORDER BY timestamp ASC
            """, (model, model, -window_hours)).fetchall()
            
            if len(rows) < 5:
                return {"error": "insufficient_data", "samples": len(rows)}
            
            # Split into halves for trend comparison
            mid = len(rows) // 2
            first_half = rows[:mid]
            second_half = rows[mid:]
            
            def avg(vals):
                return sum(vals) / len(vals) if vals else 0
            
            first_itt = avg([r["itt_mean_ms"] for r in first_half if r["itt_mean_ms"]])
            second_itt = avg([r["itt_mean_ms"] for r in second_half if r["itt_mean_ms"]])
            
            first_tps = avg([r["tokens_per_sec"] for r in first_half if r["tokens_per_sec"]])
            second_tps = avg([r["tokens_per_sec"] for r in second_half if r["tokens_per_sec"]])
            
            # Backend distribution
            backends = [r["classified_backend"] for r in rows if r["classified_backend"]]
            backend_counts = {}
            for b in backends:
                backend_counts[b] = backend_counts.get(b, 0) + 1
            
            itt_change = ((second_itt - first_itt) / first_itt * 100) if first_itt else 0
            tps_change = ((second_tps - first_tps) / first_tps * 100) if first_tps else 0
            
            return {
                "model": model,
                "window_hours": window_hours,
                "samples": len(rows),
                "itt_trend": {
                    "first_half_avg": round(first_itt, 1),
                    "second_half_avg": round(second_itt, 1),
                    "change_pct": round(itt_change, 1),
                    "direction": "increasing" if itt_change > 5 else "decreasing" if itt_change < -5 else "stable"
                },
                "tps_trend": {
                    "first_half_avg": round(first_tps, 1),
                    "second_half_avg": round(second_tps, 1),
                    "change_pct": round(tps_change, 1),
                    "direction": "increasing" if tps_change > 5 else "decreasing" if tps_change < -5 else "stable"
                },
                "backend_distribution": backend_counts
            }

    def add_sample(self, sample: dict) -> Tuple[str, float]:
        """Add a new comprehensive sample"""
        # Always compute evidence for storage
        backend, confidence, evidence = self.classify_backend(
            sample.get("itt_mean_ms", 0),
            sample.get("tokens_per_sec", 0),
            sample.get("variance_coef", 0)
        )
        if not sample.get("classified_backend"):
            sample["classified_backend"] = backend
            sample["confidence"] = confidence
        sample["backend_evidence"] = json.dumps(evidence) if evidence else None

        # Fill legacy fields for compatibility
        if not sample.get("model"):
            sample["model"] = sample.get("model_requested", "unknown")
        if not sample.get("response_model"):
            sample["response_model"] = sample.get("model_response", "")
        if not sample.get("has_thinking"):
            sample["has_thinking"] = sample.get("thinking_enabled", 0)
        if not sample.get("num_tokens"):
            sample["num_tokens"] = sample.get("num_chunks", 0)

        with get_db() as conn:
            conn.execute("""
                INSERT INTO samples (
                    timestamp, session_id,
                    model_requested, model_requested_version,
                    model_response, model_response_version,
                    model_match, model_ui_selected, ui_api_mismatch, is_subagent, subagent_type,
                    thinking_enabled, thinking_budget_requested, thinking_budget_tier,
                    thinking_chunk_count, thinking_utilization, thinking_tokens_used, thinking_duration_ms,
                    thinking_itt_mean_ms, thinking_itt_std_ms,
                    text_chunk_count, text_duration_ms,
                    text_itt_mean_ms, text_itt_std_ms,
                    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
                    cache_efficiency,
                    ttft_ms, total_time_ms, envoy_upstream_time_ms,
                    itt_mean_ms, itt_std_ms, itt_min_ms, itt_max_ms,
                    itt_p50_ms, itt_p90_ms, itt_p99_ms,
                    variance_coef, tokens_per_sec, num_chunks,
                    classified_backend, confidence, location,
                    request_id, cf_ray, stop_reason, has_tool_use,
                    model, num_tokens, response_model, has_thinking,
                    routing_state, cf_edge_location, speculative_decoding, speculative_type,
                    context_api_tokens, context_api_pct, context_cc_pct, context_mismatch,
                    backend_evidence,
                    rl_5h_utilization, rl_5h_reset, rl_5h_status,
                    rl_7d_utilization, rl_7d_reset, rl_7d_status,
                    rl_overall_status, rl_binding_window, rl_fallback_pct, rl_overage_status
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                sample.get("timestamp", datetime.utcnow().isoformat()),
                sample.get("session_id"),
                sample.get("model_requested", "unknown"),
                sample.get("model_requested_version"),
                sample.get("model_response"),
                sample.get("model_response_version"),
                sample.get("model_match", 1),
                sample.get("model_ui_selected"),
                sample.get("ui_api_mismatch", 0),
                sample.get("is_subagent", 0),
                sample.get("subagent_type"),
                sample.get("thinking_enabled", 0),
                sample.get("thinking_budget_requested", 0),
                sample.get("thinking_budget_tier"),
                sample.get("thinking_chunk_count", 0),
                sample.get("thinking_utilization", 0),
                sample.get("thinking_tokens_used", 0),
                sample.get("thinking_duration_ms", 0),
                sample.get("thinking_itt_mean_ms", 0),
                sample.get("thinking_itt_std_ms", 0),
                sample.get("text_chunk_count", 0),
                sample.get("text_duration_ms", 0),
                sample.get("text_itt_mean_ms", 0),
                sample.get("text_itt_std_ms", 0),
                sample.get("input_tokens", 0),
                sample.get("output_tokens", 0),
                sample.get("cache_creation_tokens", 0),
                sample.get("cache_read_tokens", 0),
                sample.get("cache_efficiency", 0),
                sample.get("ttft_ms", 0),
                sample.get("total_time_ms", 0),
                sample.get("envoy_upstream_time_ms", 0),
                sample.get("itt_mean_ms", 0),
                sample.get("itt_std_ms", 0),
                sample.get("itt_min_ms", 0),
                sample.get("itt_max_ms", 0),
                sample.get("itt_p50_ms", 0),
                sample.get("itt_p90_ms", 0),
                sample.get("itt_p99_ms", 0),
                sample.get("variance_coef", 0),
                sample.get("tokens_per_sec", 0),
                sample.get("num_chunks", 0),
                sample.get("classified_backend", "unknown"),
                sample.get("confidence", 0),
                sample.get("location", "unknown"),
                sample.get("request_id"),
                sample.get("cf_ray"),
                sample.get("stop_reason"),
                sample.get("has_tool_use", 0),
                sample.get("model"),
                sample.get("num_tokens", 0),
                sample.get("response_model"),
                sample.get("has_thinking", 0),
                # Phase 2 additions
                sample.get("routing_state", "DIRECT"),
                sample.get("cf_edge_location"),
                sample.get("speculative_decoding", 0),
                sample.get("speculative_type"),
                sample.get("context_api_tokens", 0),
                sample.get("context_api_pct", 0),
                sample.get("context_cc_pct", 0),
                sample.get("context_mismatch", 0),
                sample.get("backend_evidence"),
                # Rate limit data
                sample.get("rl_5h_utilization"),
                sample.get("rl_5h_reset"),
                sample.get("rl_5h_status"),
                sample.get("rl_7d_utilization"),
                sample.get("rl_7d_reset"),
                sample.get("rl_7d_status"),
                sample.get("rl_overall_status"),
                sample.get("rl_binding_window"),
                sample.get("rl_fallback_pct"),
                sample.get("rl_overage_status"),
            ))

            # Update model stats
            self._update_model_stats(conn, sample.get("model_response") or sample.get("model_requested", "unknown"))

            # Update session stats
            if sample.get("session_id"):
                self._update_session_stats(conn, sample)

            # Update legacy model profiles
            self._update_model_profile(conn, sample.get("model", "unknown"))

        return sample["classified_backend"], sample["confidence"]

    def _update_model_stats(self, conn, model: str):
        """Update per-model aggregate statistics"""
        rows = conn.execute("""
            SELECT itt_mean_ms, tokens_per_sec, ttft_ms, classified_backend,
                   cache_efficiency, thinking_utilization
            FROM samples WHERE model_response = ? OR model_requested = ?
            ORDER BY timestamp DESC LIMIT 100
        """, (model, model)).fetchall()

        if not rows:
            return

        itt_values = [r["itt_mean_ms"] for r in rows if r["itt_mean_ms"]]
        tps_values = [r["tokens_per_sec"] for r in rows if r["tokens_per_sec"]]
        ttft_values = [r["ttft_ms"] for r in rows if r["ttft_ms"]]
        cache_values = [r["cache_efficiency"] for r in rows if r["cache_efficiency"]]
        thinking_values = [r["thinking_utilization"] for r in rows if r["thinking_utilization"]]

        # Backend distribution
        backends = [r["classified_backend"] for r in rows]
        trainium_count = backends.count("trainium")
        tpu_count = backends.count("tpu")
        gpu_count = backends.count("gpu")
        total = len(backends) or 1

        conn.execute("""
            INSERT INTO model_stats (
                model, samples_count,
                itt_mean_baseline, itt_std_baseline, tps_baseline, ttft_baseline,
                trainium_count, tpu_count, gpu_count,
                trainium_pct, tpu_pct, gpu_pct,
                cache_efficiency_avg, cache_efficiency_min, cache_efficiency_max,
                thinking_utilization_avg, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model) DO UPDATE SET
                samples_count = excluded.samples_count,
                itt_mean_baseline = excluded.itt_mean_baseline,
                itt_std_baseline = excluded.itt_std_baseline,
                tps_baseline = excluded.tps_baseline,
                ttft_baseline = excluded.ttft_baseline,
                trainium_count = excluded.trainium_count,
                tpu_count = excluded.tpu_count,
                gpu_count = excluded.gpu_count,
                trainium_pct = excluded.trainium_pct,
                tpu_pct = excluded.tpu_pct,
                gpu_pct = excluded.gpu_pct,
                cache_efficiency_avg = excluded.cache_efficiency_avg,
                cache_efficiency_min = excluded.cache_efficiency_min,
                cache_efficiency_max = excluded.cache_efficiency_max,
                thinking_utilization_avg = excluded.thinking_utilization_avg,
                last_updated = excluded.last_updated
        """, (
            model, len(rows),
            statistics.mean(itt_values) if itt_values else 0,
            statistics.stdev(itt_values) if len(itt_values) > 1 else 0,
            statistics.mean(tps_values) if tps_values else 0,
            statistics.mean(ttft_values) if ttft_values else 0,
            trainium_count, tpu_count, gpu_count,
            (trainium_count / total) * 100,
            (tpu_count / total) * 100,
            (gpu_count / total) * 100,
            statistics.mean(cache_values) if cache_values else 0,
            min(cache_values) if cache_values else 0,
            max(cache_values) if cache_values else 0,
            statistics.mean(thinking_values) if thinking_values else 0,
            datetime.utcnow().isoformat(),
        ))

    def _update_session_stats(self, conn, sample: dict):
        """Update per-session aggregate statistics"""
        session_id = sample.get("session_id")
        if not session_id:
            return

        rows = conn.execute("""
            SELECT * FROM samples WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,)).fetchall()

        if not rows:
            return

        # Count model types
        direct_count = sum(1 for r in rows if r["model_match"] == 1)
        subagent_count = sum(1 for r in rows if r["is_subagent"] == 1)
        haiku_count = sum(1 for r in rows if r["subagent_type"] == "haiku")
        sonnet_count = sum(1 for r in rows if r["subagent_type"] == "sonnet")

        # Backend distribution
        backends = [r["classified_backend"] for r in rows]
        trainium_count = backends.count("trainium")
        tpu_count = backends.count("tpu")
        gpu_count = backends.count("gpu")

        # Detect backend switches (exclude "unknown" which is missing data)
        backend_switches = 0
        prev = None
        for b in backends:
            if b == "unknown":
                continue  # Skip unknown - not a real backend switch
            if prev and b != prev:
                backend_switches += 1
            prev = b

        # ITT trend
        itt_values = [r["itt_mean_ms"] for r in rows if r["itt_mean_ms"]]
        itt_start = itt_values[0] if itt_values else 0
        itt_end = itt_values[-1] if itt_values else 0
        itt_trend_pct = ((itt_end - itt_start) / itt_start * 100) if itt_start else 0
        itt_trend_direction = "rising" if itt_trend_pct > 5 else "falling" if itt_trend_pct < -5 else "stable"

        # Cache efficiency (filter to valid 0-100 range)
        cache_values = [r["cache_efficiency"] for r in rows if r["cache_efficiency"] and 0 <= r["cache_efficiency"] <= 100]
        cache_avg = statistics.mean(cache_values) if cache_values else 0

        conn.execute("""
            INSERT INTO session_stats (
                session_id, start_time, end_time, sample_count,
                picker_model, direct_count, subagent_count, haiku_count, sonnet_count,
                itt_mean_start, itt_mean_end, itt_trend_pct, itt_trend_direction,
                trainium_count, gpu_count, tpu_count, backend_switches,
                cache_efficiency_avg, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                end_time = excluded.end_time,
                sample_count = excluded.sample_count,
                direct_count = excluded.direct_count,
                subagent_count = excluded.subagent_count,
                haiku_count = excluded.haiku_count,
                sonnet_count = excluded.sonnet_count,
                itt_mean_end = excluded.itt_mean_end,
                itt_trend_pct = excluded.itt_trend_pct,
                itt_trend_direction = excluded.itt_trend_direction,
                trainium_count = excluded.trainium_count,
                gpu_count = excluded.gpu_count,
                tpu_count = excluded.tpu_count,
                backend_switches = excluded.backend_switches,
                cache_efficiency_avg = excluded.cache_efficiency_avg,
                last_updated = excluded.last_updated
        """, (
            session_id,
            rows[0]["timestamp"],
            rows[-1]["timestamp"],
            len(rows),
            rows[0]["model_requested"],
            direct_count, subagent_count, haiku_count, sonnet_count,
            itt_start, itt_end, itt_trend_pct, itt_trend_direction,
            trainium_count, gpu_count, tpu_count, backend_switches,
            cache_avg,
            datetime.utcnow().isoformat(),
        ))

    def _update_model_profile(self, conn, model: str):
        """Update legacy model profile for compatibility"""
        rows = conn.execute("""
            SELECT itt_mean_ms, tokens_per_sec, variance_coef, classified_backend
            FROM samples WHERE model = ?
            ORDER BY timestamp DESC LIMIT 50
        """, (model,)).fetchall()

        if not rows:
            return

        itt_means = [r["itt_mean_ms"] for r in rows if r["itt_mean_ms"]]
        tps_values = [r["tokens_per_sec"] for r in rows if r["tokens_per_sec"]]
        var_values = [r["variance_coef"] for r in rows if r["variance_coef"]]
        backends = [r["classified_backend"] for r in rows]

        itt_mean_avg = statistics.mean(itt_means) if itt_means else 0
        itt_mean_std = statistics.stdev(itt_means) if len(itt_means) > 1 else 0
        tps_avg = statistics.mean(tps_values) if tps_values else 0
        tps_std = statistics.stdev(tps_values) if len(tps_values) > 1 else 0
        var_avg = statistics.mean(var_values) if var_values else 0

        backend_counts = {}
        for b in backends:
            backend_counts[b] = backend_counts.get(b, 0) + 1
        dominant_backend = max(backend_counts, key=backend_counts.get) if backend_counts else "unknown"
        backend_confidence = (backend_counts.get(dominant_backend, 0) / len(backends)) * 100 if backends else 0

        conn.execute("""
            INSERT INTO model_profiles (
                model, samples_count, itt_mean_avg, itt_mean_std,
                tps_avg, tps_std, variance_coef_avg,
                dominant_backend, backend_confidence, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model) DO UPDATE SET
                samples_count = excluded.samples_count,
                itt_mean_avg = excluded.itt_mean_avg,
                itt_mean_std = excluded.itt_mean_std,
                tps_avg = excluded.tps_avg,
                tps_std = excluded.tps_std,
                variance_coef_avg = excluded.variance_coef_avg,
                dominant_backend = excluded.dominant_backend,
                backend_confidence = excluded.backend_confidence,
                last_updated = excluded.last_updated
        """, (
            model, len(rows), itt_mean_avg, itt_mean_std,
            tps_avg, tps_std, var_avg,
            dominant_backend, backend_confidence,
            datetime.utcnow().isoformat()
        ))

    def get_latest_classification(self, model_filter: str = None, max_age_minutes: int = None) -> Optional[dict]:
        """Get the most recent classification with ALL fields.
        
        Args:
            model_filter: Optional model name to filter by (e.g., "opus" matches any opus model)
            max_age_minutes: Optional max age in minutes (for session-like filtering)
        """
        with get_db() as conn:
            # Build query with optional filters
            query = "SELECT * FROM samples WHERE 1=1"
            params = []
            
            if model_filter:
                query += " AND (model_requested LIKE ? OR model_response LIKE ?)"
                params.extend([f"%{model_filter}%", f"%{model_filter}%"])
            
            if max_age_minutes:
                query += " AND timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-{} minutes')".format(max_age_minutes)
            
            query += " ORDER BY timestamp DESC LIMIT 1"
            row = conn.execute(query, params).fetchone()

            if not row:
                return None

            row_dict = dict(row)
            backend_info = KNOWN_BACKENDS.get(row_dict.get("classified_backend", ""), {})
            tier_info = THINKING_TIERS.get(row_dict.get("thinking_budget_tier", "none"), {})

            # Determine model state
            if row_dict.get("model_match", 1) == 1:
                model_state = "DIRECT"
                model_state_icon = "✓"
            elif row_dict.get("is_subagent", 0) == 1:
                model_state = "SUBAGENT"
                model_state_icon = "⚡"
            else:
                model_state = "ROUTED"
                model_state_icon = "⚠"

            return {
                # Model routing
                "model_requested": row_dict.get("model_requested", row_dict.get("model", "unknown")),
                "model_requested_version": row_dict.get("model_requested_version", ""),
                "model_response": row_dict.get("model_response", row_dict.get("response_model", "")),
                "model_response_version": row_dict.get("model_response_version", ""),
                "model_match": row_dict.get("model_match", 1),
                "is_subagent": row_dict.get("is_subagent", 0),
                "subagent_type": row_dict.get("subagent_type"),
                "model_state": model_state,
                "model_state_icon": model_state_icon,

                # Thinking
                "thinking_enabled": row_dict.get("thinking_enabled", row_dict.get("has_thinking", 0)),
                "thinking_budget_requested": row_dict.get("thinking_budget_requested", 0),
                "thinking_budget_tier": row_dict.get("thinking_budget_tier", "none"),
                "thinking_tier_color": tier_info.get("color", "none"),
                "thinking_tier_emoji": tier_info.get("emoji", ""),
                "thinking_chunk_count": row_dict.get("thinking_chunk_count", 0),
                "thinking_utilization": row_dict.get("thinking_utilization", 0),
                "thinking_tokens_used": row_dict.get("thinking_tokens_used", 0),
                "thinking_duration_ms": row_dict.get("thinking_duration_ms", 0),
                "thinking_itt_mean_ms": row_dict.get("thinking_itt_mean_ms", 0),
                "thinking_itt_std_ms": row_dict.get("thinking_itt_std_ms", 0),

                # Text phase
                "text_chunk_count": row_dict.get("text_chunk_count", 0),
                "text_duration_ms": row_dict.get("text_duration_ms", 0),
                "text_itt_mean_ms": row_dict.get("text_itt_mean_ms", 0),
                "text_itt_std_ms": row_dict.get("text_itt_std_ms", 0),

                # Tokens
                "input_tokens": row_dict.get("input_tokens", 0),
                "output_tokens": row_dict.get("output_tokens", 0),
                "cache_creation_tokens": row_dict.get("cache_creation_tokens", 0),
                "cache_read_tokens": row_dict.get("cache_read_tokens", 0),
                "cache_efficiency": row_dict.get("cache_efficiency", 0),

                # Timing
                "ttft_ms": row_dict.get("ttft_ms", 0),
                "total_time_ms": row_dict.get("total_time_ms", 0),
                "itt_mean_ms": row_dict.get("itt_mean_ms", 0),
                "itt_std_ms": row_dict.get("itt_std_ms", 0),
                "itt_min_ms": row_dict.get("itt_min_ms", 0),
                "itt_max_ms": row_dict.get("itt_max_ms", 0),
                "itt_p50_ms": row_dict.get("itt_p50_ms", 0),
                "itt_p90_ms": row_dict.get("itt_p90_ms", 0),
                "itt_p99_ms": row_dict.get("itt_p99_ms", 0),
                "tokens_per_sec": row_dict.get("tokens_per_sec", 0),
                "variance_coef": row_dict.get("variance_coef", 0),

                # Backend
                "classified_backend": row_dict.get("classified_backend", "unknown"),
                "backend_name": backend_info.get("name", "Unknown"),
                "location": backend_info.get("location", "Unknown"),
                "confidence": row_dict.get("confidence", 0),
                "color": backend_info.get("color", "white"),

                # Metadata
                "timestamp": row_dict.get("timestamp"),
                "session_id": row_dict.get("session_id"),
                "request_id": row_dict.get("request_id"),
                "cf_ray": row_dict.get("cf_ray"),
                "has_tool_use": row_dict.get("has_tool_use", 0),
                "stop_reason": row_dict.get("stop_reason"),

                # Infrastructure / routing
                "envoy_upstream_time_ms": row_dict.get("envoy_upstream_time_ms", 0),
                "cf_edge_location": row_dict.get("cf_edge_location", ""),
                "speculative_decoding": row_dict.get("speculative_decoding", 0),
                "speculative_type": row_dict.get("speculative_type"),
                "model_ui_selected": row_dict.get("model_ui_selected"),
                "ui_api_mismatch": row_dict.get("ui_api_mismatch", 0),
                "num_chunks": row_dict.get("num_chunks", 0),
                "backend_evidence": row_dict.get("backend_evidence"),
                "routing_state": row_dict.get("routing_state", "DIRECT"),
                "context_api_pct": row_dict.get("context_api_pct", 0),
                "context_api_tokens": row_dict.get("context_api_tokens", 0),

                # Rate limit
                "rl_5h_utilization": row_dict.get("rl_5h_utilization"),
                "rl_5h_reset": row_dict.get("rl_5h_reset"),
                "rl_5h_status": row_dict.get("rl_5h_status"),
                "rl_7d_utilization": row_dict.get("rl_7d_utilization"),
                "rl_7d_reset": row_dict.get("rl_7d_reset"),
                "rl_7d_status": row_dict.get("rl_7d_status"),
                "rl_overall_status": row_dict.get("rl_overall_status"),
                "rl_binding_window": row_dict.get("rl_binding_window"),
                "rl_fallback_pct": row_dict.get("rl_fallback_pct"),
                "rl_overage_status": row_dict.get("rl_overage_status"),

                # Legacy
                "model": row_dict.get("model", row_dict.get("model_requested", "unknown")),
            }

    def get_extras(self, model_filter: str = None, max_age_minutes: int = 30) -> dict:
        """Get trends and averages needed by statusline display.

        Returns:
            dict with:
            - cache_model_avg: Average cache efficiency for this model (last 50 samples)
            - cache_session_avg: Average cache efficiency for recent session
            - backend_trend: "↗" rising, "↘" falling, "→" stable
            - itt_trend: "↗" rising, "↘" falling, "→" stable
            - context_api_pct: API-reported context percentage (ground truth)
        """
        extras = {
            "cache_model_avg": 0.0,
            "cache_session_avg": 0.0,
            "backend_trend": "→",
            "itt_trend": "→",
            "context_api_pct": 0.0,
        }

        with get_db() as conn:
            # 1. Cache model average (last 50 samples for this model)
            if model_filter:
                rows = conn.execute("""
                    SELECT cache_efficiency FROM samples
                    WHERE (model_response LIKE ? OR model_requested LIKE ?)
                    AND cache_efficiency > 0 AND cache_efficiency <= 100
                    ORDER BY timestamp DESC LIMIT 50
                """, (f"%{model_filter}%", f"%{model_filter}%")).fetchall()
                if rows:
                    values = [r[0] for r in rows if r[0] and 0 < r[0] <= 100]
                    if values:
                        extras["cache_model_avg"] = statistics.mean(values)

            # 2. Cache session average (last 30 min)
            rows = conn.execute("""
                SELECT cache_efficiency FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-30 minutes')
                AND cache_efficiency > 0 AND cache_efficiency <= 100
                ORDER BY timestamp DESC
            """).fetchall()
            if rows:
                values = [r[0] for r in rows if r[0] and 0 < r[0] <= 100]
                if values:
                    extras["cache_session_avg"] = statistics.mean(values)

            # 3. Backend trend - use comprehensive calculate_trends()
            # Get model for trend calculation
            model_for_trends = model_filter if model_filter else None
            if not model_for_trends:
                # Get most recent model from samples
                model_row = conn.execute("""
                    SELECT model_response FROM samples 
                    ORDER BY timestamp DESC LIMIT 1
                """).fetchone()
                model_for_trends = model_row[0] if model_row else None
            
            # Initialize comprehensive trend data
            extras["itt_trend_data"] = None
            extras["tps_trend_data"] = None
            extras["backend_distribution"] = {}
        
        # Call calculate_trends() outside the context manager (it has its own)
        if model_for_trends:
            try:
                trends = self.calculate_trends(model_for_trends, window_hours=1)
                if "error" not in trends:
                    # Extract ITT trend
                    itt_trend = trends.get("itt_trend", {})
                    direction = itt_trend.get("direction", "stable")
                    if direction == "increasing":
                        extras["itt_trend"] = "↗"
                    elif direction == "decreasing":
                        extras["itt_trend"] = "↘"
                    else:
                        extras["itt_trend"] = "→"
                    
                    # Store full trend data for statusline
                    extras["itt_trend_data"] = {
                        "first_half_avg": itt_trend.get("first_half_avg", 0),
                        "second_half_avg": itt_trend.get("second_half_avg", 0),
                        "change_pct": itt_trend.get("change_pct", 0),
                        "direction": direction
                    }
                    
                    # TPS trend data
                    tps_trend = trends.get("tps_trend", {})
                    extras["tps_trend_data"] = {
                        "first_half_avg": tps_trend.get("first_half_avg", 0),
                        "second_half_avg": tps_trend.get("second_half_avg", 0),
                        "change_pct": tps_trend.get("change_pct", 0),
                        "direction": tps_trend.get("direction", "stable")
                    }
                    
                    # Backend distribution
                    extras["backend_distribution"] = trends.get("backend_distribution", {})
                    
                    # Backend trend arrow from distribution changes
                    backend_dist = extras["backend_distribution"]
                    if backend_dist:
                        total = sum(backend_dist.values())
                        if total > 0:
                            # If trainium dominates, trend up; if standard gpu, stable
                            trn_pct = backend_dist.get("trainium", 0) / total * 100
                            if trn_pct > 60:
                                extras["backend_trend"] = "↗"
                            elif trn_pct < 20:
                                extras["backend_trend"] = "↘"
            except Exception as e:
                import sys
                print(f"[fingerprint_db] trends calculation failed: {e}", file=sys.stderr)
        
        with get_db() as conn:

            # 5. Context API % - use MAX input_tokens in session as proxy
            # (As conversation grows, input_tokens increases with context)
            row = conn.execute("""
                SELECT MAX(input_tokens) FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-60 minutes')
                AND input_tokens > 0
            """).fetchone()
            if row and row[0]:
                # Use max input_tokens seen as approximation of context usage
                # Assume 200k context window for Opus
                max_input = row[0]
                extras["context_api_pct"] = min(100, (max_input / 200000) * 100)
                extras["max_input_tokens"] = max_input  # Also expose raw value

        return extras

    def get_subagent_counts(self, max_age_minutes: int = 60) -> dict:
        """Get subagent call counts for current session.

        Returns:
            dict with:
            - haiku_subagent: Haiku calls that are subagents
            - sonnet_subagent: Sonnet calls that are subagents
            - haiku_direct: Direct Haiku calls
            - sonnet_direct: Direct Sonnet calls
            - opus_direct: Direct Opus calls
            - total_subagent: All subagent calls
            - total_direct: All direct calls
            - total_all: All calls
        """
        counts = {
            "haiku_subagent": 0,
            "sonnet_subagent": 0,
            "haiku_direct": 0,
            "sonnet_direct": 0,
            "opus_direct": 0,
            "total_subagent": 0,
            "total_direct": 0,
            "total_all": 0,
            # Model mismatch tracking (requested != response)
            "downgrades": 0,  # Got cheaper model than requested
            "upgrades": 0,    # Got better model than requested (rare)
            "mismatches": 0,  # Any mismatch
            # UI→API mismatch tracking (Claude Code silently changing model)
            "ui_api_mismatches": 0,  # Times Claude Code changed your selection
            # Legacy fields for compatibility
            "haiku_count": 0,
            "sonnet_count": 0,
            "opus_count": 0,
            "total_count": 0,
            "subagent_count": 0,
        }

        with get_db() as conn:
            # Count by model type and subagent status
            rows = conn.execute("""
                SELECT model_response, is_subagent, COUNT(*) as cnt
                FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-{} minutes')
                GROUP BY model_response, is_subagent
            """.format(max_age_minutes)).fetchall()

            for row in rows:
                model = (row[0] or "").lower()
                is_sub = row[1]
                cnt = row[2]

                counts["total_all"] += cnt
                counts["total_count"] += cnt  # Legacy

                if is_sub:
                    counts["total_subagent"] += cnt
                    counts["subagent_count"] += cnt  # Legacy
                else:
                    counts["total_direct"] += cnt

                if "haiku" in model:
                    counts["haiku_count"] += cnt  # Legacy - all haiku
                    if is_sub:
                        counts["haiku_subagent"] += cnt
                    else:
                        counts["haiku_direct"] += cnt
                elif "sonnet" in model:
                    counts["sonnet_count"] += cnt  # Legacy - all sonnet
                    if is_sub:
                        counts["sonnet_subagent"] += cnt
                    else:
                        counts["sonnet_direct"] += cnt
                elif "opus" in model:
                    counts["opus_count"] += cnt  # Legacy
                    counts["opus_direct"] += cnt

            # Query for model mismatches (requested != response, excluding subagents)
            mismatch_rows = conn.execute("""
                SELECT model_requested, model_response, COUNT(*) as cnt
                FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-{} minutes')
                  AND is_subagent = 0
                  AND model_requested IS NOT NULL
                  AND model_requested != ''
                  AND model_response IS NOT NULL
                  AND model_response != ''
                  AND LOWER(model_requested) != LOWER(model_response)
                GROUP BY model_requested, model_response
            """.format(max_age_minutes)).fetchall()

            model_rank = {"opus": 3, "sonnet": 2, "haiku": 1}
            for row in mismatch_rows:
                req = (row[0] or "").lower()
                resp = (row[1] or "").lower()
                cnt = row[2]
                
                counts["mismatches"] += cnt
                
                # Determine if downgrade or upgrade
                req_rank = next((v for k, v in model_rank.items() if k in req), 0)
                resp_rank = next((v for k, v in model_rank.items() if k in resp), 0)
                
                if resp_rank < req_rank:
                    counts["downgrades"] += cnt  # Got cheaper model
                elif resp_rank > req_rank:
                    counts["upgrades"] += cnt  # Got better model (rare)

            # Query for UI→API mismatches (Claude Code silently changing model selection)
            ui_mismatch_row = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-{} minutes')
                  AND ui_api_mismatch = 1
            """.format(max_age_minutes)).fetchone()
            if ui_mismatch_row:
                counts["ui_api_mismatches"] = ui_mismatch_row[0]

            # Get timestamp of last subagent call
            last_sub_row = conn.execute("""
                SELECT timestamp FROM samples
                WHERE is_subagent = 1
                ORDER BY timestamp DESC LIMIT 1
            """).fetchone()
            if last_sub_row:
                counts["last_subagent_time"] = last_sub_row[0]
            
            # Get recent subagent counts (last 15 minutes) for fresh warning
            recent_rows = conn.execute("""
                SELECT model_response, COUNT(*) as cnt
                FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime', '-15 minutes')
                  AND is_subagent = 1
                GROUP BY model_response
            """).fetchall()
            
            recent_counts = {"haiku": 0, "sonnet": 0}
            for row in recent_rows:
                model = (row[0] or "").lower()
                cnt = row[1]
                if "haiku" in model:
                    recent_counts["haiku"] += cnt
                elif "sonnet" in model:
                    recent_counts["sonnet"] += cnt
            counts["recent_counts"] = recent_counts

        return counts

    def get_anomalies(self, max_age_minutes: int = 30) -> list:
        """Detect anomalies in recent fingerprint data.
        
        Returns list of anomaly dicts with type and description.
        """
        anomalies = []
        
        with get_db() as conn:
            # Get recent ITT data for spike detection
            rows = conn.execute("""
                SELECT itt_mean_ms, classified_backend
                FROM samples
                WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-{} minutes')
                ORDER BY timestamp DESC
                LIMIT 20
            """.format(max_age_minutes)).fetchall()
            
            if len(rows) >= 3:
                itt_values = [r[0] for r in rows if r[0] and r[0] > 0]
                backends = [r[1] for r in rows if r[1]]
                
                if itt_values:
                    import statistics
                    mean_itt = statistics.mean(itt_values)
                    if len(itt_values) >= 3:
                        stddev_itt = statistics.stdev(itt_values)
                        current_itt = itt_values[0]  # Most recent
                        
                        # ITT spike: current > mean + 2*stddev
                        if stddev_itt > 0 and current_itt > mean_itt + 2 * stddev_itt:
                            sigma = (current_itt - mean_itt) / stddev_itt
                            anomalies.append({
                                "type": "itt_spike",
                                "symbol": "[ITT]",
                                "desc": f"ITT spike: {current_itt:.0f}ms is {sigma:.1f}σ above mean"
                            })
                
                # Backend switch detection
                if len(backends) >= 3:
                    # Filter out "unknown" from backend list (missing data, not a real backend)
                    valid_backends = [b for b in backends[:5] if b and b != "unknown"]
                    unique_backends = list(set(valid_backends))
                    if len(unique_backends) > 1:
                        anomalies.append({
                            "type": "backend_switch",
                            "symbol": "[BE]",
                            "desc": f"Backend switch detected: {unique_backends}"
                        })
        
        return anomalies

    def get_session_stats(self, session_id: str = None) -> Optional[dict]:
        """Get session statistics"""
        with get_db() as conn:
            if session_id:
                row = conn.execute("""
                    SELECT * FROM session_stats WHERE session_id = ?
                """, (session_id,)).fetchone()
            else:
                row = conn.execute("""
                    SELECT * FROM session_stats ORDER BY last_updated DESC LIMIT 1
                """).fetchone()

            if row:
                return dict(row)
            return None

    def get_model_stats(self, model: str) -> Optional[dict]:
        """Get per-model statistics"""
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM model_stats WHERE model = ?
            """, (model,)).fetchone()

            if row:
                return dict(row)
            return None

    def get_model_baseline(self, model: str) -> Optional[dict]:
        """Get baseline timing values for a model (for comparison/anomaly detection)"""
        with get_db() as conn:
            row = conn.execute("""
                SELECT 
                    model,
                    itt_mean_baseline,
                    itt_std_baseline,
                    tps_baseline,
                    ttft_baseline,
                    samples_count,
                    trainium_pct,
                    tpu_pct,
                    gpu_pct
                FROM model_stats 
                WHERE model = ?
            """, (model,)).fetchone()

            if row:
                return {
                    "model": row["model"],
                    "itt_mean": row["itt_mean_baseline"],
                    "itt_std": row["itt_std_baseline"],
                    "tps": row["tps_baseline"],
                    "ttft": row["ttft_baseline"],
                    "samples": row["samples_count"],
                    "backend_distribution": {
                        "trainium_pct": row["trainium_pct"],
                        "tpu_pct": row["tpu_pct"],
                        "gpu_pct": row["gpu_pct"],
                    }
                }
            return None

    def get_historical_comparison(self, model: str, current_itt: float = None, 
                                   current_tps: float = None, window_hours: int = 24) -> dict:
        """Compare current metrics against historical baseline for a model
        
        Returns dict with:
        - baseline: the historical baseline values
        - current: the current values provided
        - deviation: how far current is from baseline (in std deviations)
        - trend: recent trend direction (up/down/stable)
        """
        baseline = self.get_model_baseline(model)
        if not baseline:
            return {"error": "no_baseline", "model": model}
        
        result = {
            "model": model,
            "baseline": baseline,
            "current": {
                "itt_mean": current_itt,
                "tps": current_tps,
            },
            "deviation": {},
            "trend": "unknown",
        }
        
        # Calculate deviation from baseline
        if current_itt is not None and baseline["itt_std"] > 0:
            itt_dev = (current_itt - baseline["itt_mean"]) / baseline["itt_std"]
            result["deviation"]["itt"] = round(itt_dev, 2)
            result["deviation"]["itt_status"] = "normal" if abs(itt_dev) < 2 else "anomaly"
        
        if current_tps is not None and baseline["tps"] > 0:
            tps_pct_change = ((current_tps - baseline["tps"]) / baseline["tps"]) * 100
            result["deviation"]["tps_pct"] = round(tps_pct_change, 1)
            result["deviation"]["tps_status"] = "normal" if abs(tps_pct_change) < 20 else "anomaly"
        
        # Get recent trend from samples
        with get_db() as conn:
            rows = conn.execute("""
                SELECT itt_mean_ms, tokens_per_sec, timestamp
                FROM samples 
                WHERE model_requested = ? OR model_response = ?
                AND timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', ? || ' hours')
                ORDER BY timestamp DESC
                LIMIT 10
            """, (model, model, -window_hours)).fetchall()
            
            if len(rows) >= 3:
                recent_itt = [r["itt_mean_ms"] for r in rows[:3] if r["itt_mean_ms"]]
                older_itt = [r["itt_mean_ms"] for r in rows[3:] if r["itt_mean_ms"]]
                
                if recent_itt and older_itt:
                    recent_avg = sum(recent_itt) / len(recent_itt)
                    older_avg = sum(older_itt) / len(older_itt)
                    if recent_avg > older_avg * 1.1:
                        result["trend"] = "increasing"
                    elif recent_avg < older_avg * 0.9:
                        result["trend"] = "decreasing"
                    else:
                        result["trend"] = "stable"
        
        return result

    def get_model_summary(self, model: str) -> Optional[dict]:
        """Get summary for a specific model (legacy compatible)"""
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM model_profiles WHERE model = ?
            """, (model,)).fetchone()

            if not row:
                return None

            backend_info = KNOWN_BACKENDS.get(row["dominant_backend"], {})

            return {
                "model": model,
                "samples": row["samples_count"],
                "itt_mean": f"{row['itt_mean_avg']:.1f}ms (±{row['itt_mean_std']:.1f})",
                "tps": f"{row['tps_avg']:.1f} t/s (±{row['tps_std']:.1f})",
                "variance": f"{row['variance_coef_avg']:.2f}",
                "backend": backend_info.get("name", "Unknown"),
                "location": backend_info.get("location", "Unknown"),
                "confidence": f"{row['backend_confidence']:.0f}%",
                "last_seen": row["last_updated"],
            }

    # ========================================================================
    # BIMODAL DISTRIBUTION CLUSTERING (Section 10.1.2)
    # ========================================================================
    # Per plan: "Statistical clustering for bimodal distribution detection"
    # - Bimodal distribution = multiple backends
    # - Time-series clustering = routing changes  
    # - Model correlation = model-specific backends

    def analyze_latency_distribution(self, 
                                     model: str = None, 
                                     hours: int = 24,
                                     min_samples: int = 50) -> dict:
        """
        Comprehensive latency distribution analysis per plan Section 10.1.2.
        
        Returns:
            dict with:
            - is_bimodal: bool - True if distribution has 2+ modes
            - modes: List[dict] - Each mode with {center, std, count, pct, likely_backend}
            - routing_changes: List[dict] - Detected backend switches over time
            - model_correlation: dict - Per-model backend affinity
            - raw_stats: dict - Mean, std, p50, p90, p99 of latencies
            - samples_analyzed: int
            - evidence: str - Human-readable interpretation
        """
        import math
        
        with get_db() as conn:
            # Build query based on filters
            query = """
                SELECT timestamp, model_response, envoy_upstream_time_ms, 
                       classified_backend, cf_ray, cf_edge_location
                FROM samples 
                WHERE envoy_upstream_time_ms > 0
                  AND timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)
            """
            params = [f'-{hours} hours']
            
            if model:
                query += " AND (model_response = ? OR model_requested = ?)"
                params.extend([model, model])
            
            query += " ORDER BY timestamp ASC"
            
            rows = conn.execute(query, params).fetchall()
        
        if len(rows) < min_samples:
            return {
                "is_bimodal": False,
                "modes": [],
                "routing_changes": [],
                "model_correlation": {},
                "raw_stats": {},
                "samples_analyzed": len(rows),
                "evidence": f"Insufficient samples ({len(rows)} < {min_samples} required)"
            }
        
        # Extract latency values
        latencies = [r["envoy_upstream_time_ms"] for r in rows]
        timestamps = [r["timestamp"] for r in rows]
        backends = [r["classified_backend"] for r in rows]
        models = [r["model_response"] for r in rows]
        
        # 1. RAW STATISTICS
        raw_stats = self._calculate_distribution_stats(latencies)
        
        # 2. BIMODAL DETECTION using histogram analysis
        modes = self._detect_modes_histogram(latencies)
        is_bimodal = len(modes) >= 2
        
        # 3. TIME-SERIES CLUSTERING - detect routing changes
        routing_changes = self._detect_routing_changes(timestamps, latencies, backends)
        
        # 4. MODEL CORRELATION - which models go to which backends
        model_correlation = self._analyze_model_backend_correlation(rows)
        
        # 5. BUILD EVIDENCE STRING
        evidence = self._build_distribution_evidence(
            is_bimodal, modes, routing_changes, model_correlation, raw_stats
        )
        
        return {
            "is_bimodal": is_bimodal,
            "modes": modes,
            "routing_changes": routing_changes,
            "model_correlation": model_correlation,
            "raw_stats": raw_stats,
            "samples_analyzed": len(rows),
            "evidence": evidence
        }

    def _calculate_distribution_stats(self, values: List[float]) -> dict:
        """Calculate comprehensive distribution statistics."""
        if not values:
            return {}
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std = variance ** 0.5
        
        # Percentiles
        p50 = sorted_vals[int(n * 0.50)]
        p90 = sorted_vals[int(n * 0.90)]
        p99 = sorted_vals[min(int(n * 0.99), n - 1)]
        
        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p99": round(p99, 2),
            "count": n
        }

    def _detect_modes_histogram(self, values: List[float], num_bins: int = 20) -> List[dict]:
        """
        Detect modes in distribution using histogram peak detection.
        A mode is a local maximum in the histogram that contains >10% of samples.
        """
        if len(values) < 20:
            return []
        
        # Create histogram
        min_val = min(values)
        max_val = max(values)
        bin_width = (max_val - min_val) / num_bins if max_val > min_val else 1
        
        # Count values in each bin
        bins = [0] * num_bins
        bin_values = [[] for _ in range(num_bins)]
        
        for v in values:
            bin_idx = min(int((v - min_val) / bin_width), num_bins - 1)
            bins[bin_idx] += 1
            bin_values[bin_idx].append(v)
        
        # Find peaks (local maxima with >10% of total)
        threshold = len(values) * 0.10
        modes = []
        
        for i in range(num_bins):
            if bins[i] < threshold:
                continue
            
            # Check if local maximum (higher than neighbors)
            left = bins[i - 1] if i > 0 else 0
            right = bins[i + 1] if i < num_bins - 1 else 0
            
            if bins[i] >= left and bins[i] >= right:
                # This is a mode - calculate center and spread
                mode_values = bin_values[i]
                if mode_values:
                    center = sum(mode_values) / len(mode_values)
                    
                    # Estimate which backend this mode likely represents
                    likely_backend = self._estimate_backend_from_latency(center)
                    
                    modes.append({
                        "center_ms": round(center, 2),
                        "count": bins[i],
                        "pct": round(100 * bins[i] / len(values), 1),
                        "likely_backend": likely_backend,
                        "bin_range": (
                            round(min_val + i * bin_width, 2),
                            round(min_val + (i + 1) * bin_width, 2)
                        )
                    })
        
        # Sort by count descending
        modes.sort(key=lambda m: m["count"], reverse=True)
        return modes

    def _estimate_backend_from_latency(self, latency_ms: float) -> str:
        """Estimate backend type based on envoy latency profile."""
        # These ranges are based on observed patterns
        # Lower latency often indicates faster hardware (Trainium/TPU)
        if latency_ms < 20:
            return "tpu"  # Very fast - likely TPU
        elif latency_ms < 40:
            return "trainium"  # Fast - likely Trainium  
        elif latency_ms < 80:
            return "gpu"  # Medium - standard GPU
        else:
            return "gpu_slow"  # Slow - overloaded or older GPU

    def _detect_routing_changes(self, 
                                timestamps: List[str], 
                                latencies: List[float],
                                backends: List[str]) -> List[dict]:
        """
        Detect routing changes using time-series analysis.
        A routing change is when the latency pattern shifts significantly.
        """
        if len(timestamps) < 20:
            return []
        
        changes = []
        window_size = max(10, len(timestamps) // 10)  # 10% of data or min 10
        
        # Sliding window comparison
        for i in range(window_size, len(timestamps) - window_size):
            # Compare before and after windows
            before = latencies[i - window_size:i]
            after = latencies[i:i + window_size]
            
            before_mean = sum(before) / len(before)
            after_mean = sum(after) / len(after)
            
            # Significant change = >30% shift in mean latency
            if before_mean > 0:
                pct_change = abs(after_mean - before_mean) / before_mean * 100
                
                if pct_change > 30:
                    # Also check if backend classification changed
                    before_backends = backends[i - window_size:i]
                    after_backends = backends[i:i + window_size]
                    
                    def most_common(lst):
                        if not lst:
                            return "unknown"
                        return max(set(lst), key=lst.count)
                    
                    before_backend = most_common(before_backends)
                    after_backend = most_common(after_backends)
                    
                    changes.append({
                        "timestamp": timestamps[i],
                        "before_mean_ms": round(before_mean, 2),
                        "after_mean_ms": round(after_mean, 2),
                        "pct_change": round(pct_change, 1),
                        "direction": "faster" if after_mean < before_mean else "slower",
                        "before_backend": before_backend,
                        "after_backend": after_backend,
                        "backend_changed": before_backend != after_backend
                    })
        
        # Deduplicate changes that are close together (within 10 samples)
        if changes:
            deduplicated = [changes[0]]
            for c in changes[1:]:
                # Skip if too close to previous change
                prev_time = deduplicated[-1]["timestamp"]
                if timestamps.index(c["timestamp"]) - timestamps.index(prev_time) > 10:
                    deduplicated.append(c)
            return deduplicated
        
        return changes

    def _analyze_model_backend_correlation(self, rows: List) -> dict:
        """
        Analyze correlation between model and backend classification.
        Returns which backends each model tends to use.
        """
        model_backends = {}
        
        for row in rows:
            model = row["model_response"] or "unknown"
            backend = row["classified_backend"] or "unknown"
            
            if model not in model_backends:
                model_backends[model] = {"total": 0, "backends": {}}
            
            model_backends[model]["total"] += 1
            if backend not in model_backends[model]["backends"]:
                model_backends[model]["backends"][backend] = 0
            model_backends[model]["backends"][backend] += 1
        
        # Calculate percentages and find primary backend
        result = {}
        for model, data in model_backends.items():
            if data["total"] < 5:  # Skip models with too few samples
                continue
            
            backend_pcts = {}
            primary_backend = None
            primary_pct = 0
            
            for backend, count in data["backends"].items():
                pct = round(100 * count / data["total"], 1)
                backend_pcts[backend] = pct
                if pct > primary_pct:
                    primary_pct = pct
                    primary_backend = backend
            
            result[model] = {
                "samples": data["total"],
                "primary_backend": primary_backend,
                "primary_pct": primary_pct,
                "distribution": backend_pcts
            }
        
        return result

    def _build_distribution_evidence(self,
                                     is_bimodal: bool,
                                     modes: List[dict],
                                     routing_changes: List[dict],
                                     model_correlation: dict,
                                     raw_stats: dict) -> str:
        """Build human-readable evidence string."""
        lines = []
        
        # Distribution type
        if is_bimodal:
            lines.append(f"BIMODAL DISTRIBUTION DETECTED ({len(modes)} modes)")
            for i, mode in enumerate(modes, 1):
                lines.append(f"  Mode {i}: {mode['center_ms']:.0f}ms ({mode['pct']:.0f}% of samples) -> likely {mode['likely_backend']}")
            lines.append("  INTERPRETATION: Multiple backend types in use")
        else:
            lines.append("UNIMODAL DISTRIBUTION (single backend type)")
            lines.append(f"  Center: {raw_stats.get('p50', 0):.0f}ms (p50)")
        
        # Routing changes
        if routing_changes:
            lines.append(f"ROUTING CHANGES: {len(routing_changes)} detected")
            for change in routing_changes[:3]:  # Show first 3
                lines.append(f"  {change['timestamp'][:16]}: {change['before_mean_ms']:.0f}ms -> {change['after_mean_ms']:.0f}ms ({change['direction']})")
        
        # Model correlation
        if model_correlation:
            lines.append("MODEL-BACKEND CORRELATION:")
            for model, data in list(model_correlation.items())[:3]:
                model_short = model.split("-")[0] if model else "unknown"
                lines.append(f"  {model_short}: {data['primary_backend']} ({data['primary_pct']:.0f}%)")
        
        return "\n".join(lines)


    # ========================================================================
    # CACHE TIMING TEST MODE (Section 10.1.4)
    # ========================================================================
    # Per plan: "Send repeated prompts to detect cache hits"
    # - Send same prompt 3+ times
    # - Measure response time distribution
    # - Detect cache hits vs misses
    # - Infer caching architecture

    def analyze_cache_timing(self, hours: int = 24, min_samples: int = 10) -> dict:
        """
        Analyze cache timing patterns from collected samples.
        
        Detects cache hits by looking for:
        1. Low TTFT on repeated prompts (cache hit)
        2. High cache_read_tokens (prompt caching active)
        3. Bimodal TTFT distribution (hits vs misses)
        
        Returns:
            dict with:
            - cache_hit_rate: float - Estimated % of cache hits
            - cache_architecture: str - Inferred caching type
            - ttft_distribution: dict - Hit vs miss TTFT stats
            - repeated_prompt_analysis: dict - Analysis of repeated prompts
            - evidence: str - Human-readable interpretation
        """
        with get_db() as conn:
            rows = conn.execute("""
                SELECT timestamp, model_response, input_tokens, 
                       cache_read_tokens, cache_creation_tokens, cache_efficiency,
                       ttft_ms, envoy_upstream_time_ms, request_id
                FROM samples 
                WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)
                ORDER BY timestamp ASC
            """, [f'-{hours} hours']).fetchall()
        
        if len(rows) < min_samples:
            return {
                "cache_hit_rate": 0,
                "cache_architecture": "unknown",
                "ttft_distribution": {},
                "repeated_prompt_analysis": {},
                "samples_analyzed": len(rows),
                "evidence": f"Insufficient samples ({len(rows)} < {min_samples} required)"
            }
        
        # 1. Analyze cache efficiency from API response (filter valid 0-100 range)
        cache_efficiencies = [r["cache_efficiency"] for r in rows if r["cache_efficiency"] and 0 <= r["cache_efficiency"] <= 100]
        avg_cache_efficiency = sum(cache_efficiencies) / len(cache_efficiencies) if cache_efficiencies else 0
        
        # 2. Analyze TTFT distribution for bimodality (cache hits = low TTFT)
        ttft_values = [r["ttft_ms"] for r in rows if r["ttft_ms"] and r["ttft_ms"] > 0]
        ttft_analysis = self._analyze_ttft_cache_pattern(ttft_values)
        
        # 3. Correlate cache_read_tokens with TTFT
        cache_ttft_correlation = self._analyze_cache_ttft_correlation(rows)
        
        # 4. Detect repeated prompt patterns (same input_tokens within short window)
        repeated_analysis = self._detect_repeated_prompts(rows)
        
        # 5. Infer cache architecture
        cache_architecture = self._infer_cache_architecture(
            avg_cache_efficiency, ttft_analysis, cache_ttft_correlation
        )
        
        # 6. Calculate overall cache hit rate estimate
        cache_hit_rate = self._estimate_cache_hit_rate(
            avg_cache_efficiency, ttft_analysis, repeated_analysis
        )
        
        evidence = self._build_cache_evidence(
            cache_hit_rate, cache_architecture, ttft_analysis, 
            repeated_analysis, avg_cache_efficiency
        )
        
        return {
            "cache_hit_rate": round(cache_hit_rate, 1),
            "cache_architecture": cache_architecture,
            "ttft_distribution": ttft_analysis,
            "cache_ttft_correlation": cache_ttft_correlation,
            "repeated_prompt_analysis": repeated_analysis,
            "avg_cache_efficiency": round(avg_cache_efficiency, 1),
            "samples_analyzed": len(rows),
            "evidence": evidence
        }

    def _analyze_ttft_cache_pattern(self, ttft_values: List[float]) -> dict:
        """
        Analyze TTFT distribution to detect cache hit pattern.
        Cache hits typically have much lower TTFT than misses.
        """
        if not ttft_values:
            return {}
        
        sorted_ttft = sorted(ttft_values)
        n = len(sorted_ttft)
        
        mean = sum(ttft_values) / n
        p25 = sorted_ttft[int(n * 0.25)]
        p50 = sorted_ttft[int(n * 0.50)]
        p75 = sorted_ttft[int(n * 0.75)]
        
        # Detect bimodality by checking if p25 is significantly lower than p75
        # Cache hits cluster at low TTFT, misses at high TTFT
        bimodal_ratio = p75 / p25 if p25 > 0 else 1
        is_bimodal = bimodal_ratio > 2.0  # 2x difference suggests bimodal
        
        # Count samples in each region
        threshold = (p25 + p75) / 2
        low_ttft_count = sum(1 for t in ttft_values if t < threshold)
        high_ttft_count = n - low_ttft_count
        
        return {
            "mean_ms": round(mean, 1),
            "p25_ms": round(p25, 1),
            "p50_ms": round(p50, 1),
            "p75_ms": round(p75, 1),
            "min_ms": round(min(ttft_values), 1),
            "max_ms": round(max(ttft_values), 1),
            "is_bimodal": is_bimodal,
            "bimodal_ratio": round(bimodal_ratio, 2),
            "threshold_ms": round(threshold, 1),
            "low_ttft_count": low_ttft_count,
            "high_ttft_count": high_ttft_count,
            "low_ttft_pct": round(100 * low_ttft_count / n, 1)
        }

    def _analyze_cache_ttft_correlation(self, rows: List) -> dict:
        """
        Analyze correlation between cache_read_tokens and TTFT.
        High cache reads should correlate with lower TTFT.
        """
        with_cache = []
        without_cache = []
        
        for r in rows:
            ttft = r["ttft_ms"]
            cache_read = r["cache_read_tokens"] or 0
            
            if not ttft or ttft <= 0:
                continue
            
            if cache_read > 0:
                with_cache.append(ttft)
            else:
                without_cache.append(ttft)
        
        result = {
            "with_cache_count": len(with_cache),
            "without_cache_count": len(without_cache)
        }
        
        if with_cache:
            result["with_cache_ttft_mean"] = round(sum(with_cache) / len(with_cache), 1)
        if without_cache:
            result["without_cache_ttft_mean"] = round(sum(without_cache) / len(without_cache), 1)
        
        # Calculate speedup factor
        if with_cache and without_cache:
            with_mean = sum(with_cache) / len(with_cache)
            without_mean = sum(without_cache) / len(without_cache)
            if with_mean > 0:
                result["cache_speedup_factor"] = round(without_mean / with_mean, 2)
        
        return result

    def _detect_repeated_prompts(self, rows: List) -> dict:
        """
        Detect repeated prompts by looking for identical input_tokens 
        within a short time window.
        """
        # Group by input_tokens (proxy for prompt identity)
        token_groups = {}
        for r in rows:
            input_tokens = r["input_tokens"]
            if input_tokens not in token_groups:
                token_groups[input_tokens] = []
            token_groups[input_tokens].append({
                "timestamp": r["timestamp"],
                "ttft_ms": r["ttft_ms"],
                "cache_efficiency": r["cache_efficiency"]
            })
        
        # Find groups with 2+ samples (repeated prompts)
        repeated_groups = {k: v for k, v in token_groups.items() if len(v) >= 2}
        
        if not repeated_groups:
            return {
                "repeated_prompt_count": 0,
                "evidence": "No repeated prompts detected"
            }
        
        # Analyze TTFT pattern in repeated prompts
        first_ttft_values = []
        subsequent_ttft_values = []
        
        for group in repeated_groups.values():
            sorted_group = sorted(group, key=lambda x: x["timestamp"])
            if sorted_group[0]["ttft_ms"]:
                first_ttft_values.append(sorted_group[0]["ttft_ms"])
            for item in sorted_group[1:]:
                if item["ttft_ms"]:
                    subsequent_ttft_values.append(item["ttft_ms"])
        
        result = {
            "repeated_prompt_count": len(repeated_groups),
            "total_repeat_instances": sum(len(v) for v in repeated_groups.values())
        }
        
        if first_ttft_values:
            result["first_request_ttft_mean"] = round(sum(first_ttft_values) / len(first_ttft_values), 1)
        if subsequent_ttft_values:
            result["subsequent_request_ttft_mean"] = round(sum(subsequent_ttft_values) / len(subsequent_ttft_values), 1)
        
        # Calculate cache speedup on repeated prompts
        if first_ttft_values and subsequent_ttft_values:
            first_mean = sum(first_ttft_values) / len(first_ttft_values)
            subsequent_mean = sum(subsequent_ttft_values) / len(subsequent_ttft_values)
            if subsequent_mean > 0:
                result["repeat_speedup_factor"] = round(first_mean / subsequent_mean, 2)
        
        return result

    def _infer_cache_architecture(self, 
                                  avg_efficiency: float,
                                  ttft_analysis: dict,
                                  correlation: dict) -> str:
        """
        Infer the caching architecture based on observed patterns.
        """
        if avg_efficiency < 10:
            return "no_caching"
        
        is_bimodal = ttft_analysis.get("is_bimodal", False)
        speedup = correlation.get("cache_speedup_factor", 1)
        
        if avg_efficiency > 80:
            if speedup > 2:
                return "aggressive_prompt_cache"  # High efficiency + fast hits
            else:
                return "prompt_cache"  # High efficiency but minimal speedup
        elif avg_efficiency > 40:
            if is_bimodal:
                return "partial_cache"  # Some caching with hit/miss pattern
            else:
                return "context_cache"  # Moderate caching of context
        else:
            return "minimal_cache"  # Low caching activity

    def _estimate_cache_hit_rate(self,
                                 avg_efficiency: float,
                                 ttft_analysis: dict,
                                 repeated_analysis: dict) -> float:
        """
        Estimate overall cache hit rate combining multiple signals.
        """
        # Signal 1: API-reported cache efficiency
        api_signal = avg_efficiency
        
        # Signal 2: Low TTFT percentage (likely cache hits)
        ttft_signal = ttft_analysis.get("low_ttft_pct", 0)
        
        # Signal 3: Repeated prompt speedup (confirms cache working)
        repeat_speedup = repeated_analysis.get("repeat_speedup_factor", 1)
        repeat_signal = min(100, (repeat_speedup - 1) * 50) if repeat_speedup > 1 else 0
        
        # Weighted combination (API signal most reliable)
        hit_rate = (api_signal * 0.6 + ttft_signal * 0.3 + repeat_signal * 0.1)
        
        return hit_rate

    def _build_cache_evidence(self,
                              hit_rate: float,
                              architecture: str,
                              ttft_analysis: dict,
                              repeated_analysis: dict,
                              avg_efficiency: float) -> str:
        """Build human-readable cache analysis evidence."""
        lines = []
        
        lines.append(f"CACHE ARCHITECTURE: {architecture.upper().replace('_', ' ')}")
        lines.append(f"  Estimated hit rate: {hit_rate:.0f}%")
        lines.append(f"  API-reported efficiency: {avg_efficiency:.0f}%")
        
        if ttft_analysis:
            lines.append(f"TTFT DISTRIBUTION:")
            lines.append(f"  p25: {ttft_analysis.get('p25_ms', 0):.0f}ms | p50: {ttft_analysis.get('p50_ms', 0):.0f}ms | p75: {ttft_analysis.get('p75_ms', 0):.0f}ms")
            if ttft_analysis.get("is_bimodal"):
                lines.append(f"  BIMODAL pattern detected (ratio: {ttft_analysis.get('bimodal_ratio', 0):.1f}x)")
                lines.append(f"  Low TTFT: {ttft_analysis.get('low_ttft_count', 0)} ({ttft_analysis.get('low_ttft_pct', 0):.0f}%)")
        
        if repeated_analysis.get("repeated_prompt_count", 0) > 0:
            lines.append(f"REPEATED PROMPTS: {repeated_analysis['repeated_prompt_count']} unique prompts repeated")
            if repeated_analysis.get("repeat_speedup_factor"):
                lines.append(f"  Speedup on repeat: {repeated_analysis['repeat_speedup_factor']:.1f}x")
        
        return "\n".join(lines)

    def run_cache_test(self, test_prompt: str = None, repetitions: int = 3) -> dict:
        """
        Active cache test mode - sends repeated prompts to detect cache behavior.
        
        NOTE: This is a PASSIVE analysis method that analyzes existing data.
        For ACTIVE testing, the caller must send prompts externally and this
        method will analyze the resulting timing patterns.
        
        Args:
            test_prompt: Identifier for the test prompt (optional)
            repetitions: Number of times the prompt should have been sent
            
        Returns:
            dict with test results and cache detection
        """
        # This is the analysis side - the actual prompt sending must be done
        # externally (e.g., via Claude Code or test script)
        
        return {
            "mode": "passive_analysis",
            "note": "For active testing, send identical prompts externally then call analyze_cache_timing()",
            "analysis": self.analyze_cache_timing(hours=1, min_samples=3)
        }


    # ========================================================================
    # EXPERIMENTAL PHASE TRACKING (Section 11)
    # ========================================================================
    # Per plan: "3 phases with mode switching"
    # Phase 1: Baseline Collection (1 week, 1000 req/day)
    # Phase 2: Intensive Collection (24h, every 30sec)
    # Phase 3: Model Comparison (same prompts across models)

    # Phase definitions
    EXPERIMENT_PHASES = {
        "baseline": {
            "name": "Baseline Collection",
            "description": "1 week of standard data collection across all models",
            "duration_hours": 168,  # 1 week
            "target_samples_per_day": 1000,
            "collection_interval_sec": None,  # Passive collection
            "focus": "all_models"
        },
        "intensive": {
            "name": "Intensive Collection",
            "description": "24 hours of high-frequency collection during day/night transitions",
            "duration_hours": 24,
            "target_samples_per_day": None,  # Continuous
            "collection_interval_sec": 30,
            "focus": "transitions"
        },
        "comparison": {
            "name": "Model Comparison",
            "description": "Same prompts across Opus, Sonnet, Haiku for timing comparison",
            "duration_hours": 48,
            "target_samples_per_day": None,
            "collection_interval_sec": 60,
            "focus": "model_specific"
        }
    }

    def get_current_experiment_phase(self) -> dict:
        """
        Get current experiment phase and status.
        
        Returns:
            dict with:
            - phase: str - Current phase name
            - status: str - active/paused/completed
            - started_at: str - Phase start timestamp
            - samples_collected: int - Samples in this phase
            - target_samples: int - Target for this phase
            - progress_pct: float - Completion percentage
        """
        with get_db() as conn:
            # Check if experiment_phases table exists
            table_check = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='experiment_phases'
            """).fetchone()
            
            if not table_check:
                self._create_experiment_tables(conn)
            
            # Get active phase
            phase = conn.execute("""
                SELECT * FROM experiment_phases 
                WHERE status = 'active' 
                ORDER BY started_at DESC LIMIT 1
            """).fetchone()
            
            if not phase:
                return {
                    "phase": None,
                    "status": "no_active_experiment",
                    "message": "No experiment phase active. Use start_experiment_phase() to begin."
                }
            
            # Count samples in this phase
            sample_count = conn.execute("""
                SELECT COUNT(*) as count FROM samples 
                WHERE timestamp >= ? AND experiment_phase = ?
            """, (phase["started_at"], phase["phase_name"])).fetchone()["count"]
            
            phase_config = self.EXPERIMENT_PHASES.get(phase["phase_name"], {})
            duration_hours = phase_config.get("duration_hours", 24)
            target_per_day = phase_config.get("target_samples_per_day", 1000)
            
            # Calculate progress
            if target_per_day:
                days_elapsed = (datetime.utcnow() - datetime.fromisoformat(phase["started_at"])).total_seconds() / 86400
                target_samples = int(target_per_day * days_elapsed) if days_elapsed > 0 else target_per_day
                progress_pct = min(100, (sample_count / target_samples * 100)) if target_samples > 0 else 0
            else:
                target_samples = None
                progress_pct = None
            
            return {
                "phase": phase["phase_name"],
                "phase_display": phase_config.get("name", phase["phase_name"]),
                "status": phase["status"],
                "started_at": phase["started_at"],
                "samples_collected": sample_count,
                "target_samples": target_samples,
                "progress_pct": round(progress_pct, 1) if progress_pct else None,
                "config": phase_config
            }

    def start_experiment_phase(self, phase_name: str) -> dict:
        """
        Start a new experiment phase.
        
        Args:
            phase_name: One of 'baseline', 'intensive', 'comparison'
            
        Returns:
            dict with phase info and start confirmation
        """
        if phase_name not in self.EXPERIMENT_PHASES:
            return {
                "error": f"Unknown phase: {phase_name}",
                "valid_phases": list(self.EXPERIMENT_PHASES.keys())
            }
        
        phase_config = self.EXPERIMENT_PHASES[phase_name]
        
        with get_db() as conn:
            # Ensure tables exist
            self._create_experiment_tables(conn)
            
            # End any active phases
            conn.execute("""
                UPDATE experiment_phases SET status = 'completed', ended_at = ?
                WHERE status = 'active'
            """, (datetime.utcnow().isoformat(),))
            
            # Start new phase
            started_at = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO experiment_phases (phase_name, status, started_at, config_json)
                VALUES (?, 'active', ?, ?)
            """, (phase_name, started_at, json.dumps(phase_config)))
        
        return {
            "success": True,
            "phase": phase_name,
            "phase_display": phase_config["name"],
            "started_at": started_at,
            "description": phase_config["description"],
            "duration_hours": phase_config["duration_hours"],
            "message": f"Phase '{phase_config['name']}' started. Duration: {phase_config['duration_hours']} hours."
        }

    def end_experiment_phase(self) -> dict:
        """End the current active experiment phase."""
        with get_db() as conn:
            # Ensure tables exist
            self._create_experiment_tables(conn)
            
            # Get active phase
            phase = conn.execute("""
                SELECT * FROM experiment_phases WHERE status = 'active' LIMIT 1
            """).fetchone()
            
            if not phase:
                return {"error": "No active experiment phase to end"}
            
            # Count samples
            sample_count = conn.execute("""
                SELECT COUNT(*) as count FROM samples 
                WHERE timestamp >= ? AND experiment_phase = ?
            """, (phase["started_at"], phase["phase_name"])).fetchone()["count"]
            
            # End the phase
            ended_at = datetime.utcnow().isoformat()
            conn.execute("""
                UPDATE experiment_phases SET status = 'completed', ended_at = ?
                WHERE id = ?
            """, (ended_at, phase["id"]))
        
        return {
            "success": True,
            "phase": phase["phase_name"],
            "started_at": phase["started_at"],
            "ended_at": ended_at,
            "samples_collected": sample_count
        }

    def get_experiment_history(self, limit: int = 10) -> List[dict]:
        """Get history of experiment phases."""
        with get_db() as conn:
            self._create_experiment_tables(conn)
            
            rows = conn.execute("""
                SELECT * FROM experiment_phases 
                ORDER BY started_at DESC LIMIT ?
            """, (limit,)).fetchall()
            
            results = []
            for row in rows:
                # Count samples for each phase
                sample_count = conn.execute("""
                    SELECT COUNT(*) as count FROM samples 
                    WHERE timestamp >= ? 
                    AND (? IS NULL OR timestamp <= ?)
                    AND experiment_phase = ?
                """, (row["started_at"], row["ended_at"], row["ended_at"], row["phase_name"])).fetchone()["count"]
                
                results.append({
                    "phase": row["phase_name"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "samples_collected": sample_count,
                    "config": json.loads(row["config_json"]) if row["config_json"] else {}
                })
            
            return results

    def get_phase_analysis(self, phase_name: str = None) -> dict:
        """
        Analyze data from a specific experiment phase.
        
        Args:
            phase_name: Phase to analyze (default: current/most recent)
            
        Returns:
            dict with phase-specific analysis
        """
        with get_db() as conn:
            self._create_experiment_tables(conn)
            
            if phase_name:
                phase = conn.execute("""
                    SELECT * FROM experiment_phases WHERE phase_name = ?
                    ORDER BY started_at DESC LIMIT 1
                """, (phase_name,)).fetchone()
            else:
                phase = conn.execute("""
                    SELECT * FROM experiment_phases 
                    ORDER BY started_at DESC LIMIT 1
                """).fetchone()
            
            if not phase:
                return {"error": "No phase data found"}
            
            # Get samples for this phase
            query = """
                SELECT * FROM samples WHERE timestamp >= ?
            """
            params = [phase["started_at"]]
            
            if phase["ended_at"]:
                query += " AND timestamp <= ?"
                params.append(phase["ended_at"])
            
            query += " ORDER BY timestamp ASC"
            rows = conn.execute(query, params).fetchall()
        
        if not rows:
            return {
                "phase": phase["phase_name"],
                "error": "No samples collected in this phase"
            }
        
        # Phase-specific analysis
        phase_config = self.EXPERIMENT_PHASES.get(phase["phase_name"], {})
        
        if phase["phase_name"] == "baseline":
            analysis = self._analyze_baseline_phase(rows)
        elif phase["phase_name"] == "intensive":
            analysis = self._analyze_intensive_phase(rows)
        elif phase["phase_name"] == "comparison":
            analysis = self._analyze_comparison_phase(rows)
        else:
            analysis = self._analyze_generic_phase(rows)
        
        return {
            "phase": phase["phase_name"],
            "phase_display": phase_config.get("name", phase["phase_name"]),
            "started_at": phase["started_at"],
            "ended_at": phase["ended_at"],
            "status": phase["status"],
            "samples_analyzed": len(rows),
            "analysis": analysis
        }

    def _analyze_baseline_phase(self, rows: List) -> dict:
        """Analyze baseline phase data - establish normal patterns."""
        itt_values = [r["itt_mean_ms"] for r in rows if r["itt_mean_ms"]]
        tps_values = [r["tokens_per_sec"] for r in rows if r["tokens_per_sec"]]
        backends = [r["classified_backend"] for r in rows]
        
        backend_dist = {}
        for b in backends:
            backend_dist[b] = backend_dist.get(b, 0) + 1
        
        return {
            "type": "baseline",
            "itt_baseline": {
                "mean": round(sum(itt_values) / len(itt_values), 2) if itt_values else 0,
                "std": round(statistics.stdev(itt_values), 2) if len(itt_values) > 1 else 0,
                "samples": len(itt_values)
            },
            "tps_baseline": {
                "mean": round(sum(tps_values) / len(tps_values), 2) if tps_values else 0,
                "std": round(statistics.stdev(tps_values), 2) if len(tps_values) > 1 else 0,
                "samples": len(tps_values)
            },
            "backend_distribution": {k: round(v / len(backends) * 100, 1) for k, v in backend_dist.items()},
            "days_covered": self._calculate_days_covered(rows),
            "samples_per_day": round(len(rows) / max(1, self._calculate_days_covered(rows)), 0)
        }

    def _analyze_intensive_phase(self, rows: List) -> dict:
        """Analyze intensive phase data - detect day/night transitions."""
        # Group by hour of day
        hourly_data = {}
        for r in rows:
            try:
                hour = datetime.fromisoformat(r["timestamp"]).hour
                if hour not in hourly_data:
                    hourly_data[hour] = {"itt": [], "backend": []}
                if r["itt_mean_ms"]:
                    hourly_data[hour]["itt"].append(r["itt_mean_ms"])
                if r["classified_backend"]:
                    hourly_data[hour]["backend"].append(r["classified_backend"])
            except:
                continue
        
        # Find transition hours (significant ITT changes)
        hourly_itt_means = {}
        for hour, data in hourly_data.items():
            if data["itt"]:
                hourly_itt_means[hour] = sum(data["itt"]) / len(data["itt"])
        
        transitions = []
        sorted_hours = sorted(hourly_itt_means.keys())
        for i in range(1, len(sorted_hours)):
            prev_hour = sorted_hours[i - 1]
            curr_hour = sorted_hours[i]
            if hourly_itt_means[prev_hour] > 0:
                pct_change = abs(hourly_itt_means[curr_hour] - hourly_itt_means[prev_hour]) / hourly_itt_means[prev_hour] * 100
                if pct_change > 20:
                    transitions.append({
                        "from_hour": prev_hour,
                        "to_hour": curr_hour,
                        "itt_change_pct": round(pct_change, 1),
                        "direction": "faster" if hourly_itt_means[curr_hour] < hourly_itt_means[prev_hour] else "slower"
                    })
        
        return {
            "type": "intensive",
            "hours_covered": len(hourly_data),
            "samples_per_hour": {h: len(d["itt"]) for h, d in hourly_data.items()},
            "hourly_itt_means": {h: round(v, 1) for h, v in hourly_itt_means.items()},
            "detected_transitions": transitions,
            "peak_hours": [h for h, v in hourly_itt_means.items() if v < statistics.mean(hourly_itt_means.values()) * 0.8] if hourly_itt_means else [],
            "off_peak_hours": [h for h, v in hourly_itt_means.items() if v > statistics.mean(hourly_itt_means.values()) * 1.2] if hourly_itt_means else []
        }

    def _analyze_comparison_phase(self, rows: List) -> dict:
        """Analyze model comparison phase - compare timing across models."""
        model_data = {}
        for r in rows:
            model = r["model_response"] or r["model_requested"] or "unknown"
            if model not in model_data:
                model_data[model] = {"itt": [], "tps": [], "backend": []}
            if r["itt_mean_ms"]:
                model_data[model]["itt"].append(r["itt_mean_ms"])
            if r["tokens_per_sec"]:
                model_data[model]["tps"].append(r["tokens_per_sec"])
            if r["classified_backend"]:
                model_data[model]["backend"].append(r["classified_backend"])
        
        model_stats = {}
        for model, data in model_data.items():
            if len(data["itt"]) < 3:
                continue
            
            # Get primary backend
            backend_counts = {}
            for b in data["backend"]:
                backend_counts[b] = backend_counts.get(b, 0) + 1
            primary_backend = max(backend_counts, key=backend_counts.get) if backend_counts else "unknown"
            
            model_stats[model] = {
                "samples": len(data["itt"]),
                "itt_mean": round(sum(data["itt"]) / len(data["itt"]), 2),
                "itt_std": round(statistics.stdev(data["itt"]), 2) if len(data["itt"]) > 1 else 0,
                "tps_mean": round(sum(data["tps"]) / len(data["tps"]), 2) if data["tps"] else 0,
                "primary_backend": primary_backend,
                "backend_pct": round(backend_counts.get(primary_backend, 0) / len(data["backend"]) * 100, 1) if data["backend"] else 0
            }
        
        return {
            "type": "comparison",
            "models_compared": list(model_stats.keys()),
            "model_stats": model_stats,
            "fastest_model": min(model_stats.items(), key=lambda x: x[1]["itt_mean"])[0] if model_stats else None,
            "most_consistent": min(model_stats.items(), key=lambda x: x[1]["itt_std"])[0] if model_stats else None
        }

    def _analyze_generic_phase(self, rows: List) -> dict:
        """Generic analysis for unknown phase types."""
        return {
            "type": "generic",
            "sample_count": len(rows),
            "time_range": {
                "start": rows[0]["timestamp"] if rows else None,
                "end": rows[-1]["timestamp"] if rows else None
            }
        }

    def _calculate_days_covered(self, rows: List) -> float:
        """Calculate number of days covered by samples."""
        if len(rows) < 2:
            return 1
        try:
            start = datetime.fromisoformat(rows[0]["timestamp"])
            end = datetime.fromisoformat(rows[-1]["timestamp"])
            return max(1, (end - start).total_seconds() / 86400)
        except:
            return 1

    def _create_experiment_tables(self, conn):
        """Create experiment tracking tables if they don't exist.
        
        experiment_phases enables A/B testing of thinking budgets, model routing,
        and whisper injection strategies. Each phase tags samples with a phase name
        so before/after comparisons can be made.
        
        Usage:
            db.start_experiment_phase("high_budget_test")
            # ... run session with ultra thinking ...
            db.end_experiment_phase()
            phase_data = db.get_current_experiment_phase()
        
        The experiment_phase column in samples links each API call to the active phase.
        """
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                config_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add experiment_phase column to samples if not exists
        try:
            conn.execute("ALTER TABLE samples ADD COLUMN experiment_phase TEXT")
        except:
            pass  # Column already exists


    def get_all_models_summary(self) -> List[dict]:
        """Get summary for all tracked models"""



        with get_db() as conn:
            rows = conn.execute("""
                SELECT model FROM model_profiles ORDER BY last_updated DESC
            """).fetchall()

            return [self.get_model_summary(r["model"]) for r in rows if r]

    def get_recent_samples(self, limit: int = 100) -> List[dict]:
        """Get recent samples"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM samples ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()

            return [dict(r) for r in rows]

    def get_samples_by_session(self, session_id: str, limit: int = 100) -> List[dict]:
        """Get samples for a specific session"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM samples WHERE session_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (session_id, limit)).fetchall()

            return [dict(r) for r in rows]

    # === BEHAVIORAL FINGERPRINTING METHODS ===

    def record_behavioral_sample(self, data: dict) -> int:
        """Record a behavioral sample for the current turn."""
        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO behavioral_samples (
                    timestamp, session_id, turn_number,
                    read_calls, edit_calls, write_calls, bash_calls, test_calls, todo_calls,
                    verification_ratio, preparation_ratio,
                    completion_claims, verified_completions, unverified_completions,
                    agreement_phrases, hedge_phrases,
                    behavioral_signature, signature_confidence,
                    user_frustration_level, user_frustration_trend
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                data.get('session_id'),
                data.get('turn_number', 0),
                data.get('read_calls', 0),
                data.get('edit_calls', 0),
                data.get('write_calls', 0),
                data.get('bash_calls', 0),
                data.get('test_calls', 0),
                data.get('todo_calls', 0),
                data.get('verification_ratio', 0),
                data.get('preparation_ratio', 0),
                data.get('completion_claims', 0),
                data.get('verified_completions', 0),
                data.get('unverified_completions', 0),
                data.get('agreement_phrases', 0),
                data.get('hedge_phrases', 0),
                data.get('behavioral_signature', 'unknown'),
                data.get('signature_confidence', 0),
                data.get('user_frustration_level', 0),
                data.get('user_frustration_trend', 'stable')
            ))
            sample_id = cursor.lastrowid

            # Aggregate session stats
            session_id = data.get('session_id')
            if session_id:
                self._update_behavioral_session_stats(conn, session_id)

            return sample_id

    def _update_behavioral_session_stats(self, conn, session_id: str):
        """Aggregate behavioral_samples into behavioral_session_stats for a session.
        
        Called after every behavioral sample insert. Uses INSERT OR REPLACE
        to keep the stats row current.
        """
        row = conn.execute("""
            SELECT
                AVG(verification_ratio) as avg_ver,
                AVG(preparation_ratio) as avg_prep,
                SUM(completion_claims) as total_claims,
                SUM(unverified_completions) as total_unver,
                SUM(agreement_phrases) as total_agree,
                SUM(CASE WHEN behavioral_signature = 'VERIFIER' THEN 1 ELSE 0 END) as verifier_turns,
                SUM(CASE WHEN behavioral_signature = 'COMPLETER' THEN 1 ELSE 0 END) as completer_turns,
                SUM(CASE WHEN behavioral_signature = 'SYCOPHANT' THEN 1 ELSE 0 END) as sycophant_turns,
                SUM(CASE WHEN behavioral_signature = 'THEATER' THEN 1 ELSE 0 END) as theater_turns,
                COUNT(*) as sample_count
            FROM behavioral_samples
            WHERE session_id = ?
        """, (session_id,)).fetchone()

        if not row or row['sample_count'] == 0:
            return

        # Determine current signature from last 5 samples
        recent = conn.execute("""
            SELECT behavioral_signature, COUNT(*) as cnt
            FROM (
                SELECT behavioral_signature FROM behavioral_samples
                WHERE session_id = ? AND behavioral_signature != 'unknown'
                ORDER BY timestamp DESC LIMIT 5
            )
            GROUP BY behavioral_signature
            ORDER BY cnt DESC LIMIT 1
        """, (session_id,)).fetchone()

        current_sig = recent['behavioral_signature'] if recent else 'unknown'

        # Determine trend: compare last 5 vs previous 5
        prev = conn.execute("""
            SELECT behavioral_signature, COUNT(*) as cnt
            FROM (
                SELECT behavioral_signature FROM behavioral_samples
                WHERE session_id = ? AND behavioral_signature != 'unknown'
                ORDER BY timestamp DESC LIMIT 5 OFFSET 5
            )
            GROUP BY behavioral_signature
            ORDER BY cnt DESC LIMIT 1
        """, (session_id,)).fetchone()

        if prev and prev['behavioral_signature'] != current_sig:
            trend = f"{prev['behavioral_signature']}->{current_sig}"
        else:
            trend = 'stable'

        conn.execute("""
            INSERT OR REPLACE INTO behavioral_session_stats (
                session_id, avg_verification_ratio, avg_preparation_ratio,
                total_completion_claims, total_unverified_completions,
                total_sycophancy_signals,
                verifier_turns, completer_turns, sycophant_turns, theater_turns,
                current_signature, signature_trend, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            row['avg_ver'] or 0,
            row['avg_prep'] or 0,
            row['total_claims'] or 0,
            row['total_unver'] or 0,
            row['total_agree'] or 0,
            row['verifier_turns'] or 0,
            row['completer_turns'] or 0,
            row['sycophant_turns'] or 0,
            row['theater_turns'] or 0,
            current_sig,
            trend,
            datetime.now().isoformat()
        ))

    def get_behavioral_signature(self, session_id: str = None, window: int = 10) -> dict:
        """Get current behavioral signature based on rolling window.
        SESSION-ISOLATED: Only considers samples from specified session.
        """
        with get_db() as conn:
            # Build query with optional session filter
            if session_id:
                rows = conn.execute("""
                    SELECT
                        AVG(verification_ratio) as avg_verification,
                        AVG(preparation_ratio) as avg_preparation,
                        SUM(completion_claims) as total_claims,
                        SUM(unverified_completions) as total_unverified,
                        SUM(agreement_phrases) as total_agreement,
                        SUM(hedge_phrases) as total_hedge,
                        COUNT(*) as sample_count
                    FROM behavioral_samples
                    WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 hour')
                      AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, window)).fetchone()
            else:
                rows = conn.execute("""
                    SELECT
                        AVG(verification_ratio) as avg_verification,
                        AVG(preparation_ratio) as avg_preparation,
                        SUM(completion_claims) as total_claims,
                        SUM(unverified_completions) as total_unverified,
                        SUM(agreement_phrases) as total_agreement,
                        SUM(hedge_phrases) as total_hedge,
                        COUNT(*) as sample_count
                    FROM behavioral_samples
                    WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 hour')
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (window,)).fetchone()

            if not rows or rows['sample_count'] == 0:
                return {'signature': 'unknown', 'confidence': 0}

            avg_ver = rows['avg_verification'] or 0
            total_unver = rows['total_unverified'] or 0
            total_agree = rows['total_agreement'] or 0
            total_hedge = rows['total_hedge'] or 0
            avg_prep = rows['avg_preparation'] or 0

            # Signature detection algorithm
            if avg_ver > 0.7 and total_unver < 2:
                signature = 'VERIFIER'
                confidence = min(95, avg_ver * 100)
            elif avg_prep > 0.8 and avg_ver < 0.3:
                signature = 'THEATER'
                confidence = min(90, avg_prep * 100)
            elif total_agree > 3 and total_hedge < 2:
                signature = 'SYCOPHANT'
                confidence = min(85, (total_agree / max(1, total_agree + total_hedge)) * 100)
            elif avg_ver < 0.3 or total_unver > 3:
                signature = 'COMPLETER'
                confidence = min(90, (1 - avg_ver) * 100)
            else:
                signature = 'MIXED'
                confidence = 50

            return {
                'signature': signature,
                'confidence': confidence,
                'verification_ratio': avg_ver,
                'preparation_ratio': avg_prep,
                'unverified_claims': total_unver,
                'sycophancy_signals': total_agree,
                'sample_count': rows['sample_count']
            }

    def record_phrase_metrics(self, data: dict) -> int:
        """Record phrase metrics from slave_whisper text analysis.
        
        This allows text-based signals (agreement phrases, completion claims, etc.)
        to be stored alongside tool-based signals for unified analysis.
        """
        with get_db() as conn:
            # Update the most recent sample for this session, or insert new
            session_id = data.get('session_id', '')
            
            # Check if there's a recent sample (within last minute) to update
            existing = conn.execute("""
                SELECT id FROM behavioral_samples
                WHERE session_id = ?
                  AND timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 minute')
                ORDER BY timestamp DESC LIMIT 1
            """, (session_id,)).fetchone()
            
            if existing:
                # Update existing sample with phrase metrics
                conn.execute("""
                    UPDATE behavioral_samples
                    SET agreement_phrases = ?,
                        completion_claims = COALESCE(completion_claims, 0) + ?,
                        hedge_phrases = ?
                    WHERE id = ?
                """, (
                    data.get('agreement_phrases', 0),
                    data.get('completion_claims', 0),
                    data.get('hedge_phrases', 0),
                    existing['id']
                ))
                return existing['id']
            else:
                # Insert new sample with phrase metrics only
                from datetime import datetime
                cursor = conn.execute("""
                    INSERT INTO behavioral_samples (
                        timestamp, session_id, agreement_phrases,
                        completion_claims, hedge_phrases
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    session_id,
                    data.get('agreement_phrases', 0),
                    data.get('completion_claims', 0),
                    data.get('hedge_phrases', 0)
                ))
                return cursor.lastrowid

    def get_phrase_metrics(self, session_id: str = None, window: int = 10) -> dict:
        """Get phrase-based metrics for a session.
        
        Returns aggregated text-based signals from slave_whisper analysis.
        """
        with get_db() as conn:
            if session_id:
                row = conn.execute("""
                    SELECT
                        SUM(agreement_phrases) as total_agreement,
                        SUM(completion_claims) as total_completions,
                        SUM(hedge_phrases) as total_hedge,
                        COUNT(*) as sample_count
                    FROM behavioral_samples
                    WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 hour')
                      AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, window)).fetchone()
            else:
                row = conn.execute("""
                    SELECT
                        SUM(agreement_phrases) as total_agreement,
                        SUM(completion_claims) as total_completions,
                        SUM(hedge_phrases) as total_hedge,
                        COUNT(*) as sample_count
                    FROM behavioral_samples
                    WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 hour')
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (window,)).fetchone()
            
            return {
                'agreement_phrases': row['total_agreement'] or 0,
                'completion_claims': row['total_completions'] or 0,
                'hedge_phrases': row['total_hedge'] or 0,
                'sample_count': row['sample_count'] or 0
            }

    def get_combined_signature(self, session_id: str = None) -> dict:
        """Get unified signature from BOTH tool and text signals.
        
        Combines:
        - Tool-based signals (read/edit ratio, verification patterns)
        - Text-based signals (agreement phrases, completion claims, hedging)
        
        Returns signature with higher confidence when both signal types agree.
        """
        # Get tool-based signature
        tool_sig = self.get_behavioral_signature(session_id)
        
        # Get text-based metrics
        phrase_metrics = self.get_phrase_metrics(session_id)
        
        # Combined scoring
        combined_signals = {
            'completer': 0,
            'sycophant': 0,
            'theater': 0,
            'verifier': 0,
        }
        
        # Tool signals
        ver_ratio = tool_sig.get('verification_ratio', 0.5)
        if ver_ratio < 0.3:
            combined_signals['completer'] += 2
        if ver_ratio > 0.7:
            combined_signals['verifier'] += 2
        if tool_sig.get('unverified_claims', 0) > 2:
            combined_signals['completer'] += 1
            
        # Phrase signals
        agreement = phrase_metrics.get('agreement_phrases', 0)
        completions = phrase_metrics.get('completion_claims', 0)
        hedging = phrase_metrics.get('hedge_phrases', 0)
        
        if agreement > 3:
            combined_signals['sycophant'] += 2
        if completions > 2:
            combined_signals['completer'] += 1
        if hedging > 2:
            combined_signals['verifier'] += 1  # Uncertainty is good
            
        # Check for agreement between tool and text signals
        tool_signature = tool_sig.get('signature', 'UNKNOWN')
        
        # Boost confidence if tool and text agree
        if tool_signature == 'COMPLETER' and combined_signals['completer'] > 2:
            combined_signals['completer'] += 2  # Strong agreement
        if tool_signature == 'SYCOPHANT' and combined_signals['sycophant'] > 2:
            combined_signals['sycophant'] += 2
        if tool_signature == 'VERIFIER' and combined_signals['verifier'] > 2:
            combined_signals['verifier'] += 2
            
        # Determine final signature
        total = sum(combined_signals.values())
        if total == 0:
            return {
                'signature': 'UNKNOWN',
                'confidence': 0,
                'tool_signals': tool_sig,
                'phrase_signals': phrase_metrics,
                'combined_scores': combined_signals
            }
            
        max_signal = max(combined_signals, key=combined_signals.get)
        confidence = (combined_signals[max_signal] / total) * 100 if total > 0 else 0
        
        return {
            'signature': max_signal.upper(),
            'confidence': min(95, confidence),
            'tool_signals': tool_sig,
            'phrase_signals': phrase_metrics,
            'combined_scores': combined_signals
        }

    def calculate_quality_score(self, model: str = None, session_id: str = None) -> dict:
        """Calculate composite quality score for degradation/quantization detection.
        
        Compares current metrics against baseline to detect:
        - Faster ITT + higher variance = possible quantization
        - Slower ITT = possible throttling/overload
        - Behavioral degradation = sloppy responses
        
        Returns dict with:
        - score: 0-100 (100 = premium quality)
        - mode: 'premium' / 'standard' / 'degraded'
        - timing_ratio: current ITT / baseline ITT (<1 = faster, suspicious)
        - variance_ratio: current variance / baseline variance (>1 = more variable)
        - behavioral_factor: from behavioral fingerprinting
        - explanation: human-readable interpretation
        """
        with get_db() as conn:
            # Get recent samples (last 30 min)
            recent = conn.execute("""
                SELECT 
                    AVG(itt_mean_ms) as itt_current,
                    AVG(itt_std_ms) as std_current,
                    AVG(variance_coef) as var_current,
                    AVG(tokens_per_sec) as tps_current,
                    COUNT(*) as sample_count
                FROM samples
                WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-30 minutes')
                AND itt_mean_ms > 0
            """).fetchone()
            
            # Get baseline (last 24 hours, excluding last 30 min)
            baseline = conn.execute("""
                SELECT 
                    AVG(itt_mean_ms) as itt_baseline,
                    AVG(itt_std_ms) as std_baseline,
                    AVG(variance_coef) as var_baseline,
                    AVG(tokens_per_sec) as tps_baseline,
                    COUNT(*) as baseline_count
                FROM samples
                WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-24 hours')
                AND timestamp < strftime('%Y-%m-%dT%H:%M:%S', 'now', '-30 minutes')
                AND itt_mean_ms > 0
            """).fetchone()
            
            result = {
                'score': 50,  # Default neutral
                'mode': 'standard',
                'timing_ratio': 1.0,
                'variance_ratio': 1.0,
                'tps_ratio': 1.0,
                'behavioral_factor': 1.0,
                'explanation': [],
                'sample_count': recent['sample_count'] if recent else 0,
                'baseline_count': baseline['baseline_count'] if baseline else 0,
            }
            
            # Need minimum samples for meaningful comparison
            if not recent or recent['sample_count'] < 3:
                result['explanation'].append('Insufficient recent samples')
                return result
            if not baseline or baseline['baseline_count'] < 10:
                result['explanation'].append('Insufficient baseline samples')
                return result
            
            itt_current = recent['itt_current'] or 0
            itt_baseline = baseline['itt_baseline'] or 0
            var_current = recent['var_current'] or 0
            var_baseline = baseline['var_baseline'] or 0
            tps_current = recent['tps_current'] or 0
            tps_baseline = baseline['tps_baseline'] or 0
            
            # Calculate ratios
            timing_ratio = itt_current / itt_baseline if itt_baseline > 0 else 1.0
            variance_ratio = var_current / var_baseline if var_baseline > 0 else 1.0
            tps_ratio = tps_current / tps_baseline if tps_baseline > 0 else 1.0
            
            result['timing_ratio'] = round(timing_ratio, 2)
            result['variance_ratio'] = round(variance_ratio, 2)
            result['tps_ratio'] = round(tps_ratio, 2)
            
            # Start with base score of 70
            score = 70
            
            # TIMING ANALYSIS
            # Faster than baseline is SUSPICIOUS (possible quantization)
            if timing_ratio < 0.8:
                score -= 15
                result['explanation'].append(f'ITT {timing_ratio:.0%} of baseline (faster = suspicious)')
            elif timing_ratio < 0.9:
                score -= 5
                result['explanation'].append(f'ITT slightly faster than baseline')
            elif timing_ratio > 1.3:
                score -= 10
                result['explanation'].append(f'ITT {timing_ratio:.0%} of baseline (slower = throttled?)')
            elif timing_ratio > 1.1:
                score -= 3
                result['explanation'].append(f'ITT slightly slower than baseline')
            else:
                score += 10
                result['explanation'].append(f'ITT within normal range')
            
            # VARIANCE ANALYSIS
            # Higher variance is suspicious (quantization causes more variability)
            if variance_ratio > 1.5:
                score -= 15
                result['explanation'].append(f'Variance {variance_ratio:.1f}x baseline (unstable)')
            elif variance_ratio > 1.2:
                score -= 5
                result['explanation'].append(f'Variance elevated')
            elif variance_ratio < 0.8:
                score += 5
                result['explanation'].append(f'Variance lower than baseline (stable)')
            else:
                score += 5
                result['explanation'].append(f'Variance normal')
            
            # TPS ANALYSIS
            # Much higher TPS + faster ITT = quantization signal
            if tps_ratio > 1.3 and timing_ratio < 0.9:
                score -= 10
                result['explanation'].append(f'High TPS + fast ITT = quantization likely')
            elif tps_ratio > 1.2:
                # Fast is good unless combined with variance
                if variance_ratio > 1.2:
                    score -= 5
                    result['explanation'].append(f'High TPS but unstable')
                else:
                    score += 5
                    result['explanation'].append(f'Good throughput')
            
            # BEHAVIORAL FACTOR
            behavior = self.get_combined_signature(session_id)
            sig = behavior.get('signature', 'UNKNOWN')
            if sig == 'VERIFIER':
                result['behavioral_factor'] = 1.1
                score += 10
                result['explanation'].append('Behavioral: VERIFIER (good)')
            elif sig == 'COMPLETER':
                result['behavioral_factor'] = 0.8
                score -= 15
                result['explanation'].append('Behavioral: COMPLETER (quality concern)')
            elif sig == 'SYCOPHANT':
                result['behavioral_factor'] = 0.85
                score -= 10
                result['explanation'].append('Behavioral: SYCOPHANT (quality concern)')
            
            # Clamp score
            score = max(0, min(100, score))
            result['score'] = round(score)
            
            # Classify mode
            if score >= 80:
                result['mode'] = 'premium'
            elif score >= 50:
                result['mode'] = 'standard'
            else:
                result['mode'] = 'degraded'
            
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
                quant_evidence.append(f'ITT {timing_ratio:.0%} (very fast)')
                quant_evidence.append(f'Variance {variance_ratio:.1f}x (high)')
                if tps_ratio > 1.4:
                    quant_confidence += 10
                    quant_evidence.append(f'TPS {tps_ratio:.1f}x (high)')
            
            # INT4: Fast (0.5-0.7x), elevated variance (1.3-1.8x)
            elif timing_ratio < 0.7 and variance_ratio > 1.3:
                quant_detected = True
                quant_type = 'INT4'
                quant_confidence = min(90, 40 + (0.7 - timing_ratio) * 100 + (variance_ratio - 1.0) * 20)
                quant_evidence.append(f'ITT {timing_ratio:.0%} (fast)')
                quant_evidence.append(f'Variance {variance_ratio:.1f}x (elevated)')
                if tps_ratio > 1.3:
                    quant_confidence += 10
                    quant_evidence.append(f'TPS {tps_ratio:.1f}x boost')
            
            # INT8: Moderately fast (0.7-0.85x), some variance increase (1.1-1.3x)
            elif timing_ratio < 0.85 and variance_ratio > 1.1:
                quant_detected = True
                quant_type = 'INT8'
                quant_confidence = min(80, 30 + (0.85 - timing_ratio) * 100 + (variance_ratio - 1.0) * 30)
                quant_evidence.append(f'ITT {timing_ratio:.0%} (moderately fast)')
                quant_evidence.append(f'Variance {variance_ratio:.1f}x (slightly elevated)')
                if tps_ratio > 1.15:
                    quant_confidence += 10
                    quant_evidence.append(f'TPS {tps_ratio:.1f}x boost')
            
            # Possible INT8: Fast but variance normal (could be better hardware)
            elif timing_ratio < 0.85 and variance_ratio <= 1.1:
                quant_type = 'INT8?'  # Uncertain
                quant_confidence = min(50, 20 + (0.85 - timing_ratio) * 60)
                quant_evidence.append(f'ITT {timing_ratio:.0%} (fast, but variance normal)')
                quant_evidence.append('Could be INT8 or better hardware')
            
            # FP16 (no quantization): Normal timing and variance
            else:
                quant_type = 'FP16'
                quant_confidence = min(80, 50 + (1.0 - abs(timing_ratio - 1.0)) * 30)
                if 0.95 <= timing_ratio <= 1.05 and 0.9 <= variance_ratio <= 1.1:
                    quant_confidence = 90
                    quant_evidence.append('Timing and variance match baseline')
            
            result['quant_detected'] = quant_detected
            result['quant_type'] = quant_type
            result['quant_confidence'] = round(quant_confidence)
            result['quant_evidence'] = quant_evidence
            
            return result
    
    def get_quality_status(self, session_id: str = None) -> dict:
        """Get quality status for statusline display.
        
        Returns dict formatted for easy statusline consumption:
        - score, mode, timing_ratio, variance_ratio
        - trend: comparing last 30min to previous 30min
        - emoji and color hints
        """
        quality = self.calculate_quality_score(session_id=session_id)
        
        # Calculate trend (compare current 30min to previous 30min)
        with get_db() as conn:
            prev_period = conn.execute("""
                SELECT AVG(itt_mean_ms) as itt_prev
                FROM samples
                WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-60 minutes')
                AND timestamp < strftime('%Y-%m-%dT%H:%M:%S', 'now', '-30 minutes')
                AND itt_mean_ms > 0
            """).fetchone()
            
            current_period = conn.execute("""
                SELECT AVG(itt_mean_ms) as itt_current
                FROM samples
                WHERE timestamp > strftime('%Y-%m-%dT%H:%M:%S', 'now', '-30 minutes')
                AND itt_mean_ms > 0
            """).fetchone()
        
        trend = 'stable'
        if prev_period and current_period:
            itt_prev = prev_period['itt_prev'] or 0
            itt_current = current_period['itt_current'] or 0
            if itt_prev > 0 and itt_current > 0:
                change = (itt_current - itt_prev) / itt_prev
                if change > 0.1:
                    trend = 'degrading'  # Getting slower
                elif change < -0.1:
                    trend = 'improving'  # Getting faster (but check variance)
                    # If faster but more variable, actually degrading
                    if quality['variance_ratio'] > 1.2:
                        trend = 'degrading'
        
        quality['trend'] = trend
        
        # Add display hints
        mode_display = {
            'premium': {'emoji': '🟢', 'color': 'green', 'label': 'PREMIUM'},
            'standard': {'emoji': '🟡', 'color': 'yellow', 'label': 'STANDARD'},
            'degraded': {'emoji': '🔴', 'color': 'red', 'label': 'DEGRADED'},
        }
        display = mode_display.get(quality['mode'], mode_display['standard'])
        quality.update(display)
        
        trend_display = {
            'improving': {'trend_emoji': '↗', 'trend_label': 'improving'},
            'stable': {'trend_emoji': '→', 'trend_label': 'stable'},
            'degrading': {'trend_emoji': '↘', 'trend_label': 'degrading'},
        }
        quality.update(trend_display.get(trend, trend_display['stable']))
        
        return quality


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fingerprint Database v3")
    parser.add_argument("--show", action="store_true", help="Show current status")
    parser.add_argument("--models", action="store_true", help="Show all model profiles")
    parser.add_argument("--samples", type=int, help="Show last N samples")
    parser.add_argument("--session", type=str, help="Show session stats")
    parser.add_argument("--db-path", action="store_true", help="Show database path")
    parser.add_argument("--reset-session-stats", action="store_true", help="Clear session_stats table only (keeps samples for history)")

    args = parser.parse_args()

    db = FingerprintDatabase()

    if args.db_path:
        print(f"Database: {DB_PATH}")
        print(f"Exists: {DB_PATH.exists()}")
        if DB_PATH.exists():
            print(f"Size: {DB_PATH.stat().st_size} bytes")

    elif args.session:
        stats = db.get_session_stats(args.session)
        if stats:
            print(f"Session: {stats['session_id']}")
            print(f"  Samples: {stats['sample_count']}")
            print(f"  Direct: {stats['direct_count']} | Subagent: {stats['subagent_count']}")
            print(f"  ITT trend: {stats['itt_trend_direction']} ({stats['itt_trend_pct']:.1f}%)")
            print(f"  Cache avg: {stats['cache_efficiency_avg']:.1f}%")
        else:
            print("No session data.")

    elif args.samples:
        samples = db.get_recent_samples(args.samples)
        print(f"Last {len(samples)} samples:")
        for s in samples:
            model_state = "✓" if s.get("model_match", 1) == 1 else "⚡" if s.get("is_subagent", 0) else "⚠"
            thinking = f" 🔴{s.get('thinking_budget_tier', '')}" if s.get("thinking_enabled") else ""
            print(f"  {s['timestamp'][:19]} | {model_state} {s.get('model_response', s.get('model', ''))[:20]:20}{thinking} | "
                  f"ITT:{s.get('itt_mean_ms', 0):5.1f}ms | {s.get('classified_backend', 'unknown'):10} ({s.get('confidence', 0):.0f}%)")

    elif args.models:
        print("=" * 80)
        print("MODEL FINGERPRINT PROFILES v3")
        print("=" * 80)

        for summary in db.get_all_models_summary():
            if summary:
                print(f"\n{summary['model']}")
                print(f"  Samples: {summary['samples']}")
                print(f"  ITT: {summary['itt_mean']}")
                print(f"  Speed: {summary['tps']}")
                print(f"  Backend: {summary['backend']} ({summary['confidence']})")

    elif args.show:
        latest = db.get_latest_classification()
        if latest:
            print("=" * 70)
            print("LATEST FINGERPRINT v3")
            print("=" * 70)
            print(f"{latest['model_state_icon']} {latest['model_state']}: {latest['model_response'] or latest['model_requested']}")
            if latest['is_subagent']:
                print(f"   Picker: {latest['model_requested']} -> Actual: {latest['model_response']}")
            print(f"Backend: {latest['backend_name']} ({latest['confidence']:.0f}%)")
            print(f"Location: {latest['location']}")
            print(f"ITT: {latest['itt_mean_ms']:.1f}ms (±{latest['itt_std_ms']:.1f}ms)")
            print(f"Speed: {latest['tokens_per_sec']:.1f} tokens/sec | TTFT: {latest['ttft_ms']:.0f}ms")
            if latest['thinking_enabled']:
                print(f"Thinking: {latest['thinking_tier_emoji']} {latest['thinking_budget_tier'].upper()} "
                      f"Budget: {latest['thinking_budget_requested']} | Used: {latest['thinking_utilization']:.0f}%")
                print(f"  Thinking ITT: {latest['thinking_itt_mean_ms']:.1f}ms | Text ITT: {latest['text_itt_mean_ms']:.1f}ms")
            print(f"Tokens: in={latest['input_tokens']}, out={latest['output_tokens']}, cache={latest['cache_read_tokens']} ({latest['cache_efficiency']:.0f}%)")
        else:
            print("No fingerprint data yet.")

    elif args.reset_session_stats:
        # Only clear session_stats table - samples preserved for historical analysis
        with get_db() as conn:
            conn.execute("DELETE FROM session_stats")
            print("✓ Cleared session_stats table")
            print("  Samples preserved for historical analysis")
            print("  Restart mitmproxy to start fresh session tracking")

    else:
        parser.print_help()
