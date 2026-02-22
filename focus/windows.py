"""Webview windows for Focus OS GUI — prompt editor and settings.

Each window runs in its own subprocess via `subprocess.Popen` so that
pywebview gets its own main thread (required on macOS / Cocoa).

CLI usage (invoked by gui.py, not by the user directly):
    python -m focus.windows editor <prompt_path>
    python -m focus.windows settings <config_json_b64> [config_path]
"""

import base64
import json
import sys
from pathlib import Path

# ── Prompt Editor ──────────────────────────────────────────────────────────

_EDITOR_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #1e1e1e; color: #d4d4d4;
        display: flex; flex-direction: column; height: 100vh;
        padding: 16px;
    }
    h2 { font-size: 15px; font-weight: 600; margin-bottom: 12px; color: #fff; }
    textarea {
        flex: 1; width: 100%; padding: 12px; font-size: 13px;
        font-family: "SF Mono", Menlo, Monaco, monospace;
        background: #2d2d2d; color: #d4d4d4; border: 1px solid #404040;
        border-radius: 6px; resize: none; outline: none;
        line-height: 1.5;
    }
    textarea:focus { border-color: #007aff; }
    .toolbar {
        display: flex; justify-content: flex-end; align-items: center;
        margin-top: 12px; gap: 10px;
    }
    .status { font-size: 12px; color: #888; margin-right: auto; }
    button {
        padding: 6px 16px; font-size: 13px; border-radius: 6px;
        border: none; cursor: pointer; font-weight: 500;
    }
    .btn-save { background: #007aff; color: #fff; }
    .btn-save:hover { background: #0066d6; }
    .btn-cancel { background: #404040; color: #d4d4d4; }
    .btn-cancel:hover { background: #505050; }
</style>
</head>
<body>
    <h2>Focus Rules</h2>
    <textarea id="editor" spellcheck="false"></textarea>
    <div class="toolbar">
        <span class="status" id="status"></span>
        <button class="btn-cancel" onclick="window.pywebview.api.close_window()">Cancel</button>
        <button class="btn-save" onclick="save()">Save</button>
    </div>
    <script>
        async function init() {
            const content = await window.pywebview.api.load_prompt();
            document.getElementById("editor").value = content;
        }
        async function save() {
            const content = document.getElementById("editor").value;
            const ok = await window.pywebview.api.save_prompt(content);
            document.getElementById("status").textContent = ok ? "Saved" : "Error saving";
            if (ok) setTimeout(() => window.pywebview.api.close_window(), 500);
        }
        (function waitApi(){if(window.pywebview&&window.pywebview.api){init();}else{setTimeout(waitApi,50);}})();
    </script>
</body>
</html>
"""


class _PromptEditorAPI:
    def __init__(self, prompt_path: str, window_ref: list):
        self._path = Path(prompt_path)
        self._window_ref = window_ref

    def load_prompt(self) -> str:
        try:
            return self._path.read_text()
        except FileNotFoundError:
            return ""

    def save_prompt(self, content: str) -> bool:
        try:
            self._path.write_text(content)
            return True
        except OSError:
            return False

    def close_window(self):
        if self._window_ref:
            self._window_ref[0].destroy()


def _run_prompt_editor(prompt_path: str):
    import webview
    window_ref: list = []
    api = _PromptEditorAPI(prompt_path, window_ref)
    window = webview.create_window(
        "Focus Rules Editor",
        html=_EDITOR_HTML,
        js_api=api,
        width=700,
        height=550,
        resizable=True,
    )
    window_ref.append(window)
    webview.start()


# ── Settings Window ────────────────────────────────────────────────────────

_SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #1e1e1e; color: #d4d4d4;
        padding: 20px; overflow-y: auto;
    }
    h2 { font-size: 15px; font-weight: 600; margin-bottom: 16px; color: #fff; }
    .section { margin-bottom: 20px; }
    .section h3 {
        font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        color: #888; margin-bottom: 8px;
    }
    .field {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 8px;
    }
    label { font-size: 13px; color: #ccc; }
    input, select {
        width: 180px; padding: 5px 8px; font-size: 13px;
        background: #2d2d2d; color: #d4d4d4; border: 1px solid #404040;
        border-radius: 4px; outline: none;
    }
    input:focus, select:focus { border-color: #007aff; }
    select { appearance: auto; }
    .toolbar {
        display: flex; justify-content: flex-end; align-items: center;
        margin-top: 16px; gap: 10px; padding-top: 12px;
        border-top: 1px solid #333;
    }
    .status { font-size: 12px; color: #888; margin-right: auto; }
    button {
        padding: 6px 16px; font-size: 13px; border-radius: 6px;
        border: none; cursor: pointer; font-weight: 500;
    }
    .btn-save { background: #007aff; color: #fff; }
    .btn-save:hover { background: #0066d6; }
    .btn-cancel { background: #404040; color: #d4d4d4; }
    .btn-cancel:hover { background: #505050; }
</style>
</head>
<body>
    <h2>Settings</h2>
    <div class="section">
        <h3>Intervals</h3>
        <div class="field">
            <label>Capture interval (s)</label>
            <input type="number" id="capture_interval" min="1">
        </div>
        <div class="field">
            <label>Analysis interval (s)</label>
            <input type="number" id="analysis_interval" min="5">
        </div>
    </div>
    <div class="section">
        <h3>Claude API</h3>
        <div class="field">
            <label>Model</label>
            <input type="text" id="model">
        </div>
        <div class="field">
            <label>Max tokens</label>
            <input type="number" id="max_tokens" min="64">
        </div>
    </div>
    <div class="section">
        <h3>Notifications</h3>
        <div class="field">
            <label>Style</label>
            <select id="notification_style">
                <option value="system">System (Notification Center)</option>
                <option value="banner">Banner (Full-width overlay)</option>
            </select>
        </div>
        <div class="field">
            <label>Cooldown (s)</label>
            <input type="number" id="notification_cooldown" min="10">
        </div>
        <div class="field">
            <label>Escalation delay (s)</label>
            <input type="number" id="escalation_delay" min="10">
        </div>
    </div>
    <div class="toolbar">
        <span class="status" id="status"></span>
        <button class="btn-cancel" onclick="window.pywebview.api.close_window()">Cancel</button>
        <button class="btn-save" onclick="save()">Save</button>
    </div>
    <script>
        const FIELDS = [
            "capture_interval", "analysis_interval", "model", "max_tokens",
            "notification_style", "notification_cooldown", "escalation_delay"
        ];
        const INT_FIELDS = [
            "capture_interval", "analysis_interval", "max_tokens",
            "notification_cooldown", "escalation_delay"
        ];

        async function init() {
            const data = await window.pywebview.api.load_settings();
            const settings = JSON.parse(data);
            for (const key of FIELDS) {
                const el = document.getElementById(key);
                if (el && settings[key] !== undefined) el.value = settings[key];
            }
        }

        async function save() {
            const values = {};
            for (const key of FIELDS) {
                const el = document.getElementById(key);
                if (!el) continue;
                values[key] = INT_FIELDS.includes(key) ? parseInt(el.value, 10) : el.value;
            }
            const ok = await window.pywebview.api.save_settings(JSON.stringify(values));
            document.getElementById("status").textContent = ok ? "Saved" : "Error saving";
            if (ok) setTimeout(() => window.pywebview.api.close_window(), 500);
        }

        (function waitApi(){if(window.pywebview&&window.pywebview.api){init();}else{setTimeout(waitApi,50);}})();
    </script>
</body>
</html>
"""


class _SettingsAPI:
    def __init__(self, config_dict: dict, config_path: str, window_ref: list):
        self._config_dict = config_dict
        self._config_path = Path(config_path)
        self._window_ref = window_ref

    def load_settings(self) -> str:
        return json.dumps(self._config_dict)

    def save_settings(self, data: str) -> bool:
        try:
            import yaml
            values = json.loads(data)
            if self._config_path.exists():
                with open(self._config_path) as f:
                    existing = yaml.safe_load(f) or {}
            else:
                existing = {}

            existing.update(values)

            with open(self._config_path, "w") as f:
                yaml.dump(existing, f, default_flow_style=False, sort_keys=False)

            return True
        except Exception:
            return False

    def close_window(self):
        if self._window_ref:
            self._window_ref[0].destroy()


def _run_settings(config_dict: dict, config_path: str):
    import webview
    window_ref: list = []
    api = _SettingsAPI(config_dict, config_path, window_ref)
    window = webview.create_window(
        "Focus Settings",
        html=_SETTINGS_HTML,
        js_api=api,
        width=480,
        height=450,
        resizable=False,
    )
    window_ref.append(window)
    webview.start()


# ── Usage Stats Window ─────────────────────────────────────────────────────

_STATS_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #1e1e1e; color: #d4d4d4;
        padding: 20px; overflow-y: auto;
    }
    h2 { font-size: 15px; font-weight: 600; margin-bottom: 4px; color: #fff; }
    .subtitle { font-size: 12px; color: #888; margin-bottom: 16px; }
    .total-bar {
        font-size: 13px; color: #aaa; margin-bottom: 16px;
        padding: 8px 12px; background: #252525; border-radius: 6px;
    }
    .total-bar strong { color: #fff; }
    .app-list { list-style: none; }
    .app-row {
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 6px; font-size: 13px;
    }
    .app-name {
        width: 160px; white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; flex-shrink: 0; color: #ccc;
    }
    .bar-bg {
        flex: 1; height: 18px; background: #2d2d2d;
        border-radius: 4px; overflow: hidden; position: relative;
    }
    .bar-fill {
        height: 100%; border-radius: 4px;
        transition: width 0.3s ease;
    }
    .app-time {
        width: 60px; text-align: right; flex-shrink: 0;
        font-variant-numeric: tabular-nums; color: #aaa; font-size: 12px;
    }
    .empty {
        text-align: center; padding: 40px 0; color: #666; font-size: 14px;
    }
</style>
</head>
<body>
    <h2>Usage Stats</h2>
    <div class="subtitle" id="date"></div>
    <div class="total-bar" id="total"></div>
    <ul class="app-list" id="apps"></ul>
    <script>
        const COLORS = [
            "#007aff","#34c759","#ff9500","#ff3b30","#af52de",
            "#5ac8fa","#ffcc00","#ff2d55","#64d2ff","#30b0c7",
        ];

        function fmt(secs) {
            const h = Math.floor(secs / 3600);
            const m = Math.floor((secs % 3600) / 60);
            if (h > 0) return h + "h " + m + "m";
            if (m > 0) return m + "m";
            return Math.floor(secs) + "s";
        }

        async function init() {
            const raw = await window.pywebview.api.load_stats();
            const data = JSON.parse(raw);
            const apps = data.apps;
            const keys = Object.keys(apps);

            document.getElementById("date").textContent = data.date;

            const totalSecs = Object.values(apps).reduce((a, b) => a + b, 0);
            document.getElementById("total").innerHTML =
                "Total tracked: <strong>" + fmt(totalSecs) + "</strong>";

            if (keys.length === 0) {
                document.getElementById("apps").innerHTML =
                    '<li class="empty">No usage data yet. Stats will appear as you use your Mac.</li>';
                return;
            }

            const maxVal = apps[keys[0]] || 1;
            const list = document.getElementById("apps");
            keys.forEach((app, i) => {
                const pct = (apps[app] / maxVal * 100).toFixed(1);
                const color = COLORS[i % COLORS.length];
                list.innerHTML += `
                    <li class="app-row">
                        <span class="app-name" title="${app}">${app}</span>
                        <div class="bar-bg">
                            <div class="bar-fill" style="width:${pct}%;background:${color}"></div>
                        </div>
                        <span class="app-time">${fmt(apps[app])}</span>
                    </li>`;
            });
        }

        (function waitApi(){if(window.pywebview&&window.pywebview.api){init();}else{setTimeout(waitApi,50);}})();
    </script>
</body>
</html>
"""


class _StatsAPI:
    def __init__(self, usage_file: str, window_ref: list):
        self._usage_file = Path(usage_file)
        self._window_ref = window_ref

    def load_stats(self) -> str:
        from datetime import date as _date
        today = _date.today()
        day_str = today.isoformat()
        display = today.strftime("%A, %B %-d, %Y")

        apps: dict = {}
        if self._usage_file.exists():
            try:
                data = json.loads(self._usage_file.read_text())
                if data.get("date") == day_str:
                    apps = data.get("apps", {})
            except (json.JSONDecodeError, OSError):
                pass

        # Sort descending
        sorted_apps = dict(sorted(apps.items(), key=lambda x: x[1], reverse=True))
        return json.dumps({"date": display, "apps": sorted_apps})

    def close_window(self):
        if self._window_ref:
            self._window_ref[0].destroy()


def _run_stats(usage_file: str):
    import webview
    window_ref: list = []
    api = _StatsAPI(usage_file, window_ref)
    window = webview.create_window(
        "Usage Stats",
        html=_STATS_HTML,
        js_api=api,
        width=520,
        height=500,
        resizable=True,
    )
    window_ref.append(window)
    webview.start()


# ── Daily Summary Calendar Window ──────────────────────────────────────────

_SUMMARY_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #1e1e1e; color: #d4d4d4;
        padding: 20px; overflow-y: auto;
    }

    /* Navigation */
    .cal-nav {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 16px;
    }
    .cal-nav button {
        background: none; color: #007aff; border: none;
        font-size: 18px; cursor: pointer; padding: 4px 10px;
        border-radius: 4px;
    }
    .cal-nav button:hover { background: #2a2a2a; }
    .cal-nav .month-label { font-size: 17px; font-weight: 700; color: #fff; }
    .cal-nav .today-btn {
        font-size: 12px; padding: 3px 10px; background: #333;
        color: #007aff; border-radius: 4px;
    }
    .cal-nav .today-btn:hover { background: #3a3a3a; }

    /* Calendar grid */
    .cal-grid {
        display: grid; grid-template-columns: repeat(7, 1fr);
        gap: 1px; margin-bottom: 20px;
    }
    .cal-header {
        font-size: 10px; text-align: center; color: #666;
        padding: 6px 0; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .cal-day {
        height: 52px; border-radius: 4px; display: flex;
        flex-direction: column; align-items: center;
        padding-top: 6px; cursor: pointer; position: relative;
        border: 2px solid transparent; transition: all 0.12s;
        background: #232323;
    }
    .cal-day:hover { background: #2a2a2a; }
    .cal-day.outside { background: transparent; }
    .cal-day.outside .day-num { color: #444; }
    .cal-day.outside:hover { background: #1f1f1f; }
    .cal-day.selected { border-color: #007aff; background: #1a2a3a; }
    .cal-day .day-num {
        font-size: 13px; font-weight: 500; color: #aaa;
        width: 24px; height: 24px; display: flex;
        align-items: center; justify-content: center;
        border-radius: 50%;
    }
    .cal-day.today .day-num {
        background: #ff3b30; color: #fff; font-weight: 700;
    }
    .cal-day .day-dot {
        width: 5px; height: 5px; border-radius: 50%;
        margin-top: 3px;
    }

    /* Rank dot colors */
    .dot-waste    { background: #ff453a; }
    .dot-lazy     { background: #ff9f0a; }
    .dot-nothing  { background: #636366; }
    .dot-prod     { background: #30d158; }
    .dot-dirac    { background: #64d2ff; }

    /* Detail panel */
    .detail {
        background: #252525; border-radius: 10px; padding: 16px;
        min-height: 140px;
    }
    .detail h3 { font-size: 14px; color: #fff; margin-bottom: 4px; }
    .detail .ranking-big {
        font-size: 22px; font-weight: 700; margin: 6px 0 14px;
        letter-spacing: -0.3px;
    }
    .detail .stat-grid {
        display: grid; grid-template-columns: 1fr 1fr;
        gap: 8px; margin-bottom: 12px;
    }
    .detail .stat-card {
        background: #2d2d2d; border-radius: 6px; padding: 8px 10px;
    }
    .detail .stat-val {
        font-size: 16px; font-weight: 600; color: #fff;
        font-variant-numeric: tabular-nums;
    }
    .detail .stat-label {
        font-size: 11px; color: #666; margin-top: 2px;
    }
    .detail .apps-title {
        font-size: 11px; color: #666; margin: 10px 0 6px;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .detail .app-row {
        display: flex; justify-content: space-between;
        font-size: 12px; padding: 3px 0;
    }
    .detail .app-name { color: #ccc; }
    .detail .app-mins { color: #666; font-variant-numeric: tabular-nums; }
    .no-selection { color: #555; font-size: 13px; text-align: center; padding: 40px 0; }

    /* Rating row: ranking + scale button side by side */
    .rating-row {
        display: flex; align-items: center; gap: 10px;
        margin: 6px 0 14px;
    }
    .rating-row .ranking-big { margin: 0; }
    .scale-btn {
        font-size: 11px; padding: 3px 8px; background: #333;
        color: #888; border: 1px solid #444; border-radius: 4px;
        cursor: pointer; white-space: nowrap;
    }
    .scale-btn:hover { background: #3a3a3a; color: #aaa; }

    /* Modal overlay */
    .modal-overlay {
        display: none; position: fixed; top: 0; left: 0;
        width: 100%; height: 100%; background: rgba(0,0,0,0.6);
        z-index: 100; align-items: center; justify-content: center;
    }
    .modal-overlay.open { display: flex; }
    .modal {
        background: #2a2a2a; border-radius: 12px; padding: 20px;
        width: 340px; max-height: 80vh; overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }
    .modal h3 { font-size: 15px; color: #fff; margin-bottom: 14px; text-align: center; }
    .scale-item {
        display: flex; align-items: flex-start; gap: 10px;
        padding: 10px 0; border-bottom: 1px solid #333;
    }
    .scale-item:last-child { border-bottom: none; }
    .scale-dot {
        width: 10px; height: 10px; border-radius: 50%;
        margin-top: 3px; flex-shrink: 0;
    }
    .scale-name { font-size: 13px; font-weight: 600; margin-bottom: 2px; }
    .scale-desc { font-size: 11px; color: #888; line-height: 1.4; }
</style>
</head>
<body>
    <div class="cal-nav">
        <button onclick="prevMonth()">&lsaquo;</button>
        <span class="month-label" id="monthLabel"></span>
        <button class="today-btn" onclick="goToday()">Today</button>
        <button onclick="nextMonth()">&rsaquo;</button>
    </div>
    <div class="cal-grid" id="calGrid"></div>
    <div class="detail" id="detail">
        <div class="no-selection">Select a day to view its summary</div>
    </div>

    <div class="modal-overlay" id="scaleModal">
        <div class="modal">
            <h3>Rating Scale</h3>
            <div class="scale-item">
                <div class="scale-dot" style="background:#64d2ff"></div>
                <div>
                    <div class="scale-name" style="color:#64d2ff">paul dirac</div>
                    <div class="scale-desc">Exceptional focus. You worked like a Nobel Prize-winning physicist today.</div>
                </div>
            </div>
            <div class="scale-item">
                <div class="scale-dot" style="background:#30d158"></div>
                <div>
                    <div class="scale-name" style="color:#30d158">productive</div>
                    <div class="scale-desc">Solid day. You stayed on task and got meaningful work done.</div>
                </div>
            </div>
            <div class="scale-item">
                <div class="scale-dot" style="background:#636366"></div>
                <div>
                    <div class="scale-name" style="color:#636366">nothing special</div>
                    <div class="scale-desc">Average. Not bad, not great. Around your usual baseline.</div>
                </div>
            </div>
            <div class="scale-item">
                <div class="scale-dot" style="background:#ff9f0a"></div>
                <div>
                    <div class="scale-name" style="color:#ff9f0a">lazy</div>
                    <div class="scale-desc">Below average. You drifted off task more than usual.</div>
                </div>
            </div>
            <div class="scale-item">
                <div class="scale-dot" style="background:#ff453a"></div>
                <div>
                    <div class="scale-name" style="color:#ff453a">waste of ATP</div>
                    <div class="scale-desc">Your cells burned energy for nothing. Might as well have been a rock.</div>
                </div>
            </div>
        </div>
    </div>

    <script>
    var allSummaries = {};
    var viewYear, viewMonth;
    var todayStr = new Date().toISOString().split("T")[0];

    var DOT_CLASS = {
        "waste of ATP": "dot-waste",
        "lazy": "dot-lazy",
        "nothing special": "dot-nothing",
        "productive": "dot-prod",
        "paul dirac": "dot-dirac"
    };
    var RANK_COLOR = {
        "waste of ATP": "#ff453a",
        "lazy": "#ff9f0a",
        "nothing special": "#636366",
        "productive": "#30d158",
        "paul dirac": "#64d2ff"
    };
    var MONTHS = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"];

    function pad2(n) { return String(n).padStart(2, "0"); }
    function dateStr(y, m, d) { return y + "-" + pad2(m + 1) + "-" + pad2(d); }

    var _embeddedData = __SUMMARY_DATA__;

    /* Click delegation — no inline onclick needed */
    document.getElementById("calGrid").addEventListener("click", function(e) {
        var cell = e.target.closest(".cal-day");
        if (cell && cell.dataset.date) selectDay(cell.dataset.date);
    });

    /* Rating Scale modal */
    document.getElementById("detail").addEventListener("click", function(e) {
        if (e.target.id === "scaleBtn") {
            document.getElementById("scaleModal").classList.add("open");
        }
    });
    document.getElementById("scaleModal").addEventListener("click", function(e) {
        if (e.target === this) this.classList.remove("open");
    });

    function init() {
        for (var i = 0; i < _embeddedData.length; i++) {
            allSummaries[_embeddedData[i].date] = _embeddedData[i];
        }
        var t = new Date();
        viewYear = t.getFullYear();
        viewMonth = t.getMonth();
        renderCalendar();
        selectDay(todayStr);
    }

    function renderCalendar() {
        var grid = document.getElementById("calGrid");
        document.getElementById("monthLabel").textContent = MONTHS[viewMonth] + " " + viewYear;

        var h = "";
        var dayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
        for (var di = 0; di < 7; di++) {
            h += "<div class=cal-header>" + dayNames[di] + "</div>";
        }

        var firstDow = new Date(viewYear, viewMonth, 1).getDay();
        var dim = new Date(viewYear, viewMonth + 1, 0).getDate();
        var prevDim = new Date(viewYear, viewMonth, 0).getDate();
        var totalCells = Math.ceil((firstDow + dim) / 7) * 7;

        for (var i = 0; i < totalCells; i++) {
            var day, ds, outside = false;
            if (i < firstDow) {
                day = prevDim - firstDow + 1 + i;
                var pm = viewMonth === 0 ? 11 : viewMonth - 1;
                var py = viewMonth === 0 ? viewYear - 1 : viewYear;
                ds = dateStr(py, pm, day);
                outside = true;
            } else if (i - firstDow >= dim) {
                day = i - firstDow - dim + 1;
                var nm = viewMonth === 11 ? 0 : viewMonth + 1;
                var ny = viewMonth === 11 ? viewYear + 1 : viewYear;
                ds = dateStr(ny, nm, day);
                outside = true;
            } else {
                day = i - firstDow + 1;
                ds = dateStr(viewYear, viewMonth, day);
            }

            var s = allSummaries[ds];
            var cls = "cal-day";
            if (outside) cls += " outside";
            if (ds === todayStr) cls += " today";

            var dot = "";
            if (s && DOT_CLASS[s.ranking]) {
                dot = "<div class='day-dot " + DOT_CLASS[s.ranking] + "'></div>";
            }

            h += "<div class='" + cls + "' data-date='" + ds + "'><span class=day-num>" + day + "</span>" + dot + "</div>";
        }

        grid.innerHTML = h;
    }

    function selectDay(ds) {
        var els = document.querySelectorAll(".cal-day");
        for (var i = 0; i < els.length; i++) els[i].classList.remove("selected");
        var el = document.querySelector("[data-date='" + ds + "']");
        if (el) el.classList.add("selected");

        var s = allSummaries[ds];
        var detail = document.getElementById("detail");
        if (!s) {
            var d = new Date(ds + "T12:00:00");
            var label = d.toLocaleDateString("en-US", {weekday:"long", month:"short", day:"numeric"});
            detail.innerHTML = "<div class=no-selection>" + label + "<br>No data recorded</div>";
            return;
        }

        var rc = RANK_COLOR[s.ranking] || "#636366";
        var out = "<h3>" + s.display_date + "</h3>";
        out += "<div class=rating-row>";
        out += "<div class=ranking-big style='color:" + rc + "'>" + s.ranking + "</div>";
        out += "<div class=scale-btn id=scaleBtn>Rating Scale</div>";
        out += "</div>";
        out += "<div class=stat-grid>";
        out += statCard(s.score + "/100", "Score");
        out += statCard(s.on_task_pct + "%", "On task");
        out += statCard(s.off_task_pct + "%", "Off task");
        out += statCard(s.tracked_minutes + "m", "Tracked");
        out += "</div>";

        if (s.top_apps && s.top_apps.length) {
            out += "<div class=apps-title>Top Apps</div>";
            for (var j = 0; j < s.top_apps.length; j++) {
                var a = s.top_apps[j];
                out += "<div class=app-row><span class=app-name>" + a.app +
                     "</span><span class=app-mins>" + a.minutes + " min</span></div>";
            }
        }
        detail.innerHTML = out;
    }

    function statCard(val, label) {
        return "<div class=stat-card><div class=stat-val>" + val +
               "</div><div class=stat-label>" + label + "</div></div>";
    }

    function prevMonth() {
        viewMonth--;
        if (viewMonth < 0) { viewMonth = 11; viewYear--; }
        renderCalendar();
    }
    function nextMonth() {
        viewMonth++;
        if (viewMonth > 11) { viewMonth = 0; viewYear++; }
        renderCalendar();
    }
    function goToday() {
        var t = new Date();
        viewYear = t.getFullYear();
        viewMonth = t.getMonth();
        renderCalendar();
        selectDay(todayStr);
    }

    init();
    </script>
</body>
</html>
"""


def _load_all_summaries(summaries_dir: str) -> str:
    """Load all summary JSON files and return as a JS-safe JSON string."""
    d = Path(summaries_dir)
    summaries = []
    if d.exists():
        for f in sorted(d.glob("*.json")):
            try:
                summaries.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
    return json.dumps(summaries)


def _run_summary(summaries_dir: str, log_path: str, usage_dir: str):
    import webview
    # Inject data directly into HTML — no API bridge needed
    data_json = _load_all_summaries(summaries_dir)
    html = _SUMMARY_HTML.replace("__SUMMARY_DATA__", data_json)
    window = webview.create_window(
        "Daily Summary",
        html=html,
        width=520,
        height=660,
        resizable=True,
    )
    webview.start()


# ── Subprocess spawners (called from gui.py) ──────────────────────────────

def spawn_prompt_editor(prompt_path: str):
    """Launch the editor as a lightweight subprocess."""
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "focus.windows", "editor", prompt_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def spawn_settings(config_dict: dict, config_path: str = "config.yaml"):
    """Launch settings as a lightweight subprocess."""
    import subprocess
    # Base64-encode the JSON so it's a single safe CLI arg
    payload = base64.b64encode(json.dumps(config_dict).encode()).decode()
    subprocess.Popen(
        [sys.executable, "-m", "focus.windows", "settings", payload, config_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def spawn_stats(usage_file: str):
    """Launch the usage stats window as a lightweight subprocess."""
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "focus.windows", "stats", usage_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def spawn_summary(summaries_dir: str, log_path: str, usage_dir: str):
    """Launch the daily summary calendar window as a lightweight subprocess."""
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "focus.windows", "summary", summaries_dir, log_path, usage_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── CLI entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "editor":
        _run_prompt_editor(sys.argv[2])
    elif cmd == "settings":
        config_dict = json.loads(base64.b64decode(sys.argv[2]))
        config_path = sys.argv[3] if len(sys.argv) > 3 else "config.yaml"
        _run_settings(config_dict, config_path)
    elif cmd == "stats":
        _run_stats(sys.argv[2])
    elif cmd == "summary":
        _run_summary(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f"Usage: python -m focus.windows (editor|settings|stats|summary) ...", file=sys.stderr)
        sys.exit(1)
