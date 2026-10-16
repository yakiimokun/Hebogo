"""SGF 棋譜から Policy Network を教師あり学習する。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.policy_network import PolicyNetwork  # noqa: E402
from src.policy_training_data import load_policy_splits  # noqa: E402


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("正の整数を指定してください")
    return number


def _positive_float(value: str) -> float:
    number = float(value)
    if not np.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("正の有限数を指定してください")
    return number


def _validation_fraction(value: str) -> float:
    number = float(value)
    if not np.isfinite(number) or not 0 <= number < 1:
        raise argparse.ArgumentTypeError("0以上1未満を指定してください")
    return number


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SGF 棋譜から Policy Network を学習し、state_dict を保存します。"
    )
    parser.add_argument("--input", type=Path, default=Path("data/sgf/raw"))
    parser.add_argument("--board-size", type=int, choices=(9, 13, 19), default=19)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--epochs", type=_positive_int, default=20)
    parser.add_argument("--batch-size", type=_positive_int, default=32)
    parser.add_argument("--learning-rate", type=_positive_float, default=1e-3)
    parser.add_argument("--validation-fraction", type=_validation_fraction, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--augment", action=argparse.BooleanOptionalAction, default=True,
                        help="訓練局面をランダムに回転・反転する（既定は有効、--no-augment で無効）")
    return parser.parse_args(argv)


def _encode_boards(boards: np.ndarray) -> torch.Tensor:
    """手番視点の -1/0/+1 盤面を、空点/手番/相手の3面へ変換する。"""
    channels = np.stack((boards == 0, boards == 1, boards == -1), axis=1)
    return torch.from_numpy(channels.astype(np.float32))


def _transform_sample(
    board: torch.Tensor, move: torch.Tensor, symmetry: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """3面の盤面と正解手を同じ対称変換で移し、パスは維持する。

    Args:
        board: 形状 (3, N, N) の入力盤面。
        move: 行優先の着手インデックス。N² はパス。
        symmetry: 0〜7。下位2ビットは反時計回りの90度回転数、
            4以上なら回転後に左右反転する。

    Returns:
        変換後の盤面と正解手。元のテンソルは変更しない。
    """
    size = board.shape[-1]
    rotations = symmetry % 4
    transformed = torch.rot90(board, rotations, dims=(-2, -1))
    index = int(move)
    if index != size * size:
        y, x = divmod(index, size)
        for _ in range(rotations):
            x, y = y, size - 1 - x
        if symmetry >= 4:
            x = size - 1 - x
        index = y * size + x
    if symmetry >= 4:
        transformed = transformed.flip(-1)
    return transformed.contiguous(), move.new_tensor(index)


class _AugmentedPolicyDataset(TensorDataset):
    """読み出すたびに8通りから1つ選び、局面と正解手を変換する。"""

    def __init__(self, boards: torch.Tensor, moves: torch.Tensor, seed: int):
        """入力と正解手、変換用の独立した乱数系列を初期化する。

        Args:
            boards: 形状 (N, 3, H, W) の入力盤面。
            moves: 各局面の正解手インデックス。
            seed: 対称変換用の乱数シード。
        """
        super().__init__(boards, moves)
        self._generator = torch.Generator().manual_seed(seed)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        """指定局面と正解手をランダムに同時変換して返す。

        Args:
            index: 読み出す局面の位置。

        Returns:
            回転・反転済みの入力盤面と正解手。
        """
        board, move = super().__getitem__(index)
        symmetry = int(torch.randint(8, (), generator=self._generator))
        return _transform_sample(board, move, symmetry)


def _loader(
    boards: np.ndarray,
    moves: np.ndarray,
    batch_size: int,
    shuffle: bool,
    seed: int,
    augment: bool = False,
) -> DataLoader:
    """局面を読み込み時に変換するローダーを作る。既定では変換しない。"""
    inputs = _encode_boards(boards)
    targets = torch.from_numpy(np.asarray(moves, dtype=np.int64))
    dataset = (_AugmentedPolicyDataset(inputs, targets, seed) if augment
               else TensorDataset(inputs, targets))
    generator = torch.Generator().manual_seed(seed) if shuffle else None
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, generator=generator)


def _device(requested: str) -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _epoch(
    model: PolicyNetwork,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
) -> tuple[float, float]:
    """1エポックの平均損失とtop-1正解率を返す。"""
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    count = 0
    criterion = torch.nn.CrossEntropyLoss()
    with torch.set_grad_enabled(training):
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            if optimizer is not None:
                optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, targets)
            if optimizer is not None:
                loss.backward()
                optimizer.step()
            size = targets.numel()
            total_loss += loss.item() * size
            total_correct += (logits.argmax(dim=1) == targets).sum().item()
            count += size
    return total_loss / count, total_correct / count


def main(argv: list[str] | None = None) -> int:
    """棋譜を分割し、訓練局面だけを拡張して Policy を学習する。

    Args:
        argv: コマンド引数。None の場合はプロセスの引数を使用する。

    Returns:
        正常終了時は0、データや保存処理のエラー時は1。
    """
    args = _arguments(argv)
    output = args.output or Path(
        f"data/sgf/processed/policy_{args.board_size}x{args.board_size}.pt"
    )
    try:
        splits = load_policy_splits(
            args.input,
            args.board_size,
            validation_fraction=args.validation_fraction,
            seed=args.seed,
        )
        if not len(splits.train_moves):
            raise ValueError("学習可能な棋譜がありません")
        if args.validation_fraction and not len(splits.validation_moves):
            raise ValueError(
                "検証用の棋譜がありません。2棋譜以上を用意するか、"
                "--validation-fraction 0 を指定してください"
            )
        for skipped in splits.skipped_files:
            print(
                f"スキップ: {skipped['file']}: {skipped['reason']}",
                file=sys.stderr,
            )
        print(
            f"学習: {len(splits.train_files)}棋譜 / {len(splits.train_moves)}局面、"
            f"検証: {len(splits.validation_files)}棋譜 / "
            f"{len(splits.validation_moves)}局面"
        )

        torch.manual_seed(args.seed)
        device = _device(args.device)
        model = PolicyNetwork(args.board_size).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
        train_loader = _loader(
            splits.train_boards, splits.train_moves, args.batch_size, True, args.seed,
            augment=args.augment,
        )
        print("訓練データ拡張: " + ("回転・反転8通りから局面ごとにランダム選択" if args.augment else "無効"))
        validation_loader = (
            _loader(
                splits.validation_boards,
                splits.validation_moves,
                args.batch_size,
                False,
                args.seed,
            )
            if len(splits.validation_moves)
            else None
        )
        best_loss = float("inf")
        output.parent.mkdir(parents=True, exist_ok=True)
        for epoch in range(1, args.epochs + 1):
            train_loss, train_accuracy = _epoch(model, train_loader, device, optimizer)
            report = (
                f"epoch {epoch}/{args.epochs}: train loss={train_loss:.4f}, "
                f"top-1={train_accuracy:.3f}"
            )
            if validation_loader is not None:
                validation_loss, validation_accuracy = _epoch(
                    model, validation_loader, device, None
                )
                report += (
                    f", validation loss={validation_loss:.4f}, "
                    f"top-1={validation_accuracy:.3f}"
                )
                should_save = validation_loss < best_loss
                best_loss = min(best_loss, validation_loss)
            else:
                should_save = True
            print(report)
            if should_save:
                torch.save(model.state_dict(), output)
        print(f"保存: {output} ({device})")
        return 0
    except (OSError, ValueError) as error:
        message = str(error)
        if args.validation_fraction and "2 件以上" in message:
            message += "。1棋譜で動作確認する場合は --validation-fraction 0 を指定してください"
        print(f"エラー: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
