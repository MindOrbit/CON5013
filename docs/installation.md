# Con5013 Installation Guide

## Supported Environment

- **Python**: 3.8 or newer (CPython is recommended).
- **Flask**: 2.0 or newer in the host application.
- **Dependencies**: `flask`, `psutil`, `requests`, `werkzeug`, and `jinja2` are installed automatically with the package.
- **Optional extras**:
  - `con5013[crawl4ai]` enables Crawl4AI-specific features such as terminal commands and log aliases.
  - `con5013[full]` installs the optional realtime stack (websockets, Redis, Celery) for advanced deployments.
- **Browser**: A modern browser with JavaScript enabled for the web console.

## Install the Package

### PyPI install (recommended)

```bash
pip install con5013
```

### Install with extras

```bash
# Enable Crawl4AI enhancements
pip install "con5013[crawl4ai]"

# Install all optional realtime dependencies
pip install "con5013[full]"
```

### Install from source

If you are working with a cloned repository:

```bash
pip install -e .
```

You can also build and install the wheel found in the `dist/` folder when packaging releases.

## Verify the Installation

Use the bundled CLI to confirm that the package is available:

```bash
con5013 version
```

The CLI also provides helper commands for bootstrapping and demoing the console:

```bash
# Generate a starter Flask file that already uses Con5013
con5013 init --filename app_with_con5013.py

# Launch the built-in demo application on http://localhost:5000
con5013 demo
```

## Add Con5013 to a Flask Application

### Minimal integration

```python
from flask import Flask
from con5013 import Con5013

app = Flask(__name__)
console = Con5013(app)

if __name__ == "__main__":
    app.run(debug=True)
```

Initializing the extension registers the `/con5013` blueprint, sets up logging, and exposes the overlay helper automatically.

### Application factory pattern

```python
from flask import Flask
from con5013 import Con5013

console = Con5013()

def create_app():
    app = Flask(__name__)
    console.init_app(app)
    return app
```

### Configure features and behaviour

Configuration can be supplied via `app.config` before initialization or by passing a `config={...}` mapping when constructing `Con5013`. Common options include:

```python
app = Flask(__name__)
app.config.update(
    CON5013_URL_PREFIX="/admin/console",  # Change where the blueprint mounts
    CON5013_ENABLE_TERMINAL=False,         # Disable the terminal if not needed
    CON5013_LOG_SOURCES=[
        {"name": "app", "path": "/var/log/my_app.log"},
        {"name": "api", "path": "/var/log/my_api.log"},
    ],
    CON5013_CAPTURE_ROOT_LOGGER=False,     # Attach only to explicit loggers
    CON5013_AUTO_INJECT=False,             # Opt-out of automatic overlay injection
    CON5013_HOTKEY="Ctrl+Shift+C",        # Override the default Alt+C shortcut
)
Con5013(app)
```

Refer to the defaults in `Con5013._get_default_config()` for the complete list of toggles, including API scanner, system monitor, Crawl4AI, and websocket options.

## Template and Overlay Integration

When `CON5013_AUTO_INJECT` is left enabled (the default), the extension injects template context and a `con5013_console_html()` template global. To embed the overlay manually—useful when auto-injection is disabled—add the helper and JavaScript to your base template:

```jinja2
{% if con5013_enabled %}
  {{ con5013_console_html() | safe }}
  <script src="{{ url_for('con5013.static', filename='js/con5013.js') }}"></script>
{% endif %}
```

The JavaScript bootstrapper exposes configuration such as `baseUrl`, `hotkey`, floating action button behaviour, and update intervals. You can tweak the global `con5013` instance after load to point at a different prefix or shortcut:

```html
<script>
  document.addEventListener('DOMContentLoaded', () => {
    if (window.con5013) {
      con5013.options.baseUrl = '/admin/console';
      con5013.options.hotkey = 'Ctrl+Shift+C';
      con5013.loadInitialData();
    }
  });
</script>
```

## Accessing the Console

- **Full interface**: Visit `/<prefix>/` (defaults to `/con5013/`).
- **Overlay endpoint**: Load `/<prefix>/overlay` in an iframe or via the helper HTML.
- **Keyboard shortcut**: Press the configured hotkey (Alt+C by default) when the auto-injected overlay is present.
- **REST APIs**: Logs, terminal, API scanner, and system monitor endpoints live under `/<prefix>/api/...`.

Update `CON5013_URL_PREFIX` to relocate the console without changing your templates.

## Next Steps

- Explore the feature set in [`docs/features.md`](features.md).
- Review the `examples/` directory or run `con5013 demo` for ready-made integrations.
- Check the project README for advanced usage patterns and deployment notes.
