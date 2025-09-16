# Con5013 Delivery Overview

## Release snapshot
- **Version:** 1.0.0 (`from con5013 import Con5013`)
- **Runtime support:** Python 3.8+ (Flask 2.x and Werkzeug 2.x tested)
- **What ships:** the Flask extension package (`con5013/`), first-party docs, runnable example apps, and the pytest test suite
- **Highlights in this drop:**
  - Floating in-app console powered by `static/js/con5013.js` with overlay + floating-action-button support.
  - System monitor endpoints reorganised under `/con5013/api/system/<resource>` (stats, health, processes).
  - Demo applications inside `examples/` that mirror the README walk-through, including the Matrix showcase.
  - CLI helpers in `con5013/cli.py` for bootstrapping integrations (`con5013 init`) and launching a demo server (`con5013 demo`).

---

## Repository layout
```
CON5013/
├── con5013/                         # Extension source package
│   ├── __init__.py                   # Extension factory + default config
│   ├── blueprint.py                  # Flask blueprint exposing console + APIs
│   ├── cli.py                        # ``con5013`` CLI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── api_scanner.py            # Route discovery and testing helpers
│   │   ├── log_monitor.py            # Log ingestion + source management
│   │   ├── system_monitor.py         # System metrics collector (psutil-backed)
│   │   ├── terminal_engine.py        # Sandboxed command execution + history
│   │   └── utils.py                  # Shared helpers (instance lookup, etc.)
│   ├── static/
│   │   ├── css/con5013.css           # Glassmorphism console styling
│   │   └── js/con5013.js             # Overlay launcher + UI controller
│   └── templates/
│       ├── console.html              # Full console view
│       └── overlay.html              # Embeddable overlay surface
├── docs/
│   ├── DELIVERY_OVERVIEW.md          # This delivery guide
│   ├── features.md                   # Feature catalogue
│   └── installation.md               # Installation walk-through
├── examples/
│   ├── advanced_implementation.py    # Config-heavy integration example
│   ├── crawl4ai_integration.py       # Crawl4AI monitoring sample
│   ├── matrix_app.py                 # Matrix-themed showcase used in screenshots/tests
│   ├── simple_integration.py         # Minimal integration (construct + route)
│   └── test_app.py                   # Lightweight smoke-test application
├── tests/
│   ├── test_con5013.py               # Core behaviour + blueprint/API checks
│   ├── test_con5013_app.py           # App factory/integration coverage
│   ├── test_integration.py           # Example-driven sanity tests
│   └── test_matrix_app.py            # Matrix demo regression coverage
├── README.md                         # Product overview and usage guide
├── requirements.txt                  # Example/test dependency pins
├── pyproject.toml                    # Build metadata (setuptools backend)
├── setup.py                          # Legacy build helper
├── MANIFEST.in                       # Package data manifest
└── LICENSE                           # MIT licence
```

> **Heads-up:** Distributable artifacts (wheels / sdists) are not checked in. Build them with `python -m build` when cutting a release.

---

## Key components at a glance
- **Extension (`con5013/`):** registers the blueprint, initialises the log monitor, terminal engine, API scanner, and system monitor, and optionally injects the overlay assets.
- **Front-end assets:** `static/js/con5013.js` injects styling, renders the overlay, polls REST endpoints, and keeps the floating button and hotkey (`Alt+C` by default) wired up. CSS lives alongside the script.
- **Templates:** `console.html` and `overlay.html` provide the HTML shells used by the blueprint routes.
- **Examples:** runnable Flask apps that demonstrate minimal to advanced configuration, plus a Crawl4AI-focused integration sample.
- **CLI (`con5013/cli.py`):** exposes `con5013 version`, `con5013 init`, and `con5013 demo [--crawl4ai]` commands for local tooling and demos.

---

## Installation & build pathways
1. **Editable install (developer mode)**
   ```bash
   python -m pip install -e .
   ```
2. **Standard install**
   ```bash
   python -m pip install .
   ```
3. **Build distributables**
   ```bash
   python -m pip install build
   python -m build
   # dist/ now contains the wheel and sdist
   ```
4. **Matrix demo quick-start**
   ```bash
   python -m pip install -r requirements.txt
   python examples/matrix_app.py
   ```

With the demo running, visit `http://127.0.0.1:5002/con5013/` or press `Alt+C` to toggle the overlay. Inject the floating action button by adding the launcher script to your pages:
```html
<script src="/con5013/static/js/con5013.js"></script>
```

---

## Console entry points & REST APIs
- **UI routes**
  - `GET /con5013/` – full console interface
  - `GET /con5013/overlay` – overlay-only view for embedding
  - Floating button + hotkey provided by `static/js/con5013.js`
- **Logs**
  - `GET /con5013/api/logs?source=<name>&limit=<n>&level=<LEVEL>&since=<unix>`
  - `GET /con5013/api/logs/sources`
  - `POST /con5013/api/logs/clear` (JSON body: `{"source": "app"}`)
- **Terminal**
  - `POST /con5013/api/terminal/execute` (JSON body: `{ "command": "..." }`)
  - `GET /con5013/api/terminal/commands`
  - `GET /con5013/api/terminal/history?limit=<n>`
- **API scanner**
  - `GET /con5013/api/scanner/discover?include_con5013=true|false`
  - `POST /con5013/api/scanner/test` (JSON: `{ "endpoint": "/api/test", "method": "GET" }`)
  - `POST /con5013/api/scanner/test-all?include_con5013=true|false`
- **System monitor**
  - `GET /con5013/api/system/stats`
  - `GET /con5013/api/system/health`
  - `GET /con5013/api/system/processes?sort_by=cpu|memory&page=<n>&page_size=<n>`
- **Metadata & config**
  - `GET /con5013/api/info`
  - `GET /con5013/api/config`

All endpoints respect the configurable `CON5013_URL_PREFIX` (default `/con5013`).

---

## Testing & QA workflow
```bash
PYTHONPATH=examples python -m pytest tests
```
- `tests/test_con5013.py` asserts blueprint registration, core APIs (logs, system stats/health), and configuration handling.
- `tests/test_con5013_app.py` exercises the factory pattern, ensures the overlay assets inject correctly, and validates system endpoints.
- `tests/test_matrix_app.py` boots the Matrix showcase and hits the live routes exposed by the demo app.
- `tests/test_integration.py` covers example integrations end-to-end.

Run the suite before tagging a release to confirm everything passes with the installed dependency set.

---

## Configuration quick reference
```python
console = Con5013(app, config={
    'CON5013_URL_PREFIX': '/con5013',
    'CON5013_THEME': 'dark',
    'CON5013_ENABLED': True,
    'CON5013_CAPTURE_ROOT_LOGGER': True,
    'CON5013_CAPTURE_LOGGERS': ['werkzeug', 'flask.app'],
    'CON5013_ENABLE_LOGS': True,
    'CON5013_ENABLE_TERMINAL': True,
    'CON5013_ENABLE_API_SCANNER': True,
    'CON5013_ENABLE_SYSTEM_MONITOR': True,
    'CON5013_LOG_SOURCES': ['app.log'],
    'CON5013_MAX_LOG_ENTRIES': 1000,
    'CON5013_TERMINAL_HISTORY_SIZE': 100,
    'CON5013_TERMINAL_TIMEOUT': 30,
    'CON5013_API_INCLUDE_METHODS': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    'CON5013_API_EXCLUDE_ENDPOINTS': ['/static', '/con5013'],
    'CON5013_SYSTEM_UPDATE_INTERVAL': 5,
    'CON5013_MONITOR_CPU': True,
    'CON5013_MONITOR_MEMORY': True,
    'CON5013_MONITOR_DISK': True,
    'CON5013_MONITOR_NETWORK': True,
    'CON5013_MONITOR_GPU': True,
    'CON5013_OVERLAY_MODE': True,
    'CON5013_AUTO_INJECT': True,
    'CON5013_HOTKEY': 'Alt+C',
    'CON5013_CRAWL4AI_INTEGRATION': False,
})
```
Each option can also be provided via `app.config[...]`.

---

## Example applications
- `simple_integration.py` – bolt-on integration showing the minimal wiring.
- `advanced_implementation.py` – fully customised console (alternative prefix, custom log sources, etc.).
- `matrix_app.py` – cinematic themed app referenced throughout the README.
- `crawl4ai_integration.py` – demonstrates enabling Crawl4AI-specific logging and monitoring.
- `test_app.py` – lightweight target for manual smoke testing.

Execute any example with `python examples/<filename>.py` once dependencies are installed.

---

## Recommended release checklist
1. Run the automated tests (`PYTHONPATH=examples python -m pytest tests`).
2. Build release artifacts with `python -m build`.
3. Capture fresh screenshots/GIFs from the Matrix demo for marketing collateral.
4. Publish the wheel/sdist to your package index and announce release notes.
5. Gather feedback on overlay usability and identify new integrations (e.g., authentication hooks, WebSocket streaming).

---

**Con5013 is production-ready – install it, launch the console, and unlock cinematic debugging for your Flask apps.** 🚀
