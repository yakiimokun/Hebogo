# Policy Network API

## 入力
- dtype: torch.float32
- shape: (batch_size, 3, board_size, board_size)
- channel 0: 空点
- channel 1: 現在の手番の石
- channel 2: 相手の石

## 出力

- shape: (batch_size, board_size * board_size + 1)
- 出力index = y * board_size + x
- 最後のindexはパス(board_size * board_size)
- 出力はSoftmax適用前のlogits

## PolicyAI

get_move(board, color) -> tuple[int, int] | None

- 着手可能な場合は(x, y)
- パスの場合はNone
- 占有点や自殺手などにはマスクを適用する