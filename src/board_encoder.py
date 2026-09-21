"""盤面とPolicy Networkの入出力インデックスを相互変換する。"""

import torch

from .rules import BLACK, EMPTY, WHITE, Board, Point


def encode_board(board: Board, color: int) -> torch.Tensor:
    """盤面を空点・手番の石・相手の石の3チャンネルへ変換する。"""
    if color not in (BLACK, WHITE):
        raise ValueError("color must be BLACK (1) or WHITE (-1)")

    rows = [list(row) for row in board]
    size = len(rows)
    if not size or any(len(row) != size for row in rows):
        raise ValueError("board must be a non-empty square board")
    if any(value not in (EMPTY, BLACK, WHITE) for row in rows for value in row):
        raise ValueError("board values must be 0, 1, or -1")

    stones = torch.tensor(rows, dtype=torch.int8)
    return torch.stack(
        (
            (stones == EMPTY).to(torch.float32),
            (stones == color).to(torch.float32),
            (stones == -color).to(torch.float32),
        )
    )


def point_to_index(point: Point | None, board_size: int) -> int:
    """着手(x, y)を行優先の出力番号へ変換し、Noneをパスとする。"""
    _validate_board_size(board_size)
    if point is None:
        return board_size * board_size
    x, y = point
    if not (isinstance(x, int) and isinstance(y, int)):
        raise ValueError("point coordinates must be integers")
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise ValueError("point is outside the board")
    return y * board_size + x


def index_to_point(index: int, board_size: int) -> Point | None:
    """行優先の出力番号を着手(x, y)へ戻し、パスならNoneを返す。"""
    _validate_board_size(board_size)
    if not isinstance(index, int) or not 0 <= index <= board_size * board_size:
        raise ValueError("index is outside the policy output")
    if index == board_size * board_size:
        return None
    return index % board_size, index // board_size


def _validate_board_size(board_size: int) -> None:
    if not isinstance(board_size, int) or board_size <= 0:
        raise ValueError("board_size must be a positive integer")
