# Antigravity Profile & Token Dashboard

A profile dashboard and activity visualizer for Google Antigravity, inspired by Codex.

It reads your local conversation history from Antigravity, calculates total tokens, streaks, session duration, and tool usage, and shows everything in a 52-week activity heatmap.

## Features

- **Activity Heatmap:** 52-week activity grid with Daily, Weekly, and Cumulative views.
- **Share Card:** Generates a 6-month summary card and exports it as a PNG.
- **Environment Stats:** Shows connected MCP servers, skills, commands run, and files edited.
- **Plugin Usage:** Tracks most used tools and MCPs (@playwright, etc.).
- **Customization:** Upload a custom avatar or pick custom initials, display name, handle, and colors. All edits are saved locally.
- **Metric Reference:** Built-in guide explaining how all metrics are calculated.

## Project Structure

```text
Profile-Antigravity/
├── webview/
│   ├── profile.html        # Dashboard interface
│   └── profile_data.json   # Parsed profile data and heatmap matrix
├── assets/
│   └── antigravity-logo.png
├── scripts/
│   └── collect_profile.py  # Python script to parse ~/.gemini/antigravity/brain/*/
└── README.md
```

## Quick Start

### 1. Requirements

- Python 3.8+ (no extra packages needed, uses standard library only)
- Any browser or antigravity

### 2. Parse Your Activity Data

Run the collection script to parse your Antigravity conversation transcripts:

```bash
python3 scripts/collect_profile.py
```

This generates or updates `webview/profile_data.json`.

### 3. Open the Dashboard

Open `webview/profile.html` in your browser:

```bash
open webview/profile.html
```

Or run a simple local HTTP server:

```bash
python3 -m http.server 8080 --directory webview
```

Then visit `http://localhost:8080/profile.html`.

## License

MIT
