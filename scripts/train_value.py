"""SGF 棋譜から Value Network を教師あり学習する。"""

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

from src.value_network import ValueNetwork  # noqa: E402
from src.value_training_data import load_value_splits  # noqa: E402


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
        description="SGF 棋譜から Value Network を学習し、state_dict を保存します。"
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
    return parser.parse_args(argv)


def _encode_boards(boards: np.ndarray) -> torch.Tensor:
    """手番視点の -1/0/+1 盤面を、空点/手番/相手の3面へ変換する。"""
    channels = np.stack((boards == 0, boards == 1, boards == -1), axis=1)
    return torch.from_numpy(channels.astype(np.float32))


def _loader(
    boards: np.ndarray,
    values: np.ndarray,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    dataset = TensorDataset(
        _encode_boards(boards),
        torch.from_numpy(np.asarray(values, dtype=np.float32)).reshape(-1, 1),
    )
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
    model: ValueNetwork,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
) -> tuple[float, float]:
    """1 エポックの平均二乗誤差と平均絶対誤差を返す。"""
    training = optimizer is not None
    model.train(training)
    total_squared_error = 0.0
    total_absolute_error = 0.0
    count = 0
    with torch.set_grad_enabled(training):
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            if optimizer is not None:
                optimizer.zero_grad()
            predictions = model(inputs)
            error = predictions - targets
            loss = error.square().mean()
            if optimizer is not None:
                loss.backward()
                optimizer.step()
            total_squared_error += error.detach().square().sum().item()
            total_absolute_error += error.detach().abs().sum().item()
            count += targets.numel()
    return total_squared_error / count, total_absolute_error / count


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    output = args.output or Path(
        f"data/sgf/processed/value_{args.board_size}x{args.board_size}.pt"
    )
    try:
        splits = load_value_splits(
            args.input,
            args.board_size,
            validation_fraction=args.validation_fraction,
            seed=args.seed,
        )
        if not len(splits.train_values):
            raise ValueError("学習可能な棋譜がありません")
        if args.validation_fraction and not len(splits.validation_values):
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
            f"学習: {len(splits.train_files)}棋譜 / {len(splits.train_values)}局面、"
            f"検証: {len(splits.validation_files)}棋譜 / "
            f"{len(splits.validation_values)}局面"
        )

        torch.manual_seed(args.seed)
        device = _device(args.device)
        model = ValueNetwork(args.board_size).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
        train_loader = _loader(
            splits.train_boards, splits.train_values, args.batch_size, True, args.seed
        )
        validation_loader = (
            _loader(
                splits.validation_boards,
                splits.validation_values,
                args.batch_size,
                False,
                args.seed,
            )
            if len(splits.validation_values)
            else None
        )
        best_loss = float("inf")
        output.parent.mkdir(parents=True, exist_ok=True)
        for epoch in range(1, args.epochs + 1):
            train_loss, train_mae = _epoch(model, train_loader, device, optimizer)
            report = (
                f"epoch {epoch}/{args.epochs}: train loss={train_loss:.4f}, "
                f"mae={train_mae:.4f}"
            )
            if validation_loader is not None:
                validation_loss, validation_mae = _epoch(
                    model, validation_loader, device, None
                )
                report += (
                    f", validation loss={validation_loss:.4f}, "
                    f"mae={validation_mae:.4f}"
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
