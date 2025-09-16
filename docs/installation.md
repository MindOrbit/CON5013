# Con5013 Installation Guide

## Quick Installation

Install Con5013 using pip:

```bash
pip install con5013
```

## Requirements

- Python 3.8 or higher
- Flask 2.0 or higher
- Modern web browser with JavaScript enabled

## Basic Integration

### Method 1: Simple Integration (2 lines of Python)

```python
from flask import Flask
from con5013 import Con5013

app = Flask(__name__)
console = Con5013(app)  # That's it!

if __name__ == '__main__':
    app.run(debug=True)
```

### Method 2: Factory Pattern

```python
from flask import Flask
from con5013 import Con5013

console = Con5013()

def create_app():
    app = Flask(__name__)
    console.init_app(app)
    return app

app = create_app()
```

### Method 3: With Configuration

```python
from flask import Flask
from con5013 import Con5013

app = Flask(__name__)

console = Con5013(app, config={
    'CON5013_URL_PREFIX': '/admin/console',
    'CON5013_THEME': 'dark',
    'CON5013_ENABLE_TERMINAL': True,
    'CON5013_ENABLE_API_SCANNER': True,
    'CON5013_CRAWL4AI_INTEGRATION': True
})
```

## HTML Integration (1 line)

Add this to your base template to enable the overlay console:

```html
<!-- Add this anywhere in your HTML -->
{{ con5013_console_html() }}
```

## Accessing the Console

After installation, you can access Con5013 in several ways:

1. **Full Console Interface**: Visit `/con5013` in your browser
2. **Overlay Console**: Press `Alt+C\`` (backtick) on any page
3. **Direct URL**: `http://localhost:5000/con5013`

## Verification

To verify the installation works:

```bash
# Run the demo
con5013 demo

# Or create a test app
con5013 init --filename test_app.py
python test_app.py
```

## Next Steps

- [Configuration Guide](configuration.md)
- [Features Overview](features.md)
- [API Reference](api.md)
- [Crawl4AI Integration](crawl4ai.md)

