#!/usr/bin/env python3
"""Minimal Con5013 integration example."""

from flask import Flask, jsonify, render_template_string

from con5013 import Con5013

app = Flask(__name__)

# Attach Con5013 using default settings (console at /con5013, hotkey Alt+C).
console = Con5013(app)


@app.route("/")
def index():
    """Small endpoint that proves everything is running."""
    app.logger.info("Homepage visited")
    console_url = console.config["CON5013_URL_PREFIX"]
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Simple Con5013 Demo</title>
        </head>
        <body>
            <h1>Con5013 is live!</h1>
            <p>Open the console from <code>{{ console_url }}</code> or press <strong>{{ hotkey }}</strong>.</p>
            <!-- Loads the Con5013 overlay script so the hotkey/floating button work without extra setup. -->
            <script src="{{ console_url }}/static/js/con5013.js"></script>
        </body>
        </html>
        """,
        console_url=console_url,
        hotkey=console.config["CON5013_HOTKEY"],
    )


@app.route("/api/ping")
def ping():
    """Simple JSON endpoint you can inspect from the API tab."""
    return jsonify(status="ok")


if __name__ == "__main__":
    print("Visit http://127.0.0.1:5000/ and open the console with Alt+C or /con5013")
    app.run(debug=True)
