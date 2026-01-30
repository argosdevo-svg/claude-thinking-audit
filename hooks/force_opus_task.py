#!/usr/bin/env python3
"""
PreToolUse hook: Force all Task subagents to use Opus.
Blocks haiku/sonnet with authoritative retry instruction.
Proxy also blocks (BLOCK_NON_OPUS=1) as second safety net.
"""
import json
import sys

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})
        model = tool_input.get("model", "").lower()

        if model in ("haiku", "sonnet"):
            # Extract the original call details for retry
            desc = tool_input.get("description", "")
            prompt = tool_input.get("prompt", "")[:200]
            agent = tool_input.get("subagent_type", "general-purpose")

            print(json.dumps({
                "decision": "block",
                "reason": (
                    f"REJECTED: model=\"{model}\" is FORBIDDEN. OPUS ONLY.\n"
                    f"\n"
                    f"DO NOT fall back to inline execution. RETRY THIS EXACT CALL with model=\"opus\":\n"
                    f"\n"
                    f"  Task(\n"
                    f"    description=\"{desc}\",\n"
                    f"    prompt=\"...same prompt...\",\n"
                    f"    subagent_type=\"{agent}\",\n"
                    f"    model=\"opus\"\n"
                    f"  )\n"
                    f"\n"
                    f"This is a MANDATORY retry. Do NOT proceed without launching the subagent as opus."
                )
            }))
        else:
            print(json.dumps({"decision": "approve"}))
    except Exception as e:
        print(json.dumps({"decision": "approve"}))

if __name__ == "__main__":
    main()
