"""盤面から手番視点の勝敗評価を出す Value Network。"""

import torch
from torch import nn


class ValueNetwork(nn.Module):
    """3 チャンネルの盤面から [-1, 1] の価値を予測する。"""

    def __init__(self, board_size: int = 19):
        super().__init__()
        if not isinstance(board_size, int) or board_size <= 0:
            raise ValueError("board_size must be a positive integer")
        self.board_size = board_size
        self.conv = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.value_head = nn.Sequential(
            nn.Linear(32 * board_size * board_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(N, 3, size, size) から (N, 1) の手番視点の価値を返す。"""
        if x.ndim != 4 or x.shape[1:] != (3, self.board_size, self.board_size):
            raise ValueError("input shape must be (N, 3, board_size, board_size)")
        return self.value_head(self.conv(x).flatten(1))
