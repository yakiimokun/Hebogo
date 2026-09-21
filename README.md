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
学習後、`config.json` の `policy_model_path` に保存した重みのパスを指定し、
対局設定で「Policy AI」を選んでください。
