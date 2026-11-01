"""Socket.IO event handlers. All authority checks live in game_logic.Room."""
import random

from flask import request
from flask_socketio import join_room as sio_join, leave_room as sio_leave

from game_logic import GameError
from professions import QUESTIONS


def register(socketio, mgr):
    def broadcast(room):
        """Send each connected player THEIR OWN view. Nothing is ever sent to the whole room."""
        for p in room.players.values():
            if p.sid:
                socketio.emit("state", room.view(p.pid), to=p.sid)

    def notice(room, text, kind="info"):
        socketio.emit("notice", {"text": text, "kind": kind}, to=room.code)

    def safe(fn):
        def wrapper(data=None):
            data = data if isinstance(data, dict) else {}
            with mgr.lock:
                try:
                    return fn(data)
                except GameError as e:
                    return {"ok": False, "error": str(e)}
        return wrapper

    @socketio.on("create")
    @safe
    def create(data):
        room, p = mgr.create_room(data.get("name"), data.get("max_players"), request.sid)
        sio_join(room.code)
        return {"ok": True, "code": room.code, "token": p.token}

    @socketio.on("join")
    @safe
    def join(data):
        room, p = mgr.join(data.get("code"), data.get("name"), request.sid)
        sio_join(room.code)
        notice(room, f"انضم {p.name} إلى الغرفة", "good")
        broadcast(room)
        return {"ok": True, "code": room.code, "token": p.token}

    @socketio.on("rejoin")
    @safe
    def rejoin(data):
        room, p = mgr.rejoin(data.get("code"), data.get("token"), request.sid)
        sio_join(room.code)
        notice(room, f"عاد {p.name} إلى الاتصال", "good")
        broadcast(room)
        return {"ok": True}

    @socketio.on("disconnect")
    def on_disconnect(*_):
        with mgr.lock:
            res = mgr.disconnect(request.sid)
            if res:
                room, p = res
                notice(room, f"انقطع اتصال {p.name}", "warn")
                broadcast(room)

    @socketio.on("leave")
    @safe
    def leave(data):
        room, p = mgr.lookup(request.sid)
        sio_leave(room.code)
        room = mgr.leave(request.sid)
        if room:
            notice(room, f"غادر {p.name} الغرفة", "warn")
            broadcast(room)
        return {"ok": True}

    def action(event, method=None):
        """Register a state-changing event that calls Room.<method>(player_id[, target])."""
        @socketio.on(event)
        @safe
        def handler(data):
            room, p = mgr.lookup(request.sid)
            getattr(room, method or event)(p.pid, *( [data.get("target")] if event == "vote" else [] ))
            broadcast(room)
            return {"ok": True}
        return handler

    action("start_game"); action("start_voting"); action("close_voting")
    action("new_vote"); action("reveal"); action("new_round"); action("to_lobby")
    action("seen", "mark_seen"); action("ready", "set_ready"); action("vote", "cast_vote")

    @socketio.on("request_role")
    @safe
    def request_role(data):
        room, p = mgr.lookup(request.sid)
        return {"ok": True, "job": room.role_for(p.pid)}   # ack goes only to the caller

    @socketio.on("question")
    @safe
    def question(data):
        mgr.lookup(request.sid)
        return {"ok": True, "question": random.choice(QUESTIONS)}
