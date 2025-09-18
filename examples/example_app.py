#!/usr/bin/env python3
"""Con5013 immersive playground example.

This Flask application demonstrates how to integrate the Con5013 console
with a modern landing page that doubles as an interactive guide. The page
covers every module (Logs, Terminal, API, System), exposes quick launchers,
and lets developers experiment with the JavaScript client directly in the
browser.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import textwrap
import time
from datetime import datetime
from typing import Dict, List

from flask import Flask, jsonify, render_template_string, request

# Allow running the example without installing the package first.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from con5013 import Con5013  # noqa: E402  pylint: disable=wrong-import-position


THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "Aurora": {
        "--con5013-primary": "#38bdf8",
        "--con5013-secondary": "#818cf8",
        "--con5013-success": "#22c55e",
        "--con5013-warning": "#facc15",
        "--con5013-error": "#f472b6",
        "--con5013-dark": "#0f172a",
        "--con5013-darker": "#020617",
        "--con5013-border": "rgba(56, 189, 248, 0.42)",
        "--con5013-light": "#f0f9ff",
        "--con5013-text": "#e0f2fe",
        "--con5013-text-muted": "#93c5fd",
        "--con5013-console-bg": "radial-gradient(circle at 18% 12%, rgba(56, 189, 248, 0.35), rgba(8, 47, 73, 0.92) 55%, rgba(2, 6, 23, 0.98))",
        "--con5013-console-border": "rgba(56, 189, 248, 0.55)",
        "--con5013-console-shadow": "0 45px 120px -45px rgba(56, 189, 248, 0.65)",
        "--con5013-console-radius": "28px",
        "--con5013-console-header-bg": "linear-gradient(135deg, rgba(56, 189, 248, 0.92), rgba(129, 140, 248, 0.92))",
        "--con5013-console-tabs-bg": "rgba(2, 6, 23, 0.82)",
        "--con5013-tab-hover-bg": "rgba(56, 189, 248, 0.14)",
        "--con5013-tab-active-bg": "rgba(129, 140, 248, 0.18)",
        "--con5013-tab-active-border": "rgba(56, 189, 248, 0.85)",
        "--con5013-tab-active-color": "#e0f2fe",
        "--con5013-system-card-bg": "linear-gradient(160deg, rgba(14, 116, 144, 0.85), rgba(30, 64, 175, 0.75))",
        "--con5013-system-card-border": "rgba(56, 189, 248, 0.45)",
        "--con5013-system-card-radius": "24px",
        "--con5013-system-card-shadow": "0 30px 60px -45px rgba(56, 189, 248, 0.7)",
        "--con5013-api-stats-bg": "linear-gradient(140deg, rgba(15, 118, 110, 0.7), rgba(59, 130, 246, 0.55))",
        "--con5013-api-stats-border": "rgba(165, 243, 252, 0.45)",
        "--con5013-api-stats-radius": "22px",
        "--con5013-api-stats-shadow": "0 24px 60px -48px rgba(59, 130, 246, 0.75)",
        "--con5013-endpoints-bg": "rgba(8, 47, 73, 0.75)",
        "--con5013-endpoints-border": "rgba(56, 189, 248, 0.35)",
        "--con5013-endpoints-radius": "22px",
        "--con5013-endpoints-shadow": "0 20px 55px -45px rgba(13, 148, 136, 0.6)",
        "--con5013-endpoint-bg": "rgba(15, 118, 110, 0.18)",
        "--con5013-endpoint-divider": "rgba(56, 189, 248, 0.25)",
        "--con5013-terminal-bg": "rgba(8, 47, 73, 0.88)",
        "--con5013-terminal-border": "rgba(56, 189, 248, 0.35)",
        "--con5013-terminal-radius": "20px",
        "--con5013-terminal-shadow": "0 18px 50px -30px rgba(56, 189, 248, 0.45)",
    },
    "Sunset": {
        "--con5013-primary": "#f97316",
        "--con5013-secondary": "#fb7185",
        "--con5013-success": "#34d399",
        "--con5013-warning": "#facc15",
        "--con5013-error": "#f43f5e",
        "--con5013-dark": "#2a1b1f",
        "--con5013-darker": "#160b11",
        "--con5013-border": "rgba(250, 204, 21, 0.45)",
        "--con5013-light": "#fff7ed",
        "--con5013-text": "#fde68a",
        "--con5013-text-muted": "#fbbf24",
        "--con5013-console-bg": "radial-gradient(circle at 80% 0%, rgba(249, 115, 22, 0.65), rgba(185, 28, 28, 0.85) 45%, rgba(46, 16, 16, 0.95))",
        "--con5013-console-border": "rgba(249, 115, 22, 0.55)",
        "--con5013-console-shadow": "0 40px 120px -40px rgba(249, 115, 22, 0.6)",
        "--con5013-console-radius": "34px",
        "--con5013-console-header-bg": "linear-gradient(120deg, rgba(249, 115, 22, 0.95), rgba(244, 63, 94, 0.92))",
        "--con5013-console-tabs-bg": "rgba(22, 11, 17, 0.88)",
        "--con5013-tab-hover-bg": "rgba(249, 115, 22, 0.18)",
        "--con5013-tab-active-bg": "rgba(244, 63, 94, 0.2)",
        "--con5013-tab-active-border": "rgba(250, 204, 21, 0.85)",
        "--con5013-tab-active-color": "#fff7ed",
        "--con5013-system-card-bg": "linear-gradient(160deg, rgba(124, 45, 18, 0.82), rgba(180, 83, 9, 0.85))",
        "--con5013-system-card-border": "rgba(244, 114, 182, 0.4)",
        "--con5013-system-card-radius": "30px",
        "--con5013-system-card-shadow": "0 35px 80px -50px rgba(249, 115, 22, 0.75)",
        "--con5013-api-stats-bg": "linear-gradient(135deg, rgba(244, 63, 94, 0.8), rgba(249, 115, 22, 0.6))",
        "--con5013-api-stats-border": "rgba(251, 191, 36, 0.45)",
        "--con5013-api-stats-radius": "26px",
        "--con5013-api-stats-shadow": "0 26px 70px -48px rgba(251, 191, 36, 0.7)",
        "--con5013-endpoints-bg": "rgba(88, 28, 14, 0.75)",
        "--con5013-endpoints-border": "rgba(249, 115, 22, 0.4)",
        "--con5013-endpoints-radius": "26px",
        "--con5013-endpoints-shadow": "0 24px 60px -48px rgba(239, 68, 68, 0.65)",
        "--con5013-endpoint-bg": "rgba(249, 115, 22, 0.18)",
        "--con5013-endpoint-divider": "rgba(250, 204, 21, 0.35)",
        "--con5013-terminal-bg": "rgba(60, 10, 20, 0.88)",
        "--con5013-terminal-border": "rgba(249, 115, 22, 0.35)",
        "--con5013-terminal-radius": "24px",
        "--con5013-terminal-shadow": "0 20px 55px -35px rgba(244, 63, 94, 0.55)",
    },
    "Neon Matrix": {
        "--con5013-primary": "#22d3ee",
        "--con5013-secondary": "#14b8a6",
        "--con5013-success": "#4ade80",
        "--con5013-warning": "#fde68a",
        "--con5013-error": "#f472b6",
        "--con5013-dark": "#031633",
        "--con5013-darker": "#010b1a",
        "--con5013-border": "rgba(34, 211, 238, 0.38)",
        "--con5013-light": "#ecfeff",
        "--con5013-text": "#ccfbf1",
        "--con5013-text-muted": "#22d3ee",
        "--con5013-console-bg": "radial-gradient(circle at 10% 90%, rgba(20, 184, 166, 0.35), rgba(3, 22, 51, 0.94) 50%, rgba(1, 11, 26, 0.98))",
        "--con5013-console-border": "rgba(34, 211, 238, 0.6)",
        "--con5013-console-shadow": "0 50px 140px -50px rgba(45, 212, 191, 0.7)",
        "--con5013-console-radius": "20px",
        "--con5013-console-header-bg": "linear-gradient(135deg, rgba(34, 211, 238, 0.92), rgba(20, 184, 166, 0.92))",
        "--con5013-console-tabs-bg": "rgba(1, 11, 26, 0.92)",
        "--con5013-tab-hover-bg": "rgba(34, 211, 238, 0.16)",
        "--con5013-tab-active-bg": "rgba(74, 222, 128, 0.16)",
        "--con5013-tab-active-border": "rgba(74, 222, 128, 0.75)",
        "--con5013-tab-active-color": "#ecfeff",
        "--con5013-system-card-bg": "linear-gradient(150deg, rgba(13, 148, 136, 0.8), rgba(59, 130, 246, 0.6))",
        "--con5013-system-card-border": "rgba(34, 211, 238, 0.45)",
        "--con5013-system-card-radius": "18px",
        "--con5013-system-card-shadow": "0 32px 70px -48px rgba(20, 184, 166, 0.7)",
        "--con5013-api-stats-bg": "linear-gradient(135deg, rgba(15, 118, 110, 0.75), rgba(6, 182, 212, 0.6))",
        "--con5013-api-stats-border": "rgba(34, 211, 238, 0.5)",
        "--con5013-api-stats-radius": "20px",
        "--con5013-api-stats-shadow": "0 28px 70px -52px rgba(34, 211, 238, 0.75)",
        "--con5013-endpoints-bg": "rgba(2, 20, 46, 0.85)",
        "--con5013-endpoints-border": "rgba(34, 211, 238, 0.4)",
        "--con5013-endpoints-radius": "20px",
        "--con5013-endpoints-shadow": "0 25px 65px -50px rgba(34, 197, 94, 0.6)",
        "--con5013-endpoint-bg": "rgba(20, 184, 166, 0.14)",
        "--con5013-endpoint-divider": "rgba(34, 211, 238, 0.3)",
        "--con5013-terminal-bg": "rgba(3, 22, 51, 0.88)",
        "--con5013-terminal-border": "rgba(34, 211, 238, 0.4)",
        "--con5013-terminal-radius": "18px",
        "--con5013-terminal-shadow": "0 22px 60px -40px rgba(20, 184, 166, 0.6)",
    },
    "Studio": {
        "--con5013-primary": "#a855f7",
        "--con5013-secondary": "#6366f1",
        "--con5013-success": "#10b981",
        "--con5013-warning": "#fbbf24",
        "--con5013-error": "#f87171",
        "--con5013-dark": "#111827",
        "--con5013-darker": "#0b1120",
        "--con5013-border": "rgba(129, 140, 248, 0.38)",
        "--con5013-light": "#f5f3ff",
        "--con5013-text": "#ede9fe",
        "--con5013-text-muted": "#c4b5fd",
        "--con5013-console-bg": "radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.4), rgba(15, 23, 42, 0.95) 60%, rgba(11, 17, 32, 0.98))",
        "--con5013-console-border": "rgba(129, 140, 248, 0.55)",
        "--con5013-console-shadow": "0 48px 120px -48px rgba(129, 140, 248, 0.65)",
        "--con5013-console-radius": "32px",
        "--con5013-console-header-bg": "linear-gradient(135deg, rgba(168, 85, 247, 0.95), rgba(99, 102, 241, 0.95))",
        "--con5013-console-tabs-bg": "rgba(11, 17, 32, 0.9)",
        "--con5013-tab-hover-bg": "rgba(168, 85, 247, 0.16)",
        "--con5013-tab-active-bg": "rgba(99, 102, 241, 0.2)",
        "--con5013-tab-active-border": "rgba(129, 140, 248, 0.85)",
        "--con5013-tab-active-color": "#ede9fe",
        "--con5013-system-card-bg": "linear-gradient(150deg, rgba(76, 29, 149, 0.85), rgba(129, 140, 248, 0.65))",
        "--con5013-system-card-border": "rgba(196, 181, 253, 0.45)",
        "--con5013-system-card-radius": "28px",
        "--con5013-system-card-shadow": "0 34px 80px -52px rgba(129, 140, 248, 0.7)",
        "--con5013-api-stats-bg": "linear-gradient(140deg, rgba(79, 70, 229, 0.75), rgba(167, 139, 250, 0.6))",
        "--con5013-api-stats-border": "rgba(168, 85, 247, 0.45)",
        "--con5013-api-stats-radius": "28px",
        "--con5013-api-stats-shadow": "0 30px 80px -52px rgba(139, 92, 246, 0.7)",
        "--con5013-endpoints-bg": "rgba(30, 27, 75, 0.8)",
        "--con5013-endpoints-border": "rgba(129, 140, 248, 0.4)",
        "--con5013-endpoints-radius": "28px",
        "--con5013-endpoints-shadow": "0 26px 70px -50px rgba(168, 85, 247, 0.65)",
        "--con5013-endpoint-bg": "rgba(129, 140, 248, 0.18)",
        "--con5013-endpoint-divider": "rgba(196, 181, 253, 0.35)",
        "--con5013-terminal-bg": "rgba(30, 27, 75, 0.9)",
        "--con5013-terminal-border": "rgba(139, 92, 246, 0.4)",
        "--con5013-terminal-radius": "26px",
        "--con5013-terminal-shadow": "0 24px 70px -45px rgba(129, 140, 248, 0.6)",
    },
}


def create_app() -> Flask:
    """Build and configure the Flask demonstration app."""

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="con5013-example-secret",
        JSON_SORT_KEYS=False,
    )

    # Set up structured logging so the Logs tab has rich data to work with.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app.logger.setLevel(logging.INFO)

    environment = os.getenv("FLASK_ENV", "development")
    security_profile = "secured" if environment == "production" else "open"

    console = Con5013(
        app,
        config={
            "CON5013_THEME": "dark",
            "CON5013_ENABLE_LOGS": True,
            "CON5013_ENABLE_TERMINAL": True,
            "CON5013_ENABLE_API_SCANNER": True,
            "CON5013_ENABLE_SYSTEM_MONITOR": True,
            "CON5013_LOG_SOURCES": ["example_app.log"],
            "CON5013_MONITOR_GPU": True,
            "CON5013_SYSTEM_CUSTOM_BOXES": [],
            "CON5013_SECURITY_PROFILE": security_profile,
        },
    )

    if security_profile == "secured":
        # Keep the interactive terminal available during demos while the
        # profile hardens other features such as log clearing and auto-inject.
        console.apply_security_profile("secured", extra_overrides={"CON5013_ENABLE_TERMINAL"})
        console.config["CON5013_ENABLE_TERMINAL"] = True

    # Attach an additional logger so the Logs tab showcases multiple sources.
    worker_logger = logging.getLogger("demo.worker")
    worker_logger.setLevel(logging.INFO)
    if console.log_monitor:
        console.log_monitor.attach_logger("demo.worker", alias="worker")

    # Register a dynamic custom system card to emphasise extensibility.
    def demo_pulse_box() -> Dict[str, object]:
        horizon = random.randint(12, 48)
        load = random.uniform(35, 92)
        return {
            "title": "Demo Pulse",
            "rows": [
                {"name": "Orchestrations", "value": f"{random.randint(4, 18)} active"},
                {
                    "name": "Job Throughput",
                    "value": f"{random.randint(320, 720)} rows/min",
                    "progress": {"value": random.randint(55, 96)},
                },
                {
                    "name": "Batch Window",
                    "value": f"{horizon} min",
                    "progress": {"value": min(horizon * 2, 100)},
                },
                {
                    "name": "Synthetic Load",
                    "value": f"{load:.1f}%",
                    "progress": {"value": int(load)},
                },
            ],
            "description": "Synthetic metrics generated by example_app to illustrate custom boxes.",
        }

    console.add_system_box("demo-pulse", provider=demo_pulse_box, order=10)

    # Expose a custom terminal command that returns a curated insight report.
    @console.terminal_engine.command("demo:insight")
    def demo_insight_command(args: List[str]):
        """Summarise demo application health directly inside the terminal."""

        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "features": {
                "logs": "enabled",
                "terminal": "enabled",
                "api_scanner": "enabled",
                "system_monitor": "enabled",
            },
            "next_steps": [
                "Toggle modules in the playground to see tabs appear/disappear",
                "Open the API tab and batch-test the /demo routes",
                "Use the Theme Playground to restyle the overlay in real-time",
            ],
        }

        pretty = json.dumps(summary, indent=2)
        return {
            "output": pretty,
            "type": "text",
            "description": "Formatted JSON so the terminal auto-detects the structure.",
        }

    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    """Register demonstration routes and the interactive landing page."""

    @app.route("/")
    def index():
        html = render_template_string(
            LANDING_TEMPLATE,
            theme_presets=THEME_PRESETS,
            server_config_snippet=textwrap.dedent(
                """
                from con5013 import Con5013

                console = Con5013(app, config={
                    "CON5013_THEME": "dark",
                    "CON5013_ENABLE_LOGS": True,
                    "CON5013_ENABLE_TERMINAL": True,
                    "CON5013_ENABLE_API_SCANNER": True,
                    "CON5013_ENABLE_SYSTEM_MONITOR": True,
                    "CON5013_LOG_SOURCES": ["example_app.log"],
                })
                """
            ).strip(),
        )
        return html

    @app.post("/demo/log-burst")
    def demo_log_burst():
        levels = [logging.INFO, logging.WARNING, logging.ERROR]
        messages = [
            "Cache warm completed",
            "Connected to upstream data provider",
            "Scheduled batch enqueued",
            "Synthetic anomaly detected",
            "Worker heartbeat is healthy",
        ]
        count = int(request.json.get("count", 5)) if request.is_json else 5
        count = max(1, min(count, 25))
        for _ in range(count):
            level = random.choice(levels)
            message = random.choice(messages)
            logging.getLogger("demo.worker").log(level, "%s (burst)", message)
            logging.getLogger("example_app").log(level, "%s (example)", message)
        return jsonify({"status": "ok", "count": count})

    @app.get("/demo/api/users")
    def demo_users() -> Dict[str, object]:
        data = [
            {"id": 101, "name": "Ada Lovelace", "role": "architect"},
            {"id": 102, "name": "Alan Turing", "role": "analyst"},
            {"id": 103, "name": "Grace Hopper", "role": "systems"},
        ]
        return {"users": data, "count": len(data)}

    @app.post("/demo/api/users")
    def create_demo_user():
        payload = request.get_json(silent=True) or {}
        user = {
            "id": random.randint(200, 999),
            "name": payload.get("name", "New Teammate"),
            "role": payload.get("role", "observer"),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        logging.getLogger("demo.worker").info("Provisioned demo user %s", user["name"])
        return jsonify({"status": "created", "user": user}), 201

    @app.get("/demo/api/health")
    def demo_health():
        return {
            "status": "green",
            "uptime_seconds": round(time.time() - app.start_time, 2),
            "features": ["logs", "terminal", "api", "system"],
        }

    @app.get("/demo/api/slow")
    def demo_slow_endpoint():
        time.sleep(0.6)
        return {"status": "ok", "duration": 0.6}


LANDING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Con5013 • Interactive Example Console</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            color-scheme: dark;
            --con5013-console-bg: linear-gradient(135deg, rgba(17, 24, 39, 0.96), rgba(15, 23, 42, 0.96));
            --con5013-console-border: rgba(99, 102, 241, 0.35);
            --con5013-console-shadow: 0 30px 90px -45px rgba(15, 23, 42, 0.8);
            --con5013-console-radius: 18px;
            --con5013-console-header-bg: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(139, 92, 246, 0.95));
            --con5013-console-tabs-bg: rgba(17, 24, 39, 0.9);
            --con5013-tab-hover-bg: rgba(148, 163, 184, 0.08);
            --con5013-tab-active-bg: rgba(99, 102, 241, 0.16);
            --con5013-tab-active-border: var(--con5013-primary);
            --con5013-tab-active-color: var(--con5013-primary);
            --con5013-system-card-bg: rgba(17, 24, 39, 0.92);
            --con5013-system-card-border: rgba(148, 163, 184, 0.35);
            --con5013-system-card-radius: 16px;
            --con5013-system-card-shadow: none;
            --con5013-api-stats-bg: rgba(17, 24, 39, 0.9);
            --con5013-api-stats-border: rgba(148, 163, 184, 0.35);
            --con5013-api-stats-radius: 16px;
            --con5013-api-stats-shadow: none;
            --con5013-endpoints-bg: rgba(15, 23, 42, 0.85);
            --con5013-endpoints-border: rgba(148, 163, 184, 0.35);
            --con5013-endpoints-radius: 16px;
            --con5013-endpoints-shadow: none;
            --con5013-endpoint-bg: transparent;
            --con5013-endpoint-divider: rgba(148, 163, 184, 0.25);
            --con5013-terminal-bg: rgba(15, 23, 42, 0.9);
            --con5013-terminal-border: rgba(148, 163, 184, 0.35);
            --con5013-terminal-radius: 16px;
            --con5013-terminal-shadow: none;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: radial-gradient(circle at top, #1f2937 0%, #0f172a 35%, #020617 100%);
            color: #f8fafc;
            display: flex;
            flex-direction: column;
        }
        main { flex: 1; padding: 72px 24px 96px; }
        h1, h2, h3 { margin: 0; }
        p { color: #cbd5f5; line-height: 1.6; }
        a { color: #38bdf8; }
        .hero {
            max-width: 1040px;
            margin: 0 auto 64px;
            text-align: center;
        }
        .hero h1 {
            font-size: clamp(2.8rem, 4vw, 4rem);
            font-weight: 700;
            letter-spacing: -0.03em;
            color: #f8fafc;
        }
        .hero p {
            margin: 24px auto 0;
            font-size: 1.1rem;
            max-width: 760px;
        }
        .glass-panel {
            background: linear-gradient(135deg, rgba(148,163,184,0.14), rgba(15,23,42,0.42));
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 28px;
            padding: 32px;
            backdrop-filter: blur(16px);
            box-shadow: 0 32px 80px -32px rgba(15, 23, 42, 0.65);
            margin: 0 auto 40px;
            max-width: 1100px;
        }
        .panel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 24px;
        }
        .panel-title h2 {
            font-size: 1.6rem;
            font-weight: 600;
        }
        .launch-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
        }
        .launch-button {
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(15, 23, 42, 0.7);
            color: #f8fafc;
            padding: 18px 22px;
            border-radius: 18px;
            text-align: left;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            gap: 12px;
            transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
        }
        .launch-button span.label {
            font-size: 1.05rem;
            font-weight: 600;
        }
        .launch-button span.helper { color: #94a3b8; font-size: 0.95rem; }
        .launch-button:hover {
            transform: translateY(-4px);
            border-color: rgba(56, 189, 248, 0.7);
            background: rgba(15, 23, 42, 0.9);
        }
        .playground-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 24px;
        }
        .card {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 24px;
            background: rgba(15, 23, 42, 0.6);
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .card h3 {
            font-size: 1.2rem;
            font-weight: 600;
            color: #f8fafc;
        }
        select, input[type="text"], textarea {
            width: 100%;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.4);
            background: rgba(15, 23, 42, 0.8);
            color: #f8fafc;
            font-family: inherit;
        }
        label.toggle {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(148, 163, 184, 0.08);
        }
        label.toggle span { color: #e2e8f0; }
        .tag-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 24px;
            margin-top: 12px;
        }
        .tab-card {
            border-radius: 24px;
            border: 1px solid rgba(148, 163, 184, 0.28);
            background: rgba(15, 23, 42, 0.7);
            padding: 24px;
        }
        .tab-card h3 { font-size: 1.25rem; margin-bottom: 12px; }
        .tab-card ul { margin: 0; padding-left: 20px; color: #cbd5f5; }
        .tab-card li { margin-bottom: 8px; }
        pre.code-block {
            background: rgba(15, 23, 42, 0.85);
            border-radius: 18px;
            padding: 20px;
            color: #e2e8f0;
            border: 1px solid rgba(148, 163, 184, 0.28);
            overflow-x: auto;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        .theme-preview {
            border-radius: 18px;
            border: 1px dashed rgba(56, 189, 248, 0.45);
            padding: 16px;
            background: rgba(8, 47, 73, 0.35);
            font-family: 'Courier New', monospace;
            color: #bae6fd;
            font-size: 0.9rem;
        }
        /* Con5013 console theming playground */
        body .con5013-console {
            background: var(--con5013-console-bg);
            border: 1px solid var(--con5013-console-border);
            border-radius: var(--con5013-console-radius);
            box-shadow: var(--con5013-console-shadow);
            backdrop-filter: blur(18px);
        }
        body .con5013-header {
            background: var(--con5013-console-header-bg);
        }
        body .con5013-tabs {
            background: var(--con5013-console-tabs-bg);
        }
        body .con5013-tab:hover {
            background: var(--con5013-tab-hover-bg);
        }
        body .con5013-tab.active {
            background: var(--con5013-tab-active-bg);
            border-bottom-color: var(--con5013-tab-active-border);
            color: var(--con5013-tab-active-color);
        }
        body .con5013-terminal {
            background: var(--con5013-terminal-bg);
            border: 1px solid var(--con5013-terminal-border);
            border-radius: var(--con5013-terminal-radius);
            box-shadow: var(--con5013-terminal-shadow);
            backdrop-filter: blur(14px);
        }
        body .con5013-system-card {
            background: var(--con5013-system-card-bg);
            border: 1px solid var(--con5013-system-card-border);
            border-radius: var(--con5013-system-card-radius);
            box-shadow: var(--con5013-system-card-shadow);
        }
        body .con5013-api-stats {
            background: var(--con5013-api-stats-bg);
            border: 1px solid var(--con5013-api-stats-border);
            border-radius: var(--con5013-api-stats-radius);
            box-shadow: var(--con5013-api-stats-shadow);
        }
        body .con5013-endpoints {
            background: var(--con5013-endpoints-bg);
            border: 1px solid var(--con5013-endpoints-border);
            border-radius: var(--con5013-endpoints-radius);
            box-shadow: var(--con5013-endpoints-shadow);
            overflow: hidden;
        }
        body .con5013-endpoint {
            background: var(--con5013-endpoint-bg);
            border-bottom: 1px solid var(--con5013-endpoint-divider);
        }
        body .con5013-endpoint:last-child {
            border-bottom: none;
        }
        .footer {
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 64px;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            border-radius: 12px;
            background: rgba(148, 163, 184, 0.15);
            border: 1px solid rgba(148, 163, 184, 0.25);
            font-size: 0.85rem;
            color: #e2e8f0;
        }
        button.inline {
            border: none;
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            padding: 10px 14px;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.2s ease;
            font-weight: 500;
        }
        button.inline:hover { background: rgba(56, 189, 248, 0.22); }
        @media (max-width: 720px) {
            main { padding: 48px 18px 72px; }
            .glass-panel { padding: 24px; }
        }
    </style>
</head>
<body>
    <main>
        <section class="hero">
            <h1>Meet the Con5013 Playground</h1>
            <p>Launch the console instantly, explore how every tab works, and restyle the glassmorphism overlay without leaving the page. This demo pairs live Con5013 telemetry with narrative guidance so you can master the Logs, Terminal, API, and System modules in minutes.</p>
        </section>

        <section class="glass-panel">
            <div class="panel-title">
                <h2>Quick launchers</h2>
                <span class="badge">Hotkey: Alt + C</span>
            </div>
            <div class="launch-grid">
                <button class="launch-button" id="open-default">
                    <span class="label">Open overlay</span>
                    <span class="helper">Shows the last active tab with your selected theme.</span>
                </button>
                <button class="launch-button" id="open-logs">
                    <span class="label">Jump to Logs</span>
                    <span class="helper">Observe live entries, switch sources, and export snapshots.</span>
                </button>
                <button class="launch-button" id="open-terminal">
                    <span class="label">Run demo:insight</span>
                    <span class="helper">Opens the Terminal and executes the custom command.</span>
                </button>
                <button class="launch-button" id="open-api">
                    <span class="label">Explore API Map</span>
                    <span class="helper">Loads discovery results for all /demo endpoints.</span>
                </button>
            </div>
        </section>

        <section class="glass-panel">
            <div class="panel-title">
                <h2>Overlay playground</h2>
                <button class="inline" id="generate-logs">Generate log burst</button>
            </div>
            <div class="playground-grid">
                <div class="card">
                    <h3>Theme playground</h3>
                    <p>Switch presets to rewrite the CSS variables that power <code>con5013.css</code>. The overlay updates instantly.</p>
                    <select id="theme-select">
                        {% for name, _ in theme_presets | dictsort %}
                        <option value="{{ name }}">{{ name }}</option>
                        {% endfor %}
                    </select>
                    <div class="theme-preview" id="theme-preview"></div>
                </div>
                <div class="card">
                    <h3>Module toggles</h3>
                    <p>Mirror feature-flagging logic from configuration without restarting the app.</p>
                    <label class="toggle"><span>Logs tab</span><input type="checkbox" data-module-toggle="logs" checked></label>
                    <label class="toggle"><span>Terminal tab</span><input type="checkbox" data-module-toggle="terminal" checked></label>
                    <label class="toggle"><span>API tab</span><input type="checkbox" data-module-toggle="api_scanner" checked></label>
                    <label class="toggle"><span>System tab</span><input type="checkbox" data-module-toggle="system_monitor" checked></label>
                </div>
                <div class="card">
                    <h3>Floating button</h3>
                    <p>Place the FAB anywhere on screen or hide it when you wire your own launcher.</p>
                    <label class="toggle"><span>Bottom right</span><input type="radio" name="fab" value="bottom-right" checked></label>
                    <label class="toggle"><span>Bottom left</span><input type="radio" name="fab" value="bottom-left"></label>
                    <label class="toggle"><span>Top right</span><input type="radio" name="fab" value="top-right"></label>
                    <label class="toggle"><span>Top left</span><input type="radio" name="fab" value="top-left"></label>
                    <label class="toggle"><span>Hide FAB</span><input type="checkbox" id="fab-visibility" checked></label>
                </div>
                <div class="card">
                    <h3>System metrics focus</h3>
                    <p>Toggle individual cards to curate your operational dashboard.</p>
                    <label class="toggle"><span>System info</span><input type="checkbox" data-metric-toggle="system_info" checked></label>
                    <label class="toggle"><span>Application</span><input type="checkbox" data-metric-toggle="application" checked></label>
                    <label class="toggle"><span>CPU</span><input type="checkbox" data-metric-toggle="cpu" checked></label>
                    <label class="toggle"><span>Memory</span><input type="checkbox" data-metric-toggle="memory" checked></label>
                    <label class="toggle"><span>Disk</span><input type="checkbox" data-metric-toggle="disk" checked></label>
                    <label class="toggle"><span>Network</span><input type="checkbox" data-metric-toggle="network" checked></label>
                    <label class="toggle"><span>GPU</span><input type="checkbox" data-metric-toggle="gpu" checked></label>
                </div>
            </div>
        </section>

        <section class="glass-panel">
            <div class="panel-title">
                <h2>Understand each module</h2>
            </div>
            <div class="tag-grid">
                <div class="tab-card">
                    <h3>Logs</h3>
                    <p>Streams Python logging output, file-backed sources, and attached loggers into a searchable timeline.</p>
                    <ul>
                        <li>Configure sources with <code>CON5013_LOG_SOURCES</code> or attach them programmatically.</li>
                        <li>Filter by level, export views, and pause auto-scroll when investigating incidents.</li>
                        <li>Use the REST endpoints under <code>/con5013/api/logs</code> to automate log retrieval.</li>
                    </ul>
                </div>
                <div class="tab-card">
                    <h3>Terminal</h3>
                    <p>Execute curated commands with history, HTTP helpers, and optional Python evaluation.</p>
                    <ul>
                        <li>Register custom commands via <code>@console.terminal_engine.command</code>.</li>
                        <li>Enable Python evaluation with <code>CON5013_TERMINAL_ALLOW_PY</code> when needed.</li>
                        <li>Automate runs using <code>openCon5013Console({ command })</code> from your own UI.</li>
                    </ul>
                </div>
                <div class="tab-card">
                    <h3>API</h3>
                    <p>Discovers Flask routes, generates sample paths, and batch-tests endpoints with timing metrics.</p>
                    <ul>
                        <li>Protect sensitive routes using <code>CON5013_API_PROTECTED_ENDPOINTS</code>.</li>
                        <li>Invoke discovery programmatically at <code>/con5013/api/scanner/discover</code>.</li>
                        <li>Export reports to CI/CD by calling <code>/test-all</code> after deployments.</li>
                    </ul>
                </div>
                <div class="tab-card">
                    <h3>System</h3>
                    <p>Displays CPU, memory, disk, and network telemetry with optional GPU and custom metric cards.</p>
                    <ul>
                        <li>Toggle collectors with <code>CON5013_MONITOR_*</code> flags per environment.</li>
                        <li>Inject domain-specific data via <code>console.add_system_box(...)</code>.</li>
                        <li>Query live metrics from <code>/con5013/api/system/stats</code> and <code>/health</code>.</li>
                    </ul>
                </div>
            </div>
        </section>

        <section class="glass-panel">
            <div class="panel-title">
                <h2>Server-side wiring</h2>
            </div>
            <pre class="code-block">{{ server_config_snippet }}</pre>
            <p>Drop the JavaScript client on any template where you want instant access to the overlay:</p>
            <pre class="code-block">&lt;script src="/con5013/static/js/con5013.js" data-con5013-hotkey="Alt+C"&gt;&lt;/script&gt;</pre>
        </section>

        <div class="footer">
            Con5013 ships with overlay mode, REST endpoints, and customization hooks out of the box. Mix and match them to fit your workflow.
        </div>
    </main>

    <script>
        window.CON5013_OPTIONS = {
            floatingButtonPosition: 'bottom-right',
            hideFabWhenOpen: true,
            autoFloatingButton: true,
        };
    </script>
    <script src="/con5013/static/js/con5013.js" data-con5013-hotkey="Alt+C"></script>
    <script>
        const themePresets = {{ theme_presets | tojson }};

        function renderThemePreview(presetName) {
            const preview = document.getElementById('theme-preview');
            if (!preview) return;

            const preset = themePresets[presetName] || {};
            const lines = Object.entries(preset).map(([key, value]) => `${key}: ${value};`);
            const formatted = [':root'].concat(lines.map((line) => '  ' + line)).join('\\n');

            preview.textContent = formatted;
        }


        function applyTheme(presetName) {
            const preset = themePresets[presetName] || {};
            Object.entries(preset).forEach(([key, value]) => {
                document.documentElement.style.setProperty(key, value);
            });
            renderThemePreview(presetName);
        }

        function withConsoleReady(callback) {
            if (window.con5013) {
                callback(window.con5013);
                return;
            }
            window.addEventListener('con5013:ready', (event) => {
                callback(event.detail.instance);
            }, { once: true });
        }

        function syncModuleToggles(instance) {
            document.querySelectorAll('[data-module-toggle]').forEach((input) => {
                const key = input.getAttribute('data-module-toggle');
                if (!key) return;
                input.checked = !!instance.features[key];
            });
        }

        function syncMetricToggles(instance) {
            document.querySelectorAll('[data-metric-toggle]').forEach((input) => {
                const key = input.getAttribute('data-metric-toggle');
                if (!key) return;
                input.checked = instance.systemMetrics[key] !== false;
            });
        }

        document.getElementById('theme-select').addEventListener('change', (event) => {
            applyTheme(event.target.value);
        });

        document.querySelectorAll('[data-module-toggle]').forEach((input) => {
            input.addEventListener('change', () => {
                withConsoleReady((instance) => {
                    const key = input.getAttribute('data-module-toggle');
                    instance.features[key] = input.checked;
                    instance.applyFeatureToggles();
                });
            });
        });

        document.querySelectorAll('[data-metric-toggle]').forEach((input) => {
            input.addEventListener('change', () => {
                withConsoleReady((instance) => {
                    const key = input.getAttribute('data-metric-toggle');
                    instance.systemMetrics[key] = input.checked;
                    instance.applySystemMetricToggles();
                });
            });
        });

        document.querySelectorAll('input[name="fab"]').forEach((input) => {
            input.addEventListener('change', () => {
                if (!input.checked) return;
                withConsoleReady((instance) => {
                    instance.options.floatingButtonPosition = input.value;
                    const fab = document.getElementById('con5013-fab');
                    if (fab) {
                        fab.className = `con5013-fab ${input.value}`;
                    }
                });
            });
        });

        document.getElementById('fab-visibility').addEventListener('change', (event) => {
            withConsoleReady((instance) => {
                instance.options.autoFloatingButton = event.target.checked;
                const fab = document.getElementById('con5013-fab');
                if (event.target.checked) {
                    if (!fab) {
                        instance.createFloatingButton();
                    } else {
                        fab.style.display = '';
                    }
                } else if (fab) {
                    fab.style.display = 'none';
                }
            });
        });

        document.getElementById('open-default').addEventListener('click', () => {
            openCon5013Console();
        });
        document.getElementById('open-logs').addEventListener('click', () => {
            openCon5013Console({ tab: 'logs' });
        });
        document.getElementById('open-terminal').addEventListener('click', () => {
            openCon5013Console({ tab: 'terminal', command: 'demo:insight', previewDelay: 260 });
        });
        document.getElementById('open-api').addEventListener('click', () => {
            openCon5013Console({ tab: 'api' });
        });

        document.getElementById('generate-logs').addEventListener('click', async () => {
            const button = document.getElementById('generate-logs');
            button.disabled = true;
            try {
                await fetch('/demo/log-burst', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ count: 6 })
                });
            } finally {
                button.disabled = false;
            }
        });

        withConsoleReady((instance) => {
            applyTheme(document.getElementById('theme-select').value);
            syncModuleToggles(instance);
            syncMetricToggles(instance);
        });

        // Initial theme preview for first render.
        applyTheme(document.getElementById('theme-select').value);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5003)
