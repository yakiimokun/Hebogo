# Policy Network API

## 入力
- dtype: torch.float32
- shape: (batch_size, 3, board_size, board_size)
- channel 0: 空点
- channel 1: 現在の手番の石
- channel 2: 相手の石
- `encode_board(board, color)` はバッチ次元を除いた `(3, H, W)` を返す
- `board[y][x]`、黒石は `1`、白石は `-1`、空点は `0`

## 出力

- shape: (batch_size, board_size * board_size + 1)
- 出力index = y * board_size + x
- 最後のindexはパス(board_size * board_size)
- 出力はSoftmax適用前のlogits
- `point_to_index((x, y), board_size)` と `index_to_point(index, board_size)` で変換する
- `point_to_index(None, board_size)` はパスのindex、`index_to_point` はパスで `None` を返す

## PolicyAI

`PolicyAI(model).get_move(board, color, previous_board=None, history=None) -> tuple[int, int] | None`

- 着手可能な場合は(x, y)
- パスの場合はNone
- 占有点や自殺手などにはマスクを適用する
- `previous_board` と `history` が渡された場合は劫・超劫の判定にも使う

## GUI・GTP連携

- 設定画面の選択名は `PolicyValue AI`。Policy 単体の GTP エンジンは従来どおり利用できる
- `config.json` の `policy_model_paths` に盤面サイズ別の学習済み重みを指定する。従来の `policy_model_path` は対応サイズの設定がない場合に使用する
- Policy 単体には `PolicyGTPEngine(board_size=19, komi=6.5, model_path=None, model=None)` を使う。GUI は同エンジンに `value_model_path` も渡し、内部で `PolicyValueAI` を呼ぶ
- `model_path` とテスト用の注入モデルがどちらも無い場合はエラーとし、未学習モデルで対局しない
- モデルファイルは `PolicyNetwork(board_size)` の `state_dict` とする
- 学習後に `torch.save(model.state_dict(), path)` で保存する（未学習の重みは対局用に使わない）
- 学習済み重みはリポジトリに含まれない。GUIで対局するには別途学習した重みが必要

## SGFからの教師あり学習

- `data/sgf/raw` 以下のSGF本譜を使用し、盤面サイズごとに別のモデルを学習する
- SGFから得た手番視点の盤面は `0`=空点、`1`=現在の手番、`-1`=相手の石とし、入力の3チャンネルへ変換する
- 正解手は `y * board_size + x`、パスは `board_size * board_size`
- 出力logitsと正解手に `CrossEntropyLoss` を適用する。学習前にSoftmaxは適用しない
- 学習用と検証用はSGFファイル単位で分割し、同じ棋譜の局面を双方へ入れない
- 検証では損失と着手のTop-1正解率を測定し、検証損失が最良の `state_dict` を保存する
- 検証には2棋譜以上が必要。`--validation-fraction 0` は動作確認用に検証を明示的に無効化する
- `values`（勝敗ラベル）はPolicy Networkの教師あり学習には使用しない
