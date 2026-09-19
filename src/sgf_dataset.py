"""SGF 棋譜を方策・価値学習用の NumPy データへ変換する。"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Iterator, Optional

import numpy as np

from .rules import BLACK, EMPTY, WHITE, play_move


SUPPORTED_BOARD_SIZES = (9, 13, 19)


class SGFError(ValueError):
    """SGF の構文または棋譜内容が変換できないことを表す。"""


@dataclass
class SGFNode:
    """SGF の1ノードと、そこから分岐する子ノードを保持する。"""

    properties: dict[str, list[str]] = field(default_factory=dict)
    children: list["SGFNode"] = field(default_factory=list)


@dataclass(frozen=True)
class DatasetSample:
    """1局面分の入力盤面、正解手、手番視点の勝敗。"""

    board: np.ndarray
    move: int
    value: int


class _SGFParser:
    """学習データ生成に必要な SGF FF[4] の構文を解析する。"""

    def __init__(self, text: str):
        self.text = text
        self.position = 0

    def parse_collection(self) -> list[SGFNode]:
        trees = []
        self._skip_whitespace()
        while self.position < len(self.text):
            trees.append(self._parse_game_tree())
            self._skip_whitespace()
        if not trees:
            raise SGFError("SGF にゲームツリーがありません")
        return trees

    def _parse_game_tree(self) -> SGFNode:
        self._expect("(")
        self._skip_whitespace()

        sequence = []
        while self._peek() == ";":
            sequence.append(self._parse_node())
            self._skip_whitespace()
        if not sequence:
            raise SGFError("ゲームツリーにノードがありません")

        for current, following in zip(sequence, sequence[1:]):
            current.children.append(following)

        last = sequence[-1]
        while self._peek() == "(":
            last.children.append(self._parse_game_tree())
            self._skip_whitespace()

        self._expect(")")
        return sequence[0]

    def _parse_node(self) -> SGFNode:
        self._expect(";")
        properties: dict[str, list[str]] = {}
        self._skip_whitespace()

        while self._peek().isalpha() and self._peek().isupper():
            identifier = self._parse_identifier()
            self._skip_whitespace()
            values = []
            while self._peek() == "[":
                values.append(self._parse_value())
                self._skip_whitespace()
            if not values:
                raise SGFError(f"プロパティ {identifier} に値がありません")
            properties.setdefault(identifier, []).extend(values)

        return SGFNode(properties=properties)

    def _parse_identifier(self) -> str:
        start = self.position
        while self._peek().isalpha() and self._peek().isupper():
            self.position += 1
        return self.text[start:self.position]

    def _parse_value(self) -> str:
        self._expect("[")
        value = []
        while self.position < len(self.text):
            character = self.text[self.position]
            self.position += 1
            if character == "]":
                return "".join(value)
            if character != "\\":
                value.append(character)
                continue

            if self.position >= len(self.text):
                raise SGFError("プロパティ値の末尾に不完全なエスケープがあります")
            escaped = self.text[self.position]
            self.position += 1
            if escaped == "\r":
                if self._peek() == "\n":
                    self.position += 1
            elif escaped != "\n":
                value.append(escaped)

        raise SGFError("プロパティ値の ] がありません")

    def _skip_whitespace(self) -> None:
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1

    def _peek(self) -> str:
        if self.position >= len(self.text):
            return ""
        return self.text[self.position]

    def _expect(self, expected: str) -> None:
        if self._peek() != expected:
            raise SGFError(
                f"位置 {self.position} に {expected!r} が必要です"
            )
        self.position += 1


def _decode_sgf(path: Path) -> str:
    data = path.read_bytes()
    declared_match = re.search(br"CA\[([^\]]+)\]", data[:4096], re.IGNORECASE)
    declared = declared_match.group(1).decode("ascii", errors="ignore") if declared_match else None
    aliases = {
        "UTF-8": "utf-8-sig",
        "UTF8": "utf-8-sig",
        "SHIFT_JIS": "cp932",
        "SJIS": "cp932",
        "EUC-JP": "euc_jp",
        "ISO-8859-1": "latin-1",
    }
    encodings = []
    if declared:
        encodings.append(aliases.get(declared.upper(), declared))
    encodings.extend(("utf-8-sig", "cp932", "euc_jp", "latin-1"))

    for encoding in dict.fromkeys(encodings):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    raise SGFError("文字コードを判定できません")


def _main_sequence(root: SGFNode) -> Iterator[SGFNode]:
    """各分岐の先頭を本譜とみなし、ルートから順に返す。"""
    node: Optional[SGFNode] = root
    while node is not None:
        yield node
        node = node.children[0] if node.children else None


def _single_property(node: SGFNode, name: str, default: Optional[str] = None) -> Optional[str]:
    values = node.properties.get(name)
    return values[0] if values else default


def _coordinate(value: str, board_size: int) -> tuple[int, int]:
    if len(value) != 2:
        raise SGFError(f"不正な座標です: {value!r}")

    def component(character: str) -> int:
        if "a" <= character <= "z":
            return ord(character) - ord("a")
        if "A" <= character <= "Z":
            return 26 + ord(character) - ord("A")
        raise SGFError(f"不正な座標です: {value!r}")

    point = component(value[0]), component(value[1])
    if not (0 <= point[0] < board_size and 0 <= point[1] < board_size):
        raise SGFError(f"盤外の座標です: {value!r}")
    return point


def _move_coordinate(value: str, board_size: int) -> Optional[tuple[int, int]]:
    # 空文字が FF[4] のパス。19路以下の tt は古い棋譜で使われるパス表現。
    if value == "" or (value.lower() == "tt" and board_size <= 19):
        return None
    return _coordinate(value, board_size)


def _setup_points(value: str, board_size: int) -> Iterator[tuple[int, int]]:
    if ":" not in value:
        yield _coordinate(value, board_size)
        return
    start, end = value.split(":", 1)
    x1, y1 = _coordinate(start, board_size)
    x2, y2 = _coordinate(end, board_size)
    for y in range(min(y1, y2), max(y1, y2) + 1):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            yield x, y


def _apply_setup(node: SGFNode, board: list[list[int]], board_size: int) -> bool:
    changed = False
    for property_name, color in (("AB", BLACK), ("AW", WHITE), ("AE", EMPTY)):
        for value in node.properties.get(property_name, []):
            for x, y in _setup_points(value, board_size):
                board[y][x] = color
                changed = True
    return changed


def _winner(result: Optional[str]) -> int:
    normalized = (result or "").strip().upper()
    if normalized.startswith("B+"):
        return BLACK
    if normalized.startswith("W+"):
        return WHITE
    if normalized in {"0", "DRAW", "JIGO"}:
        return EMPTY
    raise SGFError(f"勝敗を判定できません: RE[{result or ''}]")


def samples_from_sgf(path: Path) -> tuple[int, list[DatasetSample]]:
    """1つの SGF の本譜から、手番視点の学習サンプルを生成する。"""
    trees = _SGFParser(_decode_sgf(path)).parse_collection()
    if len(trees) != 1:
        raise SGFError("1ファイルに複数の棋譜が含まれています")

    nodes = list(_main_sequence(trees[0]))
    root = nodes[0]
    if _single_property(root, "GM", "1") != "1":
        raise SGFError("囲碁以外の SGF です")
    try:
        board_size = int(_single_property(root, "SZ", "19"))
    except ValueError as error:
        raise SGFError("SZ は整数で指定してください") from error
    if board_size not in SUPPORTED_BOARD_SIZES:
        raise SGFError(f"未対応の盤面サイズです: {board_size}")

    winner = _winner(_single_property(root, "RE"))
    board = [[EMPTY] * board_size for _ in range(board_size)]
    previous_board = None
    samples = []

    for move_number, node in enumerate(nodes):
        if _apply_setup(node, board, board_size):
            previous_board = None

        moves = []
        if "B" in node.properties:
            moves.append((BLACK, node.properties["B"][0]))
        if "W" in node.properties:
            moves.append((WHITE, node.properties["W"][0]))
        if len(moves) > 1:
            raise SGFError(f"ノード {move_number} に黒白両方の着手があります")
        if not moves:
            continue

        color, encoded_move = moves[0]
        point = _move_coordinate(encoded_move, board_size)
        action = board_size * board_size
        if point is not None:
            x, y = point
            action = y * board_size + x

        value = EMPTY if winner == EMPTY else (1 if winner == color else -1)
        samples.append(
            DatasetSample(
                board=np.asarray(board, dtype=np.int8) * color,
                move=action,
                value=value,
            )
        )

        before_move = [row[:] for row in board]
        if point is not None:
            result = play_move(
                board,
                x,
                y,
                color,
                previous_board=previous_board,
            )
            if not result.legal:
                raise SGFError(
                    f"ノード {move_number} の着手 {encoded_move!r} が不正です: "
                    f"{result.reason}"
                )
            board = result.board
        previous_board = before_move

    if not samples:
        raise SGFError("着手がありません")
    return board_size, samples


def generate_datasets(input_dir: Path, output_dir: Path) -> dict:
    """input_dir 内の SGF を変換し、盤面サイズ別の NPZ と一覧を保存する。"""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"入力フォルダがありません: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[int, list[DatasetSample]] = {}
    processed_files = []
    skipped_files = []

    sgf_paths = sorted(
        path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".sgf"
    )
    for path in sgf_paths:
        try:
            board_size, samples = samples_from_sgf(path)
            grouped.setdefault(board_size, []).extend(samples)
            processed_files.append(
                {
                    "file": str(path.relative_to(input_dir)),
                    "board_size": board_size,
                    "samples": len(samples),
                }
            )
        except (OSError, SGFError) as error:
            skipped_files.append(
                {"file": str(path.relative_to(input_dir)), "reason": str(error)}
            )

    datasets = []
    for board_size, samples in sorted(grouped.items()):
        filename = f"train_{board_size}x{board_size}.npz"
        np.savez_compressed(
            output_dir / filename,
            boards=np.stack([sample.board for sample in samples]),
            moves=np.asarray([sample.move for sample in samples], dtype=np.int16),
            values=np.asarray([sample.value for sample in samples], dtype=np.int8),
        )
        datasets.append(
            {
                "file": filename,
                "board_size": board_size,
                "policy_size": board_size * board_size + 1,
                "samples": len(samples),
            }
        )

    manifest = {
        "input": str(input_dir),
        "output": str(output_dir),
        "found_files": len(sgf_paths),
        "processed_files": processed_files,
        "skipped_files": skipped_files,
        "datasets": datasets,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
