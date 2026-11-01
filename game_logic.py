"""Pure game logic (no Flask / Socket.IO). One Room == one isolated game."""
import random
import secrets
import time
import uuid
from dataclasses import dataclass

from professions import PROFESSIONS

MIN_PLAYERS = 3
MAX_PLAYERS_LIMIT = 20
MAX_NAME_LEN = 16
ROLE_PHASES = ("reveal", "discussion", "voting", "tally", "final")


class GameError(Exception):
    """User-facing error (message is Arabic and safe to send to the client)."""


@dataclass
class Player:
    pid: str
    name: str
    token: str                 # private reconnect secret, never broadcast
    sid: str | None = None
    connected: bool = True
    seen: bool = False
    ready: bool = False
    vote: str | None = None


class Room:
    def __init__(self, code, max_players, rng=None, professions=None):
        if not MIN_PLAYERS <= max_players <= MAX_PLAYERS_LIMIT:
            raise GameError(f"عدد اللاعبين يجب أن يكون بين {MIN_PLAYERS} و {MAX_PLAYERS_LIMIT}.")
        self.code = code
        self.max_players = max_players
        self.rng = rng or random.SystemRandom()
        self.professions = list(dict.fromkeys(professions or PROFESSIONS))
        if len(self.professions) < 2:
            raise ValueError("Need at least two professions")
        self.players: dict[str, Player] = {}
        self.host_pid = None
        self.phase = "lobby"
        self.round_no = 0
        self.touched = time.time()
        self._reset_round()

    # ---------------------------------------------------------------- helpers
    def _reset_round(self):
        self.main_job = self.impostor_job = self.impostor_pid = None
        self.suspect_pid = self.outcome = None
        self.tally = {}
        self.vote_round = 0
        for p in self.players.values():
            p.seen = p.ready = False
            p.vote = None

    def _connected(self):
        return [p for p in self.players.values() if p.connected]

    def _require_host(self, pid):
        if pid != self.host_pid:
            raise GameError("هذا الإجراء للمضيف فقط.")

    def _require_phase(self, *phases):
        if self.phase not in phases:
            raise GameError("هذا الإجراء غير متاح في المرحلة الحالية.")

    @staticmethod
    def clean_name(name):
        name = " ".join(str(name or "").split())
        if not name:
            raise GameError("الرجاء إدخال اسم.")
        if len(name) > MAX_NAME_LEN:
            raise GameError(f"الاسم طويل جداً (الحد {MAX_NAME_LEN} حرفاً).")
        return name

    # ---------------------------------------------------------------- players
    def add_player(self, name, sid=None):
        if self.phase != "lobby":
            raise GameError("اللعبة بدأت بالفعل ولا يمكن الانضمام الآن.")
        name = self.clean_name(name)
        if len(self.players) >= self.max_players:
            raise GameError("الغرفة ممتلئة.")
        if any(p.name.casefold() == name.casefold() for p in self.players.values()):
            raise GameError("هذا الاسم مستخدم في الغرفة، اختر اسماً آخر.")
        p = Player(pid=uuid.uuid4().hex[:8], name=name, token=secrets.token_urlsafe(24), sid=sid)
        self.players[p.pid] = p
        if self.host_pid is None:
            self.host_pid = p.pid
        self.touched = time.time()
        return p

    def reconnect(self, token, sid):
        for p in self.players.values():
            if secrets.compare_digest(p.token, str(token or "")):
                p.sid, p.connected = sid, True
                self.touched = time.time()
                return p
        raise GameError("تعذّر استعادة جلستك. انضم من جديد.")

    def disconnect(self, pid):
        p = self.players.get(pid)
        if p:
            p.connected, p.sid = False, None
            self.touched = time.time()
            self._autoadvance()

    def remove_player(self, pid):
        """Leaving is only possible in the lobby; later it counts as a disconnect."""
        if self.phase != "lobby":
            self.disconnect(pid)
            return
        self.players.pop(pid, None)
        if pid == self.host_pid:
            nxt = next(iter(self._connected()), None) or next(iter(self.players.values()), None)
            self.host_pid = nxt.pid if nxt else None

    def _autoadvance(self):
        if self.phase == "reveal" and all(p.seen for p in self._connected()):
            self.phase = "discussion"

    # ------------------------------------------------------------------ flow
    def start_game(self, actor):
        self._require_host(actor)
        self._require_phase("lobby")
        self._begin_round()

    def _begin_round(self):
        for pid in [p.pid for p in self.players.values() if not p.connected]:
            del self.players[pid]            # drop absent players between rounds
        if len(self.players) < MIN_PLAYERS:
            raise GameError(f"يلزم {MIN_PLAYERS} لاعبين متصلين على الأقل.")
        self._reset_round()
        self.main_job, self.impostor_job = self.rng.sample(self.professions, 2)
        self.impostor_pid = self.rng.choice(list(self.players))
        self.round_no += 1
        self.vote_round = 1
        self.phase = "reveal"

    def role_for(self, pid):
        """The ONLY place a profession leaves the server, and only to its owner."""
        self._require_phase(*ROLE_PHASES)
        return self.impostor_job if pid == self.impostor_pid else self.main_job

    def mark_seen(self, pid):
        self._require_phase("reveal")
        self.players[pid].seen = True
        self._autoadvance()

    def set_ready(self, pid):
        self._require_phase("discussion")
        self.players[pid].ready = True

    def all_ready(self):
        return all(p.ready for p in self._connected())

    def all_voted(self):
        return all(p.vote is not None for p in self._connected())

    def start_voting(self, actor):
        self._require_host(actor)
        self._require_phase("discussion")
        if not self.all_ready():
            raise GameError("ليس كل اللاعبين جاهزين بعد.")
        self.phase = "voting"

    def cast_vote(self, pid, target):
        self._require_phase("voting")
        if target not in self.players:
            raise GameError("اللاعب غير موجود.")
        if target == pid:
            raise GameError("لا يمكنك التصويت لنفسك.")
        me = self.players[pid]
        if me.vote is not None:
            raise GameError("لقد صوّتّ بالفعل.")
        me.vote = target

    def close_voting(self, actor):
        self._require_host(actor)
        self._require_phase("voting")
        if not self.all_voted():
            raise GameError("لم يصوّت جميع اللاعبين بعد.")
        counts = {pid: 0 for pid in self.players}
        for p in self.players.values():
            if p.vote in counts:
                counts[p.vote] += 1
        top = max(counts.values())
        leaders = [pid for pid, c in counts.items() if c == top]
        self.tally = counts
        if len(leaders) == 1:
            self.outcome, self.suspect_pid = "suspect", leaders[0]
        else:
            self.outcome, self.suspect_pid = "tie", None
        self.phase = "tally"

    def new_vote(self, actor):
        self._require_host(actor)
        self._require_phase("tally")
        if self.outcome != "tie":
            raise GameError("لا يوجد تعادل.")
        for p in self.players.values():
            p.vote = None                      # nothing carries over
        self.tally, self.outcome = {}, None
        self.vote_round += 1
        self.phase = "voting"

    def reveal(self, actor):
        self._require_host(actor)
        self._require_phase("tally")
        if self.outcome != "suspect":
            raise GameError("لا يمكن الكشف قبل تحديد مشتبه به.")
        self.phase = "final"

    def new_round(self, actor):
        self._require_host(actor)
        self._require_phase("final")
        self._begin_round()

    def to_lobby(self, actor):
        self._require_host(actor)
        self._require_phase("final")
        self._reset_round()
        for pid in [p.pid for p in self.players.values() if not p.connected]:
            del self.players[pid]
        self.phase = "lobby"

    # ------------------------------------------------------------------ views
    def view(self, pid):
        """Per-player snapshot. Never contains jobs or the impostor before the final reveal."""
        me, st = self.players[pid], self.phase
        players = []
        for p in self.players.values():
            d = {"id": p.pid, "name": p.name, "connected": p.connected, "is_host": p.pid == self.host_pid}
            if st == "reveal":
                d["seen"] = p.seen
            elif st == "discussion":
                d["ready"] = p.ready
            elif st == "voting":
                d["voted"] = p.vote is not None
            players.append(d)
        v = {
            "code": self.code, "phase": st, "round_no": self.round_no,
            "vote_round": self.vote_round, "max_players": self.max_players,
            "me": {"id": pid, "name": me.name, "is_host": pid == self.host_pid,
                   "seen": me.seen, "ready": me.ready, "voted": me.vote is not None},
            "players": players,
            "can_start": len(self._connected()) >= MIN_PLAYERS,
            "all_ready": st == "discussion" and self.all_ready(),
            "all_voted": st == "voting" and self.all_voted(),
        }
        if st == "tally":
            v["outcome"], v["tally"] = self.outcome, self.tally
            v["suspect"] = self.suspect_pid
            v["tied"] = [k for k, c in self.tally.items() if c == max(self.tally.values())] if self.outcome == "tie" else []
        if st == "final":
            imp = self.players[self.impostor_pid]
            v["result"] = {
                "main_job": self.main_job, "impostor_job": self.impostor_job,
                "impostor_id": imp.pid, "impostor_name": imp.name,
                "suspect_id": self.suspect_pid,
                "correct": self.suspect_pid == self.impostor_pid,
                "tally": self.tally,
            }
        return v
