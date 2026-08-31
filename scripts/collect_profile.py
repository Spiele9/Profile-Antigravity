#!/usr/bin/env python3
"""
Antigravity Profile Collector & Builder
Parses transcripts in ~/.gemini/antigravity/brain/*/
Generates webview/profile_data.json and webview/profile.html
"""

import os
import json
import glob
from datetime import datetime, timedelta

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    webview_dir = os.path.join(root_dir, 'webview')
    os.makedirs(webview_dir, exist_ok=True)

    # 1. Locate and parse transcripts
    brain_dir = os.path.expanduser('~/.gemini/antigravity/brain')
    transcripts = glob.glob(os.path.join(brain_dir, '*', '.system_generated', 'logs', 'transcript.jsonl'))
    print(f"Found {len(transcripts)} conversation sessions in {brain_dir}")

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
                        if prev_ts is not None:
                            diff = (ts - prev_ts).total_seconds()
                            if 0 < diff < 1800:
                                session_active_sec += diff
                        prev_ts = ts
                        d_str = ts.strftime('%Y-%m-%d')
                    except Exception:
                        d_str = datetime.now().strftime('%Y-%m-%d')
                else:
                    d_str = datetime.now().strftime('%Y-%m-%d')

                c_len = len(step.get('content', '') or '')
                th_len = len(step.get('thinking', '') or '')
                tc_len = len(str(step.get('tool_calls', '') or ''))
                approx_tokens = max(80, int((c_len + th_len + tc_len) / 3.5))

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

    # 2. Build 52-week Heatmap Grid aligned to today
    today = datetime.now()
    start_date = today - timedelta(days=52 * 7)
    while start_date.weekday() != 6: # Sunday
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

    # Calculate actual consecutive streaks
    sorted_days = sorted([d for d, t in day_tokens.items() if t > 0])
    current_streak = 0
    longest_streak = 0
    curr_run = 0

    if sorted_days:
        # Longest streak calculation
        prev_date = None
        for d_s in sorted_days:
            d_obj = datetime.strptime(d_s, '%Y-%m-%d').date()
            if prev_date is None or d_obj == prev_date + timedelta(days=1):
                curr_run += 1
            elif d_obj > prev_date + timedelta(days=1):
                curr_run = 1
            if curr_run > longest_streak:
                longest_streak = curr_run
            prev_date = d_obj

        # Current streak from today backwards
        check_date = today.date()
        while check_date.strftime('%Y-%m-%d') in day_tokens and day_tokens[check_date.strftime('%Y-%m-%d')] > 0:
            current_streak += 1
            check_date -= timedelta(days=1)
        if current_streak == 0 and (today.date() - timedelta(days=1)).strftime('%Y-%m-%d') in day_tokens:
            check_date = today.date() - timedelta(days=1)
            while check_date.strftime('%Y-%m-%d') in day_tokens and day_tokens[check_date.strftime('%Y-%m-%d')] > 0:
                current_streak += 1
                check_date -= timedelta(days=1)

    # Defaults if no logs exist
    if total_chats == 0:
        current_streak = 0
        longest_streak = 0

    # Format numbers
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

    # Preserve user customization if already set
    out_json = os.path.join(webview_dir, 'profile_data.json')
    user_info = {
        'name': 'gelios_g',
        'handle': '@gelios_g',
        'badge': 'Free',
        'initials': 'GER',
        'avatarColor': '#e67e22'
    }
    if os.path.exists(out_json):
        try:
            with open(out_json, 'r') as f_prev:
                prev_data = json.load(f_prev)
                if 'user' in prev_data:
                    user_info = prev_data['user']
        except Exception:
            pass

    profile_data = {
        'user': user_info,
        'metrics': {
            'lifetimeTokens': total_tokens,
            'lifetimeTokensFormatted': fmt_num(total_tokens),
            'peakTokens': peak_tokens,
            'peakTokensFormatted': fmt_num(peak_tokens),
            'longestChatSeconds': longest_active_sec,
            'longestChatFormatted': longest_chat_fmt,
            'currentStreak': max(1, current_streak) if total_chats > 0 else 0,
            'longestStreak': max(1, longest_streak) if total_chats > 0 else 0
        },
        'insights': {
            'mcpConnected': f"{max(1, len(plugin_list))} servers" if total_chats > 0 else "0 servers",
            'skillsInstalled': '52 skills',
            'commandsRun': f"{commands_run} commands",
            'filesModified': f"{files_modified} files",
            'totalChats': f"{total_chats} chats"
        },
        'plugins': plugin_list if plugin_list else [{'name': '@antigravity', 'runs': 1, 'icon': '▲'}],
        'heatmap': {
            'weeks': weeks,
            'shareWeeks': weeks[-26:]
        }
    }

    # Save JSON
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {out_json}")

if __name__ == '__main__':
    main()
