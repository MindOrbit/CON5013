"""Advanced Con5013 integration example.

This example demonstrates a production-style setup that uses:
- Rich Con5013 configuration touching every major setting.
- Multiple dedicated log streams surfaced in the Logs tab.
- Custom terminal commands that mutate application state and emit logs.
- Runtime registration of additional log sources and command-driven tasks.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable

from flask import Flask, jsonify, request

from con5013 import Con5013

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILES = {
    "application": LOG_DIR / "application.log",
    "audit": LOG_DIR / "audit.log",
    "jobs": LOG_DIR / "jobs.log",
    "runtime": LOG_DIR / "runtime-metrics.log",
}

CON5013_CONFIG: Dict[str, Any] = {
    "CON5013_URL_PREFIX": "/operations/console",
    "CON5013_THEME": "dark",
    "CON5013_ENABLED": True,
    "CON5013_CAPTURE_ROOT_LOGGER": True,
    "CON5013_CAPTURE_LOGGERS": [
        "werkzeug",
        "audit",
        "jobs",
        "runtime",
    ],
    "CON5013_ENABLE_LOGS": True,
    "CON5013_ENABLE_TERMINAL": True,
    "CON5013_ENABLE_API_SCANNER": True,
    "CON5013_ENABLE_SYSTEM_MONITOR": True,
    "CON5013_LOG_SOURCES": [
        {"name": "application", "path": str(LOG_FILES["application"])},
        {"name": "audit", "path": str(LOG_FILES["audit"])},
        {"name": "jobs", "path": str(LOG_FILES["jobs"])},
        {"name": "runtime", "path": str(LOG_FILES["runtime"])},
        {"name": "CON5013"},
    ],
    "CON5013_DEFAULT_LOG_SOURCE": "application",
    "CON5013_LOG_LEVELS": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    "CON5013_MAX_LOG_ENTRIES": 5000,
    "CON5013_REAL_TIME_LOGS": True,
    "CON5013_TERMINAL_HISTORY_SIZE": 250,
    "CON5013_TERMINAL_TIMEOUT": 45,
    "CON5013_TERMINAL_ALLOW_PY": True,
    "CON5013_CUSTOM_COMMANDS": {},
    "CON5013_API_TEST_TIMEOUT": 15,
    "CON5013_API_INCLUDE_METHODS": [
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
    ],
    "CON5013_API_EXCLUDE_ENDPOINTS": [
        "/static",
        "/health",
        "/metrics",
    ],
    "CON5013_API_PROTECTED_ENDPOINTS": [
        "/operations/console/api/logs/clear",
        "/operations/console/api/terminal/run",
        "/operations/console/api/system/stats",
    ],
    "CON5013_SYSTEM_UPDATE_INTERVAL": 3,
    "CON5013_MONITOR_CPU": True,
    "CON5013_MONITOR_MEMORY": True,
    "CON5013_MONITOR_DISK": True,
    "CON5013_MONITOR_NETWORK": True,
    "CON5013_ASCII_ART": True,
    "CON5013_OVERLAY_MODE": True,
    "CON5013_AUTO_INJECT": True,
    "CON5013_HOTKEY": "Alt+C",
    "CON5013_CRAWL4AI_INTEGRATION": False,
    "CON5013_WEBSOCKET_SUPPORT": False,
    "CON5013_AUTHENTICATION": False,
}


def configure_logging(app: Flask) -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)

    for name, path in LOG_FILES.items():
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(fmt)
        handler.setLevel(logging.INFO)

        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.INFO)

    logging.getLogger().setLevel(logging.INFO)


def emit_audit_event(actor: str, action: str, payload: Dict[str, Any]) -> None:
    logger = logging.getLogger("audit")
    logger.info(
        "actor=%s action=%s payload=%s",
        actor,
        action,
        json.dumps(payload, sort_keys=True),
    )


def log_runtime_metric(metric: str, value: Any, tags: Iterable[str] | None = None) -> None:
    logger = logging.getLogger("runtime")
    tag_str = ",".join(tags or [])
    logger.info("metric=%s value=%s tags=%s", metric, value, tag_str)


def register_console_commands(console: Con5013, app: Flask) -> None:
    feature_flags = app.config.setdefault("FEATURE_FLAGS", {
        "RATE_LIMITING": True,
        "BILLING_GUARDRAILS": False,
        "ASYNC_NOTIFICATIONS": True,
    })

    def _terminal_response(output: str, *, type_: str = "text") -> Dict[str, Any]:
        return {"output": output, "type": type_}

    def emit_log_command(args: list[str]) -> Dict[str, Any]:
        if not args:
            return _terminal_response("Usage: emitlog <level> <message>", type_="warning")
        level = args[0].upper()
        message = " ".join(args[1:]) or "Manual log from Con5013 terminal"
        target = logging.getLogger("application")
        target.log(getattr(logging, level, logging.INFO), message)
        return _terminal_response(f"Logged {level}: {message}")

    def audit_command(args: list[str]) -> Dict[str, Any]:
        if len(args) < 2:
            return _terminal_response("Usage: audit <actor> <action> [json_payload]", type_="warning")
        actor, action, *rest = args
        payload = {}
        if rest:
            try:
                payload = json.loads(" ".join(rest))
            except json.JSONDecodeError as exc:
                return _terminal_response(f"Invalid JSON payload: {exc}", type_="error")
        emit_audit_event(actor, action, payload)
        return _terminal_response("Audit event recorded")

    def toggle_feature_command(args: list[str]) -> Dict[str, Any]:
        if len(args) < 2:
            return _terminal_response("Usage: feature <name> <on|off>", type_="warning")
        feature = args[0].upper()
        desired = args[1].lower() in {"1", "true", "on", "yes"}
        feature_flags[feature] = desired
        emit_audit_event("console", "feature_toggle", {feature: desired})
        return _terminal_response(f"Feature {feature} => {desired}")

    def job_runner_command(args: list[str]) -> Dict[str, Any]:
        job_name = args[0] if args else "rebuild-search-index"
        params = {"args": args[1:], "triggered_at": datetime.utcnow().isoformat()}
        logging.getLogger("jobs").info("job=%s params=%s", job_name, json.dumps(params))
        return _terminal_response(f"Dispatched job: {job_name}")

    def metrics_snapshot_command(args: list[str]) -> Dict[str, Any]:
        log_runtime_metric("terminal.snapshot", datetime.utcnow().isoformat(), tags=["manual"])
        stats = console.get_system_stats() if hasattr(console, "get_system_stats") else {}
        return _terminal_response(json.dumps(stats, indent=2, default=str))

    console.add_custom_command("emitlog", emit_log_command, "Emit a log entry to the application stream")
    console.add_custom_command("audit", audit_command, "Record an audit event with optional JSON payload")
    console.add_custom_command("feature", toggle_feature_command, "Toggle runtime feature flags")
    console.add_custom_command("job", job_runner_command, "Simulate a job dispatch and log it")
    console.add_custom_command("snapshot", metrics_snapshot_command, "Capture system and runtime metrics")


def register_routes(app: Flask, console: Con5013) -> None:
    @app.get("/")
    def index() -> Dict[str, Any]:
        app.logger.info("homepage-served")
        return {
            "message": "Advanced Con5013 integration",
            "console": {
                "url": console.config["CON5013_URL_PREFIX"],
                "hotkey": console.config["CON5013_HOTKEY"],
            },
            "features": app.config.get("FEATURE_FLAGS", {}),
        }

    @app.post("/api/orders")
    def create_order():
        payload = request.get_json(force=True, silent=True) or {}
        emit_audit_event(payload.get("actor", "anonymous"), "order_created", payload)
        log_runtime_metric("order.value", payload.get("amount", 0), tags=["orders"])
        response = {"status": "accepted", "payload": payload}
        logging.getLogger("application").info("order-created %s", json.dumps(response))
        return jsonify(response), 201

    @app.get("/health")
    def health():
        return {"status": "ok", "time": datetime.utcnow().isoformat()}

    @app.post("/feature/<name>/toggle")
    def toggle(name: str):
        desired = request.json.get("enabled", True) if request.is_json else True
        app.config.setdefault("FEATURE_FLAGS", {})[name.upper()] = bool(desired)
        emit_audit_event("api", "feature_toggle", {name: desired})
        return {"feature": name.upper(), "enabled": bool(desired)}

    @app.after_request
    def record_request(response):
        logging.getLogger("runtime").info(
            "request path=%s status=%s method=%s",
            request.path,
            response.status_code,
            request.method,
        )
        return response


def register_additional_log_sources(console: Con5013) -> None:
    synthetic_log = LOG_DIR / "synthetic-actions.log"
    synthetic_log.touch(exist_ok=True)
    console.add_log_source("synthetic", str(synthetic_log))
    logging.getLogger("application").info("Registered synthetic log source: %s", synthetic_log)


def create_app() -> Flask:
    app = Flask(__name__)
    configure_logging(app)
    app.config.update({
        "PROJECT_NAME": "Con5013 Advanced Demo",
        "FEATURE_FLAGS": {
            "RATE_LIMITING": True,
            "BILLING_GUARDRAILS": False,
            "ASYNC_NOTIFICATIONS": True,
        },
    })

    console = Con5013(app, config=CON5013_CONFIG)
    register_console_commands(console, app)
    register_routes(app, console)
    register_additional_log_sources(console)

    return app


if __name__ == "__main__":
    demo_app = create_app()
    demo_app.run(host="127.0.0.1", port=5003, debug=True)
