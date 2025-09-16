# Con5013 Architecture Overview

## Repository layout
- **`con5013/`** – the installable Flask extension that wires together the blueprint, back-end services, and front-end assets that power the console.【F:con5013/__init__.py†L20-L326】
- **`con5013/core/`** – modular services that back the console: log monitoring, terminal command execution, API discovery, system metrics, and utility helpers.【F:con5013/core/log_monitor.py†L12-L200】【F:con5013/core/terminal_engine.py†L14-L200】【F:con5013/core/api_scanner.py†L12-L137】【F:con5013/core/system_monitor.py†L10-L200】【F:con5013/core/utils.py†L6-L16】
- **`con5013/templates/` & `con5013/static/`** – self-contained HTML, CSS, and JavaScript used by the blueprint to render the full console UI and embeddable overlay.【F:con5013/templates/console.html†L1-L160】【F:con5013/templates/overlay.html†L1-L160】【F:con5013/static/css/con5013.css†L1-L160】【F:con5013/static/js/con5013.js†L1-L200】
- **`docs/`** – onboarding and feature guides that complement this architectural summary (installation, feature overview, release notes).【F:docs/installation.md†L1-L101】【F:docs/features.md†L1-L120】
- **`examples/`** – runnable Flask apps that demonstrate different integration styles, including a Matrix-themed showcase with custom commands and log sources.【F:examples/matrix_app.py†L1-L156】
- **`tests/`** – automated checks covering extension setup, component initialization, and demo-app behaviour.【F:tests/test_con5013.py†L1-L162】【F:tests/test_matrix_app.py†L1-L68】
- **Packaging files** – `pyproject.toml`, `setup.py`, and `requirements.txt` describe distribution metadata, dependencies, and CLI entry points.【F:pyproject.toml†L1-L108】【F:requirements.txt†L1-L6】

## Core package structure (`con5013/`)

### Extension entry point
`con5013/__init__.py` exports the `Con5013` class that can be constructed eagerly or via `init_app`, loads default configuration, and orchestrates the core services. During initialization it registers the blueprint under a configurable prefix, injects template helpers, and wires logging and optional Crawl4AI integration before exposing helper methods for logs, terminal commands, API scans, and system stats.【F:con5013/__init__.py†L29-L326】

### Blueprint and HTTP surface
`con5013/blueprint.py` defines the Flask blueprint that serves the main console page and overlay plus feature-specific APIs. Dedicated sections expose log retrieval and management, terminal execution and metadata, API discovery and testing, system statistics, configuration inspection, and JSON error handlers. All routes retrieve the active extension instance via `core.utils.get_con5013_instance` to honour runtime configuration.【F:con5013/blueprint.py†L1-L198】【F:con5013/blueprint.py†L200-L398】

### Core services
- **LogMonitor** ingests Python logging output and configured files, normalises entries, and keeps bounded buffers per source while offering helpers to attach extra loggers and expose a Flask handler.【F:con5013/core/log_monitor.py†L20-L200】
- **TerminalEngine** registers built-in commands (status, routes, HTTP probes, Python evaluation), manages history, and provides extension points for custom or Crawl4AI-specific commands alongside safe execution utilities.【F:con5013/core/terminal_engine.py†L22-L312】
- **APIScanner** walks the Flask URL map to document endpoints, build sample paths, and exercise them either through the app’s test client or outbound HTTP requests for comprehensive testing and reporting.【F:con5013/core/api_scanner.py†L20-L338】
- **SystemMonitor** aggregates system, application, and (optionally) GPU metrics using `psutil`/`pynvml`, formats uptime, paginates processes, derives overall health signals, and merges any custom boxes registered through `Con5013.add_system_box` into the stats payload so UI extensions stay in lockstep with native metrics.【F:con5013/core/system_monitor.py†L18-L320】【F:con5013/__init__.py†L318-L449】
- **Utility helpers** currently expose `get_con5013_instance` so request handlers can grab the active extension safely.【F:con5013/core/utils.py†L6-L16】

### Front-end assets
- **Templates** ship complete HTML and inline styles for both the full-screen console and the lightweight overlay, avoiding external dependencies so the UI works offline and can be embedded directly.【F:con5013/templates/console.html†L1-L160】【F:con5013/templates/overlay.html†L1-L160】
- **Static CSS** applies the glassmorphism-inspired theme, layout, and tabbed interface styling referenced by both templates and the JavaScript console shell.【F:con5013/static/css/con5013.css†L1-L160】
- **Static JavaScript** defines the `Con5013Console` class that injects required styles, renders the overlay markup, manages tabs for logs/terminal/API/system panels, attaches event handlers, and polls backend APIs for live updates.【F:con5013/static/js/con5013.js†L6-L200】

## Command-line interface
`con5013/cli.py` registers the `con5013` console script declared in `pyproject.toml`, offering commands to print the version, scaffold a starter app, or launch a demo server that enables console features and sample endpoints.【F:con5013/cli.py†L1-L166】【F:pyproject.toml†L72-L83】

## Example applications
The `examples/` directory provides ready-to-run integrations. The `matrix_app.py` showcase configures multiple log sources, demonstrates adding a custom terminal command, serves a themed homepage, and exposes helper routes for generating logs—all while shipping with a fallback import path for development installs.【F:examples/matrix_app.py†L13-L154】

## Test suite
Unit and integration tests validate that the extension registers correctly, honours configuration toggles, exposes routes, and that the Matrix demo hits critical endpoints and log APIs via Flask’s test client. These tests double as executable documentation for expected behaviours.【F:tests/test_con5013.py†L21-L158】【F:tests/test_matrix_app.py†L21-L64】

## Documentation set
Existing guides cover installation flows, configuration patterns, and feature descriptions, giving newcomers context beyond code. Pair these with the architecture overview to navigate both setup and internals.【F:docs/installation.md†L1-L101】【F:docs/features.md†L1-L120】

## Packaging and configuration metadata
`pyproject.toml` describes build requirements, project metadata, core dependencies (Flask, psutil, requests, Werkzeug, Jinja2), optional extras, and tool configuration for Black, isort, Flake8, and pytest. `requirements.txt` mirrors the runtime dependency list for quick local installs.【F:pyproject.toml†L1-L108】【F:requirements.txt†L1-L6】
