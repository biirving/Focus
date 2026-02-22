# Focus OS

A macOS menu bar app that uses Claude's vision to monitor your screen and keep you on task.

Focus OS captures your displays, sends screenshots to Claude for analysis, and nudges you when you drift off task — with gentle reminders that escalate to urgent alerts if you keep slacking.

## Features

- **Real-time screen analysis** — Claude vision analyzes your screen every 30s to determine if you're on task, off task, or on break
- **Multi-monitor support** — Captures all connected displays simultaneously
- **Smart notifications** — Gentle reminders that escalate to urgent full-width banner alerts with sound
- **Custom focus rules** — Define what "on task" means for you in plain English with optional time budgets
- **App usage tracking** — Tracks which apps you use and for how long throughout the day
- **Daily productivity summaries** — Calendar view with per-day rankings from "waste of ATP" to "paul dirac"
- **Menu bar integration** — Always-visible status icon (✓ on task, ✗ off task, ☕ break)
- **Hot-reload rules** — Edit your focus rules and they take effect immediately

## Requirements

- macOS
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
# Clone and install dependencies
git clone <repo-url> && cd Focus
pip install -r requirements.txt

# Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

## Usage

### Menu bar app (recommended)

```bash
python -m focus.gui
```

The app appears in your menu bar and auto-starts monitoring. Click the icon to:

- See current status
- Start/Stop monitoring
- View usage stats
- View daily summary calendar
- Edit focus rules
- Adjust settings

### CLI mode

```bash
python -m focus
python -m focus --verbose        # see every analysis decision
python -m focus --config my.yaml # custom config file
```

## Configuration

Edit `config.yaml`:

```yaml
capture_interval: 10      # seconds between screenshots
analysis_interval: 30     # seconds between Claude API calls
model: claude-haiku-4-5-20251001
max_tokens: 512
notification_style: system # "system" (Notification Center) or "banner" (full-width overlay)
notification_cooldown: 120 # minimum seconds between notifications
escalation_delay: 120     # seconds before escalating to urgent alerts
```

## Focus Rules

Edit `prompt.md` (or use the GUI editor) to define your rules in plain English:

```markdown
I should be working on code in my IDE or reading documentation.

Allowed:
- VS Code, Cursor, Terminal, GitHub
- Slack (for work channels only)
- Stack Overflow, MDN, documentation sites

Not allowed:
- YouTube (max 10 min per hour)
- Reddit, Twitter, Instagram
- Games
```

Time budgets like `(max 10 min per hour)` are enforced automatically.

## Ranking Scale

Daily productivity is ranked relative to your 30-day historical average:

| Ranking | Description |
|---------|-------------|
| **paul dirac** | Exceptional focus. You worked like a Nobel Prize-winning physicist. |
| **productive** | Solid day. Stayed on task and got meaningful work done. |
| **nothing special** | Average. Not bad, not great. Around your usual baseline. |
| **lazy** | Below average. Drifted off task more than usual. |
| **waste of ATP** | Your cells burned energy for nothing. |

## Building as .app

```bash
pip install py2app
python setup.py py2app
# Output: dist/Focus.app
```

## Project Structure

```
Focus/
├── focus/
│   ├── gui.py              # Menu bar app (rumps)
│   ├── daemon.py           # Capture + analysis orchestrator
│   ├── capture.py          # Multi-monitor screenshot capture
│   ├── analyzer.py         # Claude vision API integration
│   ├── notifier.py         # System + banner notifications
│   ├── config.py           # Configuration loader
│   ├── usage_tracker.py    # Per-app usage time tracking
│   ├── summary.py          # Daily scoring and rankings
│   ├── windows.py          # GUI windows (pywebview)
│   ├── activity.py         # Activity history + time budgets
│   ├── prompt_loader.py    # Focus rules hot-reload
│   ├── models.py           # Data models
│   ├── banner.swift        # Full-width notification overlay
│   └── __main__.py         # CLI entry point
├── config.yaml
├── prompt.md
├── setup.py
├── requirements.txt
└── .env                    # ANTHROPIC_API_KEY (not committed)
```

## Data Storage

All data is stored locally in `~/.focus/`:

```
~/.focus/
├── screenshots/            # Rolling buffer of recent captures
├── usage/                  # Daily app usage JSON files
├── summaries/              # Daily productivity summary JSON files
└── activity_log.jsonl      # Append-only log of every analysis
```

## Privacy

Screenshots are captured locally and sent directly to the Anthropic API for analysis. No data is stored on third-party servers. Activity logs and usage data never leave your machine.
