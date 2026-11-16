import os
import re
import secrets

from flask import Flask, redirect, render_template
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

import socket_events
from room_manager import RoomManager


def create_app():
    app = Flask(__name__)
    if os.environ.get("TRUST_PROXY", "1") == "1":      # behind Render/Nginx: honour X-Forwarded-* (HTTPS, host)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    origins = os.environ.get("CORS_ORIGINS")            # e.g. "https://my-game.onrender.com"
    socketio = SocketIO(app, async_mode="threading",
                        cors_allowed_origins=origins.split(",") if origins else None)
    mgr = RoomManager()
    socket_events.register(socketio, mgr)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if os.environ.get("FORCE_HTTPS", "1") == "1":
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/room/<code>")
    def room(code):
        code = code.upper()
        if not re.fullmatch(r"[A-Z0-9]{4,8}", code):
            return redirect("/")
        return render_template("room.html", code=code)

    @app.get("/healthz")
    def health():
        return "ok"

    app.mgr, app.socketio = mgr, socketio
    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
                 debug=os.environ.get("FLASK_DEBUG") == "1", allow_unsafe_werkzeug=True)
