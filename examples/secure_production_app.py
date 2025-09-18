"""Secure Con5013 integration example.

This example demonstrates how to run Con5013 with the hardened "secured" profile
and different authentication modes. It defaults to HTTP basic authentication, but you
can set ``CON5013_EXAMPLE_AUTH_MODE`` to ``"token"`` or ``"callback"`` to exercise the
other access guard paths.

Usage::

    # Basic auth (default credentials: ops / change-me)
    flask --app examples.secure_production_app run --debug

    # Token auth
    CON5013_EXAMPLE_AUTH_MODE=token \
    CON5013_EXAMPLE_TOKEN=super-secret-token \
    flask --app examples.secure_production_app run

    # Custom callback auth (header-based roles)
    CON5013_EXAMPLE_AUTH_MODE=callback \
    flask --app examples.secure_production_app run

The secured profile disables risky tooling (terminal, API scanner, log clearing,
auto-injection, etc.). This script selectively re-enables logs and the system monitor
because operators typically need read-only visibility in production. Adjust the
configuration to match your own operational requirements.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, request

from con5013 import Con5013


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.setdefault("SECRET_KEY", "change-me")

    # Always start from the secured profile for production-facing deployments.
    app.config.update(
        {
            "CON5013_ENABLED": True,
            "CON5013_SECURITY_PROFILE": "secured",
            # Preserve observability panels that are safe for authenticated operators.
            "CON5013_ENABLE_LOGS": True,
            "CON5013_ENABLE_SYSTEM_MONITOR": True,
            # Keep the API scanner available but restrict it to in-process routes.
            "CON5013_ENABLE_API_SCANNER": True,
            "CON5013_API_ALLOW_EXTERNAL": False,
            "CON5013_API_EXTERNAL_ALLOWLIST": [],
            # Ensure log history remains immutable.
            "CON5013_ALLOW_LOG_CLEAR": False,
        }
    )

    auth_mode = os.getenv("CON5013_EXAMPLE_AUTH_MODE", "basic").strip().lower() or "basic"

    if auth_mode == "token":
        app.config.update(
            {
                "CON5013_AUTHENTICATION": "token",
                "CON5013_AUTH_TOKEN": os.getenv("CON5013_EXAMPLE_TOKEN", "set-a-strong-token"),
            }
        )
    elif auth_mode == "callback":
        app.config["CON5013_AUTHENTICATION"] = _role_based_auth
    else:
        app.config.update(
            {
                "CON5013_AUTHENTICATION": "basic",
                "CON5013_AUTH_USER": os.getenv("CON5013_EXAMPLE_BASIC_USER", "ops"),
                "CON5013_AUTH_PASSWORD": os.getenv("CON5013_EXAMPLE_BASIC_PASSWORD", "change-me"),
            }
        )

    console = Con5013(app)

    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index() -> dict[str, Any]:
        return {"status": "ok", "message": "Production app stub"}

    @app.route("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.route("/metrics")
    def metrics() -> dict[str, Any]:
        return {
            "requests_total": 42,
            "error_rate": 0,
        }


def _role_based_auth(req: request) -> Any:
    """Authenticate Con5013 access using simple header-based roles.

    - ``X-Demo-User`` identifies the operator. Any non-empty value is considered
      authenticated.
    - ``X-Demo-Role`` controls feature access:
        * ``observer`` – read-only access to UI pages and log/system APIs.
        * ``engineer`` – same as observer plus permission to use the API scanner.
        * ``admin`` – full access, including the terminal (if enabled).
    - Requests missing headers or using an unknown role are rejected.
    """

    user = req.headers.get("X-Demo-User", "").strip()
    role = req.headers.get("X-Demo-Role", "").strip().lower()

    if not user or role not in {"observer", "engineer", "admin"}:
        return False

    endpoint = (req.endpoint or "").split(".", 1)[-1]

    if endpoint.startswith("api_terminal") and role != "admin":
        return False
    if endpoint.startswith("api_scanner") and role not in {"engineer", "admin"}:
        return False

    # Allow everything else for authenticated users.
    return True


app = create_app()


@app.route("/whoami")
def whoami() -> dict[str, Any]:
    """Simple route to show how headers map to authenticated roles."""

    return {
        "user": request.headers.get("X-Demo-User") or None,
        "role": request.headers.get("X-Demo-Role") or None,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
