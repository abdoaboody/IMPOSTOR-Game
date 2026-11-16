"""Pure game logic (no Flask / Socket.IO). One Room == one isolated game."""
import random
import secrets
import time
import uuid
from dataclasses import dataclass

from content import CATEGORIES, FOOD, QUESTIONS, RANDOM_THINGS
from content_it import WORDS_IT
from professions import PROFESSIONS

MIN_PLAYERS = 3
MAX_PLAYERS_LIMIT = 20
MAX_NAME_LEN = 16
ROLE_PHASES = ("reveal", "discussion", "voting", "tally", "final")
ACTIVE_PHASES = ("reveal", "discussion", "voting", "tally")   # impostor-loss watch applies here
MODES = ("decoy", "blind")     # decoy: impostor gets a different word; blind: impostor is told, no word


class GameError(Exception):
    """User-facing error. Carries the Arabic message (str(e)) and its Italian translation (e.it)."""

    def __init__(self, msg, it=None):
        super().__init__(msg)
        self.it = it or msg


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
    dropped_at: float = 0.0
    q_pos: dict | None = None  # per-category position in the ordered question list


class Room:
    def __init__(self, code, max_players, rng=None, professions=None):
        if not MIN_PLAYERS <= max_players <= MAX_PLAYERS_LIMIT:
            raise GameError(f"عدد اللاعبين يجب أن يكون بين {MIN_PLAYERS} و {MAX_PLAYERS_LIMIT}.", f"Il numero di giocatori deve essere tra {MIN_PLAYERS} e {MAX_PLAYERS_LIMIT}.")
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
        self.category, self.mode, self.hints = "jobs", "decoy", False
        self.touched = time.time()
        self._reset_round()

    # ---------------------------------------------------------------- helpers
    def _reset_round(self):
        self.main_job = self.impostor_job = self.impostor_pid = self.hint = None
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
            raise GameError("هذا الإجراء للمضيف فقط.", "Questa azione è riservata all'host.")

    def _require_phase(self, *phases):
        if self.phase not in phases:
            raise GameError("هذا الإجراء غير متاح في المرحلة الحالية.", "Questa azione non è disponibile in questa fase.")

    @staticmethod
    def clean_name(name):
        name = " ".join(str(name or "").split())
        if not name:
            raise GameError("الرجاء إدخال اسم.", "Inserisci un nome.")
        if len(name) > MAX_NAME_LEN:
            raise GameError(f"الاسم طويل جداً (الحد {MAX_NAME_LEN} حرفاً).", f"Il nome è troppo lungo (massimo {MAX_NAME_LEN} caratteri).")
        return name

    # ---------------------------------------------------------------- players
    def add_player(self, name, sid=None):
        if self.phase != "lobby":
            raise GameError("اللعبة بدأت بالفعل ولا يمكن الانضمام الآن.", "La partita è già iniziata, non puoi entrare ora.")
        name = self.clean_name(name)
        if len(self.players) >= self.max_players:
            raise GameError("الغرفة ممتلئة.", "La stanza è piena.")
        if any(p.name.casefold() == name.casefold() for p in self.players.values()):
            raise GameError("هذا الاسم مستخدم في الغرفة، اختر اسماً آخر.", "Questo nome è già usato nella stanza, scegline un altro.")
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
        raise GameError("تعذّر استعادة جلستك. انضم من جديد.", "Impossibile ripristinare la sessione. Entra di nuovo.")

    def disconnect(self, pid):
        p = self.players.get(pid)
        if p:
            p.connected, p.sid = False, None
            p.dropped_at = time.time()
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

    def _drop_absent(self):
        for pid in [p.pid for p in self.players.values() if not p.connected]:
            del self.players[pid]
        if self.host_pid not in self.players:
            nxt = next(iter(self._connected()), None) or next(iter(self.players.values()), None)
            self.host_pid = nxt.pid if nxt else None

    def kick(self, actor, target):
        """Host removes a player while waiting in the lobby."""
        self._require_host(actor)
        self._require_phase("lobby")
        if target == actor:
            raise GameError("لا يمكنك إخراج نفسك.", "Non puoi espellere te stesso.")
        p = self.players.pop(target, None)
        if not p:
            raise GameError("اللاعب غير موجود.", "Giocatore non trovato.")
        self.touched = time.time()
        return p

    def set_settings(self, actor, category=None, mode=None, hints=None):
        self._require_host(actor)
        self._require_phase("lobby")
        if category is not None:
            if category not in CATEGORIES:
                raise GameError("قسم غير صالح.", "Categoria non valida.")
            self.category = category
        if mode is not None:
            if mode not in MODES:
                raise GameError("نوع لعب غير صالح.", "Modalità di gioco non valida.")
            self.mode = mode
        if hints is not None:
            self.hints = bool(hints)

    def hints_active(self):
        return self.mode == "blind" and self.category == "random" and self.hints

    def lost_impostor_reset(self, pid):
        """Impostor dropped mid-round and never came back: everyone returns to the lobby."""
        if self.phase not in ACTIVE_PHASES or pid != self.impostor_pid:
            return None
        p = self.players.get(pid)
        if not p or p.connected:
            return None
        name = p.name
        self._reset_round()
        self._drop_absent()
        self.phase = "lobby"
        return name

    def next_question(self, pid):
        """Ordered (not random) yes/no questions for the round's category; wraps around."""
        self._require_phase("discussion")
        p = self.players[pid]
        p.q_pos = p.q_pos or {}
        qs = QUESTIONS[self.category]
        i = p.q_pos.get(self.category, 0)
        p.q_pos[self.category] = (i + 1) % len(qs)
        return qs[i % len(qs)]

    def _autoadvance(self):
        if self.phase == "reveal" and all(p.seen for p in self._connected()):
            self.phase = "discussion"

    # ------------------------------------------------------------------ flow
    def start_game(self, actor):
        self._require_host(actor)
        self._require_phase("lobby")
        self._begin_round()

    def _begin_round(self):
        self._drop_absent()                  # drop absent players between rounds
        if len(self.players) < MIN_PLAYERS:
            raise GameError(f"يلزم {MIN_PLAYERS} لاعبين متصلين على الأقل.", f"Servono almeno {MIN_PLAYERS} giocatori in linea.")
        self._reset_round()
        hint = None
        if self.category == "food":
            self.main_job, self.impostor_job = self.rng.sample(FOOD, 2)
        elif self.category == "random":
            group = RANDOM_THINGS[self.rng.choice(sorted(RANDOM_THINGS))]   # both words share one kind
            (self.main_job, hint), (self.impostor_job, _) = self.rng.sample(group, 2)
        else:
            self.main_job, self.impostor_job = self.rng.sample(self.professions, 2)
        if self.mode == "blind":
            self.impostor_job = None
            self.hint = hint if self.hints_active() else None
        self.impostor_pid = self.rng.choice(list(self.players))
        self.round_no += 1
        self.vote_round = 1
        self.phase = "reveal"

    def role_for(self, pid):
        """The ONLY place a secret word leaves the server, and only to its owner.
        decoy mode: the impostor just gets a different word (and is not told).
        blind mode: the impostor is told, with no word (and a tiny hint if enabled)."""
        self._require_phase(*ROLE_PHASES)
        if pid != self.impostor_pid:
            return {"word": self.main_job, "impostor": False, "hint": None}
        if self.mode == "blind":
            return {"word": None, "impostor": True, "hint": self.hint}
        return {"word": self.impostor_job, "impostor": False, "hint": None}

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
            raise GameError("ليس كل اللاعبين جاهزين بعد.", "Non tutti i giocatori sono ancora pronti.")
        self.phase = "voting"

    def cast_vote(self, pid, target):
        self._require_phase("voting")
        if target not in self.players:
            raise GameError("اللاعب غير موجود.", "Giocatore non trovato.")
        if target == pid:
            raise GameError("لا يمكنك التصويت لنفسك.", "Non puoi votare per te stesso.")
        me = self.players[pid]
        if me.vote is not None:
            raise GameError("لقد صوّتّ بالفعل.", "Hai già votato.")
        me.vote = target

    def close_voting(self, actor):
        self._require_host(actor)
        self._require_phase("voting")
        if not self.all_voted():
            raise GameError("لم يصوّت جميع اللاعبين بعد.", "Non tutti i giocatori hanno ancora votato.")
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

    def back_to_game(self, actor):
        """After a tie: return to the discussion; everyone gets ready again, then a fresh vote."""
        self._require_host(actor)
        self._require_phase("tally")
        if self.outcome != "tie":
            raise GameError("لا يوجد تعادل.", "Non c'è nessun pareggio.")
        for p in self.players.values():
            p.vote, p.ready = None, False      # nothing carries over
        self.tally, self.outcome = {}, None
        self.vote_round += 1
        self.phase = "discussion"

    def reveal(self, actor):
        self._require_host(actor)
        self._require_phase("tally")
        if self.outcome != "suspect":
            raise GameError("لا يمكن الكشف قبل تحديد مشتبه به.", "Non si può rivelare prima di avere un sospettato.")
        self.phase = "final"

    def new_round(self, actor):
        self._require_host(actor)
        self._require_phase("final")
        self._begin_round()

    def to_lobby(self, actor):
        self._require_host(actor)
        self._require_phase("final")
        self._reset_round()
        self._drop_absent()
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
            "settings": {"category": self.category, "mode": self.mode, "hints": self.hints},
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
                "category": self.category, "mode": self.mode,
                "main_job_it": WORDS_IT.get(self.main_job), "impostor_job_it": WORDS_IT.get(self.impostor_job),
            }
        return v
