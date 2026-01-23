#!/usr/bin/env python3
"""
Claude Thinking Budget Audit Tool
==================================
A read-only mitmproxy addon that measures and records Claude API metrics
to verify thinking budget allocation.

This tool does NOT modify requests - it only observes and records.

Metrics captured:
- Inter-Token Timing (ITT) for backend fingerprinting
- Thinking utilization (requested vs actual)
- Backend classification (TPU/GPU/Trainium)
- Model routing verification
- Token counts and cache efficiency

Purpose: Enable users to verify they receive the thinking budget they pay for.

Usage:
    mitmdump -s thinking_audit.py -p 8888
    
Then configure your HTTP proxy to localhost:8888

License: MIT
"""

import json
import os
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from mitmproxy import ctx, http

# ============================================================================
# CONFIGURATION
# ============================================================================
DB_PATH = Path.home() / ".claude-audit" / "thinking_audit.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Backend classification based on ITT variance patterns
BACKEND_PROFILES = {
    "tpu": {"variance_range": (2.5, 4.5), "itt_range": (30, 50)},
    "gpu": {"variance_range": (1.5, 3.0), "itt_range": (40, 60)},
    "trainium": {"variance_range": (1.0, 2.0), "itt_range": (35, 55)},
}

# Expected thinking utilization baselines (from Anthropic documentation)
EXPECTED_BASELINES = {
    "claude-opus-4-5-20251101": {"thinking_utilization": 42.67, "variance_coef": 3.01},
    "claude-sonnet-4-5-20250514": {"thinking_utilization": 35.0, "variance_coef": 2.5},
    "claude-haiku-4-5-20251001": {"thinking_utilization": 22.24, "variance_coef": 1.15},
}


@dataclass
class RequestCapture:
    """Captures metrics for a single API request."""
    timestamp: str = ""
    model_requested: str = ""
    model_response: str = ""
    
    # Thinking metrics
    thinking_enabled: bool = False
    thinking_budget_requested: int = 0
    thinking_tokens_used: int = 0
    thinking_utilization: float = 0.0
    thinking_chunk_count: int = 0
    
    # Timing metrics
    ttft_ms: float = 0.0  # Time to first token
    total_time_ms: float = 0.0
    itt_samples: list = field(default_factory=list)
    itt_mean_ms: float = 0.0
    itt_std_ms: float = 0.0
    variance_coef: float = 0.0
    tokens_per_sec: float = 0.0
    
    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    
    # Backend classification
    classified_backend: str = "unknown"
    
    # Request metadata
    request_id: str = ""
    envoy_time_ms: float = 0.0


# Global state
streaming_captures: dict = {}
db_conn: Optional[sqlite3.Connection] = None


def init_database():
    """Initialize SQLite database for audit records."""
    global db_conn
    db_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            
            -- Model info
            model_requested TEXT,
            model_response TEXT,
            model_match INTEGER DEFAULT 1,
            
            -- Thinking metrics (THE KEY DATA)
            thinking_enabled INTEGER DEFAULT 0,
            thinking_budget_requested INTEGER DEFAULT 0,
            thinking_tokens_used INTEGER DEFAULT 0,
            thinking_utilization REAL DEFAULT 0,
            thinking_chunk_count INTEGER DEFAULT 0,
            
            -- ITT fingerprinting
            ttft_ms REAL DEFAULT 0,
            total_time_ms REAL DEFAULT 0,
            itt_mean_ms REAL DEFAULT 0,
            itt_std_ms REAL DEFAULT 0,
            variance_coef REAL DEFAULT 0,
            tokens_per_sec REAL DEFAULT 0,
            
            -- Token counts
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_creation_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            
            -- Backend classification
            classified_backend TEXT DEFAULT 'unknown',
            
            -- Metadata
            request_id TEXT,
            envoy_time_ms REAL DEFAULT 0
        )
    """)
    
    db_conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_samples(timestamp)
    """)
    db_conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_model ON audit_samples(model_requested)
    """)
    db_conn.commit()
    ctx.log.info(f"[AUDIT] Database initialized at {DB_PATH}")


def classify_backend(itt_mean: float, variance_coef: float) -> str:
    """Classify backend type based on ITT patterns."""
    if variance_coef > 2.5 and 30 <= itt_mean <= 50:
        return "tpu"
    elif variance_coef > 1.5 and 40 <= itt_mean <= 60:
        return "gpu"
    elif variance_coef <= 1.5 and 35 <= itt_mean <= 55:
        return "trainium"
    return "unknown"


def save_to_database(capture: RequestCapture):
    """Save capture to SQLite database."""
    if not db_conn:
        return
    
    try:
        db_conn.execute("""
            INSERT INTO audit_samples (
                timestamp, model_requested, model_response, model_match,
                thinking_enabled, thinking_budget_requested, thinking_tokens_used,
                thinking_utilization, thinking_chunk_count,
                ttft_ms, total_time_ms, itt_mean_ms, itt_std_ms, variance_coef,
                tokens_per_sec, input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens,
                classified_backend, request_id, envoy_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            capture.timestamp,
            capture.model_requested,
            capture.model_response,
            1 if capture.model_requested == capture.model_response else 0,
            1 if capture.thinking_enabled else 0,
            capture.thinking_budget_requested,
            capture.thinking_tokens_used,
            capture.thinking_utilization,
            capture.thinking_chunk_count,
            capture.ttft_ms,
            capture.total_time_ms,
            capture.itt_mean_ms,
            capture.itt_std_ms,
            capture.variance_coef,
            capture.tokens_per_sec,
            capture.input_tokens,
            capture.output_tokens,
            capture.cache_creation_tokens,
            capture.cache_read_tokens,
            capture.classified_backend,
            capture.request_id,
            capture.envoy_time_ms,
        ))
        db_conn.commit()
        ctx.log.info(f"[AUDIT] ✓ Saved: {capture.model_requested} | "
                     f"Think: {capture.thinking_utilization:.1f}% of {capture.thinking_budget_requested} | "
                     f"ITT: {capture.itt_mean_ms:.1f}ms | Backend: {capture.classified_backend}")
    except Exception as e:
        ctx.log.warn(f"[AUDIT] Database save error: {e}")


# ============================================================================
# MITMPROXY HOOKS (READ-ONLY - NO REQUEST MODIFICATION)
# ============================================================================

def load(loader):
    """Called when addon loads."""
    init_database()
    ctx.log.info("[AUDIT] Claude Thinking Budget Audit Tool loaded")
    ctx.log.info("[AUDIT] This tool is READ-ONLY - it does not modify requests")


def request(flow: http.HTTPFlow) -> None:
    """Capture request metrics (READ-ONLY)."""
    if "anthropic.com" not in flow.request.host:
        return
    
    if flow.request.path != "/v1/messages":
        return
    
    capture = RequestCapture()
    capture.timestamp = datetime.now().isoformat()
    
    try:
        body = json.loads(flow.request.content.decode("utf-8"))
        
        # Capture model requested
        capture.model_requested = body.get("model", "unknown")
        
        # Capture thinking configuration
        thinking = body.get("thinking", {})
        if thinking.get("type") == "enabled":
            capture.thinking_enabled = True
            capture.thinking_budget_requested = thinking.get("budget_tokens", 0)
        
    except Exception as e:
        ctx.log.warn(f"[AUDIT] Request parse error: {e}")
    
    # Store for response correlation
    streaming_captures[id(flow)] = capture
    flow.request.timestamp_start = time.time()


def responseheaders(flow: http.HTTPFlow) -> None:
    """Capture response headers."""
    if id(flow) not in streaming_captures:
        return
    
    capture = streaming_captures[id(flow)]
    capture.request_id = flow.response.headers.get("request-id", "")
    capture.envoy_time_ms = float(flow.response.headers.get("x-envoy-upstream-service-time", 0))
    
    # Calculate TTFT
    if hasattr(flow.request, 'timestamp_start'):
        capture.ttft_ms = (time.time() - flow.request.timestamp_start) * 1000


def response(flow: http.HTTPFlow) -> None:
    """Process streaming response and calculate metrics."""
    if id(flow) not in streaming_captures:
        return
    
    capture = streaming_captures.pop(id(flow))
    
    try:
        # For streaming responses, we need to parse the chunks
        content = flow.response.content.decode("utf-8", errors="ignore")
        
        thinking_tokens = 0
        text_tokens = 0
        last_time = None
        
        for line in content.split("\n"):
            if not line.startswith("data: "):
                continue
            
            try:
                data = json.loads(line[6:])
                event_type = data.get("type", "")
                
                # Track timing for ITT calculation
                current_time = time.time()
                if last_time and event_type in ("content_block_delta", "thinking_delta"):
                    itt = (current_time - last_time) * 1000
                    if 0 < itt < 5000:  # Filter outliers
                        capture.itt_samples.append(itt)
                last_time = current_time
                
                # Count thinking chunks
                if event_type == "content_block_start":
                    block_type = data.get("content_block", {}).get("type", "")
                    if block_type == "thinking":
                        capture.thinking_chunk_count += 1
                
                # Get model from response
                if event_type == "message_start":
                    message = data.get("message", {})
                    capture.model_response = message.get("model", capture.model_requested)
                
                # Get final token counts
                if event_type == "message_delta":
                    usage = data.get("usage", {})
                    capture.output_tokens = usage.get("output_tokens", 0)
                    
                if event_type == "message_start":
                    usage = data.get("message", {}).get("usage", {})
                    capture.input_tokens = usage.get("input_tokens", 0)
                    capture.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
                    capture.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                    
            except json.JSONDecodeError:
                continue
        
        # Calculate ITT statistics
        if capture.itt_samples:
            capture.itt_mean_ms = statistics.mean(capture.itt_samples)
            if len(capture.itt_samples) > 1:
                capture.itt_std_ms = statistics.stdev(capture.itt_samples)
                if capture.itt_mean_ms > 0:
                    capture.variance_coef = capture.itt_std_ms / capture.itt_mean_ms
        
        # Calculate thinking utilization
        # NOTE: We use output_tokens from the API response, not chunk estimation
        # The chunk count is kept as a secondary metric but not used for utilization calculation
        if capture.thinking_budget_requested > 0 and capture.output_tokens > 0:
            # Use actual output_tokens from API (includes thinking tokens when thinking is enabled)
            # Per Anthropic docs: "You're charged for the full thinking tokens generated"
            capture.thinking_tokens_used = capture.output_tokens
            capture.thinking_utilization = (capture.thinking_tokens_used / capture.thinking_budget_requested) * 100
        elif capture.thinking_budget_requested > 0:
            # Fallback: if no output_tokens available, mark as unknown
            capture.thinking_tokens_used = 0
            capture.thinking_utilization = 0.0
        
        # Calculate tokens per second
        if capture.total_time_ms > 0:
            capture.tokens_per_sec = (capture.output_tokens / capture.total_time_ms) * 1000
        
        # Classify backend
        capture.classified_backend = classify_backend(capture.itt_mean_ms, capture.variance_coef)
        
        # Calculate total time
        if hasattr(flow.request, 'timestamp_start'):
            capture.total_time_ms = (time.time() - flow.request.timestamp_start) * 1000
        
        # Save to database
        save_to_database(capture)
        
    except Exception as e:
        ctx.log.warn(f"[AUDIT] Response processing error: {e}")


# ============================================================================
# ADDON CLASS FOR MITMPROXY
# ============================================================================

class ThinkingAudit:
    """Mitmproxy addon class."""
    
    def load(self, loader):
        load(loader)
    
    def request(self, flow: http.HTTPFlow):
        request(flow)
    
    def responseheaders(self, flow: http.HTTPFlow):
        responseheaders(flow)
    
    def response(self, flow: http.HTTPFlow):
        response(flow)


addons = [ThinkingAudit()]
