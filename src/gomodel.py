class GoModel(nn.Module):
    """囲碁の盤面評価モデル"""
    def __init__(self, board_size=19):
        super(GoModel, self).__init__()
        self.board_size = board_size
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.fc_policy = nn.Linear(64 * board_size * board_size, board_size * board_size)
        self.fc_value = nn.Linear(64 * board_size * board_size, 1)

    def forward(self, x):
        """ポリシー（行動確率）とバリュー（盤面の価値）を出力"""
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        policy = self.fc_policy(x)
        value = torch.tanh(self.fc_value(x))  # バリューは[-1, 1]に正規化
        return policy, value
