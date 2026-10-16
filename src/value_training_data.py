"""Value Network の教師あり学習用に SGF を棋譜単位で分割する。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .sgf_dataset import SGFError, SUPPORTED_BOARD_SIZES, DatasetSample, samples_from_sgf
from .training_split import fixed_game_split


@dataclass(frozen=True)
class ValueDataSplit:
    """棋譜を跨がない学習・検証データと、使用した棋譜の一覧。"""

    train_boards: np.ndarray
    train_values: np.ndarray
    validation_boards: np.ndarray
    validation_values: np.ndarray
    train_files: tuple[str, ...]
    validation_files: tuple[str, ...]
    skipped_files: tuple[dict[str, str], ...]


def _arrays(
    games: list[tuple[str, list[DatasetSample]]], board_size: int
) -> tuple[np.ndarray, np.ndarray]:
    samples = [sample for _, game_samples in games for sample in game_samples]
    if not samples:
        return (
            np.empty((0, board_size, board_size), dtype=np.int8),
            np.empty((0,), dtype=np.float32),
        )
    boards = np.stack([sample.board for sample in samples]).astype(np.int8, copy=False)
    values = np.asarray([sample.value for sample in samples], dtype=np.float32)
    return boards, values


def load_value_splits(
    input_dir: Path,
    board_size: int,
    validation_fraction: float = 0.2,
    seed: int = 42,
) -> ValueDataSplit:
    """検証棋譜を固定して分割し、手番視点の盤面・勝敗を返す。

    Args:
        input_dir: SGF の入力先。盤面サイズ別の分割 JSON もここに保存する。
        board_size: 対象の盤面サイズ（9・13・19）。
        validation_fraction: 初回の検証割合。保存後の検証棋譜は変えない。
            0 は未保存時のみ検証を無効化する。
        seed: 初回の分割用乱数シード。

    Returns:
        訓練・検証局面と教師ラベル、使用棋譜・除外棋譜の一覧。

    Raises:
        ValueError: 引数・分割履歴が不正、棋譜不足、検証棋譜の欠落・変更。
        OSError: 入力先や分割ファイルを読み書きできない場合。
    """
    input_dir = Path(input_dir)
    if board_size not in SUPPORTED_BOARD_SIZES:
        raise ValueError(f"未対応の盤面サイズです: {board_size}")
    if not 0 <= validation_fraction < 1:
        raise ValueError("validation_fraction は 0 以上 1 未満にしてください")
    if not input_dir.is_dir():
        raise FileNotFoundError(f"入力フォルダがありません: {input_dir}")

    games: list[tuple[str, list[DatasetSample]]] = []
    skipped: list[dict[str, str]] = []
    paths = sorted(
        (path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".sgf"),
        key=lambda path: str(path.relative_to(input_dir)),
    )
    for path in paths:
        relative_path = str(path.relative_to(input_dir))
        try:
            size, samples = samples_from_sgf(path)
        except (OSError, SGFError) as error:
            skipped.append({"file": relative_path, "reason": str(error)})
            continue
        if size == board_size:
            games.append((relative_path, samples))

    if not games:
        raise ValueError(f"{board_size} 路の有効な SGF 棋譜がありません: {input_dir}")
    if validation_fraction > 0 and len(games) < 2:
        raise ValueError("検証データを分けるには有効な棋譜が 2 件以上必要です")

    train_games, validation_games = fixed_game_split(
        games, input_dir, board_size, validation_fraction, seed
    )
    train_boards, train_values = _arrays(train_games, board_size)
    validation_boards, validation_values = _arrays(validation_games, board_size)
    return ValueDataSplit(
        train_boards=train_boards,
        train_values=train_values,
        validation_boards=validation_boards,
        validation_values=validation_values,
        train_files=tuple(path for path, _ in train_games),
        validation_files=tuple(path for path, _ in validation_games),
        skipped_files=tuple(skipped),
    )
