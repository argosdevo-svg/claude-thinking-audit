"""
context_trimmer.py — mitmproxy addon for proxy-side context management

Strips MCP tool schemas and compresses old conversation messages before
forwarding to Anthropic API. Controlled via shared config file written
by config_server.py.

Loaded via: mitmdump -s context_trimmer.py
"""

import json
import os
import time
from mitmproxy import http, ctx

CONFIG_PATH = os.path.expanduser("~/.claude/trimmer_config.json")
STATS_PATH = os.path.expanduser("~/.claude/trimmer_stats.json")

CHARS_PER_TOKEN = 4

DEFAULT_CONFIG = {
    "enabled": True,
    "strip_mcp_tools": True,
    "mcp_disabled": [],
    "trim_messages": True,
    "trim_threshold_tokens": 140000,
    "trim_keep_recent": 20,
    "trim_max_tool_result_chars": 700,
    "trim_max_assistant_chars": 500,
    "strip_old_thinking": True,
}

_stats = {
    "session_start": 0.0,
    "calls_processed": 0,
    "tools_stripped_total": 0,
    "tools_stripped_last": 0,
    "tokens_saved_tools": 0,
    "messages_trimmed_total": 0,
    "messages_trimmed_last": 0,
    "tokens_saved_messages": 0,
    "last_input_tokens_est": 0,
    "mcp_servers": {},
    "builtin_tools": [],
}

_config_cache = None
_config_mtime = 0.0


def _load_config() -> dict:
    global _config_cache, _config_mtime
    try:
        st = os.stat(CONFIG_PATH)
        if st.st_mtime != _config_mtime:
            with open(CONFIG_PATH) as f:
                _config_cache = json.load(f)
            _config_mtime = st.st_mtime
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        if _config_cache is None:
            _config_cache = dict(DEFAULT_CONFIG)
    return _config_cache or dict(DEFAULT_CONFIG)


def _save_stats():
    try:
        with open(STATS_PATH, "w") as f:
            json.dump(_stats, f)
    except OSError:
        pass


def _estimate_tokens(obj) -> int:
    return len(json.dumps(obj, separators=(",", ":"))) // CHARS_PER_TOKEN


def _is_mcp_tool(tool: dict) -> bool:
    return tool.get("name", "").startswith("mcp__")


def _mcp_server_name(tool: dict) -> str:
    parts = tool.get("name", "").split("__")
    return parts[1] if len(parts) >= 3 else ""


def _strip_mcp_tools(body: dict, config: dict) -> int:
    tools = body.get("tools")
    if not tools or not isinstance(tools, list):
        return 0

    disabled = set(config.get("mcp_disabled", []))
    kept = []
    stripped = 0

    for tool in tools:
        name = tool.get("name", "")
        if _is_mcp_tool(tool):
            server = _mcp_server_name(tool)
            method = name.split("__", 2)[2] if name.count("__") >= 2 else name
            # Track discovered MCP tools
            if server not in _stats["mcp_servers"]:
                _stats["mcp_servers"][server] = []
            if method not in _stats["mcp_servers"][server]:
                _stats["mcp_servers"][server].append(method)
            # Strip if server is disabled
            if disabled and server in disabled:
                stripped += 1
            else:
                kept.append(tool)
        else:
            kept.append(tool)
            if name and name not in _stats["builtin_tools"]:
                _stats["builtin_tools"].append(name)

    if stripped > 0:
        body["tools"] = kept
    return stripped


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars * 2 // 3
    tail = max_chars // 3
    cut = len(text) - head - tail
    return text[:head] + f"\n[...trimmed {cut} chars...]\n" + text[-tail:]


def _trim_content_block(block, max_chars: int):
    if isinstance(block, str):
        return _truncate_text(block, max_chars)

    if not isinstance(block, dict):
        return block

    btype = block.get("type", "")

    if btype == "thinking":
        return None

    if btype == "text" and "text" in block:
        text = block["text"]
        if len(text) > max_chars:
            block = dict(block)
            block["text"] = _truncate_text(text, max_chars)

    elif btype == "tool_result":
        if "content" in block:
            block = dict(block)
            c = block["content"]
            if isinstance(c, str):
                block["content"] = _truncate_text(c, max_chars)
            elif isinstance(c, list):
                block["content"] = [b for b in (_trim_content_block(x, max_chars) for x in c) if b is not None]

    return block


def _trim_messages(body: dict, config: dict) -> int:
    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        return 0

    total_est = _estimate_tokens(body)
    threshold = config.get("trim_threshold_tokens", 140000)
    if total_est < threshold:
        return 0

    keep_recent = config.get("trim_keep_recent", 20)
    max_tool_chars = config.get("trim_max_tool_result_chars", 700)
    max_asst_chars = config.get("trim_max_assistant_chars", 500)
    strip_thinking = config.get("strip_old_thinking", True)

    if len(messages) <= keep_recent:
        return 0

    old_end = len(messages) - keep_recent
    tokens_before = _estimate_tokens(messages[:old_end])

    for i in range(old_end):
        msg = messages[i]
        content = msg.get("content")
        if content is None:
            continue

        if isinstance(content, str):
            if msg.get("role") == "assistant" and len(content) > max_asst_chars:
                msg["content"] = _truncate_text(content, max_asst_chars)
            continue

        if isinstance(content, list):
            new_content = []
            for block in content:
                if not isinstance(block, dict):
                    new_content.append(block)
                    continue

                btype = block.get("type", "")

                if btype == "thinking" and strip_thinking:
                    continue

                if btype == "tool_result":
                    trimmed = _trim_content_block(block, max_tool_chars)
                    if trimmed is not None:
                        new_content.append(trimmed)
                    continue

                if btype == "text" and msg.get("role") == "assistant":
                    trimmed = _trim_content_block(block, max_asst_chars)
                    if trimmed is not None:
                        new_content.append(trimmed)
                    continue

                new_content.append(block)

            msg["content"] = new_content

    tokens_after = _estimate_tokens(messages[:old_end])
    return max(0, tokens_before - tokens_after)


def request(flow: http.HTTPFlow) -> None:
    if "anthropic.com" not in flow.request.host:
        return
    if "/v1/messages" not in flow.request.path:
        return
    if not flow.request.content:
        return

    config = _load_config()
    if not config.get("enabled", True):
        return

    try:
        body = json.loads(flow.request.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    modified = False
    tools_stripped = 0
    tokens_saved_msgs = 0

    if config.get("strip_mcp_tools", True):
        tools_stripped = _strip_mcp_tools(body, config)
        if tools_stripped > 0:
            modified = True
            _stats["tools_stripped_total"] += tools_stripped
            _stats["tools_stripped_last"] = tools_stripped
            est_saved = tools_stripped * 800
            _stats["tokens_saved_tools"] += est_saved
            ctx.log.info(f"[TRIM] Stripped {tools_stripped} MCP tools (~{est_saved} tok)")

    if config.get("trim_messages", True):
        tokens_saved_msgs = _trim_messages(body, config)
        if tokens_saved_msgs > 0:
            modified = True
            _stats["messages_trimmed_total"] += 1
            _stats["messages_trimmed_last"] = tokens_saved_msgs
            _stats["tokens_saved_messages"] += tokens_saved_msgs
            ctx.log.info(f"[TRIM] Compressed old messages (~{tokens_saved_msgs} tok saved)")

    if modified:
        flow.request.content = json.dumps(body).encode("utf-8")
        total_saved = (tools_stripped * 800) + tokens_saved_msgs
        ctx.log.warn(f"[TRIM] Total saved this call: ~{total_saved} tok")

    _stats["calls_processed"] += 1
    _stats["last_input_tokens_est"] = _estimate_tokens(body)

    if _stats["calls_processed"] % 5 == 0:
        _save_stats()


def load(loader):
    _stats["session_start"] = time.time()
    ctx.log.info("[TRIM] Context trimmer loaded")
    _load_config()
    # Start config web UI server in background thread
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config_server import start_config_server
        port = int(os.environ.get("CONFIG_PORT", "18889"))
        start_config_server(port=port, daemon=True)
        ctx.log.info(f"[TRIM] Config UI: http://localhost:{port}")
    except Exception as e:
        ctx.log.warn(f"[TRIM] Config server failed to start: {e}")


def done():
    _save_stats()
    ctx.log.info(f"[TRIM] Final stats: {json.dumps(_stats)}")
