"""2つの GTP エンジンを同期させて対局させる。"""

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol


class GTPConnection(Protocol):
    def send_command(self, command: str): ...


@dataclass(frozen=True)
class GTPMatchResult:
    moves: tuple
    final_score: str | None
    reason: str
    move_times: tuple[tuple[str, float], ...] = ()


class GTPMatch:
    """黒・白それぞれの GTP 接続を使い、自動対局を進行する。"""

    def __init__(self, black: GTPConnection, white: GTPConnection, board_size=19, komi=6.5):
        self.black = black
        self.white = white
        self.board_size = board_size
        self.komi = komi

    def _setup(self):
        for engine in (self.black, self.white):
            for command in ("clear_board", f"boardsize {self.board_size}", f"komi {self.komi}"):
                if engine.send_command(command) is None:
                    raise RuntimeError(f"GTP command failed: {command}")

    def play(self, max_moves=None):
        """2連続パス、投了、または上限手数まで対局する。"""
        self._setup()
        limit = max_moves if max_moves is not None else self.board_size * self.board_size * 3
        moves = []
        move_times = []
        consecutive_passes = 0
        for turn in range(limit):
            color = "black" if turn % 2 == 0 else "white"
            player, opponent = ((self.black, self.white) if color == "black" else (self.white, self.black))
            started = perf_counter()
            vertex = player.send_command(f"genmove {color}")
            move_times.append((color, perf_counter() - started))
            if vertex is None:
                raise RuntimeError(f"{color} engine failed to generate a move")
            vertex = vertex.strip().lower()
            moves.append((color, vertex))
            if vertex == "resign":
                return GTPMatchResult(tuple(moves), None, f"{color}_resigned", tuple(move_times))
            if opponent.send_command(f"play {color} {vertex}") is None:
                raise RuntimeError(f"opponent rejected {color} move: {vertex}")
            consecutive_passes = consecutive_passes + 1 if vertex == "pass" else 0
            if consecutive_passes == 2:
                return GTPMatchResult(tuple(moves), self.black.send_command("final_score"), "two_passes", tuple(move_times))
        return GTPMatchResult(tuple(moves), None, "move_limit", tuple(move_times))
