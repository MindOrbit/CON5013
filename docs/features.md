# Con5013 Feature Overview

Con5013 delivers a self-contained operations console for Flask applications. The extension combines real-time monitoring, developer tooling, and a polished overlay UI that can be dropped into any project with a single initializer.

## Observability & Monitoring

### Unified Log Viewer
- Hooks into the Python logging subsystem (root logger, the Flask app logger, or specific named loggers) so multiple sources stream into a single timeline without extra wiring.
- Configure file-backed or virtual sources via `CON5013_LOG_SOURCES`, override the initially selected channel with `CON5013_DEFAULT_LOG_SOURCE`, and register extra loggers or aliases programmatically to surface external services such as Crawl4AI.
- The console UI supports source switching, level filtering, chronological sorting, export, and auto-scroll controls, while the `/api/logs`, `/api/logs/sources`, and `/api/logs/clear` endpoints expose the same data over HTTP.

### System Insight
- Collects CPU, memory, disk, and network metrics (with graceful degradation when `psutil` is unavailable) and reports application-level details such as uptime, registered blueprints, and enabled extensions.
- Optional GPU telemetry is gathered through NVIDIA NVML (`pynvml`) or an `nvidia-smi` fallback, enabling visibility into accelerator utilization when hardware is present.
- Provides paginated process listings and aggregate health checks through `/api/system/stats`, `/api/system/health`, and `/api/system/processes` so operators can inspect load spikes or runaway workers without leaving the browser.

### Custom System Boxes
- Extend the System tab with domain-specific metrics using `console.add_system_box` or the `CON5013_SYSTEM_CUSTOM_BOXES` configuration hook. Static rows accept plain dictionaries, while callables and provider functions let you compute values on every refresh so the UI always reflects the latest state.

```python
console.add_system_box(
    "cache-metrics",
    title="Cache",
    rows=[
        {"name": "Hits", "value": "128,450"},
        {
            "name": "Hit Rate",
            "value": "86%",
            "progress": {"value": 86, "color_rules": [{"threshold": 70, "class": "warning"}]},
        },
    ],
)
```
- Boxes can be toggled or removed at runtime, reordered with the `order` parameter, and enriched with descriptions or `progress` metadata for inline gauges. The example applications demonstrate both static Matrix-themed cards and advanced provider-driven panels.

## Developer Tooling

### API Discovery & Testing
- Automatically enumerates Flask routes, including parameter metadata, docstrings, and generated sample paths that replace converters with representative values for frictionless testing.
- Tests endpoints locally through the Flask test client when possible (falling back to outbound HTTP for remote URLs), capturing status codes, response types, timings, and payload previews for every call.
- Batch testing summarizes success rates, latency percentiles, and status/method distribution while skipping sensitive routes listed in `CON5013_API_PROTECTED_ENDPOINTS`. Generated documentation can also be exported programmatically.
- `/api/scanner/discover`, `/api/scanner/test`, and `/api/scanner/test-all` expose the discovery and verification workflows so they can be automated in CI/CD pipelines.

### Interactive Terminal
- Ships with core commands (`help`, `clear`, `status`, `routes`, `config`, `logs`, `history`, `system`) plus HTTP helpers (`http`, `httpfull`) and optional Python evaluation via the `py` command when `CON5013_TERMINAL_ALLOW_PY` is enabled.
- Maintains persistent command history, enables arrow-key navigation, and streams structured results back to the UI where outputs are formatted, syntax-highlighted, or cleared as needed.
- Supports project-specific commands registered through `CON5013_CUSTOM_COMMANDS`, the `@console.terminal_engine.command` decorator, or the `add_custom_command` helper. Custom entries are surfaced in the contextual help menu automatically.
- Dedicated endpoints `/api/terminal/execute`, `/api/terminal/commands`, and `/api/terminal/history` power the browser terminal, and return 404 when the feature is disabled for added safety.

### Command Line Utilities
- `con5013 init` scaffolds an example Flask integration file, while `con5013 demo` launches a ready-to-run showcase with optional Crawl4AI support—perfect for onboarding or demonstrations.

## Integration & Extensibility
- Initialize with `Con5013(app, config=...)`, the factory/`init_app` pattern, or the provided helpers; set `CON5013_ENABLED` to guard against accidental activation in certain environments.
- Toggle entire modules (`CON5013_ENABLE_LOGS`, `CON5013_ENABLE_TERMINAL`, `CON5013_ENABLE_API_SCANNER`, `CON5013_ENABLE_SYSTEM_MONITOR`) to remove UI tabs and make the corresponding REST surface respond with 404s, reducing attack surface when a capability is not needed.
- Auto-injects the overlay markup and context helpers (`con5013_console_html`) when `CON5013_AUTO_INJECT` is true, making it trivial to drop the console into any template. Manual injection is also supported for custom layouts.
- The JavaScript client loads configuration from `/api/info`, applies feature toggles, and exposes options for hotkeys, floating button behavior, and custom launchers—so teams can align the UX with their brand or workflow.
- Logging integration utilities (`attach_logger`, `set_logger_alias`) and configuration flags (`CON5013_CAPTURE_ROOT_LOGGER`, `CON5013_CAPTURE_LOGGERS`) simplify multi-service observability. Crawl4AI-aware hooks add specialized commands, metrics, and log routing when that package is installed.

## User Experience Highlights
- Glassmorphism-inspired UI with tabbed panels for Logs, Terminal, API, and System views, plus real-time connectivity indicators that recolor the CON5013 monogram when backend requests fail.
- Overlay mode is accessible via `Alt+C`, the dedicated `/con5013/overlay` route, a floating action button (FAB), or custom buttons annotated with `data-con5013-button`. FAB placement, visibility, and coexistence with custom triggers are all configurable from JavaScript options.
- Quality-of-life touches include automatic textarea resizing, Shift+Enter multiline support, log auto-scroll pausing with resume controls, and one-click log export for quick incident sharing.

## REST & UI Endpoints

| Area | Description | Endpoint |
| --- | --- | --- |
| Console UI | Full console / overlay | `/con5013/`, `/con5013/overlay` |
| Metadata | Configuration & feature flags | `/con5013/api/info`, `/con5013/api/config` |
| Logs | Fetch sources, entries, or clear buffers | `/con5013/api/logs`, `/con5013/api/logs/sources`, `/con5013/api/logs/clear` |
| Terminal | Execute commands & view history | `/con5013/api/terminal/execute`, `/con5013/api/terminal/commands`, `/con5013/api/terminal/history` |
| API Scanner | Discover or test endpoints | `/con5013/api/scanner/discover`, `/con5013/api/scanner/test`, `/con5013/api/scanner/test-all` |
| System Monitor | Metrics, health, processes | `/con5013/api/system/stats`, `/con5013/api/system/health`, `/con5013/api/system/processes` |

All feature toggles are enforced across both the UI and the REST layer—when a module is disabled its navigation tab disappears and the related endpoints return HTTP 404, ensuring parity between what users can see and what is exposed programmatically.
