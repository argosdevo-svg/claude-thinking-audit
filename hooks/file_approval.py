#!/usr/bin/env python3
"""
File Operation Approval Hook (PreToolUse)

Prompts for approval before sensitive file operations.
Inspired by claudemon but implemented as native Claude Code hook.

Sensitive Paths:
- System: /etc/*, /usr/*, /var/*
- Security: ~/.ssh/*, ~/.gnupg/*, ~/.aws/*
- Credentials: **/.env, **/secrets*, **/*_key*

Dangerous Commands:
- rm -rf
- git push --force
- chmod 777
- dd if=
"""

import json
import sys
import os
import re
from pathlib import Path
from fnmatch import fnmatch

# Sensitive path patterns
SENSITIVE_PATHS = [
    # System directories
    "/etc/*",
    "/usr/*",
    "/var/*",
    "/boot/*",
    "/root/*",
    
    # Security directories  
    "~/.ssh/*",
    "~/.gnupg/*",
    "~/.aws/*",
    "~/.config/gcloud/*",
    "~/.kube/*",
    
    # Credential files (anywhere)
    "**/.env",
    "**/.env.*",
    "**/secrets*",
    "**/*_key*",
    "**/*_secret*",
    "**/credentials*",
    "**/*.pem",
    "**/*.key",
    "**/id_rsa*",
    "**/id_ed25519*",
]

# Dangerous bash command patterns
DANGEROUS_COMMANDS = [
    # rm commands - ALL require approval
    (r"\brm\s+-rf\b", "rm -rf can recursively delete files"),
    (r"\brm\s+-fr\b", "rm -fr can recursively delete files"),
    (r"\brm\s+-f\b", "rm -f force deletes without confirmation"),
    (r"\brm\s+(-[a-z]*r[a-z]*\s+)?/", "rm targeting root paths"),
    (r"\brm\s+(-[a-z]*r[a-z]*\s+)?~", "rm targeting home directory"),
    (r"\brm\s+.*\*", "rm with wildcard can delete unexpected files"),
    (r"\bsudo\s+rm\b", "sudo rm is dangerous"),
    
    # git destructive commands
    (r"git\s+push\s+.*--force", "Force push can destroy remote history"),
    (r"git\s+push\s+-f\b", "Force push can destroy remote history"),
    (r"git\s+reset\s+--hard", "Hard reset loses uncommitted changes"),
    (r"git\s+reset\s+HEAD~", "Reset HEAD~ can lose commits"),
    (r"git\s+clean\s+-f", "git clean -f deletes untracked files"),
    (r"git\s+checkout\s+--\s+\.", "git checkout -- . discards all changes"),
    (r"git\s+stash\s+drop", "git stash drop loses stashed changes"),
    (r"git\s+branch\s+-D", "git branch -D force deletes branch"),
    (r"git\s+rebase\s+.*--force", "Force rebase can rewrite history"),
    
    # System dangerous
    (r"\bchmod\s+777\b", "World-writable permissions are insecure"),
    (r"\bchmod\s+-R\s+777\b", "Recursive 777 is very dangerous"),
    (r"\bdd\s+if=", "dd can overwrite disks"),
    (r">\s*/dev/sd[a-z]", "Direct write to disk device"),
    (r"\bmkfs\b", "Filesystem format can destroy data"),
    (r"curl.*\|\s*(ba)?sh", "Piping curl to shell is dangerous"),
    (r"wget.*\|\s*(ba)?sh", "Piping wget to shell is dangerous"),
    (r"^\s*(?:sudo\s+)?shutdown\b", "System shutdown command"),
    (r"^\s*(?:sudo\s+)?reboot\b", "System reboot command"),
    (r"\binit\s+0", "System halt"),
]

# Whitelist - allowed despite matching sensitive patterns
WHITELIST = [
    # Reading is generally safe
    "Read",
    "Glob", 
    "Grep",
]


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path."""
    return os.path.expanduser(os.path.expandvars(path))


def matches_sensitive_path(file_path: str) -> tuple:
    """
    Check if path matches any sensitive pattern.
    Returns (matches: bool, pattern: str or None)
    """
    if not file_path:
        return False, None
    
    expanded = expand_path(file_path)
    
    for pattern in SENSITIVE_PATHS:
        expanded_pattern = expand_path(pattern)
        
        # Handle ** glob patterns
        if "**" in pattern:
            # Simple ** matching - check if file matches the suffix
            suffix = pattern.replace("**/", "")
            if fnmatch(os.path.basename(expanded), suffix):
                return True, pattern
            if fnmatch(expanded, expanded_pattern):
                return True, pattern
        else:
            if fnmatch(expanded, expanded_pattern):
                return True, pattern
    
    return False, None


def check_dangerous_command(command: str) -> tuple:
    """
    Check if bash command matches dangerous patterns.
    Returns (dangerous: bool, reason: str or None)
    """
    if not command:
        return False, None
    
    for pattern, reason in DANGEROUS_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason
    
    return False, None


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except:
        # If can't parse input, allow through
        print("Approved")
        return
    
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    
    # Read-only tools are always allowed
    if tool_name in WHITELIST:
        print("Approved")
        return
    
    # Check file paths for Write/Edit operations
    if tool_name in ["Write", "Edit", "MultiEdit", "NotebookEdit"]:
        file_path = tool_input.get("file_path", "")
        
        is_sensitive, pattern = matches_sensitive_path(file_path)
        if is_sensitive:
            result = {
                "decision": "block",
                "reason": f"⚠️ SENSITIVE PATH DETECTED\n\nPath: {file_path}\nMatched pattern: {pattern}\n\nThis operation requires manual approval.\nRe-run with explicit user confirmation to proceed."
            }
            print(json.dumps(result))
            return
    
    # Check bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        
        # Check for dangerous commands
        is_dangerous, reason = check_dangerous_command(command)
        if is_dangerous:
            result = {
                "decision": "block",
                "reason": f"⚠️ DANGEROUS COMMAND DETECTED\n\nCommand: {command[:100]}...\nReason: {reason}\n\nThis operation requires manual approval."
            }
            print(json.dumps(result))
            return
        
        # Check for file operations in bash targeting sensitive paths
        # Look for common patterns: cat, echo >, rm, cp, mv to sensitive paths
        file_ops = re.findall(r'(?:cat|echo|rm|cp|mv|>+)\s+([^\s|&;]+)', command)
        for file_path in file_ops:
            is_sensitive, pattern = matches_sensitive_path(file_path)
            if is_sensitive:
                result = {
                    "decision": "block",  
                    "reason": f"⚠️ BASH OPERATION ON SENSITIVE PATH\n\nCommand: {command[:100]}...\nPath: {file_path}\nMatched pattern: {pattern}\n\nThis operation requires manual approval."
                }
                print(json.dumps(result))
                return
    
    # All checks passed
    print("Approved")


if __name__ == "__main__":
    main()
