import json
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest
from app import create_app


@pytest.fixture()
def env():
    app, sio = create_app()
    return app, sio


def last_state(c):
    states = [e["args"][0] for e in c.get_received() if e["name"] == "state"]
    return states[-1] if states else None


def setup_room(env, n=3):
    app, sio = env
    host = sio.test_client(app)
    ack = host.emit("create", {"name": "Host", "max_players": 5}, callback=True)
    assert ack["ok"]
    code = ack["code"]
    clients = [host]
    for i in range(1, n):
        c = sio.test_client(app)
        assert c.emit("join", {"code": code, "name": f"P{i}"}, callback=True)["ok"]
        clients.append(c)
    return app, code, clients


def test_full_flow_and_privacy(env):
    app, code, cs = setup_room(env)
    mgr = app.mgr
    # non-host cannot start; late join impossible
    assert not cs[1].emit("start_game", callback=True)["ok"]
    assert cs[0].emit("start_game", callback=True)["ok"]
    late = env[1].test_client(env[0])
    assert not late.emit("join", {"code": code, "name": "Late"}, callback=True)["ok"]
    room = mgr.rooms[code]
    jobs = {}
    for c in cs:
        r = c.emit("request_role", callback=True)
        jobs[c] = r["job"]
        assert c.emit("seen", callback=True)["ok"]
    assert sorted(jobs.values()).count(room.impostor_job) == 1
    # no state event ever carried a job before the reveal
    for c in cs:
        for e in c.get_received():
            if e["name"] == "state":
                assert room.main_job not in json.dumps(e["args"][0], ensure_ascii=False)
                assert room.impostor_job not in json.dumps(e["args"][0], ensure_ascii=False)
    for c in cs:
        assert c.emit("ready", callback=True)["ok"]
    assert not cs[2].emit("start_voting", callback=True)["ok"]
    assert cs[0].emit("start_voting", callback=True)["ok"]
    ids = [last_state(c)["me"]["id"] for c in cs]
    # everyone votes for player 0 except player 0 who votes for 1
    assert not cs[0].emit("vote", {"target": ids[0]}, callback=True)["ok"]
    assert cs[0].emit("vote", {"target": ids[1]}, callback=True)["ok"]
    assert not cs[0].emit("vote", {"target": ids[2]}, callback=True)["ok"]
    assert not cs[0].emit("close_voting", callback=True)["ok"]
    for c in cs[1:]:
        assert c.emit("vote", {"target": ids[0]}, callback=True)["ok"]
    assert not cs[1].emit("close_voting", callback=True)["ok"]
    assert cs[0].emit("close_voting", callback=True)["ok"]
    st = last_state(cs[1])
    assert st["outcome"] == "suspect" and st["suspect"] == ids[0] and "result" not in st
    assert not cs[1].emit("reveal", callback=True)["ok"]
    assert cs[0].emit("reveal", callback=True)["ok"]
    for c in cs:
        res = last_state(c)["result"]
        assert res["main_job"] == room.main_job and res["impostor_job"] == room.impostor_job


def test_reconnect_via_token(env):
    app, code, cs = setup_room(env)
    app_, sio = env
    token = app.mgr.rooms[code].players[last_state(cs[1])["me"]["id"]].token
    cs[1].disconnect()
    c2 = sio.test_client(app)
    assert not c2.emit("rejoin", {"code": code, "token": "nope"}, callback=True)["ok"]
    assert c2.emit("rejoin", {"code": code, "token": token}, callback=True)["ok"]
    assert last_state(c2)["me"]["name"] == "P1"


def test_unbound_socket_is_rejected(env):
    app, sio = env
    stranger = sio.test_client(app)
    for ev in ("start_game", "request_role", "reveal", "vote", "close_voting"):
        assert not stranger.emit(ev, {"target": "x"}, callback=True)["ok"]
