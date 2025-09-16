#!/usr/bin/env python3
"""
Test application to verify Con5013 package functionality.
"""

import sys
import traceback
from pathlib import Path
from flask import Flask

# Ensure local package path is importable when not installed site-wide
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
LOCAL_PKG_ROOT = REPO_ROOT / 'CON5013'
for candidate in (REPO_ROOT, LOCAL_PKG_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


def test_con5013_import():
    """Test that Con5013 can be imported."""
    try:
        from con5013 import Con5013  # noqa: F401
        print("[OK] Con5013 import successful")
        return True
    except ImportError as e:
        print(f"[FAIL] Con5013 import failed: {e}")
        return False


def test_con5013_initialization():
    """Test that Con5013 can be initialized with Flask."""
    try:
        from con5013 import Con5013

        app = Flask(__name__)
        console = Con5013(app)

        print("[OK] Con5013 initialization successful")
        print(f"  - Console instance: {console}")
        print(f"  - URL prefix: {console.config['CON5013_URL_PREFIX']}")
        print(f"  - Theme: {console.config['CON5013_THEME']}")
        return True, app, console
    except Exception as e:
        print(f"[FAIL] Con5013 initialization failed: {e}")
        traceback.print_exc()
        return False, None, None


def test_con5013_routes():
    """Test that Con5013 routes are accessible."""
    try:
        success, app, _console = test_con5013_initialization()
        if not success:
            return False

        with app.test_client() as client:
            # Test main console route
            response = client.get('/con5013/')
            print(f"[OK] Console route accessible: {response.status_code}")

            # Test API routes
            response = client.get('/con5013/api/logs')
            print(f"[OK] Logs API accessible: {response.status_code}")

            # System endpoints available under /api/system/stats and /api/system/health
            response = client.get('/con5013/api/system/stats')
            print(f"[OK] System stats API accessible: {response.status_code}")

            response = client.get('/con5013/api/system/health')
            print(f"[OK] System health API accessible: {response.status_code}")

        return True
    except Exception as e:
        print(f"[FAIL] Route testing failed: {e}")
        traceback.print_exc()
        return False


def test_con5013_components():
    """Test that Con5013 components are initialized."""
    try:
        from con5013 import Con5013

        app = Flask(__name__)
        console = Con5013(app, config={
            'CON5013_ENABLE_LOGS': True,
            'CON5013_ENABLE_TERMINAL': True,
            'CON5013_ENABLE_API_SCANNER': True,
            'CON5013_ENABLE_SYSTEM_MONITOR': True,
        })

        components = [
            ('Log Monitor', console.log_monitor),
            ('Terminal Engine', console.terminal_engine),
            ('API Scanner', console.api_scanner),
            ('System Monitor', console.system_monitor),
        ]

        all_ok = True
        for name, component in components:
            if component is not None:
                print(f"[OK] {name} initialized")
            else:
                print(f"[WARN] {name} not initialized")
                all_ok = False

        return all_ok
    except Exception as e:
        print(f"[FAIL] Component testing failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Testing Con5013 Package Installation and Functionality")
    print("=" * 60)

    tests = [
        ("Import Test", test_con5013_import),
        ("Initialization Test", lambda: test_con5013_initialization()[0]),
        ("Routes Test", test_con5013_routes),
        ("Components Test", test_con5013_components),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n> Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {test_name}")
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name} with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! Con5013 package is working correctly.")
        return True
    else:
        print("Some tests failed. Please check the errors above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
