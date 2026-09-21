"""Policy Network を使う、プロセス不要の GTP 互換エンジン。"""

import pickle
import sys

import torch

from .policy_ai import PolicyAI
from .policy_network import PolicyNetwork
from .random_gtp_engine import (
    _COLUMNS,
    color_to_int,
    point_to_vertex,
    vertex_to_point,
)
from .rules import BLACK, calculate_score_japanese, play_move


class PolicyGTPEngine:
    """学習済みモデルと盤面を保持し、GTP コマンドに応答する。"""

    def __init__(self, board_size=19, komi=6.5, model_path=None, model=None):
        if not 2 <= board_size <= len(_COLUMNS):
            raise ValueError("unacceptable board size")
        if model is not None and model_path is not None:
            raise ValueError("provide either model or model_path, not both")
        if model is None:
            if not model_path:
                raise ValueError("a trained policy model or model_path is required")
            model = PolicyNetwork(board_size=board_size)
            try:
                state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
                model.load_state_dict(state_dict)
            except (OSError, RuntimeError, ValueError, TypeError, pickle.UnpicklingError) as error:
                raise ValueError(f"cannot load policy model: {error}") from error
        if getattr(model, "board_size", None) != board_size:
            raise ValueError("board size does not match policy model")
        self.ai = PolicyAI(model)
        self.board_size = board_size
        self.komi_value = float(komi)
        self.clear_board()

    def clear_board(self):
        self.board = [[0] * self.board_size for _ in range(self.board_size)]
        self.history = [[row[:] for row in self.board]]
        self.black_captures = 0
        self.white_captures = 0
        return True

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
        """成功時は応答本文、失敗時は None を返す。"""
        parts = command.strip().split()
        if not parts:
            return None
        name, args = parts[0].lower(), parts[1:]
        try:
            if name == "protocol_version":
                return "2"
            if name == "name":
                return "Hebogo Policy AI"
            if name == "version":
                return "1.0"
            if name == "boardsize":
                size = int(args[0])
                if size != self.ai.model.board_size:
                    raise ValueError("board size does not match policy model")
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
                move = self.ai.get_move(
                    self.board, color, previous_board=previous, history=self.history[:-1]
                )
                self._play(color, move)
                return "pass" if move is None else point_to_vertex(move, self.board_size)
            if name == "final_score":
                black, white = calculate_score_japanese(
                    self.board, self.komi_value, self.black_captures, self.white_captures
                )
                return f"B+{black - white:.1f}" if black > white else f"W+{white - black:.1f}"
            if name == "quit":
                return ""
        except (IndexError, ValueError, RuntimeError, OSError):
            return None
        return None

    def genmove(self, color):
        return self.send_command(f"genmove {color}")

    def play(self, color, vertex):
        return self.send_command(f"play {color} {vertex}") is not None

    def set_board_size(self, size):
        return self.send_command(f"boardsize {size}") is not None

    def komi(self, value):
        return self.send_command(f"komi {value}") is not None

    def get_final_score(self):
        return self.send_command("final_score")

    def showboard(self):
        return [row[:] for row in self.board], self.black_captures, self.white_captures

    def is_resign(self, move):
        return bool(move and move.lower() == "resign")

    def is_pass(self, move):
        return bool(move and move.lower() == "pass")

    def close(self):
        """外部プロセスを使わないため解放は不要。"""

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
