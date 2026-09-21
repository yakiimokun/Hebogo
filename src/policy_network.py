"""盤面から各着手とパスのlogitを出すPolicy Network。"""

import torch
from torch import nn


class PolicyNetwork(nn.Module):
    """3チャンネルの盤面から行優先の着手logitを予測する。"""

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
        self.policy_head = nn.Linear(
            32 * board_size * board_size,
            board_size * board_size + 1,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(N, 3, size, size)から(N, size²+1)の未正規化logitを返す。"""
        if x.ndim != 4 or x.shape[1:] != (3, self.board_size, self.board_size):
            raise ValueError(
                "input shape must be (N, 3, board_size, board_size)"
            )
        return self.policy_head(self.conv(x).flatten(1))
