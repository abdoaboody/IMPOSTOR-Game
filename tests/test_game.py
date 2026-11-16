import json
import random
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest
from game_logic import GameError, Room
from content import CATEGORIES, QUESTIONS, RANDOM_THINGS, WORDS
from professions import PROFESSIONS


def make_room(n=5, seed=1):
    r = Room("ABCDE", 10, rng=random.Random(seed))
    ids = [r.add_player(f"P{i}", f"sid{i}").pid for i in range(n)]
    return r, ids


def to_voting(r, ids):
    r.start_game(ids[0])
    for i in ids:
        r.mark_seen(i)
    assert r.phase == "discussion"
    for i in ids:
        r.set_ready(i)
    r.start_voting(ids[0])


def vote_all(r, ids, mapping):
    for i in ids:
        r.cast_vote(i, mapping[i])


def test_content_lists():
    assert len(set(PROFESSIONS)) >= 35
    for cat in CATEGORIES:
        qs = QUESTIONS[cat]
        assert len(qs) > 100 and len(set(qs)) == len(qs)
        assert all(q.startswith("هل") for q in qs)            # yes / no questions only
        assert not any(w in q for q in qs for w in WORDS[cat])  # never names a secret word


def test_roles_one_impostor_different_job():
    for seed in range(50):
        r, ids = make_room(6, seed)
        r.start_game(ids[0])
        assert r.main_job != r.impostor_job
        jobs = [r.role_for(i)["word"] for i in ids]
        assert jobs.count(r.impostor_job) == 1 and jobs.count(r.main_job) == 5


def test_impostor_position_is_varied():
    spots = set()
    for seed in range(60):
        r, ids = make_room(5, seed)
        r.start_game(ids[0])
        spots.add(ids.index(r.impostor_pid))
    assert spots == {0, 1, 2, 3, 4}


def test_lobby_rules():
    r, ids = make_room(3)
    with pytest.raises(GameError):
        r.add_player("p0")                      # duplicate (case-insensitive)
    with pytest.raises(GameError):
        r.add_player("")
    r.start_game(ids[0])
    with pytest.raises(GameError):
        r.add_player("late")                    # game already started


def test_min_players_and_host_only():
    r, ids = make_room(2)
    with pytest.raises(GameError):
        r.start_game(ids[0])
    r, ids = make_room(4)
    with pytest.raises(GameError):
        r.start_game(ids[1])


def test_views_never_leak_secrets():
    r, ids = make_room(4)
    r.start_game(ids[0])
    for phase_step in range(3):
        for i in ids:
            dump = json.dumps(r.view(i), ensure_ascii=False)
            assert r.main_job not in dump and r.impostor_job not in dump
            assert "impostor" not in dump and "tally" not in dump
        if phase_step == 0:
            for i in ids:
                r.mark_seen(i)
        elif phase_step == 1:
            for i in ids:
                r.set_ready(i)
            r.start_voting(ids[0])


def test_ready_and_voting_permissions():
    r, ids = make_room(4)
    r.start_game(ids[0])
    for i in ids:
        r.mark_seen(i)
    with pytest.raises(GameError):
        r.start_voting(ids[0])                  # not all ready
    for i in ids[:3]:
        r.set_ready(i)
    with pytest.raises(GameError):
        r.start_voting(ids[0])
    r.set_ready(ids[3])
    with pytest.raises(GameError):
        r.start_voting(ids[1])                  # non-host
    r.start_voting(ids[0])


def test_vote_validation():
    r, ids = make_room(4)
    to_voting(r, ids)
    with pytest.raises(GameError):
        r.cast_vote(ids[0], ids[0])             # self vote
    with pytest.raises(GameError):
        r.cast_vote(ids[0], "ghost")
    r.cast_vote(ids[0], ids[1])
    with pytest.raises(GameError):
        r.cast_vote(ids[0], ids[2])             # no change / double vote
    v = r.view(ids[1])
    assert "tally" not in v and all(set(p) <= {"id", "name", "connected", "is_host", "voted"} for p in v["players"])
    with pytest.raises(GameError):
        r.close_voting(ids[0])                  # not everyone voted


def test_unique_winner_then_reveal():
    r, ids = make_room(4)
    to_voting(r, ids)
    vote_all(r, ids, {ids[0]: ids[1], ids[1]: ids[2], ids[2]: ids[1], ids[3]: ids[1]})
    with pytest.raises(GameError):
        r.close_voting(ids[2])
    r.close_voting(ids[0])
    v = r.view(ids[0])
    assert v["outcome"] == "suspect" and v["suspect"] == ids[1]
    assert "result" not in v and r.main_job not in json.dumps(v)
    with pytest.raises(GameError):
        r.reveal(ids[1])
    r.reveal(ids[0])
    res = r.view(ids[2])["result"]
    assert res["main_job"] == r.main_job and res["impostor_job"] == r.impostor_job
    assert res["correct"] == (r.impostor_pid == ids[1])


def test_tie_revote_resets_votes_until_unique():
    r, ids = make_room(4)
    to_voting(r, ids)
    vote_all(r, ids, {ids[0]: ids[1], ids[1]: ids[0], ids[2]: ids[1], ids[3]: ids[0]})
    r.close_voting(ids[0])
    v = r.view(ids[0])
    assert v["outcome"] == "tie" and set(v["tied"]) == {ids[0], ids[1]} and v["suspect"] is None
    with pytest.raises(GameError):
        r.reveal(ids[0])                        # cannot reveal during a tie
    with pytest.raises(GameError):
        r.back_to_game(ids[1])
    r.back_to_game(ids[0])                      # tie -> back to the discussion, not straight to a vote
    assert r.phase == "discussion" and r.vote_round == 2
    assert all(p.vote is None and not p.ready for p in r.players.values())
    with pytest.raises(GameError):
        r.start_voting(ids[0])                  # everyone must be ready again
    for i in ids:
        r.set_ready(i)
    r.start_voting(ids[0])
    vote_all(r, ids, {ids[0]: ids[1], ids[1]: ids[0], ids[2]: ids[0], ids[3]: ids[0]})
    r.close_voting(ids[0])
    assert r.outcome == "suspect" and r.suspect_pid == ids[0]


def test_new_round_resets_everything():
    r, ids = make_room(4)
    to_voting(r, ids)
    vote_all(r, ids, {ids[0]: ids[1], ids[1]: ids[0], ids[2]: ids[0], ids[3]: ids[0]})
    r.close_voting(ids[0]); r.reveal(ids[0])
    with pytest.raises(GameError):
        r.new_round(ids[2])
    r.new_round(ids[0])
    assert r.phase == "reveal" and r.round_no == 2 and r.vote_round == 1
    assert all(not p.ready and not p.seen and p.vote is None for p in r.players.values())
    assert r.suspect_pid is None and r.tally == {}
    r.mark_seen(ids[0])
    r2 = r.view(ids[0])
    assert "result" not in r2 and "tally" not in r2


def test_return_to_lobby_hides_roles():
    r, ids = make_room(3)
    to_voting(r, ids)
    vote_all(r, ids, {ids[0]: ids[1], ids[1]: ids[0], ids[2]: ids[0]})
    r.close_voting(ids[0]); r.reveal(ids[0]); r.to_lobby(ids[0])
    assert r.phase == "lobby" and r.main_job is None
    with pytest.raises(GameError):
        r.role_for(ids[0])


def test_disconnect_and_reconnect_keep_identity():
    r, ids = make_room(4)
    r.start_game(ids[0])
    token = r.players[ids[2]].token
    job_before = r.role_for(ids[2])
    r.disconnect(ids[2])
    for i in (ids[0], ids[1], ids[3]):
        r.mark_seen(i)
    assert r.phase == "discussion"              # disconnected player no longer blocks
    p = r.reconnect(token, "newsid")
    assert p.pid == ids[2] and r.role_for(ids[2]) == job_before
    with pytest.raises(GameError):
        r.reconnect("wrong", "x")


def test_host_can_kick_only_in_lobby():
    r, ids = make_room(4)
    with pytest.raises(GameError):
        r.kick(ids[1], ids[2])                  # non-host
    with pytest.raises(GameError):
        r.kick(ids[0], ids[0])                  # self
    assert r.kick(ids[0], ids[3]).pid == ids[3] and ids[3] not in r.players
    r.start_game(ids[0])
    with pytest.raises(GameError):
        r.kick(ids[0], ids[2])                  # game running


def test_settings_host_lobby_only():
    r, ids = make_room(3)
    with pytest.raises(GameError):
        r.set_settings(ids[1], "food")
    with pytest.raises(GameError):
        r.set_settings(ids[0], "sports")
    r.set_settings(ids[0], "food", "blind", True)
    assert (r.category, r.mode, r.hints) == ("food", "blind", True)
    assert not r.hints_active()                 # hints only exist for random + blind
    r.start_game(ids[0])
    with pytest.raises(GameError):
        r.set_settings(ids[0], "jobs")


def test_food_and_random_decoy_words():
    for seed in range(40):
        r, ids = make_room(4, seed)
        r.set_settings(ids[0], "food")
        r.start_game(ids[0])
        assert r.main_job in WORDS["food"] and r.impostor_job in WORDS["food"]
        assert r.main_job != r.impostor_job
        r, ids = make_room(4, seed)
        r.set_settings(ids[0], "random")
        r.start_game(ids[0])
        groups = [g for g, items in RANDOM_THINGS.items() if r.main_job in [w for w, _ in items]]
        assert r.impostor_job in [w for w, _ in RANDOM_THINGS[groups[0]]]   # same kind


def test_blind_mode_and_hints():
    r, ids = make_room(4, 3)
    r.set_settings(ids[0], "random", "blind", False)
    r.start_game(ids[0])
    imp = r.role_for(r.impostor_pid)
    assert imp == {"word": None, "impostor": True, "hint": None}
    crew = [r.role_for(i) for i in ids if i != r.impostor_pid]
    assert all(c["word"] == r.main_job and not c["impostor"] for c in crew)
    r, ids = make_room(4, 3)
    r.set_settings(ids[0], "random", "blind", True)
    r.start_game(ids[0])
    imp = r.role_for(r.impostor_pid)
    assert imp["impostor"] and imp["word"] is None and imp["hint"]
    assert imp["hint"] != r.main_job
    r, ids = make_room(4, 3)
    r.set_settings(ids[0], "jobs", "blind", True)  # hint switch ignored outside random
    r.start_game(ids[0])
    assert r.role_for(r.impostor_pid)["hint"] is None


def test_questions_are_ordered_per_player_and_wrap():
    r, ids = make_room(3)
    r.set_settings(ids[0], "food")
    r.start_game(ids[0])
    for i in ids:
        r.mark_seen(i)
    qs = QUESTIONS["food"]
    got = [r.next_question(ids[0]) for _ in range(len(qs) + 2)]
    assert got[:len(qs)] == qs and got[len(qs):] == qs[:2]
    assert r.next_question(ids[1]) == qs[0]     # each player keeps their own order


def test_lost_impostor_resets_to_lobby():
    r, ids = make_room(4)
    r.start_game(ids[0])
    imp = r.impostor_pid
    other = next(i for i in ids if i != imp)
    r.disconnect(other)
    assert r.lost_impostor_reset(other) is None  # a normal player dropping changes nothing
    r.disconnect(imp)
    name = r.players[imp].name
    assert r.lost_impostor_reset(imp) == name
    assert r.phase == "lobby" and imp not in r.players and r.main_job is None
    assert r.host_pid in r.players


def test_italian_content_complete_and_aligned():
    from content_it import HINTS_IT, QUESTIONS_IT, WORDS_IT
    for cat in CATEGORIES:
        assert len(QUESTIONS_IT[cat]) == len(QUESTIONS[cat])
        assert all(q.endswith("?") for q in QUESTIONS_IT[cat])
        assert all(w in WORDS_IT for w in WORDS[cat])
    assert all(h in HINTS_IT for g in RANDOM_THINGS.values() for _, h in g)


def test_every_game_error_has_italian():
    import ast, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    for f in ("game_logic.py", "room_manager.py"):
        tree = ast.parse((root / f).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "id", None) == "GameError"]
        assert calls and all(len(c.args) == 2 for c in calls), f
