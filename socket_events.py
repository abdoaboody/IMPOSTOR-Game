"""Socket.IO event handlers. All authority checks live in game_logic.Room."""
import os

from flask import request
from flask_socketio import join_room as sio_join, leave_room as sio_leave

from content import QUESTIONS
from content_it import HINTS_IT, QUESTIONS_IT, WORDS_IT
from game_logic import ACTIVE_PHASES, GameError

# Seconds the game waits for a disconnected impostor before everyone returns to the lobby.
IMPOSTOR_GRACE = float(os.environ.get("IMPOSTOR_GRACE", 30))


def register(socketio, mgr):
    def broadcast(room):
        """Send each connected player THEIR OWN view. Nothing is ever sent to the whole room."""
        for p in room.players.values():
            if p.sid:
                socketio.emit("state", room.view(p.pid), to=p.sid)

    def notice(room, key, name, text, kind="info"):
        """`key` + `name` let the client show the notice in the player's own language."""
        socketio.emit("notice", {"key": key, "name": name, "text": text, "kind": kind}, to=room.code)

    def safe(fn):
        def wrapper(data=None):
            data = data if isinstance(data, dict) else {}
            with mgr.lock:
                try:
                    return fn(data)
                except GameError as e:
                    return {"ok": False, "error": str(e), "error_it": e.it}
        return wrapper

    # ------------------------------------------------ impostor-loss watchdog
    def watch_impostor(code, pid, stamp):
        socketio.sleep(IMPOSTOR_GRACE)
        with mgr.lock:
            room = mgr.rooms.get(code)
            p = room.players.get(pid) if room else None
            if not p or p.connected or p.dropped_at != stamp:
                return                            # came back (or dropped again: newer watch owns it)
            name = room.lost_impostor_reset(pid)
            if name is None:
                return
            socketio.emit("impostor_lost", {"name": name}, to=room.code)
            broadcast(room)

    def maybe_watch(room, p):
        if room.phase in ACTIVE_PHASES and p.pid == room.impostor_pid and not p.connected:
            socketio.start_background_task(watch_impostor, room.code, p.pid, p.dropped_at)

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
        notice(room, "joined", p.name, f"انضم {p.name} إلى الغرفة", "good")
        broadcast(room)
        return {"ok": True, "code": room.code, "token": p.token}

    @socketio.on("rejoin")
    @safe
    def rejoin(data):
        room, p = mgr.rejoin(data.get("code"), data.get("token"), request.sid)
        sio_join(room.code)
        notice(room, "back", p.name, f"عاد {p.name} إلى الاتصال", "good")
        broadcast(room)
        return {"ok": True}

    @socketio.on("disconnect")
    def on_disconnect(*_):
        with mgr.lock:
            res = mgr.disconnect(request.sid)
            if res:
                room, p = res
                notice(room, "dropped", p.name, f"انقطع اتصال {p.name}", "warn")
                broadcast(room)
                maybe_watch(room, p)

    @socketio.on("leave")
    @safe
    def leave(data):
        room, p = mgr.lookup(request.sid)
        sio_leave(room.code)
        room = mgr.leave(request.sid)
        if room:
            notice(room, "left", p.name, f"غادر {p.name} الغرفة", "warn")
            broadcast(room)
            maybe_watch(room, p)
        return {"ok": True}

    @socketio.on("kick")
    @safe
    def kick(data):
        room, p = mgr.lookup(request.sid)
        target = room.kick(p.pid, data.get("target"))
        if target.sid:
            mgr.sids.pop(target.sid, None)
            socketio.emit("kicked", {}, to=target.sid)
            sio_leave(room.code, sid=target.sid)
        notice(room, "kicked", target.name, f"أخرج المضيف {target.name} من الغرفة", "warn")
        broadcast(room)
        return {"ok": True}

    @socketio.on("settings")
    @safe
    def settings(data):
        room, p = mgr.lookup(request.sid)
        room.set_settings(p.pid, data.get("category"), data.get("mode"), data.get("hints"))
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
    action("back_to_game"); action("reveal"); action("new_round"); action("to_lobby")
    action("seen", "mark_seen"); action("ready", "set_ready"); action("vote", "cast_vote")

    @socketio.on("request_role")
    @safe
    def request_role(data):
        room, p = mgr.lookup(request.sid)
        r = room.role_for(p.pid)                            # ack goes only to the caller
        return {"ok": True, "job": r["word"], "impostor": r["impostor"], "hint": r["hint"],
                "job_it": WORDS_IT.get(r["word"]), "hint_it": HINTS_IT.get(r["hint"]),
                "category": room.category}

    @socketio.on("question")
    @safe
    def question(data):
        room, p = mgr.lookup(request.sid)
        q = room.next_question(p.pid)
        q_it = QUESTIONS_IT[room.category][QUESTIONS[room.category].index(q)]
        return {"ok": True, "question": q, "question_it": q_it}
