import sys
from pathlib import Path

# Ensure the project root and package path are importable when not installed site-wide
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
LOCAL_PKG_ROOT = REPO_ROOT / 'CON5013'
for candidate in (REPO_ROOT, LOCAL_PKG_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from flask import Flask
from con5013 import Con5013

app = Flask(__name__)

# Initialize Con5013 with your Flask app
console = Con5013(app)

# Optional: Configure Con5013
# console = Con5013(app, config={
#     'CON5013_URL_PREFIX': '/admin/console',
#     'CON5013_THEME': 'dark',
#     'CON5013_ENABLE_TERMINAL': True,
#     'CON5013_CRAWL4AI_INTEGRATION': True
# })

@app.route('/')
def home():
    return """
    <h1>Your Flask App with Con5013</h1>
    <p>Con5013 console is available at: <a href="/con5013">/con5013</a></p>
    <p>Press Alt+C to open the overlay console</p>
    """

if __name__ == '__main__':
    app.run(debug=True)
