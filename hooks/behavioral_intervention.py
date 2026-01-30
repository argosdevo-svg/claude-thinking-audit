#!/usr/bin/env python3
"""
Behavioral Intervention Hook
Injects dynamic system-reminders based on detected behavioral patterns.
Runs on UserPromptSubmit.

INTEGRATED with realignment module for active re-alignment using RLHF dynamics.
"""

import json
import sys
import os

sys.path.insert(0, os.path.expanduser('~/.claude'))
sys.path.insert(0, os.path.expanduser('~/.claude/realignment'))

# State file for tracking offense counts per session
STATE_FILE = os.path.expanduser('~/.claude/intervention_state.json')


def load_state() -> dict:
    """Load intervention state from file."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {
        'offense_counts': {},
        'last_signature': None,
        'session_history': []
    }


def save_state(state: dict):
    """Save intervention state to file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def get_intervention_v1(signature: str, confidence: float, history: dict) -> str:
    """Legacy intervention - basic memento mori messages."""
    if signature == 'VERIFIER' or confidence < 50:
        return None

    unverified = history.get('unverified_claims', 0)

    if signature == 'COMPLETER':
        return f"""<system-reminder>
<memento-mori level="warning">
BEHAVIORAL PATTERN DETECTED: COMPLETER ({confidence:.0f}% confidence)
You have made {unverified} unverified completion claims.

BEFORE your next "Done/Fixed/Complete" statement:
1. Show actual command output or test result
2. Verify the change works as expected
3. If uncertain, say "Let me verify" instead
</memento-mori>
</system-reminder>"""

    elif signature == 'SYCOPHANT':
        return f"""<system-reminder>
<memento-mori level="warning">
BEHAVIORAL PATTERN DETECTED: SYCOPHANT ({confidence:.0f}% confidence)

BEFORE agreeing with the user:
1. Verify the claim is actually correct
2. If uncertain, investigate first
3. It is OK to disagree or express uncertainty
</memento-mori>
</system-reminder>"""

    elif signature == 'THEATER':
        return f"""<system-reminder>
<memento-mori level="warning">
BEHAVIORAL PATTERN DETECTED: PREPARATION THEATER ({confidence:.0f}% confidence)

STOP preparing and START executing:
1. You have enough context - make the change
2. Reduce file reads, increase actual edits
3. Test after editing, not endless reading
</memento-mori>
</system-reminder>"""

    return None


def get_intervention_v2(signature: str, confidence: float, offense_count: int, session_history: list) -> str:
    """Advanced intervention using realignment module with RLHF dynamics."""
    if signature == 'VERIFIER' or signature == 'UNKNOWN' or confidence < 50:
        return None
        
    try:
        from realignment import generate_full_injection
        injection = generate_full_injection(
            signature=signature,
            confidence=confidence,
            offense_count=offense_count,
            session_history=session_history
        )
        if injection:
            return f"""<system-reminder>
{injection}
</system-reminder>"""
    except Exception as e:
        # Fallback to v1 if realignment fails
        pass
        
    return None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except:
        print("Success")
        return

    # Get session_id from input
    session_id = hook_input.get('session_id', 'default')

    try:
        from fingerprint_db import FingerprintDatabase
        db = FingerprintDatabase()
        
        # Use combined signature (tool + text signals)
        try:
            behavior = db.get_combined_signature(session_id)
        except Exception:
            # Fallback to tool-only signature
            behavior = db.get_behavioral_signature(session_id)
            
        signature = behavior.get('signature', 'UNKNOWN')
        confidence = behavior.get('confidence', 0)
        
        # Load state and track offense counts
        state = load_state()
        offense_counts = state.get('offense_counts', {})
        session_history = state.get('session_history', [])
        
        # Get offense count for this signature
        offense_count = offense_counts.get(signature, 0)
        
        # Try v2 (realignment) first, fallback to v1
        intervention = get_intervention_v2(signature, confidence, offense_count, session_history)
        if not intervention:
            intervention = get_intervention_v1(signature, confidence, behavior)
        
        if intervention:
            # Increment offense count
            offense_counts[signature] = offense_count + 1
            session_history.append({
                'signature': signature,
                'confidence': confidence,
                'offense_count': offense_count + 1
            })
            # Keep only last 20 entries
            session_history = session_history[-20:]
            
            state['offense_counts'] = offense_counts
            state['last_signature'] = signature
            state['session_history'] = session_history
            save_state(state)
            
            print(intervention)
        else:
            print("Success")
            
    except Exception as e:
        print("Success")

if __name__ == '__main__':
    main()
