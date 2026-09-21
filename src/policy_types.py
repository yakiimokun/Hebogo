"""
共通の型・プロトコルを示す
"""
from typing import Protocol, TypeAlias
import torch
from .rules import Board, Point


Move: TypeAlias = Point | None


class PolicyModel(Protocol):
    """PolicyAIが利用できるモデルのインターフェース。"""

    board_size: int

    def __call__(self, inputs: torch.Tensor) -> torch.Tensor:
        """(N, 3, H, W)から(N, H * W + 1)のlogitsを返す。"""
        ...


class MoveSelector(Protocol):
    """GUIやGTPエンジンが利用する着手選択インターフェース。"""

    def get_move(
        self,
        board: Board,
        color: int,
        previous_board: Board | None = None,
        history=None,
    ) -> Move:
        """着手を(x, y)で返し、パスの場合はNoneを返す。"""
        ...