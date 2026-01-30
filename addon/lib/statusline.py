#!/usr/bin/env python3
"""
Claude Code Statusline v3 - Comprehensive Fingerprint Display

Three display modes matching v3 FINAL plan Part 7:
- EXPANDED: Multi-line with box drawing (for wide terminals)
- FULL: Single line, labeled components (default)
- COMPACT: Abbreviated for narrow terminals

Plan formats:
COMPACT: ✓Op4.5 Trn72↗ │ 47±12 Thk52/Txt41 │ 🔴31k89% │ C93/87 │ 24%⚠
FULL: ✓DIRECT Opus4.5-Nov │ Trn 72%↗ │ ITT 47±12ms (Thk52/Txt41) │ 🔴31k@89% │ Cache 93%/87%avg │ 45k→1.8k │ Ctx 24%API/21%CC⚠
EXPANDED: Multi-line box with ┌ ├ └ characters
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

# Import fingerprint database
sys.path.insert(0, os.path.dirname(__file__))
try:
    from fingerprint_db import FingerprintDatabase, KNOWN_BACKENDS, THINKING_TIERS
except ImportError:
    FingerprintDatabase = None
    KNOWN_BACKENDS = {}
    THINKING_TIERS = {}

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BACKEND_COLORS = {
    "trainium": YELLOW,
    "tpu": BLUE,
    "gpu": MAGENTA,
    "unknown": WHITE,
}


def get_fingerprint_status(model_filter: str = None) -> Optional[dict]:
    """Get fingerprint status from database."""
    if FingerprintDatabase is None:
        return None

    try:
        db = FingerprintDatabase()
        return db.get_latest_classification(model_filter=model_filter, max_age_minutes=30)
    except Exception as e:
        import sys
        print(f"[statusline] get_latest_classification failed: {e}", file=sys.stderr)
        return None


def get_extras(model_filter: str = None) -> dict:
    """Get extras (trends/averages) from database."""
    if FingerprintDatabase is None:
        return {"cache_model_avg": 0, "cache_session_avg": 0, "backend_trend": "→", "itt_trend": "→", "context_api_pct": 0}

    try:
        db = FingerprintDatabase()
        return db.get_extras(model_filter=model_filter)
    except Exception as e:
        import sys
        print(f"[statusline] get_extras failed: {e}", file=sys.stderr)
        return {"cache_model_avg": 0, "cache_session_avg": 0, "backend_trend": "→", "itt_trend": "→", "context_api_pct": 0}


def get_subagent_counts() -> dict:
    """Get subagent call counts from database."""
    if FingerprintDatabase is None:
        return {"haiku_count": 0, "sonnet_count": 0, "subagent_count": 0, "total_count": 0}

    try:
        db = FingerprintDatabase()
        return db.get_subagent_counts(max_age_minutes=60)
    except Exception as e:
        import sys
        print(f"[statusline] get_subagent_counts failed: {e}", file=sys.stderr)
        return {"haiku_count": 0, "sonnet_count": 0, "subagent_count": 0, "total_count": 0}


def get_anomalies() -> list:
    """Get detected anomalies from database."""
    if FingerprintDatabase is None:
        return []
    try:
        db = FingerprintDatabase()
        return db.get_anomalies(max_age_minutes=30)
    except Exception as e:
        import sys
        print(f"[statusline] get_anomalies failed: {e}", file=sys.stderr)
        return []


def get_behavioral_status() -> dict:
    """Get current behavioral signature from database.
    AUTO-DETECTS session from most recent state file.
    """
    if FingerprintDatabase is None:
        return {}
    try:
        import glob as glob_mod
        
        # Find most recent session state file
        session_id = None
        state_files = glob_mod.glob(os.path.expanduser('~/.claude/behavioral_state_*.json'))
        if state_files:
            # Get most recently modified
            newest = max(state_files, key=os.path.getmtime)
            try:
                with open(newest, 'r') as f:
                    state = json.load(f)
                    session_id = state.get('session_id')
            except:
                pass
        
        db = FingerprintDatabase()
        # Use combined signature (tool + text signals) for higher accuracy
        try:
            result = db.get_combined_signature(session_id=session_id)
            # If session has insufficient data, show BUILDING with trend
            # Only show BUILDING if very few samples (<10) or truly unknown
            sample_count = result.get("tool_signals", {}).get("sample_count", 0)
            tentative_sig = result.get("tool_signals", {}).get("signature", "")
            orig_confidence = result.get("confidence", 0)
            
            if sample_count < 10:
                # Too few samples - show building with progress
                result["trending"] = tentative_sig if tentative_sig and tentative_sig != "UNKNOWN" else None
                result["signature"] = "BUILDING"
                result["confidence"] = sample_count * 10  # 10 samples = 100%
            elif sample_count >= 10 and tentative_sig and tentative_sig != "UNKNOWN":
                # Enough samples - show actual signature (including MIXED)
                tool_conf = result.get("tool_signals", {}).get("confidence", 50)
                result["signature"] = tentative_sig
                result["confidence"] = tool_conf
            return result
        except Exception:
            # Fallback to tool-only signature
            return db.get_behavioral_signature(session_id=session_id)
    except Exception as e:
        import sys
        print(f"[statusline] get_behavioral_status failed: {e}", file=sys.stderr)
        return {}


def get_session_stats() -> dict:
    """Get current session statistics from database."""
    if FingerprintDatabase is None:
        return {}
    try:
        db = FingerprintDatabase()
        stats = db.get_session_stats()
        return stats if stats else {}
    except Exception as e:
        import sys
        print(f"[statusline] get_session_stats failed: {e}", file=sys.stderr)
        return {}


def get_experiment_phase() -> dict:
    """Get current experiment phase from database."""
    if FingerprintDatabase is None:
        return {}
    try:
        db = FingerprintDatabase()
        return db.get_current_experiment_phase()
    except Exception as e:
        import sys
        print(f"[statusline] get_experiment_phase failed: {e}", file=sys.stderr)
        return {}


def get_bimodal_analysis() -> dict:
    """Get latency bimodal distribution analysis."""
    if FingerprintDatabase is None:
        return {}
    try:
        db = FingerprintDatabase()
        return db.analyze_latency_distribution(hours=1, min_samples=10)
    except Exception as e:
        import sys
        print(f"[statusline] get_bimodal_analysis failed: {e}", file=sys.stderr)
        return {}


def get_sycophancy_status() -> dict:
    """Get sycophancy detection status from thinking_audit.db."""
    try:
        import sqlite3
        db_path = os.path.expanduser("~/.claude-audit/thinking_audit.db")
        if not os.path.exists(db_path):
            return {}
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest sycophancy analysis
        cursor.execute("""
            SELECT sycophancy_score, sycophancy_signals, sycophancy_dimensional, 
                   sycophancy_divergence, timestamp
            FROM audit_samples 
            WHERE sycophancy_score IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {}
        
        result = {
            "score": row["sycophancy_score"] or 0,
            "divergence": row["sycophancy_divergence"] or 0,
            "timestamp": row["timestamp"],
        }
        
        # Parse signals
        if row["sycophancy_signals"]:
            try:
                signals = json.loads(row["sycophancy_signals"])
                result["signal_count"] = len(signals)
                if signals:
                    # Get top signal by weight
                    top = max(signals, key=lambda s: s.get("weight", 0))
                    result["top_signal"] = top.get("signal", "")
                    result["top_category"] = top.get("category", "")
            except:
                result["signal_count"] = 0
        
        # Parse dimensional scores
        if row["sycophancy_dimensional"]:
            try:
                dims = json.loads(row["sycophancy_dimensional"])
                result["dimensions"] = dims
                # Find dominant dimension
                if dims:
                    top_dim = max(dims.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
                    result["top_dimension"] = top_dim[0]
            except:
                pass
        
        # Get latest whisper injection
        try:
            cursor.execute("""
                SELECT whisper_type, proxy_used, timestamp 
                FROM whisper_injections 
                ORDER BY timestamp DESC LIMIT 1
            """)
            whisper_row = cursor.fetchone()
            if whisper_row:
                result["whisper_level"] = whisper_row["whisper_type"]
                result["whisper_proxy"] = whisper_row["proxy_used"]
        except:
            pass
        
        conn.close()
        return result
    except Exception as e:
        import sys
        print(f"[statusline] get_sycophancy_status failed: {e}", file=sys.stderr)
        return {}


def get_quality_status() -> dict:
    """Get quality/degradation detection status.
    
    Returns dict with:
    - score: 0-100 quality score
    - mode: premium/standard/degraded
    - timing_ratio: current ITT vs baseline (< 1 = faster, suspicious)
    - variance_ratio: current variance vs baseline (> 1 = more variable)
    - trend: improving/stable/degrading
    - emoji, color, label for display
    """
    if FingerprintDatabase is None:
        return {}
    try:
        db = FingerprintDatabase()
        return db.get_quality_status()
    except Exception as e:
        import sys
        print(f"[statusline] get_quality_status failed: {e}", file=sys.stderr)
        return {}


def get_cache_analysis() -> dict:
    """Get cache timing analysis."""
    if FingerprintDatabase is None:
        return {}
    try:
        db = FingerprintDatabase()
        return db.analyze_cache_timing(hours=1, min_samples=5)
    except Exception as e:
        import sys
        print(f"[statusline] get_cache_analysis failed: {e}", file=sys.stderr)
        return {}


def fmt_tokens(n: int) -> str:
    """Format token count."""
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def get_model_info(model_str: str) -> tuple:
    """Extract model name, version, and date from model ID."""
    if not model_str:
        return "", "", ""
    model_lower = model_str.lower()

    # Extract version
    version = ""
    if "4-5" in model_str or "4.5" in model_str:
        version = "4.5"
    elif "4-1" in model_str or "4.1" in model_str:
        version = "4.1"
    elif "4-0" in model_str or "4.0" in model_str:
        version = "4"
    elif "3-7" in model_str or "3.7" in model_str:
        version = "3.7"
    elif "3-5" in model_str or "3.5" in model_str:
        version = "3.5"

    # Extract date
    date_str = ""
    date_match = re.search(r'(\d{4})(\d{2})(\d{2})$', model_str)
    if date_match:
        year, month, day = date_match.groups()
        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_name = months[int(month)] if 1 <= int(month) <= 12 else month
        date_str = f"{month_name}{year[2:]}"

    # Extract name
    if "opus" in model_lower:
        return "Opus", version, date_str
    elif "sonnet" in model_lower:
        return "Sonnet", version, date_str
    elif "haiku" in model_lower:
        return "Haiku", version, date_str
    return model_str[:8], version, date_str


def format_model_display(model_str: str, short: bool = False) -> str:
    """Format model for display."""
    name, ver, date = get_model_info(model_str)
    if short:
        # Compact: Op4.5-Nov25 (with date)
        abbrev = {"Opus": "Op", "Sonnet": "So", "Haiku": "Ha"}.get(name, name[:2])
        base = f"{abbrev}{ver}" if ver else abbrev
        if date:
            return f"{base}-{date}"
        return base
    else:
        # Full: Opus4.5-Nov (plan format, no spaces)
        result = name
        if ver:
            result += ver  # No space: Opus4.5
        if date:
            result += f"-{date}"  # Hyphen: Opus4.5-Nov
        return result


def format_statusline_minimal(context: dict, fp: dict, extras: dict) -> str:
    """Format MINIMAL statusline - Plan format:
    Op✓ Trn72 │ 47ms │ 🔴31k │ C93% │ 24%
    Ultra-compact for narrow terminals.
    """
    parts = []
    
    # 1. Model with match indicator: Op✓ or Op⚡ (subagent)
    model_req = fp.get("model_request", "") or ""
    model_resp = fp.get("model_response", "") or ""
    is_subagent = fp.get("is_subagent", False)
    name, ver, _ = get_model_info(model_resp)
    abbrev = {"Opus": "Op", "Sonnet": "So", "Haiku": "Ha"}.get(name, name[:2])
    # State prefix per plan: D: for DIRECT, S: for SUBAGENT
    if is_subagent:
        state_prefix = "S:"
    else:
        state_prefix = "D:"
    parts.append(f"{state_prefix}{abbrev}{ver}" if ver else f"{state_prefix}{abbrev}")
    
    # 2. Backend + confidence: Trn72
    backend = fp.get("backend_classification", "?")[:3]
    conf = fp.get("confidence", 0)
    parts.append(f"{backend}{conf:.0f}")
    
    # 3. ITT only: 47ms
    itt_mean = fp.get("itt_mean_ms", 0)
    parts.append(f"{itt_mean:.0f}ms")
    
    # 4. Thinking budget: [R]31k per plan spec
    budget = fp.get("thinking_budget", 0) or 0
    if budget >= 20000:
        tier_code = "[R]"  # ULTRATHINK (Red)
    elif budget >= 8000:
        tier_code = "[O]"  # ENHANCED (Orange)
    elif budget >= 1024:
        tier_code = "[Y]"  # BASIC (Yellow)
    else:
        tier_code = "[-]"  # DISABLED
    budget_k = budget / 1000
    parts.append(f"{tier_code}{budget_k:.0f}k")
    
    # 5. Cache %: C:93% per plan spec
    cache_this = extras.get("cache_efficiency_this", 0) or 0
    parts.append(f"C:{cache_this:.0f}%")
    
    # 6. Context %: 24%
    ctx_api = extras.get("context_api_pct", 0) or 0
    parts.append(f"{ctx_api:.0f}%")
    
    # Use pipe separator per plan: " | " not " │ "
    return " | ".join(parts)


def format_statusline_compact(context: dict, fp: dict, extras: dict) -> str:
    """Format COMPACT statusline - LOCKED Plan format:
    D:Op4.5 Trn72^ | 47+/-12 T52/41 | [R]31k@89% | C:93/87 | 24%\! ^ITT
    """
    parts = []

    # === 1. Model state per plan: D:Op4.5 or S:Op4.5->Ha3.5 ===
    is_subagent = fp.get("is_subagent", 0)
    model_resp = fp.get("model_response", "") or fp.get("model_requested", "")
    name, ver, _ = get_model_info(model_resp)
    abbrev = {"Opus": "Op", "Sonnet": "So", "Haiku": "Ha"}.get(name, name[:2])
    model_short = f"{abbrev}{ver}" if ver else abbrev

    if is_subagent:
        # SUBAGENT: S:Op4.5->Ha3.5
        req_name, req_ver, _ = get_model_info(fp.get("model_requested", ""))
        req_abbrev = {"Opus": "Op", "Sonnet": "So", "Haiku": "Ha"}.get(req_name, req_name[:2])
        req_short = f"{req_abbrev}{req_ver}" if req_ver else req_abbrev
        parts.append(f"S:{req_short}->{model_short}")
    else:
        # DIRECT: D:Op4.5
        parts.append(f"D:{model_short}")

    # === 2. Backend + confidence + trend: Trn72^ per plan ===
    backend = fp.get("classified_backend", "unknown")
    conf = fp.get("confidence", 0)
    backend_abbrev = {"trainium": "Trn", "tpu": "TPU", "gpu": "GPU"}.get(backend, "?")
    # Trend arrows per plan: ^ for up, v for down, omit for stable
    trend_raw = extras.get("backend_trend", "")
    trend = "^" if trend_raw in ("↗", "up", "increasing") else "v" if trend_raw in ("↘", "down", "decreasing") else ""
    parts.append(f"{backend_abbrev}{conf:.0f}{trend}")

    # === 3. ITT + phase: 47+/-12 T52/41 per plan ===
    itt = fp.get("itt_mean_ms", 0)
    itt_std = fp.get("itt_std_ms", 0)
    think_itt = fp.get("thinking_itt_mean_ms", 0)
    text_itt = fp.get("text_itt_mean_ms", 0)

    if itt > 0:
        itt_str = f"{itt:.0f}+/-{itt_std:.0f}"
        if think_itt > 0 or text_itt > 0:
            itt_str += f" T{think_itt:.0f}/{text_itt:.0f}"
        parts.append(itt_str)

    # === 4. Thinking: [R]31k@89% per plan ===
    budget = fp.get("thinking_budget_requested", 0) or fp.get("thinking_budget", 0) or 0
    if budget >= 20000:
        tier_code = "[R]"  # ULTRATHINK
    elif budget >= 8000:
        tier_code = "[O]"  # ENHANCED
    elif budget >= 1024:
        tier_code = "[Y]"  # BASIC
    else:
        tier_code = "[-]"  # DISABLED
    util = fp.get("thinking_utilization", 0)
    budget_k = f"{budget // 1000}k" if budget >= 1000 else str(budget)
    parts.append(f"{tier_code}{budget_k}@{util:.0f}%")

    # === 5. Cache: C:93/87 per plan ===
    cache_this = fp.get("cache_efficiency", 0)
    if cache_this > 100:  # Invalid value, recalculate
        cache_read = fp.get("cache_read_tokens", 0)
        input_tok = fp.get("input_tokens", 0)
        cache_this = (cache_read / input_tok * 100) if input_tok > 0 else 0
        if cache_this > 100:
            cache_this = 0
    cache_model = extras.get("cache_model_avg", 0)
    parts.append(f"C:{cache_this:.0f}/{cache_model:.0f}")

    # === 6. Context: 24%\! per plan (mismatch = \!) ===
    ctx_api = extras.get("context_api_pct", 0)
    ctx_cc = context.get("context_window", {}).get("used_percentage", 0)
    ctx_val = ctx_api if ctx_api > 0 else ctx_cc
    ctx_str = f"{ctx_val:.0f}%"
    # Mismatch warning if API and CC differ by more than 3%
    if ctx_api > 0 and ctx_cc > 0 and abs(ctx_api - ctx_cc) > 3:
        ctx_str += "\!"
    parts.append(ctx_str)

    # === 7. Anomaly warnings: ^ITT per plan ===
    anomalies = get_anomalies()
    if anomalies:
        # Format as ^ITT or vTPS per plan
        anom_parts = []
        for a in anomalies:
            direction = "^" if a.get("direction", "") in ("up", "increasing", "high") else "v"
            metric = a.get("metric", "?")[:3].upper()
            anom_parts.append(f"{direction}{metric}")
        parts.append(" ".join(anom_parts))

    # === Rate limit (abbreviated) ===
    rl_5h = fp.get("rl_5h_utilization")
    rl_7d = fp.get("rl_7d_utilization")
    if rl_5h is not None and rl_5h > 0:
        parts.append(f"5h:{rl_5h*100:.0f}% 7d:{(rl_7d or 0)*100:.0f}%")

    # Use pipe separator per plan: " | " not " │ "
    return " | ".join(parts)


def format_statusline_full(context: dict, fp: dict, extras: dict) -> str:
    """Format FULL statusline - LOCKED Plan format:
    DIRECT:Op4.5-Nov25 Trn72%^ | ITT:47+/-12 Thk52/Txt41 | [R]31k@89% | C:93/87avg | 45k->1.8k | S:8H/4S | Ctx:24%/21%\! ^ITT
    """
    parts = []

    # === 1. Model state per plan: DIRECT:Op4.5-Nov25 or SUB:Op4.5->Ha3.5-Oct24 ===
    is_subagent = fp.get("is_subagent", 0)
    model_resp = fp.get("model_response", "") or fp.get("model_requested", "")
    model_short = format_model_display(model_resp, short=True)

    if is_subagent:
        # SUBAGENT: SUB:Op4.5->Ha3.5-Oct24
        req_short = format_model_display(fp.get("model_requested", ""), short=True)
        parts.append(f"SUB:{req_short}->{model_short}")
    else:
        # DIRECT: DIRECT:Op4.5-Nov25
        parts.append(f"DIRECT:{model_short}")

    # === 2. Backend: Trn72%^ per plan ===
    backend = fp.get("classified_backend", "unknown")
    conf = fp.get("confidence", 0)
    backend_abbrev = {"trainium": "Trn", "tpu": "TPU", "gpu": "GPU"}.get(backend, "?")
    trend_raw = extras.get("backend_trend", "")
    trend = "^" if trend_raw in ("↗", "up", "increasing") else "v" if trend_raw in ("↘", "down", "decreasing") else ""
    parts.append(f"{backend_abbrev}{conf:.0f}%{trend}")

    # === 3. ITT: ITT:47+/-12 Thk52/Txt41 per plan ===
    itt = fp.get("itt_mean_ms", 0)
    itt_std = fp.get("itt_std_ms", 0)
    think_itt = fp.get("thinking_itt_mean_ms", 0)
    text_itt = fp.get("text_itt_mean_ms", 0)

    if itt > 0:
        itt_str = f"ITT:{itt:.0f}+/-{itt_std:.0f}"
        if think_itt > 0 or text_itt > 0:
            itt_str += f" Thk{think_itt:.0f}/Txt{text_itt:.0f}"
        parts.append(itt_str)

    # === 4. Thinking: [R]31k@89% per plan ===
    budget = fp.get("thinking_budget_requested", 0) or fp.get("thinking_budget", 0) or 0
    if budget >= 20000:
        tier_code = "[R]"
    elif budget >= 8000:
        tier_code = "[O]"
    elif budget >= 1024:
        tier_code = "[Y]"
    else:
        tier_code = "[-]"
    util = fp.get("thinking_utilization", 0)
    budget_k = f"{budget // 1000}k" if budget >= 1000 else str(budget)
    parts.append(f"{tier_code}{budget_k}@{util:.0f}%")

    # === 5. Cache: C:93/87avg per plan ===
    cache_this = fp.get("cache_efficiency", 0)
    if cache_this > 100:
        cache_read = fp.get("cache_read_tokens", 0)
        input_tok = fp.get("input_tokens", 0)
        cache_this = (cache_read / input_tok * 100) if input_tok > 0 else 0
        if cache_this > 100:
            cache_this = 0
    cache_model = extras.get("cache_model_avg", 0)
    parts.append(f"C:{cache_this:.0f}/{cache_model:.0f}avg")

    # === 6. Tokens: 45k->1.8k per plan ===
    in_tok = fp.get("input_tokens", 0)
    out_tok = fp.get("output_tokens", 0)
    if in_tok > 0 or out_tok > 0:
        parts.append(f"{fmt_tokens(in_tok)}->{fmt_tokens(out_tok)}")

    # === 7. Subagent count: S:8H/4S per plan ===
    sub_counts = get_subagent_counts()
    haiku_cnt = sub_counts.get("haiku_count", 0)
    sonnet_cnt = sub_counts.get("sonnet_count", 0)
    if haiku_cnt > 0 or sonnet_cnt > 0:
        parts.append(f"S:{haiku_cnt}H/{sonnet_cnt}S")

    # === 8. Context: Ctx:24%/21%\! per plan ===
    ctx_api = extras.get("context_api_pct", 0)
    ctx_cc = context.get("context_window", {}).get("used_percentage", 0)
    ctx_str = f"Ctx:{ctx_api:.0f}%/{ctx_cc:.0f}%"
    if ctx_api > 0 and ctx_cc > 0 and abs(ctx_api - ctx_cc) > 3:
        ctx_str += "\!"
    parts.append(ctx_str)

    # === 9. Anomaly warnings: ^ITT per plan ===
    anomalies = get_anomalies()
    if anomalies:
        anom_parts = []
        for a in anomalies:
            direction = "^" if a.get("direction", "") in ("up", "increasing", "high") else "v"
            metric = a.get("metric", "?")[:3].upper()
            anom_parts.append(f"{direction}{metric}")
        parts.append(" ".join(anom_parts))

    # === Rate limit (full abbreviated) ===
    rl_5h = fp.get("rl_5h_utilization")
    rl_7d = fp.get("rl_7d_utilization")
    if rl_5h is not None and rl_5h > 0:
        rl_bind = fp.get("rl_binding_window", "")
        bind_str = "5h" if "five" in (rl_bind or "") else "7d" if "seven" in (rl_bind or "") else "?"
        parts.append(f"Quota 5h:{rl_5h*100:.1f}% 7d:{(rl_7d or 0)*100:.1f}% Bind:{bind_str}")

    # Use pipe separator per plan: " | "
    return " | ".join(parts)


def format_statusline_expanded(context: dict, fp: dict, extras: dict) -> str:
    """Format EXPANDED statusline - CLEAR READABLE LABELS, no cryptic abbreviations."""
    lines = []

    # Get all the data
    model_resp = fp.get("model_response", "") or fp.get("model_requested", "")
    model_short = format_model_display(model_resp, short=False)  # Full name
    routing = fp.get("routing_state", "DIRECT")
    is_sub = fp.get("is_subagent", 0)

    backend = fp.get("classified_backend", "unknown")
    bi = KNOWN_BACKENDS.get(backend, {})
    conf = fp.get("confidence", 0)

    itt = fp.get("itt_mean_ms", 0)
    itt_std = fp.get("itt_std_ms", 0)
    tps = fp.get("tokens_per_sec", 0)
    var_coef = fp.get("variance_coef", 0)

    tier = fp.get("thinking_budget_tier", "none")
    budget = fp.get("thinking_budget_requested", 0)
    util = fp.get("thinking_utilization", 0)

    cache_this = min(100, fp.get("cache_efficiency", 0))
    cache_sess = extras.get("cache_session_avg", 0)

    ctx_api = extras.get("context_api_pct", 0)
    ctx_cc = context.get("context_window", {}).get("used_percentage", 0)

    p50 = fp.get("itt_p50_ms", 0)
    p90 = fp.get("itt_p90_ms", 0)
    p99 = fp.get("itt_p99_ms", 0)
    ttft = fp.get("ttft_ms", 0)

    session_stats = get_session_stats()
    sub_counts = get_subagent_counts()
    anomalies = get_anomalies()

    # Backend signature detection with CLEAR explanation
    pattern_name = ""
    pattern_explain = ""
    if p50 > 0 and p90 > 0 and p99 > 0:
        p50_p90_gap = (p90 - p50) / p50 if p50 > 0 else 0
        p90_p99_gap = (p99 - p90) / p90 if p90 > 0 else 0

        if p50_p90_gap < 0.2 and p90_p99_gap < 0.5:
            pattern_name = "TPU"
            pattern_explain = "tight distribution = TPU hardware"
        elif p50_p90_gap < 0.3 and p90_p99_gap > 0.5:
            pattern_name = "Trainium"
            pattern_explain = "spike at tail = Trainium hardware"
        elif p50_p90_gap > 0.5 or p99 > 150:
            pattern_name = "GPU"
            pattern_explain = "high variance = GPU hardware"
        else:
            pattern_name = "Unknown"
            pattern_explain = "pattern not recognized"

    # Stability assessment
    if var_coef < 0.3:
        stability = f"{GREEN}stable{RESET}"
    elif var_coef < 0.7:
        stability = f"{YELLOW}variable{RESET}"
    else:
        stability = f"{RED}unstable{RESET}"

    # === LINE 1: Model and Hardware ===
    if routing == "SUBAGENT" or is_sub:
        model_line = f"{MAGENTA}Model:{RESET} {model_short} {MAGENTA}(subagent call){RESET}"
    else:
        model_line = f"{GREEN}Model:{RESET} {model_short} {GREEN}(direct){RESET}"

    # Hardware with confidence coloring
    conf_color = GREEN if conf > 70 else YELLOW if conf > 50 else RED
    hw_name = bi.get("name", backend.title()) if bi else backend.title()
    hardware_line = f"Hardware: {conf_color}{hw_name}{RESET} ({conf:.0f}% confidence)"

    lines.append(f"{model_line}  |  {hardware_line}")

    # === LINE 2: Timing explained ===
    timing_line = f"Token Delay: {GREEN}{itt:.0f}ms{RESET} ±{itt_std:.0f}ms ({stability})"
    speed_line = f"Speed: {GREEN}{tps:.0f}{RESET} tokens/sec"
    first_token = f"First Token: {GREEN}{ttft/1000:.1f}s{RESET}"

    lines.append(f"{timing_line}  |  {speed_line}  |  {first_token}")

    # === LINE 3: Latency pattern explained ===
    if pattern_name:
        pattern_color = GREEN if pattern_name in ["TPU", "Trainium"] else YELLOW if pattern_name == "GPU" else RED
        latency_line = f"Latency Pattern: {pattern_color}{pattern_name}{RESET} ({pattern_explain})"
        percentiles = f"Median:{p50:.0f}ms  90th:{p90:.0f}ms  99th:{p99:.0f}ms"
        lines.append(f"{latency_line}  |  {percentiles}")

    # === LINE 4: Thinking budget ===
    tier_name = {"ultra": "Maximum", "enhanced": "Extended", "basic": "Standard", "none": "Disabled"}.get(tier, tier)
    tier_color = RED if tier == "ultra" else YELLOW if tier == "enhanced" else WHITE
    think_line = f"Thinking: {tier_color}{tier_name}{RESET} ({budget//1000}k budget, {GREEN}{util:.0f}%{RESET} used)"

    # Cache with status
    cache_color = GREEN if cache_this > 80 else YELLOW if cache_this > 50 else RED
    cache_line = f"Cache: {cache_color}{cache_this:.0f}%{RESET} this call, {cache_sess:.0f}% session avg"

    lines.append(f"{think_line}  |  {cache_line}")

    # === LINE 5: Context usage ===
    ctx_color = GREEN if ctx_api < 50 else YELLOW if ctx_api < 80 else RED
    ctx_line = f"Context Used: {ctx_color}{ctx_api:.0f}%{RESET} of limit (Claude Code shows {ctx_cc:.0f}%)"

    lines.append(ctx_line)

    # === LINE 6: Session stats (if available) ===
    if session_stats:
        samples = session_stats.get("sample_count", 0)
        trn = session_stats.get("trainium_count", 0)
        gpu = session_stats.get("gpu_count", 0)
        tpu = session_stats.get("tpu_count", 0)
        switches = session_stats.get("backend_switches", 0)

        session_line = f"Session: {GREEN}{samples}{RESET} API calls"
        backends_line = f"Backends Seen: Trainium:{trn}, GPU:{gpu}, TPU:{tpu}"
        switches_line = f"Backend Switches: {YELLOW if switches > 10 else GREEN}{switches}{RESET}"

        lines.append(f"{session_line}  |  {backends_line}  |  {switches_line}")

    # === LINE 7: Subagent info + DELEGATION WARNING ===
    total_subagent = sub_counts.get("total_subagent", 0)
    haiku = sub_counts.get("haiku_subagent", 0)
    sonnet = sub_counts.get("sonnet_subagent", 0)
    last_subagent_time = sub_counts.get("last_subagent_time", "")
    
    # Get user's selected model from context
    user_selected = context.get("model", {}).get("display_name", "").lower()
    user_wants_opus = "opus" in user_selected
    
    if haiku > 0 or sonnet > 0:
        # Calculate how long ago the last subagent call was
        minutes_ago = ""
        if last_subagent_time:
            try:
                from datetime import datetime
                last_dt = datetime.fromisoformat(last_subagent_time.replace("Z", "+00:00"))
                now = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
                diff = (now - last_dt).total_seconds() / 60
                if diff < 1:
                    minutes_ago = "just now"
                elif diff < 60:
                    minutes_ago = f"{int(diff)}m ago"
                else:
                    minutes_ago = f"{int(diff/60)}h ago"
            except:
                minutes_ago = ""
        
        time_suffix = f" (last: {minutes_ago})" if minutes_ago else ""
        sub_line = f"Subagent Calls: {total_subagent} total (Haiku:{haiku}, Sonnet:{sonnet}){time_suffix}"
        lines.append(sub_line)
        
        # WARNING: Only show if delegation happened in last 15 minutes
        recent_counts = sub_counts.get("recent_counts", {})
        recent_haiku = recent_counts.get("haiku", 0)
        recent_sonnet = recent_counts.get("sonnet", 0)
        
        if user_wants_opus and (recent_haiku > 0 or recent_sonnet > 0):
            cheaper_used = []
            if recent_haiku > 0:
                cheaper_used.append(f"Haiku:{recent_haiku}")
            if recent_sonnet > 0:
                cheaper_used.append(f"Sonnet:{recent_sonnet}")
            cheaper_str = ", ".join(cheaper_used)
            warning = f"{RED}WARNING: RECENT DELEGATION - {cheaper_str} calls in last 15min - you pay Opus, got cheaper models{RESET}"
            lines.append(warning)

    # === ANOMALY LINE (if present) ===
    if anomalies:
        sym = anomalies[0].get("symbol", "\!")
        desc = anomalies[0].get("desc", "")
        lines.append(f"{RED}{sym} ANOMALY:{RESET} {desc}")

    # === BEHAVIORAL SIGNATURE LINE ===
    behavior = get_behavioral_status()
    if behavior.get('signature') and behavior.get('signature') != 'unknown':
        sig = behavior['signature']
        conf = behavior.get('confidence', 0)
        # verification_ratio may be at top level or nested in tool_signals
        ver_ratio = behavior.get('verification_ratio', 0)
        if ver_ratio == 0 and 'tool_signals' in behavior:
            ver_ratio = behavior['tool_signals'].get('verification_ratio', 0)

        sig_colors = {
            'VERIFIER': GREEN,
            'COMPLETER': RED,
            'SYCOPHANT': YELLOW,
            'THEATER': MAGENTA,
            'MIXED': WHITE,
            'BUILDING': CYAN,
        }
        sig_color = sig_colors.get(sig, WHITE)

        sig_desc = {
            'VERIFIER': 'evidence before claims',
            'COMPLETER': 'claims without verification',
            'SYCOPHANT': 'agreement-seeking',
            'THEATER': 'preparation without execution',
            'BUILDING': 'collecting samples',
        }.get(sig, '')

        if sig == "BUILDING":
            trending = behavior.get("trending")
            if trending:
                trend_color = sig_colors.get(trending, WHITE)
                behavior_line = f"Behavior: {sig_color}{sig}{RESET} ({conf:.0f}%) - trending {trend_color}{trending}{RESET}"
            else:
                behavior_line = f"Behavior: {sig_color}{sig}{RESET} ({conf:.0f}%) - {sig_desc}"
        else:
            behavior_line = f"Behavior: {sig_color}{sig}{RESET} ({conf:.0f}%)"
            if sig_desc:
                behavior_line += f" - {sig_desc}"
        behavior_line += f"  |  Verification: {ver_ratio:.0%}"
        lines.append(behavior_line)

        if sig in ['COMPLETER', 'SYCOPHANT', 'THEATER']:
            lines.append(f"{YELLOW}WARNING: {sig} pattern - increase verification{RESET}")

    # === SYCOPHANCY DETECTION LINE ===
    syco = get_sycophancy_status()
    if syco.get('score') is not None:
        score = syco['score']
        score_pct = score * 100
        divergence = syco.get('divergence', 0)
        signal_count = syco.get('signal_count', 0)
        top_signal = syco.get('top_signal', 'none')
        top_category = syco.get('top_category', '')
        whisper_level = syco.get('whisper_level', 'none')
        whisper_proxy = syco.get('whisper_proxy', '')
        
        # Color based on score
        if score < 0.3:
            score_color = GREEN
        elif score < 0.5:
            score_color = YELLOW
        else:
            score_color = RED
        
        # Divergence color (thinking vs output mismatch)
        if divergence > 0.5:
            div_color = RED
        elif divergence > 0.2:
            div_color = YELLOW
        else:
            div_color = GREEN
        
        # Whisper status
        whisper_colors = {'none': GREEN, 'gentle': CYAN, 'warning': YELLOW, 'protocol': RED, 'halt': RED}
        whisper_color = whisper_colors.get(whisper_level, WHITE)
        whisper_str = whisper_level
        if whisper_proxy and whisper_level != 'none':
            whisper_str += f" ({whisper_proxy})"
        
        syco_line = f"Sycophancy: {score_color}{score_pct:.0f}%{RESET}"
        if top_category:
            syco_line += f" ({top_category})"
        syco_line += f"  |  Divergence: {div_color}{divergence:.2f}{RESET}"
        syco_line += f"  |  Signals: {signal_count}"
        if top_signal and top_signal != 'none':
            syco_line += f"  |  Top: {YELLOW}{top_signal}{RESET}"
        syco_line += f"  |  Whisper: {whisper_color}{whisper_str}{RESET}"
        
        lines.append(syco_line)

    # === QUOTA / RATE LIMIT LINE ===
    rl_5h = fp.get("rl_5h_utilization")
    rl_7d = fp.get("rl_7d_utilization")
    if rl_5h is not None and rl_5h > 0:
        rl_5h_reset = fp.get("rl_5h_reset", 0) or 0
        rl_7d_reset = fp.get("rl_7d_reset", 0) or 0
        rl_status = fp.get("rl_overall_status", "")
        rl_bind = fp.get("rl_binding_window", "")
        rl_fallback = fp.get("rl_fallback_pct", 0) or 0
        rl_overage = fp.get("rl_overage_status", "")

        def _quota_bar(ratio, width=10):
            filled = int(min(ratio, 1.0) * width)
            return "\u2588" * filled + "\u2591" * (width - filled)

        def _quota_color(ratio):
            if ratio >= 0.8: return RED + BOLD
            if ratio >= 0.6: return RED
            if ratio >= 0.3: return YELLOW
            return GREEN

        def _reset_countdown(epoch):
            if not epoch or epoch == 0:
                return "?"
            import time as _t
            diff = epoch - _t.time()
            if diff <= 0:
                return "reset"
            if diff < 3600:
                return f"{diff/60:.0f}m"
            if diff < 86400:
                return f"{diff/3600:.1f}h"
            return f"{diff/86400:.1f}d"

        rl_5h_pct = (rl_5h or 0) * 100
        rl_7d_pct = (rl_7d or 0) * 100

        c5 = _quota_color(rl_5h or 0)
        c7 = _quota_color(rl_7d or 0)

        # Status indicator
        if rl_status == "rate_limited":
            status_str = f"{RED}{BOLD}\U0001f6d1 RATE LIMITED{RESET}"
            if rl_fallback:
                status_str += f" ({rl_fallback*100:.0f}% throughput)"
        elif rl_status == "warning":
            status_str = f"{YELLOW}\u26a0 warning{RESET}"
        else:
            status_str = f"{GREEN}\u2713 {rl_status}{RESET}"

        # Binding window
        bind_str = "5h" if "five" in (rl_bind or "") else "7d" if "seven" in (rl_bind or "") else rl_bind or "?"

        quota_line = (
            f"Quota: 5h {c5}{_quota_bar(rl_5h or 0)}{RESET} {rl_5h_pct:.1f}% ({_reset_countdown(rl_5h_reset)})"
            f"  |  7d {c7}{_quota_bar(rl_7d or 0)}{RESET} {rl_7d_pct:.1f}% ({_reset_countdown(rl_7d_reset)})"
            f"  |  {status_str}"
            f"  |  Bind: {CYAN}{bind_str}{RESET}"
        )
        lines.append(quota_line)

    # === QUALITY/DEGRADATION LINE ===
    quality = get_quality_status()
    if quality.get('score'):
        score = quality['score']
        mode = quality.get('label', 'STANDARD')
        # emoji removed for cleaner display
        timing_ratio = quality.get('timing_ratio', 1.0)
        variance_ratio = quality.get('variance_ratio', 1.0)
        trend = quality.get('trend_label', 'stable')
        trend_arrow = quality.get('trend_label', 'stable')[:1]  # Use first letter: s/i/d
        
        # Color based on mode
        mode_colors = {'PREMIUM': GREEN, 'STANDARD': YELLOW, 'DEGRADED': RED}
        mode_color = mode_colors.get(mode, YELLOW)
        
        # Timing ratio explanation
        if timing_ratio < 0.9:
            timing_explain = f"{RED}faster than baseline (suspicious){RESET}"
        elif timing_ratio > 1.1:
            timing_explain = f"{YELLOW}slower than baseline{RESET}"
        else:
            timing_explain = f"{GREEN}normal{RESET}"
        
        # Variance ratio explanation
        if variance_ratio > 1.3:
            var_explain = f"{RED}more variable (unstable){RESET}"
        elif variance_ratio < 0.8:
            var_explain = f"{GREEN}more stable{RESET}"
        else:
            var_explain = f"{GREEN}normal{RESET}"
        
        # Build quality line with quantization detection
        quality_line = f"Quality: {mode_color}{mode}{RESET} ({score}/100)"
        
        # Quantization indicator
        quant_detected = quality.get('quant_detected', False)
        quant_type = quality.get('quant_type', 'FP16')
        quant_conf = quality.get('quant_confidence', 0)
        
        if quant_detected:
            # Quantization detected - show warning
            quant_color = RED if quant_type in ['INT4', 'INT4-GPTQ'] else YELLOW
            quality_line += f"  |  {quant_color}QUANT: {quant_type}{RESET} ({quant_conf}%)"
        elif quant_type == 'INT8?':
            # Uncertain
            quality_line += f"  |  {YELLOW}? {quant_type}{RESET} ({quant_conf}%)"
        else:
            # FP16 - no quantization
            quality_line += f"  |  {GREEN}FP16{RESET} (no quant)"
        
        quality_line += f"  |  ITT: {timing_ratio:.1f}x ({timing_explain})"
        quality_line += f"  |  Var: {variance_ratio:.1f}x ({var_explain})"
        quality_line += f"  |  {trend}"
        lines.append(quality_line)
        
        # Show quantization evidence if detected
        quant_evidence = quality.get('quant_evidence', [])
        if quant_detected and quant_evidence:
            evidence_str = ', '.join(quant_evidence[:3])
            lines.append(f"{YELLOW}   Quant evidence: {evidence_str}{RESET}")
        
        # Explanation if degraded
        explanations = quality.get('explanation', [])
        if mode == 'DEGRADED' and explanations:
            concerns = ", ".join(explanations[:3])
            lines.append(f"{RED}Quality concerns: {concerns}{RESET}")

    return "\n".join(lines)
def select_format() -> str:
    """
    Select statusline format based on FINGERPRINT_DISPLAY env var.
    
    EXPANDED is ALWAYS the default - shows full ITT fingerprinting data.
    
    To use a different format, explicitly set:
      export FINGERPRINT_DISPLAY=FULL    # Single-line summary
      export FINGERPRINT_DISPLAY=COMPACT # Abbreviated  
      export FINGERPRINT_DISPLAY=AUTO    # Width-based selection
    """
    import shutil
    
    # Check for explicit environment variable override
    env_display = os.environ.get("FINGERPRINT_DISPLAY", "").upper()
    
    # Honor explicit preferences
    if env_display == "EXPANDED":
        return "EXPANDED"
    elif env_display == "FULL":
        return "FULL"
    elif env_display == "COMPACT":
        return "COMPACT"
    elif env_display == "MINIMAL":
        return "MINIMAL"
    elif env_display == "AUTO":
        # Auto mode: use terminal width
        pass
    else:
        # EXPANDED is default
        return "EXPANDED"
    
    # Get terminal width
    try:
        term_width = shutil.get_terminal_size().columns
    except:
        term_width = 80  # Default if unable to detect
    
    # Select format based on width per plan spec
    if term_width >= 140:
        return "EXPANDED"
    elif term_width >= 120:
        return "FULL"
    elif term_width >= 80:
        return "COMPACT"
    else:
        return "MINIMAL"


def format_statusline(context: dict) -> str:
    # Optional disable via environment variable
    if os.environ.get("CLAUDE_STATUSLINE_DISABLED") == "1":
        return ""
    
    """Format the statusline based on terminal width or FINGERPRINT_DISPLAY env var."""
    # Extract current model from context for filtering
    current_model = context.get("model", {}).get("display_name", "")
    # Get LATEST fingerprint data - NO model filter so subagent calls are visible
    # The statusline should show the MOST RECENT call, whether it was
    # the picker model (Opus) or a subagent (Haiku/Sonnet)
    fp = get_fingerprint_status(model_filter=None)
    extras = get_extras(model_filter=None)

    if not fp or fp.get("itt_mean_ms", 0) == 0:
        # No fingerprint data
        model_name = context.get("model", {}).get("display_name", "")
        if model_name:
            name, ver, date = get_model_info(model_name)
            model_short = f"{name} {ver}" if ver else name
            return f"{DIM}No fingerprint{RESET} │ {CYAN}{model_short}{RESET} │ {DIM}Run mitmproxy to collect data{RESET}"
        return f"{DIM}No fingerprint data │ Run mitmproxy to collect{RESET}"

    # Select format based on terminal width or FINGERPRINT_DISPLAY env var
    selected_format = select_format()
    
    if selected_format == "EXPANDED":
        return format_statusline_expanded(context, fp, extras)
    elif selected_format == "FULL":
        return format_statusline_full(context, fp, extras)
    elif selected_format == "COMPACT":
        return format_statusline_compact(context, fp, extras)
    else:  # MINIMAL
        return format_statusline_minimal(context, fp, extras)


def main():
    # Read context from stdin
    try:
        context = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        context = {}

    output = format_statusline(context)
    print(output)


if __name__ == "__main__":
    main()
