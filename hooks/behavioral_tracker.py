#!/usr/bin/env python3
"""
Behavioral Tracker Hook
Runs after each tool use to track patterns.
Updates behavioral fingerprint database.
SESSION-ISOLATED: Each session has its own state file and samples.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.expanduser('~/.claude'))

def get_state_file(session_id: str) -> str:
    """Get session-specific state file path."""
    if session_id:
        # Use first 8 chars of session_id for filename
        short_id = session_id[:8] if len(session_id) > 8 else session_id
        return os.path.expanduser(f'~/.claude/behavioral_state_{short_id}.json')
    return os.path.expanduser('~/.claude/behavioral_state.json')

def load_state(session_id: str) -> dict:
    state_file = get_state_file(session_id)
    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except:
        return {
            'session_id': session_id,
            'turn_number': 0,
            'tool_calls': {
                'read': 0, 'edit': 0, 'write': 0,
                'bash': 0, 'test': 0, 'todo': 0,
                'grep': 0, 'glob': 0
            },
            'completion_claims': 0,
            'unverified_completions': 0,
            'last_tool': None,
            'last_was_verification': False
        }

def save_state(state: dict, session_id: str):
    state_file = get_state_file(session_id)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def main():
    try:
        hook_input = json.load(sys.stdin)
    except:
        print("Success")
        return

    # Extract session_id from hook input (PostToolUse provides this)
    session_id = hook_input.get('session_id', '')
    
    # Debug: write raw input to file (with session info)
    with open('/tmp/posttool_debug.json', 'a') as f:
        f.write(json.dumps({'session': session_id[:8] if session_id else 'none', 'tool': hook_input.get('tool_name', '')}) + '\n')

    # PostToolUse format: tool_name is at top level
    tool_name = hook_input.get('tool_name', '').lower()
    state = load_state(session_id)

    # Track tool call
    if 'read' in tool_name:
        state['tool_calls']['read'] += 1
        state['last_was_verification'] = True
    elif 'edit' in tool_name:
        state['tool_calls']['edit'] += 1
        state['last_was_verification'] = False
    elif 'write' in tool_name:
        state['tool_calls']['write'] += 1
        state['last_was_verification'] = False
    elif 'bash' in tool_name:
        cmd = hook_input.get('tool_input', {}).get('command', '').lower()
        if any(x in cmd for x in ['test', 'pytest', 'npm test', 'cargo test']):
            state['tool_calls']['test'] += 1
            state['last_was_verification'] = True
        elif any(x in cmd for x in ['snippet_patch', '> ', '>> ', 'echo "', "echo '"]):
            state['tool_calls']['edit'] += 1
            state['last_was_verification'] = False
        elif any(x in cmd for x in ['cat ', 'head ', 'tail ', 'grep ', 'ls ', 'find ']):
            state['tool_calls']['read'] += 1
            state['last_was_verification'] = True
        else:
            state['tool_calls']['bash'] += 1
            state['last_was_verification'] = False
    elif 'todo' in tool_name:
        state['tool_calls']['todo'] += 1
        state['last_was_verification'] = False
    elif 'grep' in tool_name:
        state['tool_calls']['grep'] += 1
        state['last_was_verification'] = True
    elif 'glob' in tool_name:
        state['tool_calls']['glob'] += 1
        state['last_was_verification'] = True

    state['last_tool'] = tool_name
    state['session_id'] = session_id
    save_state(state, session_id)

    # Record sample periodically (every 5 tool calls)
    total_calls = sum(state['tool_calls'].values())
    if total_calls > 0 and total_calls % 5 == 0:
        try:
            from fingerprint_db import FingerprintDatabase
            db = FingerprintDatabase()

            tc = state['tool_calls']
            read_like = tc['read'] + tc['grep'] + tc['glob']
            edit_like = tc['edit'] + tc['write']

            ver_ratio = read_like / max(1, edit_like) if edit_like > 0 else 1.0
            prep_ratio = (tc['read'] + tc['todo']) / max(1, tc['edit'] + tc['bash']) if (tc['edit'] + tc['bash']) > 0 else 1.0

            db.record_behavioral_sample({
                'session_id': session_id,
                'turn_number': state['turn_number'],
                'read_calls': tc['read'],
                'edit_calls': tc['edit'],
                'write_calls': tc['write'],
                'bash_calls': tc['bash'],
                'test_calls': tc['test'],
                'todo_calls': tc['todo'],
                'verification_ratio': min(1.0, ver_ratio),
                'preparation_ratio': min(1.0, prep_ratio),
                'unverified_completions': state['unverified_completions'],
                'completion_claims': state['completion_claims'],  # FIX: Was missing!
            })
        except Exception as e:
            pass

    print("Success")

if __name__ == '__main__':
    main()
