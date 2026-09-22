# Hebogo

## Policy Network の学習

リポジトリ直下から実行します。まず `requirements.txt` の依存関係を導入し、
`data/sgf/raw` 以下に9路・13路・19路のSGF棋譜を置きます。
学習と検証の局面が同じ棋譜に由来しないよう、分割はSGFファイル単位で行います。

```bash
python3 -m pip install -r requirements.txt
python3 scripts/train_policy.py --input data/sgf/raw --board-size 19 \
  --output data/sgf/processed/policy_19x19.pt
```

標準設定で検証するには、対象の盤面サイズの有効なSGFが2棋譜以上必要です。
1棋譜で学習処理だけを確認する場合は `--validation-fraction 0` を指定できますが、
その結果から未知の棋譜に対する性能は判断できません。
GUI の「PolicyValue AI」には、同じ盤面サイズで学習した Policy と Value の両方が必要です。
Value の学習例は次のとおりです。

```bash
python3 scripts/train_value.py --input data/sgf/raw --board-size 19 \
  --output data/sgf/processed/value_19x19.pth
```

学習後、`config.json` に盤面サイズ別の重みのパスを指定し、
対局設定で「PolicyValue AI」を選んでください。例えば19路では次のように設定します。

```json
{
  "policy_model_paths": {"19": "data/sgf/processed/policy_19x19.pth"},
  "value_model_paths": {"19": "data/sgf/processed/value_19x19.pth"}
}
```

従来の `policy_model_path` と単一の `value_model_path` も、サイズ別設定がない場合に使用できます。
Value の重みが設定されていない場合、GUI はエラーを表示し対局を開始しません。

## 9路の対戦評価

学習済みの9路モデルを、黒白を交代して Random AI と対戦させます。

```bash
python3 scripts/benchmark_policy.py --policy-model data/sgf/processed/policy_9x9.pth --opponent random --games 20
```

KataGo と比較する場合は `config.json` の `katago` 設定を用意し、
`--opponent katago` を指定します。`--seed` は Random AI の乱数を固定します。
勝率の分母は決着局のみで、持碁は半勝とします。上限手数 (`--max-moves`、既定243手)
に達した局やスコアを取得できない局は未決着として表示します。
着手時間は各エンジンの `genmove` 応答に要した壁時計時間の平均です。
モデルの読み込みや KataGo の起動、盤面の初期化、相手への着手通知は含みません。
内蔵エンジンの終局スコアは簡易日本ルールで計算し、死石の合意処理は含みません。
