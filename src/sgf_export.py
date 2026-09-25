"""現在の対局とAI診断情報をSGF FF[4]として出力する。"""

from .move_diagnostics import MoveAnalysis, MoveRecord
from .rules import BLACK, WHITE, Point


def _escape(value: object) -> str:
    """SGFのSimpleText/Text値として安全な文字列へ変換する。"""
    return str(value).replace("\\", "\\\\").replace("]", "\\]").replace("\r", "")


def _coordinate(move: Point | None) -> str:
    if move is None:
        return ""
    x, y = move
    return f"{chr(ord('a') + x)}{chr(ord('a') + y)}"


def _move_name(move: Point | None, board_size: int) -> str:
    if move is None:
        return "PASS"
    x, y = move
    column = chr(ord("A") + x + (1 if x >= 8 else 0))
    return f"{column}{board_size - y}"


def _analysis_comment(analysis: MoveAnalysis, board_size: int) -> str:
    lines = [
        f"AI selected: {_move_name(analysis.selected_move, board_size)}",
        f"Policy weight: {analysis.policy_weight:.9g}",
        f"Value weight: {analysis.value_weight:.9g}",
        "Candidates (combined score order):",
    ]
    ranked = sorted(analysis.candidates, key=lambda item: item.combined_score, reverse=True)
    for index, candidate in enumerate(ranked, 1):
        lines.append(
            f"{index}. {_move_name(candidate.move, board_size)} | "
            f"policy={candidate.policy_probability:.9g} | "
            f"value={candidate.value:.9g} | captured={candidate.captured_stones} | "
            f"rescued={candidate.rescued_stones} | "
            f"combined={candidate.combined_score:.9g}"
        )
    return "\n".join(lines)


def build_diagnostic_sgf(
    board_size: int,
    komi: float,
    black_name: str,
    white_name: str,
    moves: list[MoveRecord] | tuple[MoveRecord, ...],
    current_turn: int,
) -> str:
    """対局開始から現在までの履歴を、AI評価コメント付きSGFにする。"""
    if current_turn not in (BLACK, WHITE):
        raise ValueError("current_turn must be BLACK or WHITE")
    if board_size <= 0 or board_size > 26:
        raise ValueError("board_size must be between 1 and 26")

    root = (
        f"(;GM[1]FF[4]CA[UTF-8]AP[Hebogo:1.0]"
        f"SZ[{board_size}]KM[{komi:g}]"
        f"PB[{_escape(black_name)}]PW[{_escape(white_name)}]"
    )
    nodes = []
    for record in moves:
        if record.color not in (BLACK, WHITE):
            raise ValueError("move color must be BLACK or WHITE")
        color = "B" if record.color == BLACK else "W"
        node = f";{color}[{_coordinate(record.move)}]"
        if record.analysis is not None:
            node += f"C[{_escape(_analysis_comment(record.analysis, board_size))}]"
        nodes.append(node)

    turn = "B" if current_turn == BLACK else "W"
    return root + "".join(nodes) + f";PL[{turn}]C[Current turn: {turn}])\n"
