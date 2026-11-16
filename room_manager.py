"""Registry of rooms and socket-id bookkeeping. Swap storage here for a DB later."""
import secrets
import threading
import time

from game_logic import GameError, Room

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I


class RoomManager:
    def __init__(self, professions=None):
        self.rooms: dict[str, Room] = {}
        self.sids: dict[str, tuple[str, str]] = {}     # sid -> (code, pid)
        self.lock = threading.RLock()
        self.professions = professions

    def _new_code(self):
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(5))
            if code not in self.rooms:
                return code

    def _bind(self, room, player, sid):
        if sid in self.sids:
            raise GameError("أنت داخل غرفة بالفعل.")
        self.sids[sid] = (room.code, player.pid)

    def create_room(self, name, max_players, sid):
        with self.lock:
            self.cleanup()
            try:
                max_players = int(max_players)
            except (TypeError, ValueError):
                raise GameError("عدد اللاعبين غير صالح.")
            room = Room(self._new_code(), max_players, professions=self.professions)
            player = room.add_player(name, sid)
            self._bind(room, player, sid)
            self.rooms[room.code] = room
            return room, player

    def _room(self, code):
        room = self.rooms.get(str(code or "").strip().upper())
        if not room:
            raise GameError("الغرفة غير موجودة. تحقق من الرمز.")
        return room

    def join(self, code, name, sid):
        with self.lock:
            room = self._room(code)
            player = room.add_player(name, sid)
            try:
                self._bind(room, player, sid)
            except GameError:
                room.remove_player(player.pid)
                raise
            return room, player

    def rejoin(self, code, token, sid):
        with self.lock:
            room = self._room(code)
            player = room.reconnect(token, sid)
            for old, (c, p) in list(self.sids.items()):
                if c == room.code and p == player.pid:
                    del self.sids[old]            # evict stale socket
            self.sids[sid] = (room.code, player.pid)
            return room, player

    def lookup(self, sid):
        with self.lock:
            code, pid = self.sids.get(sid, (None, None))
            room = self.rooms.get(code)
            if not room or pid not in room.players:
                raise GameError("الجلسة غير صالحة. حدّث الصفحة.")
            return room, room.players[pid]

    def disconnect(self, sid):
        with self.lock:
            entry = self.sids.pop(sid, None)
            room = self.rooms.get(entry[0]) if entry else None
            if not room or entry[1] not in room.players:
                return None
            player = room.players[entry[1]]
            if player.sid != sid:
                return None
            room.disconnect(player.pid)
            return room, player

    def leave(self, sid):
        with self.lock:
            room, player = self.lookup(sid)
            self.sids.pop(sid, None)
            room.remove_player(player.pid)
            if not room.players:
                self.rooms.pop(room.code, None)
                return None
            return room

    def cleanup(self, max_idle=6 * 3600):
        now = time.time()
        for code, room in list(self.rooms.items()):
            if not room._connected() and now - room.touched > max_idle:
                del self.rooms[code]
