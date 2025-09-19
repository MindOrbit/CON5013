"""Secure Con5013 integration example.

This file now doubles as an interactive experience that explains how to deploy
the ``secured`` profile in production. Launch the application and follow the
guided tour at ``http://localhost:5000`` to explore the hardening choices,
authentication strategies, and observability surface.

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
auto-injection, etc.). This script selectively re-enables logs and the system
monitor because operators typically need read-only visibility in production.
The accompanying walkthrough surfaces each decision so teams can adapt the
configuration to match their operational requirements.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template_string, request

from con5013 import Con5013


EXPERIENCE_STEPS = [
    {
        "id": "profile",
        "title": "Start from the secured profile",
        "lede": "Inspect the guardrails that production deployments inherit by default.",
        "endpoint": "/demo/security-profile",
    },
    {
        "id": "auth",
        "title": "Choose an authentication strategy",
        "lede": "Compare basic, token, and callback auth flows for the embedded console.",
        "endpoint": "/demo/auth",
    },
    {
        "id": "observability",
        "title": "Review operator observability",
        "lede": "See which read-only panels stay enabled to help on-call engineers.",
        "endpoint": "/demo/observability",
    },
    {
        "id": "audit",
        "title": "Walk through a secure session",
        "lede": "Replay a sample operator session and the audit artefacts it leaves behind.",
        "endpoint": "/demo/audit-log",
    },
]


LANDING_TEMPLATE = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <title>CON5013 · Secure Production Console Demo</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <style>
      :root {
        color-scheme: dark;
        --bg: #070a15;
        --card: rgba(19, 28, 56, 0.72);
        --card-border: rgba(80, 130, 255, 0.35);
        --accent: #60a5fa;
        --accent-strong: #3b82f6;
        --muted: rgba(148, 163, 184, 0.82);
        --success: #34d399;
        --warning: #fbbf24;
        --danger: #f87171;
        --font: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 45%),
                    radial-gradient(circle at 10% 80%, rgba(14, 116, 144, 0.22), transparent 55%),
                    var(--bg);
        color: #e2e8f0;
        font-family: var(--font);
        padding: 48px clamp(24px, 6vw, 72px);
        display: flex;
        align-items: flex-start;
        justify-content: center;
      }

      main {
        width: min(1100px, 100%);
        display: grid;
        gap: 32px;
      }

      header.hero {
        background: var(--card);
        border: 1px solid var(--card-border);
        border-radius: 28px;
        padding: clamp(24px, 4vw, 40px);
        box-shadow: 0 40px 120px -60px rgba(56, 189, 248, 0.4);
      }

      header.hero h1 {
        margin: 0 0 12px;
        font-size: clamp(2.2rem, 4vw, 3rem);
        line-height: 1.05;
      }

      header.hero p.lede {
        margin: 0;
        color: var(--muted);
        font-size: 1.04rem;
        max-width: 720px;
      }

      .layout {
        display: grid;
        grid-template-columns: minmax(240px, 300px) 1fr;
        gap: 28px;
      }

      aside.timeline {
        display: flex;
        flex-direction: column;
        gap: 16px;
        position: sticky;
        top: 48px;
        align-self: start;
      }

      button.step {
        background: rgba(13, 21, 44, 0.88);
        border: 1px solid rgba(59, 130, 246, 0.25);
        border-radius: 18px;
        padding: 18px 20px;
        text-align: left;
        color: inherit;
        cursor: pointer;
        display: flex;
        gap: 14px;
        align-items: center;
        transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
      }

      button.step .index {
        display: inline-flex;
        width: 32px;
        height: 32px;
        border-radius: 12px;
        align-items: center;
        justify-content: center;
        background: rgba(59, 130, 246, 0.22);
        border: 1px solid rgba(59, 130, 246, 0.45);
        font-weight: 600;
        color: var(--accent);
      }

      button.step strong {
        display: block;
        font-size: 1.02rem;
      }

      button.step span.lede {
        color: var(--muted);
        font-size: 0.88rem;
      }

      button.step:hover {
        transform: translateX(4px);
        border-color: rgba(96, 165, 250, 0.65);
        background: rgba(15, 32, 65, 0.95);
      }

      button.step.active {
        border-color: rgba(96, 165, 250, 0.85);
        box-shadow: 0 22px 60px -45px rgba(56, 189, 248, 0.55);
        background: linear-gradient(140deg, rgba(30, 64, 175, 0.75), rgba(37, 99, 235, 0.55));
      }

      article.panel {
        min-height: 520px;
        background: rgba(9, 16, 35, 0.78);
        border-radius: 26px;
        border: 1px solid rgba(96, 165, 250, 0.25);
        padding: clamp(24px, 4vw, 40px);
        backdrop-filter: blur(14px);
        box-shadow: 0 36px 120px -65px rgba(37, 99, 235, 0.55);
      }

      article.panel h2 {
        margin: 0 0 16px;
        font-size: clamp(1.6rem, 3vw, 2rem);
      }

      article.panel p {
        color: var(--muted);
        line-height: 1.55;
        margin: 0 0 16px;
      }

      .highlights {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin: 0 0 16px;
      }

      .highlight {
        background: rgba(15, 31, 64, 0.92);
        border: 1px solid rgba(96, 165, 250, 0.35);
        border-radius: 18px;
        padding: 16px 18px;
      }

      .highlight span.label {
        display: block;
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .highlight strong {
        display: block;
        margin-top: 6px;
        font-size: 1.08rem;
      }

      .highlight p {
        margin: 8px 0 0;
        font-size: 0.88rem;
        line-height: 1.45;
      }

      ul.bullets {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 10px;
      }

      ul.bullets li {
        background: rgba(10, 22, 50, 0.92);
        border: 1px solid rgba(96, 165, 250, 0.28);
        padding: 14px 16px;
        border-radius: 16px;
        line-height: 1.5;
      }

      .kbd, code.inline {
        font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        background: rgba(15, 23, 42, 0.75);
        border-radius: 8px;
        padding: 2px 6px;
        border: 1px solid rgba(96, 165, 250, 0.35);
        font-size: 0.86rem;
      }

      .timeline-tip {
        margin-top: auto;
        font-size: 0.85rem;
        color: var(--muted);
        line-height: 1.45;
      }

      .cta {
        margin-top: 24px;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 12px 18px;
        border-radius: 14px;
        background: rgba(45, 212, 191, 0.12);
        border: 1px solid rgba(34, 211, 238, 0.4);
        color: #5eead4;
        text-decoration: none;
        font-weight: 600;
      }

      footer {
        text-align: center;
        font-size: 0.84rem;
        color: var(--muted);
      }

      footer code {
        background: rgba(15, 23, 42, 0.75);
        border-radius: 6px;
        padding: 2px 6px;
        border: 1px solid rgba(96, 165, 250, 0.25);
      }

      @media (max-width: 960px) {
        body {
          padding: 32px 20px;
        }

        .layout {
          grid-template-columns: 1fr;
        }

        aside.timeline {
          position: static;
          flex-direction: row;
          overflow-x: auto;
          padding-bottom: 4px;
        }

        button.step {
          min-width: 260px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <header class=\"hero\">
        <h1>Experience the secured CON5013 deployment</h1>
        <p class=\"lede\">Follow the guided steps to understand how CON5013 stays safe in production: explore the hardened profile, test the available authentication flows, and see which observability windows remain open for your operators.</p>
      </header>
      <section class=\"layout\">
        <aside class=\"timeline\">
          {% for step in steps %}
          <button class=\"step\" data-endpoint=\"{{ step.endpoint }}\" data-step-id=\"{{ step.id }}\">
            <span class=\"index\">{{ loop.index }}</span>
            <span>
              <strong>{{ step.title }}</strong>
              <span class=\"lede\">{{ step.lede }}</span>
            </span>
          </button>
          {% endfor %}
          <p class=\"timeline-tip\">Tip: keep this window open next to your CON5013 console to follow along as you authenticate and explore.</p>
        </aside>
        <article class=\"panel\" id=\"experience-panel\">
          <h2>Launch the interactive tour</h2>
          <p>Start the Flask app with <span class=\"kbd\">flask --app examples.secure_production_app run</span> and open the CON5013 interface in a new tab. Select a step to reveal configuration insights, recommended environment variables, and curated callouts that explain how the secured profile behaves.</p>
          <ul class=\"bullets\">
            <li>Every card on the left issues a live request to the Flask backend—exactly what your operators would use.</li>
            <li>Use the <code class=\"inline\">/whoami</code> route or the callback headers to try different operator roles.</li>
            <li>Ready to ship? Copy the snippets and add them to your deployment manifests.</li>
          </ul>
        </article>
      </section>
      <footer>
        Need a quickstart? Combine this walkthrough with <code>CON5013_SECURITY_PROFILE=secured</code> in your environment configuration.
      </footer>
    </main>
    <script>
      const panel = document.getElementById('experience-panel');
      const buttons = Array.from(document.querySelectorAll('button.step'));

      function highlight(button) {
        buttons.forEach((btn) => btn.classList.toggle('active', btn === button));
      }

      function renderHighlights(highlights) {
        if (!Array.isArray(highlights) || !highlights.length) {
          return '';
        }

        return `<div class="highlights">${highlights.map((item) => `
          <div class="highlight">
            <span class="label">${item.label ?? ''}</span>
            <strong>${item.value ?? ''}</strong>
            ${item.description ? `<p>${item.description}</p>` : ''}
          </div>
        `).join('')}</div>`;
      }

      function renderList(items, className = 'bullets') {
        if (!Array.isArray(items) || !items.length) {
          return '';
        }

        return `<ul class="${className}">${items.map((item) => `<li>${item}</li>`).join('')}</ul>`;
      }

      function renderActions(actions) {
        if (!Array.isArray(actions) || !actions.length) {
          return '';
        }

        return actions.map((action) => `<a class="cta" href="${action.href}" target="_blank" rel="noreferrer">${action.label}</a>`).join('');
      }

      function renderTimeline(events) {
        if (!Array.isArray(events) || !events.length) {
          return '';
        }

        return `<div class="timeline-block">${events.map((event) => `
          <div class="highlight" style="border-color: rgba(148, 163, 184, 0.35); background: rgba(15, 23, 42, 0.85);">
            <span class="label">${event.time ?? ''}</span>
            <strong>${event.actor ?? ''}</strong>
            <p>${event.action ?? ''}</p>
          </div>
        `).join('')}</div>`;
      }

      async function loadExperience(button) {
        const endpoint = button.dataset.endpoint;

        try {
          const response = await fetch(endpoint, { headers: { 'Accept': 'application/json' } });
          if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
          }

          const data = await response.json();
          highlight(button);

          panel.innerHTML = `
            <h2>${data.title ?? 'Secure deployment highlight'}</h2>
            ${data.intro ? `<p>${data.intro}</p>` : ''}
            ${renderHighlights(data.highlights)}
            ${renderList(data.bullets ?? [])}
            ${renderTimeline(data.timeline ?? [])}
            ${renderList(data.callouts ?? [], 'bullets')}
            ${renderActions(data.actions ?? [])}
          `;
        } catch (error) {
          panel.innerHTML = `
            <h2>We could not load that step</h2>
            <p>${error.message}</p>
            <p>Verify that the Flask server is running and reachable, then try again.</p>
          `;
        }
      }

      buttons.forEach((button) => {
        button.addEventListener('click', () => loadExperience(button));
      });

      if (buttons[0]) {
        loadExperience(buttons[0]);
      }
    </script>
  </body>
</html>"""


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
    app.config["CON5013_EXAMPLE_ACTIVE_AUTH_MODE"] = auth_mode

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
    def index() -> str:
        return render_template_string(
            LANDING_TEMPLATE,
            steps=EXPERIENCE_STEPS,
        )

    @app.get("/demo/security-profile")
    def demo_security_profile() -> Any:
        config = app.config
        highlights = [
            {
                "label": "Security profile",
                "value": config.get("CON5013_SECURITY_PROFILE", "secured"),
                "description": "We always start from the hardened preset to disable destructive tooling by default.",
            },
            {
                "label": "API exposure",
                "value": "Internal only",
                "description": "External hosts are blocked because CON5013_API_ALLOW_EXTERNAL is False.",
            },
            {
                "label": "Log retention",
                "value": "Immutable",
                "description": "Operators cannot clear history – CON5013_ALLOW_LOG_CLEAR stays False.",
            },
        ]

        bullets = [
            "Terminal access stays locked until an administrator deliberately enables it.",
            "The secured preset disables auto-injection and other risky helpers behind the scenes.",
            "Tweak the values in create_app() to align with your change management policies.",
        ]

        callouts = [
            "Set <code class=\"inline\">CON5013_SECURITY_PROFILE=secured</code> in production manifests.",
            "Use environment overrides for any tooling you want to selectively re-enable.",
        ]

        return jsonify(
            {
                "title": "Secured profile as the foundation",
                "intro": "The CON5013 secured profile trims capabilities down to the safest baseline so you can grant access confidently.",
                "highlights": highlights,
                "bullets": bullets,
                "callouts": callouts,
            }
        )

    @app.get("/demo/auth")
    def demo_auth() -> Any:
        active_mode = app.config.get("CON5013_EXAMPLE_ACTIVE_AUTH_MODE", "basic")
        highlights = [
            {
                "label": "Active mode",
                "value": active_mode.title(),
                "description": "Switch modes with CON5013_EXAMPLE_AUTH_MODE=basic|token|callback before launching the app.",
            },
            {
                "label": "Basic credentials",
                "value": f"{app.config.get('CON5013_AUTH_USER', 'ops')} / {app.config.get('CON5013_AUTH_PASSWORD', 'change-me')}",
                "description": "Rotate these values through secrets management before going live.",
            },
            {
                "label": "Token header",
                "value": "Authorization: Bearer <token>",
                "description": "If you prefer machine-to-machine control, supply CON5013_AUTH_TOKEN.",
            },
        ]

        bullets = [
            "Basic auth keeps onboarding simple for small on-call teams.",
            "Token auth is ideal for automated platforms or reverse proxies.",
            "Callback auth lets you enforce custom role mappings from your SSO or gateway.",
        ]

        callouts = [
            "Callback mode expects <code class=\"inline\">X-Demo-User</code> and <code class=\"inline\">X-Demo-Role</code> headers.",
            "Use <code class=\"inline\">curl -H \"X-Demo-User: jane\" -H \"X-Demo-Role: engineer\" http://localhost:5000/whoami</code> to test the mapping.",
        ]

        actions = [
            {
                "label": "View /whoami helper",
                "href": "/whoami",
            }
        ]

        return jsonify(
            {
                "title": "Authentication options for every team",
                "intro": "Pick the guard that fits your infrastructure. Swap modes by setting environment variables before the Flask server starts.",
                "highlights": highlights,
                "bullets": bullets,
                "callouts": callouts,
                "actions": actions,
            }
        )

    @app.get("/demo/observability")
    def demo_observability() -> Any:
        highlights = [
            {
                "label": "Logs",
                "value": "Enabled",
                "description": "Read-only visibility keeps responders informed while respecting least privilege.",
            },
            {
                "label": "System monitor",
                "value": "Enabled",
                "description": "Expose health, metrics, and resource usage without dropping to the shell.",
            },
            {
                "label": "API scanner",
                "value": "Internal scope",
                "description": "Engineers can inspect Flask routes, but the secured preset blocks outbound probing.",
            },
        ]

        bullets = [
            "Keep operators in the loop during incidents without handing out shell access.",
            "Audit trails record every query made through the console.",
            "Pair the system monitor with your /metrics endpoint for deeper visibility.",
        ]

        callouts = [
            "Set <code class=\"inline\">CON5013_ENABLE_LOGS=True</code> to surface the log viewer.",
            "Leave <code class=\"inline\">CON5013_API_ALLOW_EXTERNAL=False</code> to fence off third-party systems.",
        ]

        actions = [
            {
                "label": "Open /metrics",
                "href": "/metrics",
            },
            {
                "label": "Check /health",
                "href": "/health",
            },
        ]

        return jsonify(
            {
                "title": "Operator visibility without compromise",
                "intro": "The secured profile keeps just enough telemetry online so responders can triage issues while sensitive tooling stays disabled.",
                "highlights": highlights,
                "bullets": bullets,
                "callouts": callouts,
                "actions": actions,
            }
        )

    @app.get("/demo/audit-log")
    def demo_audit_log() -> Any:
        timeline = [
            {
                "time": "08:00",
                "actor": "ops@acme (observer)",
                "action": "Authenticated via basic auth and reviewed overnight logs.",
            },
            {
                "time": "08:05",
                "actor": "ops@acme (observer)",
                "action": "Checked /metrics through the system monitor to confirm recovery trends.",
            },
            {
                "time": "08:12",
                "actor": "devon@acme (engineer)",
                "action": "Escalated with callback role=engineer to run an internal API scan.",
            },
            {
                "time": "08:17",
                "actor": "devon@acme (engineer)",
                "action": "Raised a change request to temporarily enable the terminal for deeper debugging.",
            },
        ]

        bullets = [
            "Every action is captured by CON5013's audit log, keeping compliance simple.",
            "Observer and engineer roles demonstrate how granular access maps to responsibilities.",
            "Pair these records with your SIEM for long-term retention.",
        ]

        callouts = [
            "Configure webhook sinks to stream audit entries to your incident management tooling.",
            "The secured profile keeps log clearing disabled so records remain immutable.",
        ]

        return jsonify(
            {
                "title": "A glimpse into a secured operator shift",
                "intro": "Follow a morning incident review and see how CON5013 documents each touch point.",
                "timeline": timeline,
                "bullets": bullets,
                "callouts": callouts,
            }
        )

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
