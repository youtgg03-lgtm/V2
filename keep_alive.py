"""
keep_alive.py — Uchiro Store

Note: this pattern comes from Replit-style hosting, where a bot process
goes to sleep unless something pings it. Railway services don't sleep
like that, so on Railway this file isn't actually necessary — the
webapp_server.py Flask app already responds on its own and keeps the
service alive. Kept here anyway since you asked for it explicitly and
it doesn't hurt to have a lightweight /health-style endpoint.
"""

from flask import Flask
from threading import Thread

_app = Flask("keep_alive")


@_app.route("/")
def _home():
    return "Uchiro Store is alive 🏴‍☠️"


def keep_alive(port=8081):
    """Runs a tiny Flask app on its own thread. Only start this if you're
    NOT already running webapp_server.py (which has its own /health route)
    on the same port — main.py does not call this by default."""
    t = Thread(target=lambda: _app.run(host="0.0.0.0", port=port))
    t.daemon = True
    t.start()
