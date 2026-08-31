#!/usr/bin/env python3
"""
Antigravity Profile Collector & Builder
Parses transcripts in ~/.gemini/antigravity/brain/*/
Generates webview/profile_data.json and updates webview/profile.html
"""

import os
import re
import json
import glob
from datetime import datetime, timedelta

def format_num(n):
    if n >= 1000000:
        return f"{n/1000000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return f"{n:,}"

def format_date_str(d_str):
    try:
        dt = datetime.strptime(d_str, '%Y-%m-%d')
        return dt.strftime('%b %d, %Y')
    except Exception:
        return d_str

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    webview_dir = os.path.join(root_dir, 'webview')
    os.makedirs(webview_dir, exist_ok=True)

    # 1. Locate and parse transcripts
    brain_dir = os.path.expanduser('~/.gemini/antigravity/brain')
    transcripts = glob.glob(os.path.join(brain_dir, '*', '.system_generated', 'logs', 'transcript.jsonl'))
    print(f"Found {len(transcripts)} conversation sessions in {brain_dir}")

    day_tokens = {}
    longest_active_sec = 0
    total_chats = len(transcripts)

    commands_run = 0
    files_modified = 0

    mcp_counts = {}

    mcp_icons = {
        '@blender': '🎨',
        '@playwright': '🌐',
        '@after-effects': '✨',
        '@stitch': '🧵',
        '@netlify': '⚡',
        '@sequential-thinking': '🧠',
        '@github': '🐙',
        '@better-icons': '💎',
        '@chrome-devtools': '🔍',
        '@chrome-devtools-mcp': '🔍',
        '@context7': '📚',
        '@firebase': '🔥',
        '@firebase-mcp-server': '🔥'
    }

    for path in transcripts:
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

                day_tokens[d_str] = day_tokens.get(d_str, 0) + approx_tokens

                # Track Tool Calls
                for call in step.get('tool_calls', []):
                    if isinstance(call, dict):
                        name = call.get('name', '')
                        args = call.get('args', {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                pass
                        sname = args.get('ServerName', '') if isinstance(args, dict) else ''
                    else:
                        name = str(call)
                        sname = ''

                    sname_clean = sname.strip('"\'') if isinstance(sname, str) else ''

                    if 'command' in name:
                        commands_run += 1
                    if any(x in name for x in ['file', 'write', 'replace', 'create']):
                        files_modified += 1

                    # Count MCP tool usage
                    if name == 'call_mcp_tool' and sname_clean:
                        key = f"@{sname_clean}"
                        mcp_counts[key] = mcp_counts.get(key, 0) + 1
                    elif name.startswith('mcp_'):
                        parts = name.split('_')
                        if len(parts) > 1:
                            key = f"@{parts[1]}"
                            mcp_counts[key] = mcp_counts.get(key, 0) + 1
                    else:
                        for known_mcp in mcp_icons:
                            clean_k = known_mcp.replace('@', '')
                            if clean_k in name.lower():
                                mcp_counts[known_mcp] = mcp_counts.get(known_mcp, 0) + 1
                                break

        if session_active_sec > longest_active_sec:
            longest_active_sec = session_active_sec

    total_tokens = sum(day_tokens.values())
    peak_tokens = max(day_tokens.values()) if day_tokens else 0

    # Count Connected MCP servers and Installed Skills
    mcp_dir = os.path.expanduser('~/.gemini/antigravity/mcp')
    connected_mcp_count = len([d for d in glob.glob(os.path.join(mcp_dir, '*')) if os.path.isdir(d)]) if os.path.exists(mcp_dir) else len(mcp_counts)
    if connected_mcp_count == 0 and mcp_counts:
        connected_mcp_count = len(mcp_counts)

    skills_paths = glob.glob(os.path.expanduser('~/.gemini/config/plugins/**/SKILL.md'), recursive=True) + \
                   glob.glob(os.path.expanduser('~/.gemini/antigravity/builtin/skills/**/SKILL.md'), recursive=True)
    skills_installed_count = len(set(skills_paths)) if skills_paths else 52

    # 2. Build 52-week Heatmap Grid ending on current week (Saturday)
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    today_date = today.date()

    end_date = today_date
    while end_date.weekday() != 5: # Saturday
        end_date += timedelta(days=1)

    start_date = end_date - timedelta(days=52 * 7 - 1)

    weeks = []
    curr = start_date
    cumulative = 0

    while curr <= end_date:
        week = []
        for _ in range(7):
            d_str = curr.strftime('%Y-%m-%d')
            t_count = day_tokens.get(d_str, 0)
            in_range = curr <= today_date
            if in_range:
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
                'formattedDate': format_date_str(d_str),
                'tokens': t_count,
                'formattedTokens': format_num(t_count) if t_count > 0 else '0',
                'level': lvl,
                'cumulative': cumulative,
                'formattedCumulative': format_num(cumulative) if cumulative > 0 else '0',
                'inRange': in_range
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

        check_date = today_date
        while check_date.strftime('%Y-%m-%d') in day_tokens and day_tokens[check_date.strftime('%Y-%m-%d')] > 0:
            current_streak += 1
            check_date -= timedelta(days=1)
        if current_streak == 0 and (today_date - timedelta(days=1)).strftime('%Y-%m-%d') in day_tokens:
            check_date = today_date - timedelta(days=1)
            while check_date.strftime('%Y-%m-%d') in day_tokens and day_tokens[check_date.strftime('%Y-%m-%d')] > 0:
                current_streak += 1
                check_date -= timedelta(days=1)

    if total_chats == 0:
        current_streak = 0
        longest_streak = 0

    hours = int(longest_active_sec // 3600)
    minutes = int((longest_active_sec % 3600) // 60)
    longest_chat_fmt = f"{hours}h {minutes:02d}m" if hours > 0 else f"{minutes}m"

    plugin_list = []
    for k, runs in mcp_counts.items():
        if runs > 0:
            plugin_list.append({
                'name': k,
                'runs': runs,
                'icon': mcp_icons.get(k, '🔌')
            })
    plugin_list.sort(key=lambda x: x['runs'], reverse=True)
    if not plugin_list:
        plugin_list = [{'name': '@antigravity', 'runs': 1, 'icon': '▲'}]

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
            'lifetimeTokensFormatted': format_num(total_tokens),
            'peakTokens': peak_tokens,
            'peakTokensFormatted': format_num(peak_tokens),
            'longestChatSeconds': longest_active_sec,
            'longestChatFormatted': longest_chat_fmt,
            'currentStreak': max(1, current_streak) if total_chats > 0 else 0,
            'longestStreak': max(1, longest_streak) if total_chats > 0 else 0
        },
        'insights': {
            'mcpConnected': f"{connected_mcp_count} servers",
            'skillsInstalled': f"{skills_installed_count} skills",
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
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {out_json}")

    # Update profile.html inline data & TODAY_STR
    html_path = os.path.join(webview_dir, 'profile.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f_html:
            html_content = f_html.read()

        json_str = json.dumps(profile_data, ensure_ascii=False)
        html_content = re.sub(
            r'const profileData = \{.*?\};',
            f'const profileData = {json_str};',
            html_content,
            flags=re.DOTALL
        )
        html_content = re.sub(
            r'const TODAY_STR = ".*?";',
            f'const TODAY_STR = "{today_str}";',
            html_content
        )

        with open(html_path, 'w', encoding='utf-8') as f_html:
            f_html.write(html_content)
        print(f"Successfully updated embedded profile data in {html_path}")

if __name__ == '__main__':
    main()
