# Antigravity Profile & Token Dashboard

A dark-themed profile dashboard and activity visualizer for Google Antigravity, inspired by Codex.

It reads your local conversation history from Antigravity, calculates total tokens, streaks, session duration, and tool usage, and shows everything in a 52-week activity heatmap.

Available both as a **standalone web application** and as a **native Antigravity / VS Code IDE extension**.

## Features

- **Activity Heatmap:** 52-week activity grid with Daily, Weekly, and Cumulative views.
- **Share Card:** Generates a 6-month summary card and exports it as a 2x Retina PNG.
- **Environment Stats:** Shows connected MCP servers, skills, commands run, and files edited.
- **Plugin Usage:** Tracks most used tools and MCPs (@blender, @playwright, etc.).
- **Customization:** Upload a custom avatar or pick custom initials, display name, handle, and colors. All edits are saved locally.
- **Metric Reference:** Built-in guide explaining how all metrics are calculated.

## Project Structure

```text
Profile-Antigravity/
├── extension/              # Native Node.js IDE extension (Activity Bar & Sidebar)
│   ├── package.json
│   └── src/
│       ├── extension.js    # WebviewViewProvider & state coordinator
│       └── parser.js       # Fast streaming Node.js transcript parser (< 60ms)
├── webview/
│   ├── profile.html        # Dashboard interface
│   └── profile_data.json   # Parsed profile data and heatmap matrix
├── assets/
│   └── antigravity-logo.png
├── scripts/
│   └── collect_profile.py  # Standalone Python parser for ~/.gemini/antigravity/brain/*/
└── README.md
```

## Option 1: Native IDE Extension (Sidebar)

### Installation

Copy the `extension` folder to your IDE extensions directory:

```bash
# For Antigravity IDE
mkdir -p ~/.antigravity-ide/extensions/gelios.antigravity-profile-1.0.0
cp -r extension/* ~/.antigravity-ide/extensions/gelios.antigravity-profile-1.0.0/

# For VS Code
mkdir -p ~/.vscode/extensions/gelios.antigravity-profile-1.0.0
cp -r extension/* ~/.vscode/extensions/gelios.antigravity-profile-1.0.0/
```

Restart or reload your IDE window (`Cmd+Shift+P` -> `Developer: Reload Window`). A new **Profile** icon will appear in the left Activity Bar.

---

## Option 2: Standalone Web Dashboard

### 1. Requirements

- Python 3.8+ (no external dependencies, standard library only)
- Any modern browser

### 2. Parse Your Activity Data

Run the collection script to parse your Antigravity conversation transcripts:

```bash
python3 scripts/collect_profile.py
```

This generates or updates `webview/profile_data.json`.

### 3. Open the Dashboard

Open `webview/profile.html` directly in your browser:

```bash
open webview/profile.html
```

Or run a local HTTP server:

```bash
python3 -m http.server 8080 --directory webview
```

Then visit `http://localhost:8080/profile.html`.

## License

MIT
