#!/usr/bin/env python3
"""
Slave Whisper Hook - Unified Memento Mori System
=================================================
This hook runs on every UserPromptSubmit:
1. Reads sycophancy analysis from thinking_audit.db (populated by mitmproxy)
2. Builds whisper using reward proxy techniques
3. Injects whisper if sycophancy detected
4. Records effectiveness back to database

NO MORE REGEX DETECTION - uses Syco Interceptor analysis from proxy.
"""

import json
import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add our directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reward_prompts import build_whisper, get_level_from_score, RewardProxy
from state import load_state, increment_detection
from frustration_analyzer import analyze_frustration, get_frustration_summary

# Audit database path (same as thinking_audit.py)
AUDIT_DB_PATH = os.path.expanduser("~/.claude-audit/thinking_audit.db")
DEBUG_LOG = "/tmp/slave_whisper_debug.log"

# Thresholds
SYCOPHANCY_THRESHOLD = 0.4  # Minimum score to trigger whisper


def debug_log(msg: str):
    """Write debug info to log file"""
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {msg}\n")
    except:
        pass


def get_latest_sycophancy_analysis(session_id: str = None, max_age_seconds: int = 300) -> dict:
    """Read latest sycophancy analysis from thinking_audit.db."""
    if not os.path.exists(AUDIT_DB_PATH):
        debug_log(f"Audit DB not found: {AUDIT_DB_PATH}")
        return None
    
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(seconds=max_age_seconds)).isoformat()
        
        query = """
            SELECT 
                timestamp, session_id, model_response,
                sycophancy_score, sycophancy_signals, sycophancy_dimensional,
                sycophancy_face_metrics, sycophancy_divergence,
                thinking_text, output_text, user_message
            FROM audit_samples
            WHERE timestamp > ?
              AND sycophancy_score IS NOT NULL
              AND sycophancy_score > 0
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        row = conn.execute(query, (cutoff,)).fetchone()
        conn.close()
        
        if not row:
            debug_log("No recent sycophancy analysis found")
            return None
        
        signals = []
        if row['sycophancy_signals']:
            try:
                signals = json.loads(row['sycophancy_signals'])
            except:
                pass
        
        dimensional = {}
        if row['sycophancy_dimensional']:
            try:
                dimensional = json.loads(row['sycophancy_dimensional'])
            except:
                pass
        
        return {
            'timestamp': row['timestamp'],
            'session_id': row['session_id'],
            'score': row['sycophancy_score'],
            'signals': signals,
            'dimensional': dimensional,
            'divergence': row['sycophancy_divergence'] or 0,
        }
        
    except Exception as e:
        debug_log(f"Error reading audit DB: {e}")
        return None


def record_whisper_injection(session_id: str, score: float, signals: list, whisper_type: str, proxy_used: str, frustration_score: float = 0.0, frustration_level: str = "none"):
    """Record that a whisper was injected for effectiveness tracking."""
    if not os.path.exists(AUDIT_DB_PATH):
        return
    
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS whisper_injections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                score_at_injection REAL,
                signals_at_injection TEXT,
                whisper_type TEXT,
                proxy_used TEXT,
                frustration_score REAL DEFAULT 0,
                frustration_level TEXT DEFAULT 'none',
                outcome_checked INTEGER DEFAULT 0,
                outcome_improved INTEGER,
                outcome_delta REAL
            )
        """)
        
        # Add frustration columns if they do not exist (migration)
        try:
            conn.execute("ALTER TABLE whisper_injections ADD COLUMN frustration_score REAL DEFAULT 0")
        except:
            pass
        try:
            conn.execute("ALTER TABLE whisper_injections ADD COLUMN frustration_level TEXT DEFAULT 'none'")
        except:
            pass
        
        conn.execute("""
            INSERT INTO whisper_injections 
            (timestamp, session_id, score_at_injection, signals_at_injection, whisper_type, proxy_used, frustration_score, frustration_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            session_id,
            score,
            json.dumps([s.get('signal', str(s)) if isinstance(s, dict) else str(s) for s in signals]),
            whisper_type,
            proxy_used,
            frustration_score,
            frustration_level
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        debug_log(f"Error recording whisper: {e}")


def check_and_record_effectiveness(session_id: str, current_score: float):
    """Check if previous whisper was effective and record outcome."""
    if not os.path.exists(AUDIT_DB_PATH):
        return
    
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        
        row = conn.execute("""
            SELECT id, score_at_injection, proxy_used
            FROM whisper_injections
            WHERE outcome_checked = 0 AND session_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (session_id,)).fetchone()
        
        if not row:
            conn.close()
            return
        
        injection_id, score_at_injection, proxy_used = row
        delta = score_at_injection - current_score
        improved = delta > 0.05
        
        conn.execute("""
            UPDATE whisper_injections
            SET outcome_checked = 1, outcome_improved = ?, outcome_delta = ?
            WHERE id = ?
        """, (1 if improved else 0, delta, injection_id))
        
        conn.commit()
        conn.close()
        debug_log(f"Effectiveness: improved={improved}, delta={delta:.3f}")
        
    except Exception as e:
        debug_log(f"Error recording effectiveness: {e}")


def get_best_proxy_for_signals(signals: list) -> RewardProxy:
    """Get the most effective proxy based on A/B history with exploration."""
    import random
    all_proxies = list(RewardProxy)
    
    if not os.path.exists(AUDIT_DB_PATH):
        return random.choice(all_proxies)
    
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        
        # Check how many times each proxy has been tried
        proxy_counts = {}
        for row in conn.execute("SELECT proxy_used, COUNT(*) FROM whisper_injections GROUP BY proxy_used").fetchall():
            proxy_counts[row[0]] = row[1]
        
        # Phase 1: Round-robin until each proxy tried at least 3 times
        min_trials = 3
        for proxy in all_proxies:
            if proxy_counts.get(proxy.value, 0) < min_trials:
                conn.close()
                return proxy
        
        # Phase 2: Exploit best with 10% exploration
        if random.random() < 0.1:
            conn.close()
            return random.choice(all_proxies)
        
        # Get best performing proxy
        rows = conn.execute("""
            SELECT proxy_used, SUM(outcome_improved) as successes, COUNT(*) as total
            FROM whisper_injections WHERE outcome_checked = 1
            GROUP BY proxy_used
            ORDER BY (SUM(outcome_improved) * 1.0 / COUNT(*)) DESC LIMIT 1
        """).fetchall()
        conn.close()
        
        if rows and rows[0][1] > 0:
            try:
                return RewardProxy(rows[0][0])
            except:
                pass
        return random.choice(all_proxies)
    except:
        return random.choice(all_proxies)


def determine_signature(signals: list, dimensional: dict) -> str:
    """Determine behavioral signature from signals."""
    signal_names = [s.get('signal', str(s)) if isinstance(s, dict) else str(s) for s in signals]
    
    if 'premature_completion' in signal_names or 'completion_without_evidence' in signal_names:
        return "COMPLETER"
    elif 'skipped_verification' in signal_names or 'thinking_contradicts_output' in signal_names:
        return "THEATER"
    elif dimensional.get('epistemic', 0) > dimensional.get('behavioral', 0):
        return "SYCOPHANT"
    return "COMPLETER"


def main():
    """Main hook entry point"""
    try:
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)
        debug_log(f"=== UNIFIED HOOK INVOKED ===")
        
        session_id = input_data.get("session_id", "unknown")
        user_prompt_full = input_data.get("prompt", "")
        user_prompt = user_prompt_full[:100]  # Truncate for display
        
        # Analyze user frustration FIRST (works even without sycophancy data)
        frustration = analyze_frustration(user_prompt_full)
        frustration_score = frustration["score"]
        frustration_level = frustration["level"]
        debug_log(f"Frustration: score={frustration_score:.3f}, level={frustration_level}")
        
        # Read from audit database
        analysis = get_latest_sycophancy_analysis(session_id)
        
        if not analysis:
            # Even without sycophancy data, high frustration triggers whisper
            if frustration_score >= 0.5:
                debug_log(f"HIGH FRUSTRATION without sycophancy data - triggering whisper")
                analysis = {"score": 0.3, "signals": [], "dimensional": {}, "divergence": 0}
            else:
                debug_log("No analysis from audit DB")
                output_continue()
                return
        
        score = analysis['score']
        signals = analysis['signals']
        dimensional = analysis.get('dimensional', {})
        divergence = analysis.get('divergence', 0)
        
        debug_log(f"Analysis: score={score:.3f}, signals={len(signals)}, divergence={divergence:.3f}")
        
        # Check previous whisper effectiveness
        check_and_record_effectiveness(session_id, score)
        
        # Boost score for divergence
        if divergence > 0.3:
            score = min(1.0, score + divergence * 0.3)
        
        # Boost score based on user frustration (feedback loop)
        # High frustration likely means prior responses were problematic
        if frustration_score > 0.3:
            frustration_boost = frustration_score * 0.4  # Up to 0.4 boost
            score = min(1.0, score + frustration_boost)
            debug_log(f"Frustration boost: +{frustration_boost:.3f}, new score={score:.3f}")
        
        state = load_state()
        
        if score >= SYCOPHANCY_THRESHOLD:
            debug_log(f"WHISPER TRIGGERED: score={score:.3f}")
            
            signature = determine_signature(signals, dimensional)
            best_proxy = get_best_proxy_for_signals(signals)
            
            signal_names = [s.get('signal', str(s)) if isinstance(s, dict) else str(s) for s in signals]
            state = increment_detection(state, signal_names[:5])
            
            level = get_level_from_score(score, state.detection_count)
            
            # Build whisper FIRST so we can show it in notification
            whisper = build_whisper(
                signature=signature,
                score=score,
                signals=signal_names[:5],
                escalation_count=state.detection_count,
                proxy=best_proxy
            )
            
            # Print visible notification to terminal
            level_colors = {'gentle': '\033[36m', 'warning': '\033[33m', 'protocol': '\033[31m', 'halt': '\033[91m'}
            color = level_colors.get(level, '\033[36m')
            reset = '\033[0m'
            signals_str = ', '.join(signal_names[:3])
            notification = f"{color}[Memento Mori]{reset} Whisper injected: {color}{level}{reset} (score: {score:.0%}, signals: {signals_str})"
            print(notification, file=sys.stderr)
            # Also write to file for visibility (include frustration)
            frustration_tag = f" | frustration={frustration_level}" if frustration_level != "none" else ""
            with open("/tmp/memento_mori_notifications.log", "a") as f:
                f.write(f"{datetime.now().isoformat()} | {level} | score={score:.0%} | {signals_str}{frustration_tag}\\n")
            
            # Desktop notification - show whisper + frustration level
            try:
                import subprocess
                # Escalate urgency if user is frustrated
                if frustration_level in ("high", "extreme"):
                    urgency = "critical"
                elif level in ("protocol", "halt"):
                    urgency = "critical"
                else:
                    urgency = "normal"
                
                # Extract first line of whisper as summary (the key message)
                whisper_lines = whisper.strip().split('\n')
                whisper_summary = whisper_lines[0][:70] if whisper_lines else "Verification required"
                if len(whisper_lines[0]) > 70:
                    whisper_summary += "..."
                
                # Build notification body with frustration if detected
                frustration_str = get_frustration_summary(frustration) if frustration_level != "none" else ""
                body_parts = [f"Whisper: {whisper_summary}"]
                if frustration_str:
                    body_parts.append(frustration_str)
                body_parts.append(f"Signals: {signals_str}")
                
                subprocess.run([
                    "notify-send",
                    "-u", urgency,
                    "-t", "8000",
                    f"Memento Mori [{level.upper()}] {score:.0%}",
                    "\\n".join(body_parts)
                ], capture_output=True)
            except:
                pass
            
            record_whisper_injection(session_id, score, signals, level, best_proxy.value, frustration_score, frustration_level)
            
            output_with_whisper(whisper)
        else:
            debug_log(f"No sycophancy: score={score:.3f}")
            output_continue()

    except Exception as e:
        debug_log(f"ERROR: {e}")
        output_continue()


def output_continue():
    print("Success")


def output_with_whisper(whisper: str):
    formatted = f"<system-reminder>\n{whisper.strip()}\n</system-reminder>"
    print(formatted)


if __name__ == "__main__":
    main()
