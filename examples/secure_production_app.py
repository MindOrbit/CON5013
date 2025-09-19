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


ROLE_LABELS = {
    "observer": "Observer",
    "engineer": "Engineer",
    "admin": "Admin",
}


SIMULATED_FEATURES = [
    {
        "name": "Log viewer",
        "endpoint": "con5013.logs",
        "description": "Inspect immutable application logs captured by the secured profile.",
    },
    {
        "name": "System monitor",
        "endpoint": "con5013.system_monitor",
        "description": "Review CPU, memory, and request counters without shelling into the host.",
    },
    {
        "name": "API scanner",
        "endpoint": "api_scanner.index",
        "description": "Enumerate Flask routes to understand which surfaces are exposed.",
    },
    {
        "name": "Interactive terminal",
        "endpoint": "api_terminal.execute",
        "description": "Break-glass capability for administrators when deeper debugging is required.",
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

      section.interactive {
        margin-top: 32px;
        padding: 24px;
        border-radius: 20px;
        border: 1px solid rgba(96, 165, 250, 0.28);
        background: rgba(14, 24, 52, 0.75);
        box-shadow: inset 0 1px 0 rgba(148, 163, 184, 0.08);
        display: grid;
        gap: 18px;
      }

      section.interactive h3 {
        margin: 0;
        font-size: 1.2rem;
      }

      .mode-selector,
      .role-selector {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .mode-selector button,
      .role-selector button {
        background: rgba(30, 64, 175, 0.15);
        border: 1px solid rgba(96, 165, 250, 0.45);
        color: inherit;
        border-radius: 12px;
        padding: 10px 16px;
        cursor: pointer;
        font-size: 0.95rem;
        transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
      }

      .mode-selector button:hover,
      .role-selector button:hover {
        transform: translateY(-1px);
        border-color: rgba(148, 163, 184, 0.65);
      }

      .mode-selector button.active,
      .role-selector button.active {
        background: rgba(59, 130, 246, 0.25);
        border-color: rgba(96, 165, 250, 0.85);
        box-shadow: 0 14px 30px -22px rgba(59, 130, 246, 0.9);
      }

      .role-selector span.label {
        align-self: center;
        color: var(--muted);
        font-size: 0.9rem;
        margin-right: 4px;
      }

      .experience-result h4 {
        margin: 0;
        font-size: 1.15rem;
      }

      .experience-result h5 {
        margin: 12px 0 8px;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--muted);
      }

      .experience-result p.description {
        color: var(--muted);
        line-height: 1.5;
        margin: 6px 0 18px;
      }

      .experience-layout {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
        align-items: start;
      }

      .console-preview {
        border-radius: 18px;
        border: 1px solid rgba(96, 165, 250, 0.25);
        background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.16), transparent 55%),
                    rgba(8, 15, 34, 0.85);
        padding: 18px;
        min-height: 220px;
        box-shadow: inset 0 1px 0 rgba(148, 163, 184, 0.08);
        display: grid;
      }

      .console-window {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(96, 165, 250, 0.28);
        background: rgba(9, 14, 29, 0.92);
        display: grid;
        grid-template-rows: auto 1fr;
      }

      .console-window header {
        padding: 12px 16px;
        background: linear-gradient(120deg, rgba(30, 58, 138, 0.72), rgba(30, 64, 175, 0.55));
        border-bottom: 1px solid rgba(96, 165, 250, 0.28);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        font-size: 0.95rem;
      }

      .console-window header span.mode {
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.4);
        background: rgba(30, 58, 138, 0.35);
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .console-body {
        padding: 18px;
        display: grid;
        gap: 18px;
      }

      .console-body .persona {
        display: grid;
        gap: 4px;
      }

      .console-body .persona strong {
        font-size: 1.05rem;
      }

      .console-body .persona span {
        color: var(--muted);
        font-size: 0.85rem;
      }

      .console-panels {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
      }

      .console-panel {
        border-radius: 12px;
        border: 1px solid rgba(96, 165, 250, 0.22);
        padding: 14px;
        display: grid;
        gap: 6px;
        background: rgba(11, 20, 42, 0.85);
        position: relative;
        min-height: 110px;
      }

      .console-panel.allowed::before,
      .console-panel.blocked::before {
        content: attr(data-status);
        position: absolute;
        top: 12px;
        right: 12px;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 2px 8px;
        border-radius: 999px;
      }

      .console-panel.allowed::before {
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.45);
        background: rgba(22, 101, 52, 0.35);
      }

      .console-panel.blocked {
        border-color: rgba(248, 113, 113, 0.45);
        background: rgba(127, 29, 29, 0.25);
      }

      .console-panel.blocked::before {
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.4);
        background: rgba(127, 29, 29, 0.25);
      }

      .console-panel h6 {
        margin: 0;
        font-size: 0.95rem;
      }

      .console-panel p {
        margin: 0;
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.45;
      }

      .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        margin: 18px 0 8px;
      }

      .feature {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 12px;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid rgba(96, 165, 250, 0.3);
        background: rgba(12, 22, 44, 0.85);
        align-items: start;
      }

      .feature .status {
        font-size: 1.25rem;
        font-weight: 600;
      }

      .feature.allowed .status {
        color: var(--success);
      }

      .feature.blocked {
        border-color: rgba(248, 113, 113, 0.5);
        background: rgba(127, 29, 29, 0.25);
      }

      .feature.blocked .status {
        color: var(--danger);
      }

      .feature p {
        margin: 4px 0 0;
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.45;
      }

      .code-block {
        background: rgba(15, 23, 42, 0.85);
        border-radius: 12px;
        border: 1px solid rgba(96, 165, 250, 0.35);
        padding: 14px 16px;
        font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.85rem;
        overflow-x: auto;
        margin-top: 12px;
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

      function renderAccessMatrix(items) {
        if (!Array.isArray(items) || !items.length) {
          return '';
        }

        return `<div class="feature-grid">${items.map((item) => `
          <div class="feature ${item.allowed ? 'allowed' : 'blocked'}">
            <div class="status" aria-hidden="true">${item.allowed ? '✓' : '✕'}</div>
            <div>
              <strong>${item.name ?? ''}</strong>
              ${item.description ? `<p>${item.description}</p>` : ''}
            </div>
          </div>
        `).join('')}</div>`;
      }

      function renderConsolePreview(access = [], preview = {}, mode = 'basic') {
        const modeLabel = String(preview.mode ?? mode ?? 'mode').toUpperCase();
        const title = preview.title ?? 'Console ready for access simulation';
        const subtitle = preview.subtitle ?? 'Toggle authentication modes to see which panels appear.';

        const panels = Array.isArray(access) && access.length
          ? access.map((item) => {
              const allowed = Boolean(item.allowed);
              const status = allowed ? 'Allowed' : 'Locked';
              return `
                <div class="console-panel ${allowed ? 'allowed' : 'blocked'}" data-status="${status}">
                  <h6>${item.name ?? ''}</h6>
                  ${item.description ? `<p>${item.description}</p>` : ''}
                </div>
              `;
            }).join('')
          : '<p class="description">No console panels are enabled for this mode.</p>';

        return `
          <div class="console-window">
            <header>
              <span>CON5013 secure console</span>
              <span class="mode">${modeLabel}</span>
            </header>
            <div class="console-body">
              <div class="persona">
                <strong>${title}</strong>
                <span>${subtitle}</span>
              </div>
              <div class="console-panels">
                ${panels}
              </div>
            </div>
          </div>
        `;
      }

      function mountInteractiveExperience(container, interactive) {
        if (!interactive || interactive.type !== 'auth-modes') {
          return;
        }

        const section = document.createElement('section');
        section.className = 'interactive auth-modes';
        section.innerHTML = `
          <h3>${interactive.heading ?? 'Simulate each authentication mode'}</h3>
          ${interactive.description ? `<p class="description">${interactive.description}</p>` : ''}
          <div class="mode-selector">
            ${interactive.modes.map((mode) => `<button class="mode-btn" data-mode="${mode.id}">${mode.label}</button>`).join('')}
          </div>
          <div class="role-selector" ${interactive.roleOptions?.length ? '' : 'hidden'}>
            <span class="label">Roles:</span>
            ${interactive.roleOptions?.map((role) => `<button class="role-btn" data-role="${role.id}">${role.label}</button>`).join('') ?? ''}
          </div>
          <div class="experience-layout">
            <div class="experience-result">
              <p class="description">Choose a mode to preview the operator journey.</p>
            </div>
            <div class="console-preview" aria-live="polite">
              <div class="console-window">
                <header>
                  <span>CON5013 secure console</span>
                  <span class="mode">mode</span>
                </header>
                <div class="console-body">
                  <div class="persona">
                    <strong>Select a mode to render the console</strong>
                    <span>The preview updates to mirror the simulated access level.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        `;

        container.appendChild(section);

        const modeButtons = Array.from(section.querySelectorAll('.mode-btn'));
        const roleButtons = Array.from(section.querySelectorAll('.role-btn'));
        const roleWrapper = section.querySelector('.role-selector');
        const result = section.querySelector('.experience-result');
        const preview = section.querySelector('.console-preview');

        const defaultMode = interactive.defaultMode ?? (modeButtons[0] && modeButtons[0].dataset.mode);
        let currentMode = defaultMode;
        let currentRole = interactive.roleOptions?.[0]?.id ?? null;

        function setActive(buttons, targetAttr, value) {
          buttons.forEach((btn) => {
            btn.classList.toggle('active', btn.dataset[targetAttr] === value);
          });
        }

        function showRoleSelector() {
          if (!roleButtons.length) {
            roleWrapper.hidden = true;
            return;
          }

          if (currentMode === 'callback') {
            roleWrapper.hidden = false;
            if (!roleButtons.some((btn) => btn.dataset.role === currentRole)) {
              currentRole = roleButtons[0].dataset.role;
            }
            setActive(roleButtons, 'role', currentRole);
          } else {
            roleWrapper.hidden = true;
          }
        }

        async function fetchExperience() {
          if (!currentMode) {
            return;
          }

          const params = new URLSearchParams({ mode: currentMode });
          if (currentMode === 'callback' && currentRole) {
            params.set('role', currentRole);
          }

          try {
            result.innerHTML = '<p class="description">Loading experience…</p>';
            const response = await fetch(`${interactive.endpoint}?${params.toString()}`, { headers: { 'Accept': 'application/json' } });
            if (!response.ok) {
              throw new Error(`Request failed with status ${response.status}`);
            }

            const payload = await response.json();
            const sections = [];

            sections.push(`<h4>${payload.title ?? 'Authentication preview'}</h4>`);
            if (payload.subtitle) {
              sections.push(`<p class="description">${payload.subtitle}</p>`);
            }

            const detailHighlights = [];
            if (Array.isArray(payload.credentials)) {
              detailHighlights.push(...payload.credentials);
            }
            if (Array.isArray(payload.headers)) {
              detailHighlights.push(...payload.headers);
            }

            if (detailHighlights.length) {
              sections.push('<h5>How to authenticate</h5>');
              sections.push(renderHighlights(detailHighlights));
            }

            if (Array.isArray(payload.notes) && payload.notes.length) {
              sections.push('<h5>What to expect</h5>');
              sections.push(renderList(payload.notes, 'bullets'));
            }

            if (Array.isArray(payload.access) && payload.access.length) {
              sections.push('<h5>Console access</h5>');
              sections.push(renderAccessMatrix(payload.access));
            }

            if (payload.sample) {
              sections.push('<h5>Try it from your terminal</h5>');
              sections.push(`<pre class="code-block">${payload.sample}</pre>`);
            }

            result.innerHTML = sections.join('');

            const previewHtml = renderConsolePreview(payload.access ?? [], payload.preview ?? {}, payload.mode ?? currentMode);
            preview.innerHTML = previewHtml;
          } catch (error) {
            result.innerHTML = `<p class="description">${error.message}</p>`;
            preview.innerHTML = `<div class="console-window"><header><span>CON5013 secure console</span><span class="mode">error</span></header><div class="console-body"><div class="persona"><strong>Preview unavailable</strong><span>${error.message}</span></div></div></div>`;
          }
        }

        modeButtons.forEach((button) => {
          button.addEventListener('click', () => {
            currentMode = button.dataset.mode;
            setActive(modeButtons, 'mode', currentMode);
            showRoleSelector();
            fetchExperience();
          });
        });

        roleButtons.forEach((button) => {
          button.addEventListener('click', () => {
            currentRole = button.dataset.role;
            setActive(roleButtons, 'role', currentRole);
            fetchExperience();
          });
        });

        if (currentMode) {
          setActive(modeButtons, 'mode', currentMode);
        }
        showRoleSelector();
        fetchExperience();
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

          if (data.interactive) {
            mountInteractiveExperience(panel, data.interactive);
          }
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


def _describe_mode(mode: str) -> str:
    if mode == "basic":
        return "basic"
    if mode == "token":
        return "token"
    if mode == "callback":
        return "callback"
    return mode


def _build_preview_payload(*, title: str, subtitle: str | None, mode: str) -> dict[str, str | None]:
    return {
        "title": title,
        "subtitle": subtitle,
        "mode": _describe_mode(mode),
    }


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

        interactive = {
            "type": "auth-modes",
            "endpoint": "/demo/auth/experience",
            "heading": "Hands-on authentication sandbox",
            "description": "Click a mode to load credentials, sample requests, and the console access it unlocks.",
            "modes": [
                {"id": "basic", "label": "Basic (username/password)"},
                {"id": "token", "label": "Token (Bearer)"},
                {"id": "callback", "label": "Callback (header roles)"},
            ],
            "roleOptions": [
                {"id": key, "label": value} for key, value in ROLE_LABELS.items()
            ],
            "defaultMode": active_mode,
        }

        return jsonify(
            {
                "title": "Authentication options for every team",
                "intro": "Pick the guard that fits your infrastructure. Swap modes by setting environment variables before the Flask server starts.",
                "highlights": highlights,
                "bullets": bullets,
                "callouts": callouts,
                "actions": actions,
                "interactive": interactive,
            }
        )

    @app.get("/demo/auth/experience")
    def demo_auth_experience() -> Any:
        mode = (request.args.get("mode", "basic") or "basic").strip().lower()
        role = (request.args.get("role", "observer") or "observer").strip().lower()

        if mode not in {"basic", "token", "callback"}:
            return jsonify({"error": f"Unknown authentication mode: {mode}"}), 400

        if mode in {"basic", "token"}:
            features = [
                {
                    "name": feature["name"],
                    "description": feature["description"],
                    "allowed": feature["endpoint"] != "api_terminal.execute",
                }
                for feature in SIMULATED_FEATURES
            ]

            if mode == "basic":
                user = app.config.get("CON5013_AUTH_USER", "ops")
                password = app.config.get("CON5013_AUTH_PASSWORD", "change-me")
                return jsonify(
                    {
                        "mode": mode,
                        "title": "Basic authentication",
                        "subtitle": "Great for small on-call rotations that sign in with shared credentials.",
                        "credentials": [
                            {"label": "Username", "value": user},
                            {"label": "Password", "value": password, "description": "Rotate through your secrets manager."},
                        ],
                        "notes": [
                            "Pair with network-level protections or a VPN when exposing the console.",
                            "Force HTTPS so credentials stay encrypted in transit.",
                        ],
                        "access": features,
                        "preview": _build_preview_payload(
                            title=f"Signed in as {user}",
                            subtitle="Shared operator credential active.",
                            mode=mode,
                        ),
                        "sample": f"curl -u {user}:{password} http://localhost:5000/health",
                    }
                )

            token = app.config.get("CON5013_AUTH_TOKEN", "set-a-strong-token")
            return jsonify(
                {
                    "mode": mode,
                    "title": "Token authentication",
                    "subtitle": "Ideal for API gateways, reverse proxies, or machine-to-machine control.",
                    "headers": [
                        {
                            "label": "Authorization header",
                            "value": f"Bearer {token}",
                            "description": "Inject this header from your proxy or deployment platform.",
                        }
                    ],
                    "notes": [
                        "Rotate the token frequently and store it securely.",
                        "Pair with IP allow-lists or mutual TLS for defense in depth.",
                    ],
                    "access": features,
                    "preview": _build_preview_payload(
                        title="Automation token connected",
                        subtitle="Bearer authentication presents a service account view.",
                        mode=mode,
                    ),
                    "sample": "curl -H \"Authorization: Bearer {}\" http://localhost:5000/metrics".format(token),
                }
            )

        if role not in ROLE_LABELS:
            role = "observer"

        simulated_access = []
        for feature in SIMULATED_FEATURES:
            mock_request = _MockRequest(feature["endpoint"], role)
            allowed = bool(_role_based_auth(mock_request))
            simulated_access.append(
                {
                    "name": feature["name"],
                    "description": feature["description"],
                    "allowed": allowed,
                }
            )

        role_label = ROLE_LABELS[role]
        return jsonify(
            {
                "mode": mode,
                "role": role,
                "title": "Callback authentication",
                "subtitle": f"Project your SSO or reverse proxy roles directly into CON5013 (currently previewing as {role_label}).",
                "headers": [
                    {
                        "label": "X-Demo-User",
                        "value": "<user@company>",
                        "description": "Identifies the operator arriving from your identity provider.",
                    },
                    {
                        "label": "X-Demo-Role",
                        "value": role,
                        "description": "Map SSO groups to observer, engineer, or admin capabilities.",
                    },
                ],
                "notes": [
                    "Observer keeps the console strictly read-only.",
                    "Engineer unlocks the API scanner for deeper investigations.",
                    "Admin can approve escalations that enable the terminal.",
                ],
                "access": simulated_access,
                "preview": _build_preview_payload(
                    title=f"{role_label} permissions active",
                    subtitle="Header-based SSO projection controls which panels unlock.",
                    mode=mode,
                ),
                "sample": f"curl -H 'X-Demo-User: jane' -H 'X-Demo-Role: {role}' http://localhost:5000/whoami",
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


class _MockRequest:
    def __init__(self, endpoint: str, role: str) -> None:
        self.endpoint = endpoint
        self.headers = {
            "X-Demo-User": "demo",
            "X-Demo-Role": role,
        }


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
