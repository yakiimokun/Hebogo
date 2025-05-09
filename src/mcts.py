import time
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

class MCTSNode:
    """モンテカルロ木探索のノード"""
    def __init__(self, parent=None, prior=1.0):
        self.parent = parent
        self.children = {}
        self.visit_count = 0
        self.total_value = 0
        self.prior = prior

    @property
    def value(self):
        """ノードの価値を計算"""
        if self.visit_count == 0:
            return 0
        return self.total_value / self.visit_count

    def expand(self, action_probs):
        """子ノードを展開"""
        for action, prob in enumerate(action_probs):
            if action not in self.children:
                self.children[action] = MCTSNode(parent=self, prior=prob)

    def select_child(self, c_puct=1.0):
        """UCB値を基に子ノードを選択"""
        best_score = -float('inf')
        best_action = None
        best_child = None

        for action, child in self.children.items():
            ucb = (
                child.value +
                c_puct * child.prior * np.sqrt(self.visit_count) / (1 + child.visit_count)
            )
            if ucb > best_score:
                best_score = ucb
                best_action = action
                best_child = child

        return best_action, best_child

    def backpropagate(self, value):
        """バックプロパゲーション"""
        self.visit_count += 1
        self.total_value += value
        if self.parent:
            self.parent.backpropagate(-value)  # 相手の手番では価値が反転する

class MCTS:
    def __init__(self, model, board_size=19, simulations=100, c_puct=1.0):
        self.model = model
        self.board_size = board_size
        self.simulations = simulations
        self.c_puct = c_puct

    def run(self, board, current_player, time_limit=15.0):
        """
        モンテカルロ木探索（MCTS）を実行
        - board: 現在の盤面（numpy配列）
        - current_player: 現在のプレイヤー（1 = 黒, -1 = 白）
        - time_limit: 探索の制限時間（秒）
        """
        root = MCTSNode()
        start_time = time.time()

        while time.time() - start_time < time_limit:
            node = root
            simulation_board = board.copy()
            player = current_player

            # 選択
            while node.children:
                action, node = node.select_child(self.c_puct)
                simulation_board = self._apply_action(simulation_board, action, player)
                player = -player

            # 評価
            action_probs, value = self._evaluate(simulation_board, player)
            if not node.children:
                node.expand(action_probs)

            # バックプロパゲーション
            node.backpropagate(value)

        # 最善手を選択
        return self._select_action(root)

    def _evaluate(self, board, player):
        """ニューラルネットワークで盤面を評価"""
        board_tensor = torch.tensor(board, dtype=torch.float32).unsqueeze(0)
        policy, value = self.model(board_tensor)
        policy = F.softmax(policy, dim=-1).detach().cpu().numpy().flatten()
        value = value.detach().cpu().item() * player  # プレイヤー視点での価値
        return policy, value

    def _apply_action(self, board, action, player):
        """指定されたアクションを適用して盤面を更新"""
        board[action // self.board_size, action % self.board_size] = player
        return board

    def _select_action(self, root):
        """訪問回数が最大のアクションを選択"""
        visit_counts = {action: child.visit_count for action, child in root.children.items()}
        best_action = max(visit_counts, key=visit_counts.get)
        return best_action
    
class GoModel(nn.Module):
    """囲碁の盤面評価モデル"""
    def __init__(self, board_size=19):
        super(GoModel, self).__init__()
        self.board_size = board_size
        # 畳み込み層    
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        # 全結合層(Flattenして全結合へ)
        self.fc_input_dim = 64 * board_size * board_size # Conv2dの出力サイズ
        self.fc_policy = nn.Linear(self.fc_input_dim, board_size * board_size)
        self.fc_value = nn.Linear(self.fc_input_dim, 1)

    def forward(self, x):
        """ポリシー（行動確率）とバリュー（盤面の価値）を出力"""
        # 入力サイズの確認
        if len(x.shape) == 3: # (batch_size, board_size, board_size) → (batch_size, 1, board_size, board_size)
            x = x.unsqueeze(1)

        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))

        x = x.view(x.size(0), -1)
        policy = self.fc_policy(x)
        value = torch.tanh(self.fc_value(x))  # バリューは[-1, 1]に正規化
        return policy, value

