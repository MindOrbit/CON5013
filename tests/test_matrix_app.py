#!/usr/bin/env python3
"""
Basic tests for the Matrix demo app using Flask's test client.
"""

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

from matrix_app import create_app


def run_tests() -> bool:
    app = create_app()
    ok = True
    with app.test_client() as client:
        # Home page contains Matrix content
        r = client.get('/')
        print('GET / ->', r.status_code)
        ok &= (r.status_code == 200)
        ok &= (b'Welcome to The Matrix' in r.data)

        # Generate some logs
        r = client.get('/generate-logs')
        print('GET /generate-logs ->', r.status_code, r.is_json)
        ok &= (r.status_code == 200)

        # Con5013 console page
        r = client.get('/con5013/')
        print('GET /con5013/ ->', r.status_code)
        ok &= (r.status_code == 200)

        # Info API
        r = client.get('/con5013/api/info')
        print('GET /con5013/api/info ->', r.status_code)
        ok &= (r.status_code == 200)

        # System health API
        r = client.get('/con5013/api/system/health')
        print('GET /con5013/api/system/health ->', r.status_code)
        ok &= (r.status_code == 200)

        # Logs API (default source = flask)
        r = client.get('/con5013/api/logs')
        d = r.get_json()
        print('GET /con5013/api/logs ->', r.status_code, 'total=', d.get('total'))
        ok &= (r.status_code == 200 and d.get('total', 0) >= 1)

        # Logs API for file-backed source
        r = client.get('/con5013/api/logs?source=matrix')
        d = r.get_json()
        print('GET /con5013/api/logs?source=matrix ->', r.status_code, 'total=', d.get('total'))
        ok &= (r.status_code == 200 and d.get('total', 0) >= 1)

    print('Result:', 'PASS' if ok else 'FAIL')
    return ok


if __name__ == '__main__':
    raise SystemExit(0 if run_tests() else 1)
