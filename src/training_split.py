"""棋譜単位の訓練・検証割り当てを保存し、新規棋譜を訓練側へ追加する。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import tempfile

from .sgf_dataset import DatasetSample


def fixed_game_split(
    games: list[tuple[str, list[DatasetSample]]],
    input_dir: Path,
    board_size: int,
    validation_fraction: float,
    seed: int,
) -> tuple[list[tuple[str, list[DatasetSample]]], list[tuple[str, list[DatasetSample]]]]:
    """初回の検証棋譜を固定し、その後の追加棋譜を訓練用へ割り当てる。

    Args:
        games: 有効な棋譜の相対パスと学習サンプル。初回はパス順に渡す。
        input_dir: 元の SGF を保存したディレクトリ。
        board_size: 分割を共有する盤面サイズ。
        validation_fraction: 初回の検証割合。0 は保存せず検証を無効にする。
            検証割り当ての保存後は0に変更できない。
        seed: 初回の分割用乱数シード。既存の割り当てには影響しない。

    Returns:
        訓練棋譜と検証棋譜のリスト。検証順序も初回のまま維持する。

    Raises:
        ValueError: 履歴の破損、検証棋譜の欠落・内容変更、重複混入、同時更新。
        OSError: 元棋譜や割り当てファイルの読み書きに失敗した場合。
    """
    path = input_dir / f"split_{board_size}x{board_size}.json"
    lock = path.with_suffix(".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError(f"分割処理中かロックが残っています: {lock}") from error
    try:
        os.close(descriptor)
        return _split(games, input_dir, board_size, validation_fraction, seed, path)
    finally:
        lock.unlink(missing_ok=True)


def _split(games, input_dir, board_size, fraction, seed, path):
    """保存済み検証棋譜の内容を照合し、更新を一時ファイル経由で保存する。"""
    current = dict(games)
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(manifest, dict) or manifest.get("version") != 1
                    or manifest.get("board_size") != board_size):
                raise ValueError("版または盤面サイズが不正です")
            train_names = manifest["train_files"]
            validation = manifest["validation_files"]
            if (not isinstance(train_names, list) or not all(isinstance(p, str) for p in train_names)
                    or not isinstance(validation, list) or not validation
                    or not all(isinstance(item, dict) and isinstance(item.get("file"), str)
                               and isinstance(item.get("sha256"), str) for item in validation)):
                raise ValueError("棋譜一覧の形式が不正です")
            validation_names = [item["file"] for item in validation]
            names = train_names + validation_names
            if len(names) != len(set(names)):
                raise ValueError("割り当てに重複があります")
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"分割ファイルを読み込めません: {path}: {error}") from error
        if fraction == 0:
            raise ValueError("検証割り当てが保存済みのため --validation-fraction 0 は使えません")
        for item in validation:
            name = item["file"]
            if name not in current:
                raise ValueError(f"固定した検証棋譜がないか、読み込めません: {name}")
            if hashlib.sha256((input_dir / name).read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"固定した検証棋譜の内容が変更されています: {name}")
        known = set(names)
        additions = [name for name, _ in games if name not in known]
        validation_hashes = {item["sha256"] for item in validation}
        for name in additions:
            if hashlib.sha256((input_dir / name).read_bytes()).hexdigest() in validation_hashes:
                raise ValueError(f"追加棋譜が検証棋譜と同一内容です。訓練用には追加できません: {name}")
        # 削除された訓練棋譜の割り当ても記録に残し、復元時に再利用する。
        train_names = train_names + additions
        manifest["train_files"] = train_names
    else:
        shuffled = list(games)
        random.Random(seed).shuffle(shuffled)
        if fraction == 0:
            return shuffled, []
        count = max(1, min(len(games) - 1, int(len(games) * fraction)))
        validation_names = [name for name, _ in shuffled[:count]]
        train_names = [name for name, _ in shuffled[count:]]
        manifest = {
            "version": 1, "board_size": board_size,
            "initial_seed": seed, "initial_validation_fraction": fraction,
            "train_files": train_names,
            "validation_files": [
                {"file": name, "sha256": hashlib.sha256((input_dir / name).read_bytes()).hexdigest()}
                for name in validation_names
            ],
        }
    train = [(name, current[name]) for name in train_names if name in current]
    if not train:
        raise ValueError("固定した分割に訓練用棋譜がありません")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=input_dir, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return train, [(name, current[name]) for name in validation_names]
