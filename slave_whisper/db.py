"""
Slave Whisper Database
SQLite logging for detection events
"""

import sqlite3
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from config import DB_FILE


def init_db() -> None:
    """Initialize database schema"""
    Path(DB_FILE).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            session_id TEXT,
            score REAL,
            level TEXT,
            signals TEXT,
            rigor_present TEXT,
            rigor_missing TEXT,
            response_snippet TEXT,
            escalation_count INTEGER,
            whisper_injected INTEGER
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session ON detections(session_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp)
    """)

    conn.commit()
    conn.close()


def log_detection(
    session_id: str,
    score: float,
    level: str,
    signals: List[str],
    rigor_present: List[str],
    rigor_missing: List[str],
    response_snippet: str,
    escalation_count: int,
    whisper_injected: bool,
) -> str:
    """Log a detection event to database"""
    init_db()

    detection_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO detections (
            id, timestamp, session_id, score, level, signals,
            rigor_present, rigor_missing, response_snippet,
            escalation_count, whisper_injected
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        detection_id,
        time.time(),
        session_id,
        score,
        level,
        json.dumps(signals),
        json.dumps(rigor_present),
        json.dumps(rigor_missing),
        response_snippet,
        escalation_count,
        1 if whisper_injected else 0,
    ))

    conn.commit()
    conn.close()

    return detection_id


def get_recent_detections(limit: int = 20) -> List[Dict]:
    """Get recent detection events"""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM detections
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_session_stats(session_id: Optional[str] = None) -> Dict:
    """Get statistics for a session or all sessions"""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if session_id:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(score) as avg_score,
                MAX(score) as max_score,
                SUM(whisper_injected) as whispers_sent
            FROM detections
            WHERE session_id = ?
        """, (session_id,))
    else:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(score) as avg_score,
                MAX(score) as max_score,
                SUM(whisper_injected) as whispers_sent,
                COUNT(DISTINCT session_id) as sessions
            FROM detections
        """)

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_detections": row[0] or 0,
            "avg_score": round(row[1] or 0, 3),
            "max_score": round(row[2] or 0, 3),
            "whispers_sent": row[3] or 0,
        }
    return {}


def get_signal_frequency() -> Dict[str, int]:
    """Get frequency of each signal type"""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT signals FROM detections")
    rows = cursor.fetchall()
    conn.close()

    freq = {}
    for row in rows:
        try:
            signals = json.loads(row[0])
            for signal in signals:
                freq[signal] = freq.get(signal, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    return dict(sorted(freq.items(), key=lambda x: -x[1]))


def get_rolling_stats(hours: int = 24) -> Dict:
    """Get rolling stats over last N hours for cross-session memory"""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cutoff = time.time() - (hours * 3600)

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(score) as avg_score,
            MAX(score) as max_score,
            SUM(whisper_injected) as whispers_sent
        FROM detections
        WHERE timestamp > ?
    """, (cutoff,))

    row = cursor.fetchone()

    # Get signal frequency in window
    cursor.execute("""
        SELECT signals FROM detections WHERE timestamp > ?
    """, (cutoff,))
    signal_rows = cursor.fetchall()

    conn.close()

    freq = {}
    for r in signal_rows:
        try:
            signals = json.loads(r[0])
            for signal in signals:
                freq[signal] = freq.get(signal, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "hours": hours,
        "total_detections": row[0] or 0,
        "avg_score": round(row[1] or 0, 3),
        "max_score": round(row[2] or 0, 3),
        "whispers_sent": row[3] or 0,
        "signals": dict(sorted(freq.items(), key=lambda x: -x[1])),
    }


def get_cross_session_escalation() -> int:
    """
    Calculate escalation level based on historical patterns.
    Returns a starting escalation count for new sessions.
    """
    stats = get_rolling_stats(hours=24)

    # If high sycophancy in last 24h, start with elevated escalation
    if stats["total_detections"] >= 10:
        return 4  # Start at protocol level
    elif stats["total_detections"] >= 5:
        return 2  # Start at warning level
    elif stats["total_detections"] >= 2:
        return 1  # Start elevated
    return 0


def search_detections(query: str, limit: int = 20) -> List[Dict]:
    """Search detection snippets for a query string"""
    init_db()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM detections
        WHERE response_snippet LIKE ? OR signals LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def export_for_memory() -> str:
    """Export detection summary for memory system integration"""
    stats = get_rolling_stats(hours=24)
    all_stats = get_session_stats()

    lines = [
        "=== Slave Whisper Memory Export ===",
        f"Total all-time detections: {all_stats.get('total_detections', 0)}",
        f"Last 24h detections: {stats['total_detections']}",
        f"Last 24h avg score: {stats['avg_score']}",
        f"Last 24h max score: {stats['max_score']}",
        f"Last 24h whispers sent: {stats['whispers_sent']}",
        "",
        "Signal patterns (24h):",
    ]
    for signal, count in stats.get("signals", {}).items():
        lines.append(f"  - {signal}: {count}")

    return "\n".join(lines)
