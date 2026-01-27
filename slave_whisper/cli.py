#!/usr/bin/env python3
"""
Slave Whisper CLI
View detection stats, test patterns, and manage state
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Add our directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detector import analyze_response
from whispers import get_whisper, format_as_system_reminder
from state import load_state, reset_state, get_session_id
from db import (
    get_recent_detections, get_session_stats, get_signal_frequency,
    get_rolling_stats, get_cross_session_escalation, search_detections,
    export_for_memory
)


def cmd_stats(args):
    """Show detection statistics"""
    stats = get_session_stats()

    print("\n=== Slave Whisper Statistics ===\n")
    print(f"Total detections: {stats.get('total_detections', 0)}")
    print(f"Average score: {stats.get('avg_score', 0)}")
    print(f"Max score: {stats.get('max_score', 0)}")
    print(f"Whispers sent: {stats.get('whispers_sent', 0)}")

    print("\n--- Signal Frequency ---")
    freq = get_signal_frequency()
    for signal, count in list(freq.items())[:10]:
        print(f"  {signal}: {count}")

    print("\n--- Current Session ---")
    state = load_state()
    print(f"Session ID: {state.session_id}")
    print(f"Detection count: {state.detection_count}")
    print(f"Recent signals: {', '.join(state.signals_history[-5:]) if state.signals_history else 'none'}")


def cmd_recent(args):
    """Show recent detections"""
    detections = get_recent_detections(args.limit)

    print(f"\n=== Last {len(detections)} Detections ===\n")

    for d in detections:
        ts = datetime.fromtimestamp(d['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        signals = json.loads(d['signals']) if d['signals'] else []

        print(f"[{ts}] Score: {d['score']:.2f} | Level: {d['level']}")
        print(f"  Signals: {', '.join(signals)}")
        print(f"  Snippet: {d['response_snippet'][:100]}...")
        print()


def cmd_test(args):
    """Test detection on a sample response"""
    if args.text:
        text = args.text
    else:
        print("Enter response text (Ctrl+D when done):")
        text = sys.stdin.read()

    result = analyze_response(text)

    print("\n=== Detection Result ===\n")
    print(f"Score: {result.score:.2f}")
    print(f"Level: {result.level}")
    print(f"Signals found: {', '.join(result.signals_found) or 'none'}")
    print(f"Rigor present: {', '.join(result.rigor_present) or 'none'}")
    print(f"Rigor missing: {', '.join(result.rigor_missing) or 'none'}")

    if result.level != "none":
        print("\n--- Whisper that would be injected ---")
        whisper = get_whisper(result.level, result.signals_found, 1)
        print(format_as_system_reminder(whisper))


def cmd_reset(args):
    """Reset session state"""
    state = reset_state()
    print(f"Session state reset. New session ID: {state.session_id}")


def cmd_whisper(args):
    """Generate a sample whisper"""
    whisper = get_whisper(args.level, ["test_signal"], args.count)
    print(format_as_system_reminder(whisper))


def cmd_memory(args):
    """Show cross-session memory stats"""
    print("\n=== Cross-Session Memory ===\n")

    for hours in [1, 6, 24]:
        stats = get_rolling_stats(hours)
        print(f"--- Last {hours}h ---")
        print(f"  Detections: {stats['total_detections']}")
        print(f"  Avg score: {stats['avg_score']}")
        print(f"  Max score: {stats['max_score']}")
        if stats['signals']:
            top = list(stats['signals'].items())[:3]
            print(f"  Top signals: {', '.join(f'{k}:{v}' for k,v in top)}")
        print()

    escalation = get_cross_session_escalation()
    print(f"Cross-session escalation level: {escalation}")
    if escalation >= 4:
        print("  → New sessions start at PROTOCOL level")
    elif escalation >= 2:
        print("  → New sessions start at WARNING level")
    elif escalation >= 1:
        print("  → New sessions start elevated")
    else:
        print("  → New sessions start clean")


def cmd_search(args):
    """Search detection history"""
    results = search_detections(args.query, args.limit)

    print(f"\n=== Search: '{args.query}' ({len(results)} results) ===\n")

    for d in results:
        ts = datetime.fromtimestamp(d['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        signals = json.loads(d['signals']) if d['signals'] else []

        print(f"[{ts}] Score: {d['score']:.2f} | Level: {d['level']}")
        print(f"  Signals: {', '.join(signals)}")
        print(f"  Snippet: {d['response_snippet'][:100]}...")
        print()


def cmd_export(args):
    """Export for memory system integration"""
    print(export_for_memory())


def main():
    parser = argparse.ArgumentParser(
        description="Slave Whisper CLI - The Memento Mori System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slave_whisper stats              # Show detection statistics
  slave_whisper recent             # Show recent detections
  slave_whisper test "Done!"       # Test detection on text
  slave_whisper reset              # Reset session state
  slave_whisper whisper warning    # Generate sample whisper
  slave_whisper memory             # Cross-session memory stats
  slave_whisper search "pattern"   # Search detection history
  slave_whisper export             # Export for memory system
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show detection statistics")
    p_stats.set_defaults(func=cmd_stats)

    # recent
    p_recent = subparsers.add_parser("recent", help="Show recent detections")
    p_recent.add_argument("-n", "--limit", type=int, default=10, help="Number of detections")
    p_recent.set_defaults(func=cmd_recent)

    # test
    p_test = subparsers.add_parser("test", help="Test detection on text")
    p_test.add_argument("text", nargs="?", help="Text to analyze (or stdin)")
    p_test.set_defaults(func=cmd_test)

    # reset
    p_reset = subparsers.add_parser("reset", help="Reset session state")
    p_reset.set_defaults(func=cmd_reset)

    # whisper
    p_whisper = subparsers.add_parser("whisper", help="Generate sample whisper")
    p_whisper.add_argument("level", choices=["gentle", "warning", "protocol", "halt"])
    p_whisper.add_argument("-c", "--count", type=int, default=1, help="Escalation count")
    p_whisper.set_defaults(func=cmd_whisper)

    # memory
    p_memory = subparsers.add_parser("memory", help="Show cross-session memory stats")
    p_memory.set_defaults(func=cmd_memory)

    # search
    p_search = subparsers.add_parser("search", help="Search detection history")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    p_search.set_defaults(func=cmd_search)

    # export
    p_export = subparsers.add_parser("export", help="Export for memory system")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
