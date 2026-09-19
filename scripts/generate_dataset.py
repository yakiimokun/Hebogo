#!/usr/bin/env python3
"""data/sgf/raw の SGF から学習用データを生成する。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sgf_dataset import generate_datasets  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SGF の本譜を方策・価値学習用の NPZ に変換します。"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "sgf" / "raw",
        help="SGF の入力フォルダ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "sgf" / "processed",
        help="NPZ と manifest.json の出力フォルダ",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    try:
        manifest = generate_datasets(arguments.input, arguments.output)
    except (OSError, ValueError) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1

    for dataset in manifest["datasets"]:
        print(f"生成: {dataset['file']} ({dataset['samples']}局面)")
    for skipped in manifest["skipped_files"]:
        print(f"スキップ: {skipped['file']}: {skipped['reason']}", file=sys.stderr)

    processed = len(manifest["processed_files"])
    skipped = len(manifest["skipped_files"])
    print(f"完了: {processed}棋譜を処理、{skipped}棋譜をスキップ")
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
