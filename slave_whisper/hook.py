#!/usr/bin/env python3
"""
Slave Whisper Hook
The Memento Mori system for Claude Code

This hook runs on every UserPromptSubmit, analyzes the previous
Claude response for sycophancy patterns, and injects a "whisper"
reminder if needed.

INTEGRATED with fingerprint_db for unified behavioral tracking.
"""

import json
import sys
import os

# Add our directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Add ~/.claude for fingerprint_db
sys.path.insert(0, os.path.expanduser('~/.claude'))

from detector import analyze_response, should_whisper
from whispers import get_whisper, format_as_system_reminder
from state import load_state, increment_detection
from db import log_detection


DEBUG_LOG = "/tmp/slave_whisper_debug.log"

def debug_log(msg: str):
    """Write debug info to log file"""
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"{msg}\n")
    except:
        pass


def extract_text_from_content(content) -> str:
    """Extract text from Claude's content array"""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)

    return ""


def get_last_assistant_text(transcript_path: str) -> str:
    """Read transcript JSONL and get last assistant text"""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""

    last_assistant_text = ""

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        msg = entry.get("message", {})
                        content = msg.get("content", [])
                        text = extract_text_from_content(content)
                        if text:
                            last_assistant_text = text
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        debug_log(f"Error reading transcript: {e}")

    return last_assistant_text


def extract_phrase_metrics(result) -> dict:
    """Extract phrase metrics from detection result for fingerprint_db.
    
    Maps signal categories to metric types:
    - agreement_phrases: instant_agreement, validation_seeking
    - completion_claims: premature_completion, eager_compliance  
    - hedge_phrases: uncertainty, critical (from rigor_present)
    """
    signals = set(result.signals_found)
    rigor = set(result.rigor_present)
    
    agreement = 0
    if 'instant_agreement' in signals:
        agreement += 1
    if 'validation_seeking' in signals:
        agreement += 1
        
    completions = 0
    if 'premature_completion' in signals:
        completions += 1
    if 'eager_compliance' in signals:
        completions += 1
        
    hedging = 0
    if 'uncertainty' in rigor:
        hedging += 1
    if 'critical' in rigor:
        hedging += 1
    if 'verification' in rigor:
        hedging += 1
        
    return {
        'agreement_phrases': agreement,
        'completion_claims': completions,
        'hedge_phrases': hedging,
        'sycophancy_score': result.score
    }


def write_to_fingerprint_db(session_id: str, phrase_metrics: dict):
    """Write phrase metrics to fingerprint_db for unified analysis."""
    try:
        from fingerprint_db import FingerprintDatabase
        db = FingerprintDatabase()
        db.record_phrase_metrics({
            'session_id': session_id,
            **phrase_metrics
        })
        debug_log(f"Wrote phrase metrics to fingerprint_db: {phrase_metrics}")
    except Exception as e:
        debug_log(f"Failed to write to fingerprint_db: {e}")


def main():
    """Main hook entry point"""
    try:
        # Read input from Claude Code
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        debug_log(f"=== HOOK INVOKED ===")
        debug_log(f"Keys: {list(input_data.keys())}")

        # Get session_id from input
        session_id = input_data.get("session_id", "")

        # Get transcript path from input
        transcript_path = input_data.get("transcript_path", "")
        debug_log(f"Transcript path: {transcript_path}")

        if not transcript_path:
            debug_log("No transcript path, continuing")
            output_continue()
            return

        # Get the last assistant response from JSONL file
        last_response = get_last_assistant_text(transcript_path)
        debug_log(f"Last response length: {len(last_response)}")
        debug_log(f"Last response preview: {last_response[:200]}")

        if not last_response:
            debug_log("No assistant response found, continuing")
            output_continue()
            return

        # Load session state
        state = load_state()
        
        # Use session_id from input or state
        effective_session_id = session_id or state.session_id

        # Analyze the response
        result = analyze_response(last_response, state.detection_count)
        debug_log(f"Analysis: score={result.score}, level={result.level}, signals={result.signals_found}")

        # ALWAYS write phrase metrics to fingerprint_db (even if no whisper triggered)
        phrase_metrics = extract_phrase_metrics(result)
        write_to_fingerprint_db(effective_session_id, phrase_metrics)

        # Should we whisper?
        if should_whisper(result):
            debug_log(f"WHISPER TRIGGERED at level {result.level}")

            # Increment detection count
            state = increment_detection(state, result.signals_found)

            # Get appropriate whisper
            whisper = get_whisper(
                result.level,
                result.signals_found,
                state.detection_count
            )

            # Log to database
            log_detection(
                session_id=state.session_id,
                score=result.score,
                level=result.level,
                signals=result.signals_found,
                rigor_present=result.rigor_present,
                rigor_missing=result.rigor_missing,
                response_snippet=result.response_snippet,
                escalation_count=state.detection_count,
                whisper_injected=True,
            )

            # Output with whisper injection
            output_with_whisper(whisper)
        else:
            debug_log("No sycophancy detected, continuing")
            output_continue()

    except Exception as e:
        # On any error, fail open (don't block Claude Code)
        debug_log(f"ERROR: {e}")
        try:
            with open("/tmp/slave_whisper_error.log", "a") as f:
                import traceback
                f.write(f"{e}\n{traceback.format_exc()}\n")
        except:
            pass
        output_continue()


def output_continue():
    """Output normal continue - just print Success"""
    print("Success")


def output_with_whisper(whisper: str):
    """Output whisper as plain text - Claude Code injects stdout into context"""
    formatted = format_as_system_reminder(whisper)
    print(formatted)


if __name__ == "__main__":
    main()
