# Value Network 契約

## 入力と出力

- 入力は既存の `encode_board(board, color)` を使う。
- dtype は `torch.float32`、shape は `(N, 3, board_size, board_size)`。
- チャンネルは順に空点、評価する手番の石、相手の石。
- `ValueNetwork(board_size)` の出力は shape `(N, 1)`、値域 `[-1, 1]`。
- `+1` は入力で指定した手番の勝ち、`-1` は負け、`0` は持碁を表す。
- 盤面サイズが一致しない入力は `ValueError` とする。

## 教師データと学習

- `src/sgf_dataset.py` の `DatasetSample.value` を教師ラベルに使う。
- ラベルは各局面の手番視点で `+1`（勝ち）、`-1`（負け）、`0`（持碁）。
- 学習用と検証用は SGF ファイル単位で分割し、同じ棋譜を双方に含めない。
- 盤面サイズごとに別モデルを学習する。
- 保存形式は `ValueNetwork(board_size)` の `state_dict` とする。
- 未学習の重みを対局用として読み込まない。
- `scripts/train_value.py --input data/sgf/raw --board-size 19 --output value_19x19.pt` で学習する。平均二乗誤差で学習し、検証損失が最良の `state_dict` を保存する。
- 検証には2棋譜以上が必要。1棋譜で処理だけ確認する場合は `--validation-fraction 0` を指定する。

## Policy Network との融合

- 既存の Policy Network の入力、出力、重み形式は変更しない。
- Policy の logits で合法な候補を順位付けし、上位 K 手とパスを評価する。
- 各候補を着手した後の盤面を、**次の手番**を指定して Value Network に入力する。
- Value の出力は次の手番から見た値なので、元の手番の評価には符号を反転する。
- 候補の総合点は `policy_weight * policy_score - value_weight * next_player_value` とする。
- `policy_score` は合法手とパスの logits 全体に softmax を適用した確率とする。候補の順位は元の logits で決める。
- 既定値は `K=5`、`policy_weight=1.0`、`value_weight=1.0` とする。K はパス以外の候補数で、パスは常に別枠で評価する。
- 着手には既存の合法手判定を使い、劫・超劫、パスを維持する。
- Value モデルが未設定の場合は既存の Policy AI と同じ動作にする。
- モデルのサイズ不一致や非有限値は明示的なエラーにする。
- 公開 API は `PolicyValueAI(policy_model, value_model=None, top_k=5, policy_weight=1.0, value_weight=1.0).get_move(board, color, previous_board=None, history=None)` とする。返り値は `(x, y)`、パスは `None`。
- GUI の選択名は `PolicyValue AI`。`config.json` の `policy_model_paths` と `value_model_paths` から同じ盤面サイズの学習済み重みを読み込む。単一パス設定の `policy_model_path` と `value_model_path` も使える。
- GUI ではどちらかの重みが未設定・読み込み不能なら対局を開始しない。

## 並列作業の境界

1. Value 実装担当: `src/value_network.py`、学習用コード。上記 API を実装する。
2. テスト担当: `test/test_value_network.py` など。契約に基づき shape、値域、入力エラー、手番視点のラベルを検証する。実装の内部構造には依存しない。
3. 融合担当: 新しい着手選択クラスとそのテスト。Value Network はこの契約の API だけを前提にし、担当 1 のファイルを編集しない。

共通ファイルの変更が必要になった場合は、担当を決めてから編集する。
