#!/usr/bin/env python3
"""
Antigravity Profile Collector & Builder
Parses transcripts in ~/.gemini/antigravity/brain/*/
Generates profile_data.json and webview/profile.html
"""

import os
import json
import glob
import base64
from datetime import datetime, timedelta

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, 'assets')
    webview_dir = os.path.join(root_dir, 'webview')
    os.makedirs(webview_dir, exist_ok=True)

    # 1. Parse Transcripts
    brain_dir = os.path.expanduser('~/.gemini/antigravity/brain')
    transcripts = glob.glob(os.path.join(brain_dir, '*', '.system_generated', 'logs', 'transcript.jsonl'))
    print(f"Found {len(transcripts)} conversation sessions to parse.")

    day_tokens = {}
    total_tokens = 0
    peak_tokens = 0
    longest_active_sec = 0
    total_chats = len(transcripts)

    commands_run = 0
    files_modified = 0

    mcp_usage = {
        '@blender': 0,
        '@playwright': 0,
        '@after-effects': 0,
        '@stitch': 0,
        '@netlify': 0,
        '@sequential-thinking': 0,
        '@github': 0
    }

    for path in transcripts:
        session_tokens = 0
        first_time = None
        last_time = None
        prev_ts = None
        session_active_sec = 0

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line)
                except Exception:
                    continue

                ts_str = step.get('created_at')
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        if first_time is None:
                            first_time = ts
                        last_time = ts
                        if prev_ts is not None:
                            diff = (ts - prev_ts).total_seconds()
                            if 0 < diff < 1800:
                                session_active_sec += diff
                        prev_ts = ts
                        d_str = ts.strftime('%Y-%m-%d')
                    except Exception:
                        d_str = '2026-08-31'
                else:
                    d_str = '2026-08-31'

                c_len = len(step.get('content', '') or '')
                th_len = len(step.get('thinking', '') or '')
                tc_len = len(str(step.get('tool_calls', '') or ''))
                approx_tokens = max(100, int((c_len + th_len + tc_len) / 3.5))

                session_tokens += approx_tokens
                total_tokens += approx_tokens
                day_tokens[d_str] = day_tokens.get(d_str, 0) + approx_tokens

                # Track Tool Calls
                for call in step.get('tool_calls', []):
                    name = call.get('name', '') if isinstance(call, dict) else str(call)
                    if 'command' in name:
                        commands_run += 1
                    if 'file' in name or 'write' in name or 'replace' in name:
                        files_modified += 1
                    for mcp_key in mcp_usage:
                        clean_k = mcp_key.replace('@', '')
                        if clean_k in name.lower():
                            mcp_usage[mcp_key] += 1

        if session_tokens > peak_tokens:
            peak_tokens = session_tokens
        if session_active_sec > longest_active_sec:
            longest_active_sec = session_active_sec

    # 2. Build 52-week Heatmap Grid
    today = datetime(2026, 8, 31)
    start_date = today - timedelta(days=52 * 7)
    while start_date.weekday() != 6:
        start_date -= timedelta(days=1)

    weeks = []
    curr = start_date
    cumulative = 0

    while curr <= today or len(weeks) < 52:
        week = []
        for _ in range(7):
            d_str = curr.strftime('%Y-%m-%d')
            t_count = day_tokens.get(d_str, 0)
            if curr <= today:
                cumulative += t_count

            if t_count == 0:
                lvl = 0
            elif t_count < 10000:
                lvl = 1
            elif t_count < 40000:
                lvl = 2
            elif t_count < 80000:
                lvl = 3
            else:
                lvl = 4

            week.append({
                'date': d_str,
                'tokens': t_count,
                'level': lvl,
                'cumulative': cumulative
            })
            curr += timedelta(days=1)
        weeks.append(week)
        if len(weeks) == 52:
            break

    # Formatters
    def fmt_num(n):
        if n >= 1000000:
            return f"{n/1000000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    hours = int(longest_active_sec // 3600)
    minutes = int((longest_active_sec % 3600) // 60)
    longest_chat_fmt = f"{hours}h {minutes:02d}m" if hours > 0 else f"{minutes}m"

    plugin_list = [
        {'name': '@blender', 'runs': mcp_usage['@blender'], 'icon': '🎨'},
        {'name': '@playwright', 'runs': mcp_usage['@playwright'], 'icon': '🌐'},
        {'name': '@after-effects', 'runs': mcp_usage['@after-effects'], 'icon': '✨'},
        {'name': '@stitch', 'runs': mcp_usage['@stitch'], 'icon': '🧵'},
        {'name': '@netlify', 'runs': mcp_usage['@netlify'], 'icon': '⚡'},
        {'name': '@sequential-thinking', 'runs': mcp_usage['@sequential-thinking'], 'icon': '🧠'},
        {'name': '@github', 'runs': mcp_usage['@github'], 'icon': '🐙'}
    ]
    plugin_list = [p for p in plugin_list if p['runs'] > 0]
    plugin_list.sort(key=lambda x: x['runs'], reverse=True)

    profile_data = {
        'user': {
            'name': 'gelios_g',
            'handle': '@gelios_g',
            'badge': 'Free',
            'initials': 'GER',
            'avatarColor': '#e67e22'
        },
        'metrics': {
            'lifetimeTokens': total_tokens,
            'lifetimeTokensFormatted': fmt_num(total_tokens),
            'peakTokens': peak_tokens,
            'peakTokensFormatted': fmt_num(peak_tokens),
            'longestChatSeconds': longest_active_sec,
            'longestChatFormatted': longest_chat_fmt,
            'currentStreak': 8,
            'longestStreak': 8
        },
        'insights': {
            'mcpConnected': f"{len(plugin_list) + 1} servers",
            'skillsInstalled': '52 skills',
            'commandsRun': f"{commands_run} commands",
            'filesModified': f"{files_modified} files",
            'totalChats': f"{total_chats} chats"
        },
        'plugins': plugin_list,
        'heatmap': {
            'weeks': weeks,
            'shareWeeks': weeks[-26:]
        }
    }

    # Save JSON
    out_json = os.path.join(webview_dir, 'profile_data.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    print(f"Updated {out_json}")

if __name__ == '__main__':
    main()
