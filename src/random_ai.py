import random
from typing import Optional

from .rules import BLACK, EMPTY, WHITE, Board, Point, legal_moves, play_move


def _neighbors(point: Point, size: int):
    x, y = point
    if x > 0:
        yield x - 1, y
    if x + 1 < size:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y + 1 < size:
        yield x, y + 1


def _group_and_liberties(board: Board, point: Point) -> tuple[set[Point], set[Point]]:
    """指定点を含む連と、その呼吸点を返す。"""
    color = board[point[1]][point[0]]
    group: set[Point] = set()
    liberties: set[Point] = set()
    pending = [point]
    size = len(board)

    while pending:
        current = pending.pop()
        if current in group:
            continue
        group.add(current)
        for neighbor in _neighbors(current, size):
            x, y = neighbor
            if board[y][x] == EMPTY:
                liberties.add(neighbor)
            elif board[y][x] == color and neighbor not in group:
                pending.append(neighbor)

    return group, liberties


class RandomAI:
    """合法手のうち、明らかに価値が低い手を除いて一手を選ぶ。"""

    def __init__(self, color: int, rng: Optional[random.Random] = None):
        if color not in (BLACK, WHITE):
            raise ValueError("color must be BLACK (1) or WHITE (-1)")
        self.color = color
        self.rng = rng or random.Random()

    def get_move(self, board: Board, previous_board=None, history=None) -> Optional[Point]:
        """有用そうな合法手を返し、候補がなければパスする。"""
        candidates = self.get_worthwhile_moves(board, previous_board, history)
        return self.rng.choice(candidates) if candidates else None

    def get_worthwhile_moves(self, board: Board, previous_board=None, history=None):
        """石取りを残し、自眼埋めと自己アタリを除いた合法手を返す。"""
        # history がジェネレーターでも、全候補の判定に同じ履歴を利用できるようにする。
        history = tuple(history) if history is not None else None
        candidates = legal_moves(board, self.color, previous_board, history)
        worthwhile = []

        for point in candidates:
            result = play_move(
                board,
                *point,
                self.color,
                previous_board=previous_board,
                history=history,
            )

            # 石を取る手は、眼の中や自己アタリに見えても候補に残す。
            if result.captured:
                worthwhile.append(point)
                continue
            if self._fills_own_eye(board, point):
                continue

            _, liberties = _group_and_liberties(result.board, point)
            if len(liberties) <= 1:
                continue
            worthwhile.append(point)

        return worthwhile

    def _fills_own_eye(self, board: Board, point: Point) -> bool:
        """周囲と斜めの形から、明らかな自眼を埋める手かを判定する。"""
        size = len(board)
        if any(board[y][x] != self.color for x, y in _neighbors(point, size)):
            return False

        x, y = point
        diagonals = [
            (dx, dy)
            for dx, dy in (
                (x - 1, y - 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x + 1, y + 1),
            )
            if 0 <= dx < size and 0 <= dy < size
        ]
        non_friendly_diagonals = sum(
            board[dy][dx] != self.color for dx, dy in diagonals
        )
        on_edge = x in (0, size - 1) or y in (0, size - 1)
        allowed_bad_diagonals = 0 if on_edge else 1
        return non_friendly_diagonals <= allowed_bad_diagonals

    def get_legal_moves(self, board: Board, color=None, previous_board=None, history=None):
        """テストや盤面解析向けに合法手の一覧を返す。"""
        return legal_moves(board, self.color if color is None else color, previous_board, history)
