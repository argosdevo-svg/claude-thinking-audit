"""
config_server.py — Web UI for mitmproxy context trimmer configuration

Dark cybersec-themed dashboard with per-MCP-server toggles.
Access: http://localhost:18889
"""

import json
import os
import re
import sqlite3
import threading
import time
import importlib.util
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CONFIG_PATH = os.path.expanduser("~/.claude/trimmer_config.json")
DB_PATH = os.path.expanduser("~/.claude/fingerprint.db")
STATS_PATH = os.path.expanduser("~/.claude/trimmer_stats.json")

STATUSLINE_PATH = os.path.expanduser("~/.claude/statusline.py")
_STATUSLINE_MOD = None
_STATUSLINE_LOCK = threading.Lock()
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s or "")

def _load_statusline_module():
    global _STATUSLINE_MOD
    if not os.path.exists(STATUSLINE_PATH):
        return None
    with _STATUSLINE_LOCK:
        if _STATUSLINE_MOD is None:
            spec = importlib.util.spec_from_file_location("statusline_live", STATUSLINE_PATH)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _STATUSLINE_MOD = mod
    return _STATUSLINE_MOD

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
    "block_haiku": True,
    "block_sonnet": False,
    "force_thinking": True,
    "thinking_budget": 31999,
    "force_interleaved": False,
    "statusline_enabled": True,
}

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CLAUDE AUDIT // Proxy Config</title>
<style>
  :root { --bg: #0a0e14; --card: #11151c; --border: #1a1f2e; --text: #c5cdd9;
          --muted: #5c6773; --accent: #39bae6; --green: #7fd962; --red: #ff3333;
          --orange: #ff8f40; --purple: #d2a6ff; --cyan: #95e6cb; --yellow: #e7c547;
          --glow: rgba(57,186,230,0.15); }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
         background: var(--bg); color: var(--text); padding: 24px; max-width: 960px; margin: 0 auto;
         font-size: 15px; line-height: 1.6; }
  ::selection { background: var(--accent); color: var(--bg); }

  /* ═══ HEADER ═══ */
  .header { text-align: center; margin-bottom: 20px; padding: 16px 0; border-bottom: 1px solid var(--border); }
  .header .logo { font-size: 1.5em; letter-spacing: 4px; color: var(--accent); }
  .header .sub { color: var(--muted); font-size: 0.8em; margin-top: 4px; }

  /* ═══ STATS GRID ═══ */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 14px; text-align: center; }
  .stat .num { font-size: 1.8em; font-weight: bold; color: var(--green); font-variant-numeric: tabular-nums; }
  .stat .lbl { font-size: 0.75em; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
  .stat .ico { font-size: 1.2em; display: block; margin-bottom: 2px; }
  .stat.warn .num { color: var(--orange); }
  .stat.crit .num { color: var(--red); }

  /* ═══ CARDS ═══ */
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
          margin-bottom: 16px; overflow: hidden; }
  .card-head { padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex;
               align-items: center; gap: 10px; font-size: 1.1em; color: var(--accent); }
  .card-head .icon { font-size: 1.3em; }
  .card-body { padding: 16px 18px; }

  /* ═══ ROWS ═══ */
  .row { display: flex; align-items: center; justify-content: space-between;
         padding: 10px 0; border-bottom: 1px solid var(--border); }
  .row:last-child { border-bottom: none; }
  .row label { flex: 1; }
  .row .desc { color: var(--muted); font-size: 0.75em; display: block; }

  /* ═══ MCP TOOL GRID ═══ */
  .mcp-grid { display: grid; grid-template-columns: 1fr; gap: 0; }
  .mcp-server { border-bottom: 1px solid var(--border); }
  .mcp-server:last-child { border-bottom: none; }
  .mcp-header { display: flex; align-items: center; justify-content: space-between;
                padding: 10px 0; cursor: pointer; }
  .mcp-header:hover { color: var(--accent); }
  .mcp-name { font-weight: bold; display: flex; align-items: center; gap: 6px; }
  .mcp-name .srv-icon { color: var(--purple); }
  .mcp-badge { font-size: 0.7em; background: var(--border); color: var(--muted);
               padding: 2px 6px; border-radius: 3px; margin-left: 6px; }
  .mcp-badge.on { background: rgba(127,217,98,0.15); color: var(--green); }
  .mcp-badge.off { background: rgba(255,51,51,0.15); color: var(--red); }
  .mcp-methods { padding: 0 0 8px 24px; display: none; }
  .mcp-methods.open { display: block; }
  .mcp-method { font-size: 0.8em; color: var(--muted); padding: 2px 0; }
  .mcp-method::before { content: "|--> "; color: var(--border); }
  .no-tools { color: var(--muted); font-style: italic; padding: 12px 0; text-align: center; }

  /* ═══ TOGGLE ═══ */
  .toggle { position: relative; width: 44px; height: 24px; flex-shrink: 0; }
  .toggle input { position: absolute; inset: 0; opacity: 0; margin: 0; width: 100%; height: 100%;
                  cursor: pointer; z-index: 2; }
  .toggle .sl { position: absolute; inset: 0; background: var(--border); border-radius: 10px;
                cursor: pointer; transition: 0.2s; z-index: 1; }
  .toggle .sl::before { content: ""; position: absolute; width: 18px; height: 18px;
                        left: 3px; bottom: 3px; background: var(--muted); border-radius: 50%;
                        transition: 0.2s; }
  .toggle input:checked + .sl { background: var(--green); }
  .toggle input:checked + .sl::before { transform: translateX(20px); background: var(--bg); }

  /* ═══ INPUTS ═══ */
  input[type=number] { width: 80px; background: var(--bg); border: 1px solid var(--border);
                       color: var(--text); padding: 4px 8px; border-radius: 3px; font-family: inherit;
                       font-size: 0.85em; }
  input[type=range] { width: 120px; accent-color: var(--accent); }
  .val { color: var(--accent); font-family: inherit; min-width: 40px; text-align: right; margin-left: 8px; font-size: 0.85em; }

  /* ═══ SAVE BAR ═══ */
  .save-bar { position: sticky; bottom: 0; background: var(--card); border-top: 2px solid var(--accent);
              padding: 10px; text-align: center; border-radius: 0 0 6px 6px; box-shadow: 0 -4px 20px rgba(0,0,0,0.5); }
  .btn { background: var(--accent); color: var(--bg); border: none; padding: 10px 28px;
         border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.95em; font-family: inherit;
         letter-spacing: 1px; }
  .btn:hover { filter: brightness(1.15); }
  .btn-dim { background: var(--border); color: var(--text); margin-left: 8px; }
  .status { display: inline-block; margin-left: 12px; font-size: 0.8em; }
  .status.ok { color: var(--green); }
  .status.err { color: var(--red); }

  /* ═══ DIVIDER ═══ */
  .divider { text-align: center; color: var(--border); font-size: 0.7em; padding: 4px 0; letter-spacing: 2px; }

  /* ═══ TABS ═══ */
  .tabs { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 2px solid var(--border); }
  .tab { padding: 10px 24px; cursor: pointer; color: var(--muted); font-size: 0.9em; letter-spacing: 1px;
         border-bottom: 2px solid transparent; margin-bottom: -2px; transition: 0.2s; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* ═══ SELECT ═══ */
  select { background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 4px 8px;
           border-radius: 3px; font-family: inherit; font-size: 0.85em; }

  /* ═══ MONITOR TABLE ═══ */
  .mon-table { width: 100%; border-collapse: collapse; font-size: 0.78em; }
  .mon-table th { text-align: left; color: var(--accent); font-weight: normal; padding: 6px 8px;
                  border-bottom: 1px solid var(--border); letter-spacing: 1px; text-transform: uppercase; font-size: 0.85em; }
  .mon-table td { padding: 5px 8px; border-bottom: 1px solid rgba(26,31,46,0.5); white-space: nowrap; }
  .mon-table tr:hover td { background: rgba(57,186,230,0.04); }
  .mon-backend { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 0.85em; letter-spacing: 0.5px; }
  .mon-backend.trainium { background: rgba(127,217,98,0.15); color: var(--green); }
  .mon-backend.tpu { background: rgba(210,166,255,0.15); color: var(--purple); }
  .mon-backend.gpu { background: rgba(255,143,64,0.15); color: var(--orange); }
  .mon-backend.unknown { background: rgba(92,103,115,0.15); color: var(--muted); }
  .mon-rl { display: inline-block; min-width: 36px; text-align: right; }
  .mon-rl.green { color: var(--green); }
  .mon-rl.yellow { color: var(--yellow); }
  .mon-rl.red { color: var(--red); }
  .mon-bar { display: inline-block; width: 50px; height: 8px; background: var(--border); border-radius: 2px; overflow: hidden; vertical-align: middle; margin-left: 4px; }
  .mon-bar-fill { height: 100%; border-radius: 2px; }
  .mon-age { color: var(--muted); font-size: 0.9em; }
  .mon-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .mon-header .btn { font-size: 0.8em; padding: 4px 12px; }
  .mon-count { color: var(--muted); font-size: 0.8em; }
  .mon-auto { color: var(--muted); font-size: 0.75em; margin-left: 12px; }
  .mon-auto.active { color: var(--green); }

  /* ═══ STATUSLINE TAB ═══ */
  .sl-output { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px;
               white-space: pre-wrap; font-size: 0.85em; line-height: 1.4; }
  .sl-metrics th { text-transform: uppercase; font-size: 0.75em; letter-spacing: 1px; }

  /* ═══ ENFORCEMENT BADGE ═══ */
  .enforce-status { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.75em;
                    letter-spacing: 1px; margin-left: 8px; }
  .enforce-status.on { background: rgba(255,51,51,0.15); color: var(--red); }
  .enforce-status.off { background: rgba(127,217,98,0.15); color: var(--green); }
</style>
</head>
<body>

<div class="header">
  <div class="logo">CLAUDE AUDIT <span style="color:#5c6773">//</span> PROXY CONFIG</div>
  <div class="sub">&#x2694;&#xFE0F; context trimmer &#x2022; mcp control &#x2022; model enforcement &#x2694;&#xFE0F;</div>
  <div class="sub" style="margin-top:2px;font-size:0.7em;letter-spacing:6px;color:#1a1f2e">&#x2500;&#x2500;&#x2500; &#x2500;&#x2500;&#x2500; &#x2500;&#x2500;&#x2500;</div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('trimmer')">&#x1F5DC;&#xFE0F; Trimmer</div>
  <div class="tab" onclick="switchTab('enforce')">&#x1F6E1;&#xFE0F; Enforcement</div>
  <div class="tab" onclick="switchTab('statusline')">&#x1F4CA; Statusline</div>
  <div class="tab" onclick="switchTab('monitor')">&#x1F4E1; Monitor</div>
</div>

<div id="tab-trimmer" class="tab-panel active">

<div class="stats" id="stats">
  <div class="stat"><span class="ico">&#x1F4E1;</span><div class="num" id="s-calls">-</div><div class="lbl">API Calls</div></div>
  <div class="stat"><span class="ico">&#x2702;&#xFE0F;</span><div class="num" id="s-tools">-</div><div class="lbl">Tools Stripped</div></div>
  <div class="stat"><span class="ico">&#x1F48E;</span><div class="num" id="s-tok-tools">-</div><div class="lbl">Tok Saved (MCP)</div></div>
  <div class="stat"><span class="ico">&#x1F4E6;</span><div class="num" id="s-trims">-</div><div class="lbl">Msg Trims</div></div>
  <div class="stat"><span class="ico">&#x1F4B0;</span><div class="num" id="s-tok-msgs">-</div><div class="lbl">Tok Saved (Msg)</div></div>
  <div class="stat" id="s-est-wrap"><span class="ico">&#x1F9E0;</span><div class="num" id="s-est">-</div><div class="lbl">Last Input Est</div></div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F6E1;&#xFE0F;</span> Master Controls</div>
  <div class="card-body">
    <div class="row">
      <label>Context Trimmer <span class="desc">master on/off for all trimming</span></label>
      <div class="toggle"><input type="checkbox" id="enabled"><span class="sl"></span></div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F50C;</span> MCP Server Control</div>
  <div class="card-body">
    <div class="row">
      <label>Strip MCP Tools <span class="desc">remove disabled MCP server schemas from requests</span></label>
      <div class="toggle"><input type="checkbox" id="strip_mcp_tools"><span class="sl"></span></div>
    </div>
    <div class="divider">&#x2500;&#x2500; &#x1F50D; discovered servers &#x1F50D; &#x2500;&#x2500;</div>
    <div class="mcp-grid" id="mcp-grid">
      <div class="no-tools" id="no-tools">&#x1F4E1; waiting for first API call to discover tools...</div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F5DC;&#xFE0F;</span> Message Compression</div>
  <div class="card-body">
    <div class="row">
      <label>Trim Old Messages <span class="desc">compress old turns when threshold exceeded</span></label>
      <div class="toggle"><input type="checkbox" id="trim_messages"><span class="sl"></span></div>
    </div>
    <div class="row">
      <label>Threshold <span class="desc">start trimming above this token estimate</span></label>
      <input type="number" id="trim_threshold_tokens" min="50000" max="195000" step="5000">
      <span class="val" id="v-threshold"></span>
    </div>
    <div class="row">
      <label>Keep Recent <span class="desc">never touch the last N messages</span></label>
      <input type="range" id="trim_keep_recent" min="6" max="60" step="2">
      <span class="val" id="v-recent"></span>
    </div>
    <div class="row">
      <label>Max Tool Result <span class="desc">truncate old tool results (chars)</span></label>
      <input type="number" id="trim_max_tool_result_chars" min="100" max="5000" step="100">
    </div>
    <div class="row">
      <label>Max Assistant Text <span class="desc">truncate old assistant text (chars)</span></label>
      <input type="number" id="trim_max_assistant_chars" min="100" max="5000" step="100">
    </div>
    <div class="row">
      <label>Strip Old Thinking <span class="desc">remove thinking blocks from old messages</span></label>
      <div class="toggle"><input type="checkbox" id="strip_old_thinking"><span class="sl"></span></div>
    </div>
  </div>
</div>

</div><!-- /tab-trimmer -->

<div id="tab-enforce" class="tab-panel">

<div class="card">
  <div class="card-head"><span class="icon">&#x1F6AB;</span> Model Blocking</div>
  <div class="card-body">
    <div class="row">
      <label>Block Haiku <span class="desc">reject all Haiku subagent requests (403)</span></label>
      <div class="toggle"><input type="checkbox" id="block_haiku"><span class="sl"></span></div>
    </div>
    <div class="row">
      <label>Block Sonnet <span class="desc">reject all Sonnet subagent requests (403)</span></label>
      <div class="toggle"><input type="checkbox" id="block_sonnet"><span class="sl"></span></div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x2699;</span> Thinking Control</div>
  <div class="card-body">
    <div class="row">
      <label>Force Thinking <span class="desc">inject thinking.type=enabled on all requests</span></label>
      <div class="toggle"><input type="checkbox" id="force_thinking"><span class="sl"></span></div>
    </div>
    <div class="row">
      <label>Thinking Budget <span class="desc">override budget_tokens on every request</span></label>
      <select id="thinking_budget" onchange="updateBudgetLabel()">
        <option value="0">Disabled (0)</option>
        <option value="10000">Basic (10k)</option>
        <option value="16000">Enhanced (16k)</option>
        <option value="31999">Ultra (32k)</option>
        <option value="200000">Interleaved (200k)</option>
      </select>
      <span class="val" id="v-budget"></span>
    </div>
    <div class="row">
      <label>Force Interleaved <span class="desc">inject interleaved-thinking beta header + 200k budget</span></label>
      <div class="toggle"><input type="checkbox" id="force_interleaved"><span class="sl"></span></div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F5A5;</span> Statusline</div>
  <div class="card-body">
    <div class="row">
      <label>Statusline Enabled <span class="desc">show integrated statusline in Claude Code output</span></label>
      <div class="toggle"><input type="checkbox" id="statusline_enabled"><span class="sl"></span></div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F4CA;</span> Current Status</div>
  <div class="card-body" id="enforce-live" style="font-size:0.85em;color:var(--muted);">
    Loading...
  </div>
</div>

</div><!-- /tab-enforce -->

<div id="tab-statusline" class="tab-panel">

<div class="card">
  <div class="card-head">
    <span class="icon">&#x1F4CA;</span> Statusline Snapshot
    <span class="mon-auto" id="sl-auto-status">auto-refresh: off</span>
  </div>
  <div class="card-body">
    <div class="mon-header">
      <div>
        <button class="btn" onclick="loadStatusline()">&#x21BB; Refresh</button>
        <button class="btn btn-dim" id="sl-auto-btn" onclick="toggleStatuslineAuto()">&#x25B6; Auto</button>
        <span class="mon-count" id="sl-updated"></span>
      </div>
    </div>
    <pre class="sl-output" id="sl-output">Click Refresh or switch to this tab to load data</pre>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x2139;&#xFE0F;</span> Metrics Explained</div>
  <div class="card-body">
    <div style="overflow-x:auto;">
      <table class="mon-table sl-metrics">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Explanation</th>
          </tr>
        </thead>
        <tbody id="sl-metrics-body">
          <tr><td colspan="3" style="color:var(--muted);text-align:center;padding:20px;">No data yet</td></tr>
        </tbody>
      </table>
    </div>
    <details style="margin-top:10px;">
      <summary style="cursor:pointer;color:var(--muted);">Raw JSON</summary>
      <pre class="sl-output" id="sl-raw"></pre>
    </details>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="icon">&#x1F4DD;</span> All Metrics (Raw Fields)</div>
  <div class="card-body">
    <div class="mon-count" id="sl-all-count"></div>
    <div style="overflow-x:auto;">
      <table class="mon-table sl-metrics">
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody id="sl-all-body">
          <tr><td colspan="2" style="color:var(--muted);text-align:center;padding:20px;">No data yet</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

</div><!-- /tab-statusline -->

<div id="tab-monitor" class="tab-panel">

<div class="card">
  <div class="card-head">
    <span class="icon">&#x1F4E1;</span> Live Request Monitor
    <span class="mon-auto" id="mon-auto-status">auto-refresh: off</span>
  </div>
  <div class="card-body">
    <div class="mon-header">
      <div>
        <button class="btn" onclick="loadMonitor()">&#x21BB; Refresh</button>
        <button class="btn btn-dim" id="mon-auto-btn" onclick="toggleAutoRefresh()">&#x25B6; Auto</button>
        <span class="mon-count" id="mon-count"></span>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table class="mon-table">
        <thead>
          <tr>
            <th>Age</th>
            <th>Model</th>
            <th>Backend</th>
            <th>ITT</th>
            <th>TTFT</th>
            <th>Tokens</th>
            <th>Think</th>
            <th>5h Quota</th>
            <th>7d Quota</th>
            <th>Status</th>
            <th>Location</th>
          </tr>
        </thead>
        <tbody id="mon-body">
          <tr><td colspan="11" style="color:var(--muted);text-align:center;padding:20px;">Click Refresh or switch to this tab to load data</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

</div><!-- /tab-monitor -->

<div class="save-bar">
  <button class="btn" onclick="save()">&#x2714; SAVE</button>
  <button class="btn btn-dim" onclick="reset()">&#x21BA; RESET</button>
  <span class="status" id="save-status"></span>
</div>

<script>
const FIELDS = ['enabled','strip_mcp_tools','trim_messages','trim_threshold_tokens',
  'trim_keep_recent','trim_max_tool_result_chars','trim_max_assistant_chars','strip_old_thinking',
  'block_haiku','block_sonnet','force_thinking','thinking_budget','force_interleaved','statusline_enabled'];
const TOGGLES = ['enabled','strip_mcp_tools','trim_messages','strip_old_thinking',
  'block_haiku','block_sonnet','force_thinking','force_interleaved','statusline_enabled'];
const SELECTS = ['thinking_budget'];
let mcpDisabled = [];
let mcpServers = {};

const TAB_NAMES = ['trimmer','enforce','statusline','monitor'];
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', i === TAB_NAMES.indexOf(name)));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-'+name));
  if (name === 'monitor') loadMonitor();
  if (name === 'statusline') loadStatusline();
}

function updateBudgetLabel() {
  const sel = document.getElementById('thinking_budget');
  const v = document.getElementById('v-budget');
  if (sel && v) v.textContent = parseInt(sel.value) >= 1000 ? (parseInt(sel.value)/1000).toFixed(0)+'k' : sel.value;
}

function updateEnforceLive(cfg) {
  const el = document.getElementById('enforce-live');
  if (!el) return;
  const bh = cfg.block_haiku ? '<span class="enforce-status on">BLOCKED</span>' : '<span class="enforce-status off">allowed</span>';
  const bs = cfg.block_sonnet ? '<span class="enforce-status on">BLOCKED</span>' : '<span class="enforce-status off">allowed</span>';
  const ft = cfg.force_thinking ? '<span class="enforce-status on">FORCED</span>' : '<span class="enforce-status off">off</span>';
  const budget = cfg.thinking_budget || 0;
  const budgetStr = budget >= 1000 ? (budget/1000).toFixed(0)+'k' : String(budget);
  const fi = cfg.force_interleaved ? '<span class="enforce-status on">ACTIVE</span>' : '<span class="enforce-status off">off</span>';
  const sl = cfg.statusline_enabled ? '<span class="enforce-status off">ON</span>' : '<span class="enforce-status on">OFF</span>';
  el.innerHTML = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
    + '<div>Haiku: '+bh+'</div><div>Sonnet: '+bs+'</div>'
    + '<div>Thinking: '+ft+'</div><div>Budget: <span style="color:var(--cyan)">'+budgetStr+'</span></div>'
    + '<div>Interleaved: '+fi+'</div><div>Statusline: '+sl+'</div>'
    + '</div>';
}

function load() {
  fetch('/api/config').then(r=>r.json()).then(cfg => {
    FIELDS.forEach(f => {
      const el = document.getElementById(f);
      if (!el) return;
      if (TOGGLES.includes(f)) el.checked = !!cfg[f];
      else if (SELECTS.includes(f)) el.value = String(cfg[f]);
      else el.value = cfg[f];
    });
    mcpDisabled = cfg.mcp_disabled || [];
    updateLabels();
    updateBudgetLabel();
    updateEnforceLive(cfg);
  });
  loadStats();
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function fmtNum(v, digits=1) {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toFixed(digits);
}
function fmtMs(v) {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toFixed(1) + 'ms';
}
function fmtPct(v, fractional=true) {
  if (v === null || v === undefined || v === '') return '—';
  let n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (fractional && n <= 1) n = n * 100;
  return n.toFixed(1) + '%';
}
function clip(s, max=180) {
  const str = String(s ?? '');
  return str.length > max ? str.slice(0, max) + '…' : str;
}

function flatten(obj, prefix, out) {
  if (obj === null || obj === undefined) {
    out.push([prefix || '(root)', '—']);
    return;
  }
  if (Array.isArray(obj)) {
    if (obj.length === 0) {
      out.push([prefix || '(root)', '[]']);
      return;
    }
    obj.forEach((v, i) => flatten(v, `${prefix || '(root)'}[${i}]`, out));
    return;
  }
  if (typeof obj === 'object') {
    const keys = Object.keys(obj).sort();
    if (keys.length === 0) {
      out.push([prefix || '(root)', '{}']);
      return;
    }
    keys.forEach(k => flatten(obj[k], prefix ? `${prefix}.${k}` : k, out));
    return;
  }
  out.push([prefix || '(root)', clip(obj)]);
}

function renderStatuslineMetrics(data) {
  const fp = data.fp || {};
  const ex = data.extras || {};
  const q = data.quality || {};
  const cache = data.cache || {};
  const beh = data.behavior || {};
  const sess = data.session || {};
  const rows = [];

  const section = (title) => {
    rows.push('<tr><th colspan="3">'+esc(title)+'</th></tr>');
  };
  const add = (label, value, desc) => {
    rows.push('<tr><td>'+esc(label)+'</td><td>'+esc(value)+'</td><td class="mon-age">'+esc(desc)+'</td></tr>');
  };

  section('Model & Routing');
  add('Model requested', fp.model_requested || '—', 'Model name in API request.');
  add('Model response', fp.model_response || '—', 'Model reported by API response.');
  add('Routing state', fp.routing_state || '—', 'DIRECT or SUBAGENT.');
  add('Is subagent', fp.is_subagent ? 'yes' : 'no', 'Whether this call was a subagent.');
  add('UI model selected', fp.model_ui_selected || '—', 'Model chosen in UI (if captured).');
  add('UI/API mismatch', fp.ui_api_mismatch ? 'YES' : 'no', 'UI-selected model differs from API.');

  section('Backend & Location');
  add('Backend', fp.classified_backend || '—', 'Hardware class inferred from ITT.');
  add('Backend confidence', fmtPct(fp.confidence, false), 'Confidence in backend classification.');
  add('Edge location', fp.cf_edge_location || '—', 'Cloudflare edge code.');

  section('Timing');
  add('ITT mean', fmtMs(fp.itt_mean_ms), 'Average inter-token time.');
  add('ITT std', fmtMs(fp.itt_std_ms), 'Std dev of inter-token time.');
  add('Tokens/sec', fmtNum(fp.tokens_per_sec, 0), 'Output speed.');
  add('TTFT', fmtMs(fp.ttft_ms), 'Time to first token.');
  add('Variance coef', fmtNum(fp.variance_coef, 2), 'Timing variability.');
  add('P50 / P90 / P99', `${fmtNum(fp.itt_p50_ms,0)} / ${fmtNum(fp.itt_p90_ms,0)} / ${fmtNum(fp.itt_p99_ms,0)} ms`, 'ITT percentiles.');
  add('Envoy upstream', fmtMs(fp.envoy_upstream_time_ms), 'Server-side latency (if available).');
  add('Stop reason', fp.stop_reason || '—', 'Why generation stopped.');

  section('Thinking');
  add('Thinking tier', fp.thinking_budget_tier || '—', 'Budget tier label.');
  add('Budget requested', fp.thinking_budget_requested ?? '—', 'Thinking budget tokens requested.');
  add('Utilization', fmtPct(fp.thinking_utilization, false), 'Percent of budget used.');
  add('Thinking tokens used', fp.thinking_tokens_used ?? '—', 'Raw thinking tokens (if captured).');
  add('Thinking duration', fmtNum((fp.thinking_duration_ms||0)/1000,1)+'s', 'Time spent thinking.');
  add('Text duration', fmtNum((fp.text_duration_ms||0)/1000,1)+'s', 'Time spent generating text.');

  section('Cache & Context');
  add('Cache efficiency (call)', fmtPct(fp.cache_efficiency, false), 'Cache hit rate for this call.');
  add('Cache session avg', fmtPct(ex.cache_session_avg, false), 'Average cache hit rate this session.');
  add('Cache read tokens', fp.cache_read_tokens ?? '—', 'Tokens served from cache.');
  add('Cache create tokens', fp.cache_creation_tokens ?? '—', 'Tokens added to cache.');
  add('Context API %', fmtPct(ex.context_api_pct, false), 'True context % (cache+input).');
  add('Context CC %', fmtPct(ex.context_cc_pct, false), 'Claude Code UI % (if recorded).');
  add('Context mismatch', ex.context_mismatch ?? '—', 'Difference between API and CC %.');

  section('Rate Limits');
  add('5h utilization', fmtPct(fp.rl_5h_utilization, true), '5h rolling utilization.');
  add('7d utilization', fmtPct(fp.rl_7d_utilization, true), '7d rolling utilization.');
  add('Status', fp.rl_overall_status || '—', 'allowed / warning / rate_limited.');
  add('Binding window', fp.rl_binding_window || '—', 'Which window is binding.');
  add('Fallback %', fmtPct(fp.rl_fallback_pct, false), 'Throughput when rate-limited.');

  section('Quality');
  add('Quality label', q.label || '—', 'Quality classification.');
  add('Score', q.score ?? '—', 'Composite quality score.');
  add('Timing ratio', fmtNum(q.timing_ratio,2), 'Relative timing vs baseline.');
  add('Variance ratio', fmtNum(q.variance_ratio,2), 'Relative variance vs baseline.');
  add('TPS ratio', fmtNum(q.tps_ratio,2), 'Relative throughput vs baseline.');
  add('Trend', q.trend_label || q.trend || '—', 'Recent quality trend.');

  section('Behavior');
  add('Behavior signature', beh.signature || '—', 'Behavior classification.');
  add('Verifier score', beh.combined_scores ? (beh.combined_scores.verifier ?? '—') : '—', 'Verification tendency.');
  add('Sycophant score', beh.combined_scores ? (beh.combined_scores.sycophant ?? '—') : '—', 'Sycophancy tendency.');
  add('Completer score', beh.combined_scores ? (beh.combined_scores.completer ?? '—') : '—', 'Completion bias.');
  add('Trending', beh.trending || '—', 'Behavior trend.');

  section('Session');
  add('Session ID', sess.session_id || '—', 'Current session identifier.');
  add('Samples', sess.sample_count ?? '—', 'Samples in session stats.');
  add('Backend switches', sess.backend_switches ?? '—', 'Number of backend switches.');
  add('Subagent calls', sess.subagent_count ?? '—', 'Subagent call count.');

  const body = document.getElementById('sl-metrics-body');
  body.innerHTML = rows.join('');
}

function renderAllMetrics(data) {
  const out = [];
  flatten(data, '', out);
  const body = document.getElementById('sl-all-body');
  const rows = out.map(([k,v]) => '<tr><td>'+esc(k)+'</td><td>'+esc(v)+'</td></tr>');
  body.innerHTML = rows.join('');
  const count = document.getElementById('sl-all-count');
  if (count) count.textContent = out.length + ' fields';
}

let slAutoInterval = null;
function loadStatusline() {
  fetch('/api/statusline').then(r=>r.json()).then(data => {
    const out = document.getElementById('sl-output');
    out.textContent = data.lines || 'No fingerprint data yet';
    const raw = document.getElementById('sl-raw');
    if (raw) raw.textContent = JSON.stringify(data, null, 2);
    renderStatuslineMetrics(data);
    renderAllMetrics(data);
    const ts = document.getElementById('sl-updated');
    if (ts) ts.textContent = data.generated_at ? ('updated ' + new Date(data.generated_at*1000).toLocaleTimeString()) : '';
  }).catch(e => {
    document.getElementById('sl-output').textContent = 'Error: ' + e.message;
  });
}

function toggleStatuslineAuto() {
  const btn = document.getElementById('sl-auto-btn');
  const st = document.getElementById('sl-auto-status');
  if (slAutoInterval) {
    clearInterval(slAutoInterval);
    slAutoInterval = null;
    btn.textContent = '\u25B6 Auto';
    st.textContent = 'auto-refresh: off';
    st.className = 'mon-auto';
  } else {
    loadStatusline();
    slAutoInterval = setInterval(loadStatusline, 3000);
    btn.textContent = '\u25A0 Stop';
    st.textContent = 'auto-refresh: 3s';
    st.className = 'mon-auto active';
  }
}

function loadStats() {
  fetch('/api/stats').then(r=>r.json()).then(s => {
    document.getElementById('s-calls').textContent = s.calls_processed || 0;
    document.getElementById('s-tools').textContent = s.tools_stripped_total || 0;
    document.getElementById('s-tok-tools').textContent = fmt(s.tokens_saved_tools||0);
    document.getElementById('s-trims').textContent = s.messages_trimmed_total || 0;
    document.getElementById('s-tok-msgs').textContent = fmt(s.tokens_saved_messages||0);
    const est = s.last_input_tokens_est||0;
    document.getElementById('s-est').textContent = fmt(est);
    const wrap = document.getElementById('s-est-wrap');
    wrap.className = 'stat' + (est > 150000 ? ' crit' : est > 100000 ? ' warn' : '');

    // Render MCP servers
    mcpServers = s.mcp_servers || {};
    renderMcpGrid(mcpServers, s.builtin_tools || []);
  }).catch(()=>{});
}

function fmt(n) { return n >= 1000 ? (n/1000).toFixed(1)+'k' : String(n); }

function renderMcpGrid(servers, builtins) {
  const grid = document.getElementById('mcp-grid');
  const keys = Object.keys(servers);
  if (keys.length === 0) {
    grid.innerHTML = '<div class="no-tools">waiting for first API call to discover tools...</div>';
    return;
  }

  let html = '';
  keys.sort().forEach(srv => {
    const methods = servers[srv] || [];
    const disabled = mcpDisabled.includes(srv);
    const badge = disabled
      ? '<span class="mcp-badge off">STRIPPED</span>'
      : '<span class="mcp-badge on">ACTIVE</span>';
    const icon = disabled ? '&#x1F6AB;' : '&#x1F50C;';

    html += '<div class="mcp-server">';
    html += '<div class="mcp-header" onclick="toggleMethods(this)">';
    html += '<div class="mcp-name"><span class="srv-icon">'+icon+'</span> mcp__'+srv+' '+badge+'</div>';
    html += '<div class="toggle" onclick="event.stopPropagation()">';
    html += '<input type="checkbox" '+(disabled?'':'checked')+' onchange="toggleServer(\''+srv+'\',this.checked)">';
    html += '<span class="sl"></span></div>';
    html += '</div>';
    html += '<div class="mcp-methods">';
    methods.forEach(m => {
      html += '<div class="mcp-method">'+m+'</div>';
    });
    html += '</div></div>';
  });

  grid.innerHTML = html;
}

function toggleMethods(header) {
  const methods = header.nextElementSibling;
  methods.classList.toggle('open');
}

function toggleServer(srv, enabled) {
  if (enabled) {
    mcpDisabled = mcpDisabled.filter(s => s !== srv);
  } else {
    if (!mcpDisabled.includes(srv)) mcpDisabled.push(srv);
  }
  // Re-render immediately for visual feedback
  renderMcpGrid(mcpServers, []);
}

function updateLabels() {
  const th = document.getElementById('trim_threshold_tokens');
  document.getElementById('v-threshold').textContent = th ? (th.value/1000).toFixed(0)+'k' : '';
  const rc = document.getElementById('trim_keep_recent');
  document.getElementById('v-recent').textContent = rc ? rc.value : '';
}

function getConfig() {
  const cfg = {};
  FIELDS.forEach(f => {
    const el = document.getElementById(f);
    if (!el) return;
    if (TOGGLES.includes(f)) cfg[f] = el.checked;
    else if (SELECTS.includes(f)) cfg[f] = parseInt(el.value);
    else cfg[f] = parseInt(el.value);
  });
  cfg.mcp_disabled = mcpDisabled;
  return cfg;
}

function save() {
  const st = document.getElementById('save-status');
  const cfg = getConfig();
  fetch('/api/config', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(cfg)
  }).then(r => {
    st.textContent = r.ok ? '[+] saved' : '[x] error';
    st.className = 'status ' + (r.ok ? 'ok' : 'err');
    setTimeout(()=>st.textContent='', 2000);
    if (r.ok) updateEnforceLive(cfg);
  });
}

function reset() {
  fetch('/api/reset', {method:'POST'}).then(()=>{mcpDisabled=[];load();});
}

document.getElementById('trim_keep_recent').addEventListener('input', updateLabels);
document.getElementById('trim_threshold_tokens').addEventListener('input', updateLabels);
setInterval(loadStats, 5000);
load();

// ═══ MONITOR ═══
let monAutoInterval = null;

function rlColor(pct) {
  if (pct >= 80) return 'red';
  if (pct >= 30) return 'yellow';
  return 'green';
}

function rlBar(pct, color) {
  const w = Math.min(pct, 100);
  const c = color === 'red' ? 'var(--red)' : color === 'yellow' ? 'var(--yellow)' : 'var(--green)';
  return '<span class="mon-rl '+color+'">'+pct.toFixed(1)+'%</span>'
    + '<div class="mon-bar"><div class="mon-bar-fill" style="width:'+w+'%;background:'+c+'"></div></div>';
}

function backendBadge(b) {
  if (!b) return '<span class="mon-backend unknown">—</span>';
  const lower = b.toLowerCase();
  let cls = 'unknown';
  if (lower.includes('trainium')) cls = 'trainium';
  else if (lower.includes('tpu')) cls = 'tpu';
  else if (lower.includes('gpu')) cls = 'gpu';
  return '<span class="mon-backend '+cls+'">'+b+'</span>';
}

function timeAgo(ts) {
  const d = new Date(ts);
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 60) return sec+'s';
  if (sec < 3600) return Math.floor(sec/60)+'m';
  if (sec < 86400) return (sec/3600).toFixed(1)+'h';
  return (sec/86400).toFixed(1)+'d';
}

function loadMonitor() {
  fetch('/api/monitor?n=50').then(r=>r.json()).then(rows => {
    const body = document.getElementById('mon-body');
    const count = document.getElementById('mon-count');
    count.textContent = rows.length + ' samples';
    if (rows.length === 0) {
      body.innerHTML = '<tr><td colspan="11" style="color:var(--muted);text-align:center;padding:20px;">No data yet</td></tr>';
      return;
    }
    let html = '';
    rows.forEach(r => {
      const model = (r.model_requested || '').replace('claude-','').replace('-20251101','').replace('-20250514','');
      const itt = r.itt_mean_ms ? r.itt_mean_ms.toFixed(1)+'ms' : '—';
      const ttft = r.ttft_ms ? (r.ttft_ms/1000).toFixed(1)+'s' : '—';
      const tokens = (r.output_tokens||0);
      const think = r.thinking_enabled ? (r.thinking_budget_tier||'on') : '—';
      const rl5 = r.rl_5h_utilization ? r.rl_5h_utilization * 100 : null;
      const rl7 = r.rl_7d_utilization ? r.rl_7d_utilization * 100 : null;
      const rl5html = rl5 !== null ? rlBar(rl5, rlColor(rl5)) : '<span style="color:var(--muted)">—</span>';
      const rl7html = rl7 !== null ? rlBar(rl7, rlColor(rl7)) : '<span style="color:var(--muted)">—</span>';
      const status = r.rl_overall_status || '—';
      const loc = r.cf_edge_location || r.location || '—';
      html += '<tr>'
        + '<td class="mon-age">'+timeAgo(r.timestamp)+'</td>'
        + '<td>'+model+'</td>'
        + '<td>'+backendBadge(r.classified_backend)+'</td>'
        + '<td>'+itt+'</td>'
        + '<td>'+ttft+'</td>'
        + '<td>'+tokens+'</td>'
        + '<td>'+think+'</td>'
        + '<td>'+rl5html+'</td>'
        + '<td>'+rl7html+'</td>'
        + '<td>'+status+'</td>'
        + '<td>'+loc+'</td>'
        + '</tr>';
    });
    body.innerHTML = html;
  }).catch(e => {
    document.getElementById('mon-body').innerHTML = '<tr><td colspan="11" style="color:var(--red);">Error: '+e.message+'</td></tr>';
  });
}

function toggleAutoRefresh() {
  const btn = document.getElementById('mon-auto-btn');
  const st = document.getElementById('mon-auto-status');
  if (monAutoInterval) {
    clearInterval(monAutoInterval);
    monAutoInterval = null;
    btn.textContent = '\u25B6 Auto';
    st.textContent = 'auto-refresh: off';
    st.className = 'mon-auto';
  } else {
    loadMonitor();
    monAutoInterval = setInterval(loadMonitor, 3000);
    btn.textContent = '\u25A0 Stop';
    st.textContent = 'auto-refresh: 3s';
    st.className = 'mon-auto active';
  }
}
</script>
</body>
</html>"""


class ConfigHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        if self.path == "/api/config":
            try:
                with open(CONFIG_PATH) as f:
                    cfg = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(cfg)
                cfg = merged
            except (FileNotFoundError, json.JSONDecodeError):
                cfg = dict(DEFAULT_CONFIG)
            self._send_json(cfg)
        elif self.path == "/api/stats":
            try:
                with open(STATS_PATH) as f:
                    stats = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                stats = {}
            self._send_json(stats)
        elif self.path == "/api/statusline":
            try:
                mod = _load_statusline_module()
                if mod is None:
                    self._send_json({"error": "statusline.py not found"}, status=500)
                    return
                fp = mod.get_fingerprint_status(model_filter=None) or {}
                extras = mod.get_extras(model_filter=None) or {}
                quality = mod.get_quality_status() or {}
                cache = mod.get_cache_analysis() or {}
                behavior = mod.get_behavioral_status() or {}
                session = mod.get_session_stats() or {}
                subagents = mod.get_subagent_counts() or {}
                anomalies = mod.get_anomalies() or []
                experiment = mod.get_experiment_phase() or {}
                bimodal = mod.get_bimodal_analysis() or {}
                sycophancy = mod.get_sycophancy_status() or {}
                if fp:
                    lines = mod.format_statusline_expanded({}, fp, extras)
                else:
                    lines = "No fingerprint data yet."
                payload = {
                    "lines": _strip_ansi(lines),
                    "fp": fp,
                    "extras": extras,
                    "quality": quality,
                    "cache": cache,
                    "behavior": behavior,
                    "session": session,
                    "subagents": subagents,
                    "anomalies": anomalies,
                    "experiment": experiment,
                    "bimodal": bimodal,
                    "sycophancy": sycophancy,
                    "generated_at": time.time(),
                }
                self._send_json(payload)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
        elif self.path.startswith("/api/monitor"):
            try:
                qs = parse_qs(urlparse(self.path).query)
                n = min(int(qs.get("n", [50])[0]), 200)
                conn = sqlite3.connect(DB_PATH, timeout=2)
                conn.row_factory = sqlite3.Row
                cols = [
                    "id", "timestamp", "model_requested", "classified_backend",
                    "itt_mean_ms", "ttft_ms", "output_tokens", "thinking_enabled",
                    "thinking_budget_tier", "cf_edge_location",
                    "rl_5h_utilization", "rl_7d_utilization", "rl_overall_status",
                    "rl_binding_window", "rl_fallback_pct"
                ]
                sql = f"SELECT {','.join(cols)} FROM samples ORDER BY id DESC LIMIT ?"
                rows = conn.execute(sql, (n,)).fetchall()
                conn.close()
                self._send_json([dict(r) for r in rows])
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
        elif self.path in ("/", "/index.html"):
            self._send_html(HTML_PAGE)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/config":
            try:
                data = json.loads(self._read_body())
                merged = dict(DEFAULT_CONFIG)
                merged.update(data)
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, "w") as f:
                    json.dump(merged, f, indent=2)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/api/reset":
            try:
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_config_server(port=18889, daemon=True):
    server = HTTPServer(("127.0.0.1", port), ConfigHandler)
    t = threading.Thread(target=server.serve_forever, daemon=daemon)
    t.start()
    return server


if __name__ == "__main__":
    port = int(os.environ.get("CONFIG_PORT", "18889"))
    print(f"[*] Claude Audit proxy config: http://localhost:{port}")
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    server = HTTPServer(("127.0.0.1", port), ConfigHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
