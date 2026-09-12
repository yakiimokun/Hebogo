import random
from typing import Optional

from .rules import BLACK, WHITE, Board, Point, legal_moves

class RandomAI:
    """盤外・着手済み・自殺手・劫を除いた候補から一手を選ぶ。"""

    def __init__(self, color: int, rng: Optional[random.Random] = None):
        if color not in (BLACK, WHITE):
            raise ValueError("color must be BLACK (1) or WHITE (-1)")
        self.color = color
        self.rng = rng or random.Random()

    def get_move(self, board: Board, previous_board=None, history=None) -> Optional[Point]:
        """合法手を返す。候補がなければパスを表す ``None`` を返す。"""
        candidates = legal_moves(board, self.color, previous_board, history)
        return self.rng.choice(candidates) if candidates else None

    def get_legal_moves(self, board: Board, color=None, previous_board=None, history=None):
        """テストや盤面解析向けに合法手の一覧を返す。"""
        return legal_moves(board, self.color if color is None else color, previous_board, history)
