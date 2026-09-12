"""ランダム AI を標準的な GTP コマンドで操作するエンジン。"""

import random
import sys

from .random_ai import RandomAI
from .rules import BLACK, WHITE, calculate_score_japanese, play_move

_COLUMNS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def color_to_int(color):
    normalized = color.lower()
    if normalized in ("b", "black"):
        return BLACK
    if normalized in ("w", "white"):
        return WHITE
    raise ValueError("invalid color")


def point_to_vertex(point, board_size):
    x, y = point
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise ValueError("point is outside the board")
    return f"{_COLUMNS[x]}{board_size - y}"


def vertex_to_point(vertex, board_size):
    if vertex.lower() == "pass":
        return None
    column = vertex[0].upper()
    if column not in _COLUMNS[:board_size]:
        raise ValueError("invalid vertex")
    try:
        row = int(vertex[1:])
    except ValueError as error:
        raise ValueError("invalid vertex") from error
    point = (_COLUMNS.index(column), board_size - row)
    if not (0 <= point[1] < board_size):
        raise ValueError("invalid vertex")
    return point


class RandomGTPEngine:
    """盤面を保持し、ランダム AI に GTP 形式で応答する。"""

    def __init__(self, board_size=19, komi=6.5, seed=None):
        self.rng = random.Random(seed)
        self.board_size = board_size
        self.komi_value = float(komi)
        self.clear_board()

    def clear_board(self):
        self.board = [[0] * self.board_size for _ in range(self.board_size)]
        self.history = [[row[:] for row in self.board]]
        self.black_captures = 0
        self.white_captures = 0

    def _play(self, color, point):
        if point is None:
            self.history.append([row[:] for row in self.board])
            return
        previous = self.history[-2] if len(self.history) >= 2 else None
        result = play_move(self.board, *point, color, previous_board=previous)
        if not result.legal:
            raise ValueError(f"illegal move: {result.reason}")
        self.board = result.board
        if color == BLACK:
            self.white_captures += result.captured
        else:
            self.black_captures += result.captured
        self.history.append([row[:] for row in self.board])

    def send_command(self, command):
        """GTPClient と同じ形で、成功時は応答本文、失敗時は ``None`` を返す。"""
        parts = command.strip().split()
        if not parts:
            return None
        name, args = parts[0].lower(), parts[1:]
        try:
            if name == "protocol_version": return "2"
            if name == "name": return "Hebogo Random AI"
            if name == "version": return "1.0"
            if name == "boardsize":
                size = int(args[0])
                if size < 2 or size > len(_COLUMNS):
                    raise ValueError("unacceptable size")
                self.board_size = size
                self.clear_board()
                return ""
            if name == "clear_board":
                self.clear_board()
                return ""
            if name == "komi":
                self.komi_value = float(args[0])
                return ""
            if name == "play":
                self._play(color_to_int(args[0]), vertex_to_point(args[1], self.board_size))
                return ""
            if name == "genmove":
                color = color_to_int(args[0])
                previous = self.history[-2] if len(self.history) >= 2 else None
                move = RandomAI(color, self.rng).get_move(
                    self.board, previous_board=previous, history=self.history[:-1]
                )
                self._play(color, move)
                return "pass" if move is None else point_to_vertex(move, self.board_size)
            if name == "final_score":
                black, white = calculate_score_japanese(
                    self.board, self.komi_value, self.black_captures, self.white_captures)
                return f"B+{black - white:.1f}" if black > white else f"W+{white - black:.1f}"
            if name == "quit": return ""
        except (IndexError, ValueError):
            return None
        return None

    def run(self, input_stream=sys.stdin, output_stream=sys.stdout):
        """標準入出力で GTP 2 の要求を処理する。"""
        for line in input_stream:
            command = line.strip()
            if not command:
                continue
            response = self.send_command(command)
            output_stream.write("? command failed\n\n" if response is None else f"= {response}\n\n")
            output_stream.flush()
            if command.split()[0].lower() == "quit":
                break


if __name__ == "__main__":
    RandomGTPEngine().run()
