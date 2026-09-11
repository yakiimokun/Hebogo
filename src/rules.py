"""囲碁の着手可否を判定するルール処理。

盤面は ``0``（空点）、``1``（黒）、``-1``（白）の二次元配列で表す。
このモジュールは盤面を直接変更せず、着手後の新しい盤面を返す。
"""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple


EMPTY = 0
BLACK = 1
WHITE = -1

OUT_OF_BOUNDS = "out_of_bounds"
OCCUPIED = "occupied"
SUICIDE = "suicide"
KO = "ko"

Point = Tuple[int, int]
Board = Sequence[Sequence[int]]


@dataclass(frozen=True)
class MoveResult:
    """データ保持用のクラス(イミュータブル)"""
    """着手判定の結果。``board`` は常に通常の list 形式で返す。"""

    legal: bool
    board: list[list[int]]
    captured: int = 0
    reason: Optional[str] = None


def _copy_board(board: Board) -> list[list[int]]:
    copied = [list(row) for row in board]
    if not copied or any(len(row) != len(copied) for row in copied):
        raise ValueError("board must be a non-empty square board")
    if any(value not in (EMPTY, BLACK, WHITE) for row in copied for value in row):
        raise ValueError("board values must be 0, 1, or -1")
    return copied


def _neighbors(x: int, y: int, size: int) -> Iterable[Point]:
    if x > 0:
        yield x - 1, y
    if x + 1 < size:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y + 1 < size:
        yield x, y + 1


def _group_and_liberties(board: Board, x: int, y: int) -> tuple[set[Point], set[Point]]:
    color = board[y][x]
    group: set[Point] = set()
    liberties: set[Point] = set()
    pending = [(x, y)]
    size = len(board)

    while pending:
        px, py = pending.pop()
        if (px, py) in group:
            continue
        group.add((px, py))
        for nx, ny in _neighbors(px, py, size):
            value = board[ny][nx]
            if value == EMPTY:
                liberties.add((nx, ny))
            elif value == color and (nx, ny) not in group:
                pending.append((nx, ny))
    return group, liberties


def play_move(
    board: Board,
    x: int,
    y: int,
    color: int,
    previous_board: Optional[Board] = None,
    history: Optional[Iterable[Board]] = None,
) -> MoveResult:
    """着手を試し、合法なら石取りを反映した盤面を返す。

    ``previous_board`` を渡すと単純劫（着手後にその盤面へ戻る手）を、
    ``history`` を渡すと同一局面の再現をすべて禁じる超劫を判定する。
    """
    current = _copy_board(board)
    if color not in (BLACK, WHITE):
        raise ValueError("color must be BLACK (1) or WHITE (-1)")

    size = len(current)
    if not (0 <= x < size and 0 <= y < size):
        return MoveResult(False, current, reason=OUT_OF_BOUNDS)
    if current[y][x] != EMPTY:
        return MoveResult(False, current, reason=OCCUPIED)

    candidate = [row[:] for row in current]
    candidate[y][x] = color
    captured = 0

    # 隣接する相手の連を、一つの連につき一度だけ調べる。
    checked: set[Point] = set()
    for nx, ny in _neighbors(x, y, size):
        if candidate[ny][nx] != -color or (nx, ny) in checked:
            continue
        group, liberties = _group_and_liberties(candidate, nx, ny)
        checked.update(group)
        if not liberties:
            captured += len(group)
            for gx, gy in group:
                candidate[gy][gx] = EMPTY

    _, liberties = _group_and_liberties(candidate, x, y)
    if not liberties:
        return MoveResult(False, current, reason=SUICIDE)

    if previous_board is not None and candidate == _copy_board(previous_board):
        return MoveResult(False, current, reason=KO)

    if history is not None:
        for old_board in history:
            if candidate == _copy_board(old_board):
                return MoveResult(False, current, reason=KO)

    return MoveResult(True, candidate, captured=captured)


def forbidden_reason(
    board: Board,
    x: int,
    y: int,
    color: int,
    previous_board: Optional[Board] = None,
    history: Optional[Iterable[Board]] = None,
) -> Optional[str]:
    """合法手なら ``None``、着手禁止なら理由を返す。"""
    return play_move(board, x, y, color, previous_board, history).reason


def is_legal_move(
    board: Board,
    x: int,
    y: int,
    color: int,
    previous_board: Optional[Board] = None,
    history: Optional[Iterable[Board]] = None,
) -> bool:
    """指定した手が合法かを返す。"""
    return play_move(board, x, y, color, previous_board, history).legal


def legal_moves(
    board: Board,
    color: int,
    previous_board: Optional[Board] = None,
    history: Optional[Iterable[Board]] = None,
) -> list[Point]:
    """現在の盤面における全合法手を ``(x, y)`` で返す。"""
    size = len(_copy_board(board))
    return [
        (x, y)
        for y in range(size)
        for x in range(size)
        if is_legal_move(board, x, y, color, previous_board, history)
    ]


def calculate_score_japanese(
    board: Board,
    komi: float = 6.5,
    black_captures: int = 0,
    white_captures: int = 0,
) -> tuple[float, float]:
    """日本ルールの簡易得点（地＋アゲハマ）を返す。

    ``black_captures`` は白が取った黒石、``white_captures`` は黒が
    取った白石の数。死石の合意処理は含まず、盤上で囲まれた空点を地とする。
    """
    current = _copy_board(board)
    size = len(current)
    visited: set[Point] = set()
    black_territory = 0
    white_territory = 0

    for y in range(size):
        for x in range(size):
            if current[y][x] != EMPTY or (x, y) in visited:
                continue
            region: set[Point] = set()
            borders: set[int] = set()
            pending = [(x, y)]
            while pending:
                px, py = pending.pop()
                if (px, py) in region:
                    continue
                region.add((px, py))
                visited.add((px, py))
                for nx, ny in _neighbors(px, py, size):
                    value = current[ny][nx]
                    if value == EMPTY and (nx, ny) not in region:
                        pending.append((nx, ny))
                    elif value != EMPTY:
                        borders.add(value)

            if borders == {BLACK}:
                black_territory += len(region)
            elif borders == {WHITE}:
                white_territory += len(region)

    return (
        float(black_territory + white_captures),
        float(white_territory + black_captures) + float(komi),
    )


class Rules:
    """クラス形式で利用したい呼び出し側向けの互換インターフェース。"""

    play_move = staticmethod(play_move)
    forbidden_reason = staticmethod(forbidden_reason)
    is_legal_move = staticmethod(is_legal_move)
    legal_moves = staticmethod(legal_moves)
    calculate_score_japanese = staticmethod(calculate_score_japanese)
