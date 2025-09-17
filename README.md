# Con5013 - Universal Flask Console Extension

🚀 **The Ultimate Flask Debugging and Monitoring Console**

Con5013 is a professional Flask console extension that provides a beautiful, glassmorphism-styled monitoring interface with real-time data display, logs, terminal, API scanning, and system monitoring capabilities. It is designed to be easy to install and use, and is compatible with Crawl4AI for advanced web scraping monitoring.

## 🧪 Quick Start (Local venv + Matrix Demo)

Run the package locally with a small Matrix-themed Flask app included in this repo.

1) Create and activate a virtual environment (Windows PowerShell)

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies (no internet required for the package itself)

```
pip install -r CON5013/requirements.txt
```

3) Option A — Install the built wheel from this repo (recommended)

```
pip install CON5013/dist/con5013-1.0.0-py3-none-any.whl
```

3) Option B — Use the local source path (dev)

If you prefer not to install the wheel, the demo app falls back to importing from
`CON5013` when the package is not installed.

4) Run the demo app

```
python matrix_app.py
```

Then visit:

- Home page (Matrix demo): http://127.0.0.1:5002/
- Con5013 console: http://127.0.0.1:5002/con5013/
- Console info API: http://127.0.0.1:5002/con5013/api/info
- System health API: http://127.0.0.1:5002/con5013/api/system/health

Logs demo:

- Generate sample logs: http://127.0.0.1:5002/generate-logs
- View file-backed logs: http://127.0.0.1:5002/con5013/api/logs?source=matrix
- View Flask stream logs (default): http://127.0.0.1:5002/con5013/api/logs?source=flask

5) Validate via tests (optional)

```
python -m pytest CON5013/tests/test_matrix_app.py
```

You should see 200 responses and a PASS result.

## Floating Overlay Button (FAB)

Give users instant access to the Con5013 console from any page by including the Con5013 script. A floating, glassy action button appears on the page; clicking it opens the Con5013 window as an embedded overlay.

### Add to your template/page

Include the JS once on pages where you want the overlay launcher:

```
<script src="/con5013/static/js/con5013.js"></script>
```

That’s it. The console hotkey remains available too (Alt + C).

Notes:
- The JS auto-injects the Con5013 CSS if it’s not already present.
- Default `baseUrl` is `/con5013`. If you changed the URL prefix, initialize with `new Con5013Console({ baseUrl: '/your-prefix' })` or expose a global initializer.

### Custom Con5013 button

If your page already has its own button, add the attribute below and it will toggle the overlay. When a custom button exists, the floating button won’t be rendered by default.

```
<button data-con5013-button>Open Con5013</button>
```

### Programmatic launcher & terminal automation

Need to open the console from your own scripts? Call the globally available helper once `con5013.js` has loaded:

```js
openCon5013Console({ tab: 'terminal' });
```

The helper waits for the console to finish booting before opening the overlay. You can target a specific tab (`logs`, `terminal`, `api`, or `system`) and even execute a command automatically on the terminal tab:

```js
openCon5013Console({
  tab: 'terminal',
  command: "python crawler.py --profile demo"
});
```

When a command is provided, the helper will:

- switch to the Terminal tab,
- paste the command into the "Enter command…" box,
- run it immediately, and
- clear the input 200 ms after execution to avoid accidental re-runs.

Optional extras:

- `previewDelay` (ms) — wait before executing to keep the command visible momentarily.
- `clearDelay` (ms) — customise how long the command stays visible after running (default `200`).
- `inputTimeout` (ms) — control how long to wait for the terminal input to appear (default `4000`).

An alias `launchCon5013Console(...)` is also exposed for convenience. Both helpers return a promise that resolves with the console instance, so you can chain further interactions if needed.

### Hide or reposition the floating button

- Disable FAB on a specific page:
  - `<meta name="con5013-no-fab" content="1">`
- Change position via options when instantiating manually:
  - `floatingButtonPosition: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'`
- Hide while open: FAB auto-hides while the overlay is visible.

### JS options (if you manually instantiate)

```
new Con5013Console({
  baseUrl: '/con5013',
  autoFloatingButton: true,
  floatingButtonPosition: 'bottom-right',
  hideFabWhenOpen: true,
  hideFabIfCustomButton: true,
  customButtonSelector: '[data-con5013-button]'
});
```

## 📜 Logging Integration

Con5013 captures logs from your application and external libraries so you can view them under the Console → Logs tab.

### What gets captured by default

- Python root logger (all loggers that propagate to root)
- Your Flask app logger (aliased to source "flask")
- Common web server logger `werkzeug` (if not already covered by root)

You can switch sources in the Logs tab to see different channels (e.g., `flask`, `werkzeug`, or any file-backed source you configure).

### File-backed log sources

Provide paths for log files to monitor via config:

```python
Con5013(app, config={
    'CON5013_LOG_SOURCES': [
        {'name': 'appfile', 'path': '/var/log/my_app.log'},
        {'name': 'api', 'path': '/var/log/my_app_api.log'},
    ]
})
```

These appear as selectable sources in the Logs tab (e.g., `appfile`, `api`).

### Logger-based sources (e.g., Crawl4AI)

If you want to surface logs from a specific library (like Crawl4AI), you have two options:

1) Configure Con5013 to capture that named logger:

```python
Con5013(app, config={
    # Keep root capture enabled to grab most logs automatically
    'CON5013_CAPTURE_ROOT_LOGGER': True,
    # Additionally attach to specific loggers that do not propagate to root
    'CON5013_CAPTURE_LOGGERS': ['crawl4ai']
})
```

2) Programmatically attach the logger and alias its source name:

```python
from con5013 import Con5013
import platform

console = Con5013(app)

# Attach a named logger (appears under source 'crawl4ai' in the UI)
console.log_monitor.attach_logger('crawl4ai', alias='crawl4ai')

# Optional: map a logger prefix to a specific source name
console.log_monitor.set_logger_alias('crawl4ai.', 'crawl4ai')
```

If Con5013 detects Crawl4AI (`CON5013_CRAWL4AI_INTEGRATION=True`), it automatically aliases common Crawl4AI loggers and attaches the handler so logs appear under the `crawl4ai` source.

### Emitting logs in your app

Use standard Python logging from your application or libraries:

```python
import logging

logger = logging.getLogger(__name__)
logger.info('Hello from my app')  # shows under source 'flask' (aliased)

logging.getLogger('crawl4ai').info('Crawl4AI log entry')  # shows under 'crawl4ai'
```

### Viewing logs

- Open the console: `http://localhost:<port>/con5013/`
- Go to the "Logs" tab
- Select a Source (e.g., `flask`, `crawl4ai`, `appfile`) and enable Auto refresh

Logs display timestamps, level badges, and messages. Use the Export button to download the current view.

## ✨ Features

### 🎯 **Core Functionality**
- **Real-time Logs**: Monitor application logs with filtering and search
- **Interactive Terminal**: Execute commands safely within your Flask app
- **API Discovery**: Automatically discover and test all Flask endpoints
- **System Monitoring**: Track CPU, memory, disk, and network usage
- **Beautiful Interface**: Modern dark theme with professional styling

### 🔧 **Advanced Features**
- **Overlay Mode**: Console opens over your app without disruption
- **Hotkey Access**: Press `Alt + C` to toggle console anywhere
- **Command History**: Navigate terminal history with arrow keys
- **Real-time Updates**: Live monitoring with configurable intervals
- **Export Capabilities**: Export logs, API results, and system reports

### 🕷️ **Crawl4AI Integration**
- Enhanced monitoring for web scraping operations
- Special terminal commands for Crawl4AI management
- Scraping job monitoring and control
- Performance metrics for crawling operations

## 🚀 Quick Start

### Installation

You can install Con5013 from PyPI for the latest stable release or directly from GitHub for the freshest code.

```bash
# Latest stable release from PyPI
pip install con5013

# Enable Crawl4AI integration and its browser runtime
pip install "con5013[crawl4ai]"
python -m playwright install  # downloads the Chromium binary used by Crawl4AI

# If the command above fails, ensure Playwright is installed first:
# pip install playwright
```

```bash
# Install directly from GitHub
pip install git+https://github.com/MindOrbit/CON5013.git
```

### Basic Usage

After installing the package (from PyPI or via the GitHub command above), integrate it into your Flask application:

```python
from flask import Flask
from con5013 import Con5013

app = Flask(__name__)

# One line integration!
console = Con5013(app)

if __name__ == '__main__':
    app.run(debug=True)
```

That's it! Your Flask app now has a powerful console interface ready to use whether you installed from PyPI or directly from GitHub.

### Access Your Console

- **Main Console**: Visit `http://localhost:5000/con5013`
- **Overlay Mode**: Press `Ctrl + \`` anywhere in your app
- **API Access**: Use `http://localhost:5000/con5013/api/*` endpoints

## 📖 Documentation

### Configuration Options

```python
console = Con5013(app, config={
    'CON5013_URL_PREFIX': '/admin/console',    # Custom URL prefix
    'CON5013_THEME': 'dark',                   # Console theme
    'CON5013_ENABLE_LOGS': True,               # Enable Logs module (UI + APIs)
    'CON5013_ENABLE_TERMINAL': True,           # Enable Terminal module (UI + APIs)
    'CON5013_ENABLE_API_SCANNER': True,        # Enable API Scanner module (UI + APIs)
    'CON5013_ENABLE_SYSTEM_MONITOR': True,     # Enable System Monitor module (UI + APIs)
    'CON5013_LOG_SOURCES': ['app.log'],        # Log file sources
    'CON5013_TERMINAL_ALLOW_PY': False,        # Allow `py` evaluation in terminal (off by default)
    'CON5013_HOTKEY': 'Alt+C',                 # Hotkey combination
    'CON5013_MAX_LOG_ENTRIES': 1000,          # Max log entries
    'CON5013_UPDATE_INTERVAL': 5000,          # Update interval (ms)
    'CON5013_CRAWL4AI_INTEGRATION': True      # Enable Crawl4AI features
})
```

### Custom Commands

Add your own terminal commands:

```python
@console.terminal_engine.command('my-command')
def my_custom_command(args):
    \"\"\"My custom command description.\"\"\"
    return {
        'output': f'Hello from custom command! Args: {args}',
        'type': 'text'
    }
```

### Feature Toggles and Security

All core modules are enabled by default. You can selectively disable modules at init time. When a module is disabled:

- The corresponding tab is removed from the UI.
- All related REST endpoints return HTTP 404 (hidden surface area).
- Any dependent UI actions are hidden (e.g., the “Run in Terminal” button disappears when Terminal is disabled).

Example:

```python
Con5013(app, config={
    'CON5013_ENABLE_LOGS': False,            # Hides Logs tab; /con5013/api/logs* -> 404
    'CON5013_ENABLE_TERMINAL': False,        # Hides Terminal; /con5013/api/terminal* -> 404; hides Run in Terminal
    'CON5013_ENABLE_API_SCANNER': True,      # Keep API Scanner
    'CON5013_ENABLE_SYSTEM_MONITOR': True,   # Keep System Monitor
})
```

Python eval in terminal is off by default for safety. To allow multi-line Python evaluation via the `py` command, set:

```python
Con5013(app, config={
    'CON5013_TERMINAL_ALLOW_PY': True
})
```

### Log Sources

Configure multiple log sources:

```python
console = Con5013(app, config={
    'CON5013_LOG_SOURCES': [
        'app.log',
        {'name': 'error', 'path': 'error.log'},
        {'name': 'access', 'path': 'access.log'}
    ]
})
```

## 🎨 Interface Overview

### 📊 **Logs Tab**
- Real-time application logs with timestamps
- Color-coded log levels (INFO, WARNING, ERROR)
- Search and filtering capabilities
- Export functionality

### 💻 **Terminal Tab**
- Interactive command-line interface
- Built-in commands: `help`, `status`, `routes`, `config`, `logs`, `system`
- Command history with arrow key navigation
- Safe command execution environment

### 🔍 **API Tab**
- Automatic Flask route discovery
- Sequential endpoint testing
- Performance metrics and response times
- Beautiful results visualization
- Export test results

### 📈 **System Tab**
- Real-time CPU, memory, and disk monitoring
- Application statistics and health status
- Performance graphs and progress bars
- System information and uptime tracking

## 🛠️ Advanced Usage

### Factory Pattern

```python
from con5013 import create_console_extension

def create_app():
    app = Flask(__name__)
    
    console = create_console_extension(app, config={
        'CON5013_LOG_SOURCES': ['app.log', 'system.log'],
        'CON5013_TERMINAL_ENABLED': True,
        'CON5013_API_DISCOVERY': True
    })
    
    return app
```

### Blueprint Integration

```python
from con5013 import Con5013Blueprint

app = Flask(__name__)
console_bp = Con5013Blueprint(config={
    'url_prefix': '/admin/console'
})
app.register_blueprint(console_bp)
```

### Crawl4AI Integration

```python
from flask import Flask
from con5013 import Con5013
import crawl4ai

app = Flask(__name__)
console = Con5013(app, config={
    'CON5013_CRAWL4AI_INTEGRATION': True
})

# Con5013 automatically detects Crawl4AI and adds special features:
# - Enhanced monitoring for scraping jobs
# - Special terminal commands: crawl4ai-status, crawl4ai-test
# - Performance metrics for crawling operations
```

### Custom System Boxes

Con5013's system monitor can be extended with additional cards so teams can surface
application-specific metrics alongside built-in CPU, memory, and disk panels. Core cards
can also be toggled individually using configuration flags such as
`CON5013_MONITOR_SYSTEM_INFO`, `CON5013_MONITOR_APPLICATION`, or `CON5013_MONITOR_GPU`
when you need to slim down the System tab.

```python
from con5013 import Con5013
import platform

console = Con5013(app)

console.add_system_box(
    'runtime-insights',
    title='Runtime Insights',
    rows=[
        {'name': 'Platform', 'value': platform.platform()},
        {
            'name': 'Active Jobs',
            'value': '42%',
            'progress': {
                'value': 42,
                'min': 0,
                'max': 100,
                'color_rules': [
                    {'threshold': 80, 'class': 'error'},
                    {'threshold': 60, 'class': 'warning'},
                ],
            },
        },
    ]
)

def cache_metrics_panel():
    usage = get_cache_usage()
    return {
        'title': 'Cache',
        'rows': [
            {'name': 'Hits', 'value': usage['hits']},
            {
                'name': 'Utilization',
                'value': f"{usage['percent']}%",
                'progress': {
                    'value': usage['percent'],
                    'min': 0,
                    'max': 100,
                    'color_rules': [
                        {'threshold': 90, 'class': 'error'},
                        {'threshold': 75, 'class': 'warning'},
                    ],
                },
            },
        ],
    }

console.add_system_box('cache', provider=cache_metrics_panel)

# Boxes can be toggled or removed later
console.set_system_box_enabled('cache', False)
console.remove_system_box('runtime-insights')
```

Each row accepts a `name`, `value`, and optional `progress` configuration. Progress bars support
`min`, `max`, and custom colour rules based on thresholds, mirroring the styling used by the built-in
CPU, memory, and storage cards. Static definitions can also be provided via the
`CON5013_SYSTEM_CUSTOM_BOXES` configuration key.

## 🎯 Built-in Commands

### General Commands
- `help` - Show available commands
- `clear` - Clear terminal screen
- `status` - Show application status
- `routes` - List all Flask routes
- `config` - Show application configuration
- `logs [limit]` - Show recent log entries
- `system` - Show system information

### Crawl4AI Commands (when enabled)
- `crawl4ai-status` - Show Crawl4AI integration status
- `crawl4ai-test [url]` - Test Crawl4AI functionality

## 🔧 API Endpoints

Con5013 provides a REST API for programmatic access:

- `GET /con5013/api/logs` — Get application logs
- `GET /con5013/api/logs/sources` — List available log sources
- `POST /con5013/api/logs/clear` — Clear logs for a source
- `POST /con5013/api/terminal/execute` — Execute terminal command
- `GET /con5013/api/terminal/commands` — List available terminal commands
- `GET /con5013/api/terminal/history` — Terminal history
- `GET /con5013/api/scanner/discover` — Discover Flask endpoints
- `POST /con5013/api/scanner/test` — Test specific endpoint
- `POST /con5013/api/scanner/test-all` — Test all endpoints
- `GET /con5013/api/system/stats` — System statistics
- `GET /con5013/api/system/health` — App/system health

## 🎨 Customization

### Custom Themes

```python
console = Con5013(app, config={
    'CON5013_THEME': 'custom',
    'CON5013_CUSTOM_CSS': '/path/to/custom.css'
})
```

### Custom Log Processors

```python
def custom_log_processor(log_entry):
    # Process log entry
    return processed_entry

console.log_monitor.add_processor(custom_log_processor)
```

## 📦 Requirements

- Python 3.7+
- Flask 1.0+
- Optional: psutil (for system monitoring)
- Optional: crawl4ai (for enhanced web scraping features)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](https://con5013.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/MindOrbit/CON5013/issues)
- 💬 [Discussions](https://github.com/MindOrbit/CON5013/discussions)

## 🌟 Why Con5013?

- **Universal**: Works with any Flask application
- **Beautiful**: Modern, professional interface
- **Powerful**: Comprehensive debugging and monitoring tools
- **Easy**: One-line integration
- **Extensible**: Add custom commands and features
- **Production-Ready**: Safe for production environments

---

**Made with ❤️ for the Flask community**

Transform your Flask development experience with Con5013! 🚀



### Logs Configuration (Sources and Defaults)

You can fully customize which sources appear in the Logs tab and which one is selected by default.

- Without configuration, Con5013 discovers sources automatically (e.g., `flask`, `werkzeug`, file-backed sources, and `CON5013` for Con5013 logs) and shows them in the dropdown.
- With explicit configuration, the dropdown shows only the names you specify, in the order you list them.

Supported source formats:

1) Name + path (file-backed):

```python
Con5013(app, config={
    "CON5013_LOG_SOURCES": [
        {"name": "appfile", "path": "/var/log/my_app.log"}
    ]
})
```

2) Name only (virtual/aliased): include common aliases like `CON5013`, `flask`, `werkzeug` so they appear explicitly in the dropdown:

```python
Con5013(app, config={
    "CON5013_LOG_SOURCES": [
        {"name": "CON5013"},
        {"name": "flask"},
        {"name": "werkzeug"},
        {"name": "matrix", "path": "/path/to/matrix_app.log"}
    ]
})
```

Set the initially selected source using `CON5013_DEFAULT_LOG_SOURCE`:

```python
Con5013(app, config={
    "CON5013_LOG_SOURCES": [
        {"name": "CON5013"},
        {"name": "flask"},
        {"name": "werkzeug"},
        {"name": "matrix", "path": "/path/to/matrix_app.log"}
    ],
    "CON5013_DEFAULT_LOG_SOURCE": "CON5013"  # preselect this in Logs tab
})
```

Notes:
- When `CON5013_LOG_SOURCES` is provided, the UI dropdown is populated strictly from the listed names for predictability.
- Con5013 maps logger names starting with `con5013` to the `CON5013` source automatically.
- If no sources can be determined, the UI falls back to showing `CON5013`.


### Custom Commands

You can extend the terminal with your own commands. Help automatically lists custom commands under a "Custom:" section if any are available.

Two ways to register commands

1) After init, using the public API:

```python
def my_custom_command(args):
    """Greets the user (demo)."""
    name = args[0] if args else "world"
    return {"output": f"Hello, {name}!", "type": "text"}

console = Con5013(app)
console.add_custom_command("hello", my_custom_command, description=my_custom_command.__doc__)
```

2) At init time, via CON5013_CUSTOM_COMMANDS config (function references):

```python
def echo_cmd(args):
    """Echo text back in the terminal."""
    return {"output": " ".join(args) if args else "(empty)", "type": "text"}

Con5013(app, config={
    "CON5013_CUSTOM_COMMANDS": {
        "echo": echo_cmd,
    }
})
```

Return format

- A command handler receives args: List[str] and should return a dict:

```python
{"output": "string to print", "type": "text" | "error" | "warning" | "clear"}
```

If you return a plain string, it is treated as {"output": string, "type": "text"}.

Help text

- The help page shows a "Custom:" block only when custom commands exist.
- For each command, help uses the description passed to add_custom_command(...) or falls back to the handler's docstring (first line) if provided.

Example (multi-action command)

```python
def matrix_command(args):
    """Matrix demo: matrix [hello|status|time]"""
    sub = (args[0] if args else '').lower()
    if sub == 'hello':
        return {"output": "Hello from the Matrix custom command.", "type": "text"}
    elif sub == 'status':
        import time as _t
        up = '(unknown)'
        if hasattr(app, 'start_time'):
            up = f"{int(_t.time() - app.start_time)}s"
        return {"output": f"App: {app.name}\nUptime: {up}\nDebug: {app.debug}", "type": "text"}
    elif sub == 'time':
        import time as _t
        return {"output": _t.strftime('%Y-%m-%d %H:%M:%S'), "type": "text"}
    else:
        return {"output": "Usage: matrix [hello|status|time]", "type": "text"}

console.add_custom_command("matrix", matrix_command, description=matrix_command.__doc__)
```

Notes:

- Use 'type': 'clear' to clear the terminal output area.
- Keep commands quick and safe. For heavier operations, consider background tasks and stream results to the terminal progressively.

