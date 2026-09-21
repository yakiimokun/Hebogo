"""Policy Network の出力から合法な着手を選択する。"""

import torch

from .board_encoder import encode_board, point_to_index
from .rules import BLACK, WHITE, Board, legal_moves


class PolicyAI:
    """局面を推論し、パスを含む合法候補の最大 logit を選ぶ。"""

    def __init__(self, model):
        if not hasattr(model, "board_size"):
            raise ValueError("policy model must define board_size")
        self.model = model
        self.model.eval()

    def get_move(self, board: Board, color: int, previous_board=None, history=None):
        """着手を (x, y) で返す。パスは None。"""
        if color not in (BLACK, WHITE):
            raise ValueError("color must be BLACK (1) or WHITE (-1)")
        size = self.model.board_size
        if len(board) != size or any(len(row) != size for row in board):
            raise ValueError("board size does not match policy model")
        # 履歴がジェネレーターでも、候補ごとの劫判定で同じ内容を使う。
        history = tuple(history) if history is not None else None
        candidates = legal_moves(board, color, previous_board, history)
        if not candidates:
            return None

        inputs = encode_board(board, color).unsqueeze(0)
        with torch.inference_mode():
            logits = self.model(inputs)
        if logits.shape != (1, size * size + 1):
            raise ValueError("policy model returned incorrect logits shape")
        scores = logits[0]
        if not torch.isfinite(scores).all().item():
            raise ValueError("policy model returned non-finite logits")

        best_move = None
        best_score = scores[size * size].item()
        for point in candidates:
            score = scores[point_to_index(point, size)].item()
            if score > best_score:
                best_score = score
                best_move = point
        return best_move
