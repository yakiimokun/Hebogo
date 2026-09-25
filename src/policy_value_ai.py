"""Policy と Value の推論結果から合法な着手を選択する。"""

import math

import torch

from .board_encoder import encode_board, point_to_index
from .move_diagnostics import CandidateEvaluation, MoveAnalysis
from .policy_ai import PolicyAI
from .rules import (
    BLACK, EMPTY, WHITE, Board, Point, group_and_liberties, legal_moves, play_move,
)


def _tactical_moves(
    board: Board,
    color: int,
    legal: set[Point],
    previous_board=None,
    history=None,
) -> dict[Point, tuple[int, int]]:
    """取りと、着手後に2呼吸以上になるアタリ救出の候補を返す。"""
    size = len(board)
    visited: set[Point] = set()
    rescue_targets: dict[Point, list[tuple[Point, int]]] = {}
    tactical_points: set[Point] = set()

    for y in range(size):
        for x in range(size):
            if board[y][x] == EMPTY or (x, y) in visited:
                continue
            group, liberties = group_and_liberties(board, x, y)
            visited.update(group)
            if len(liberties) != 1:
                continue
            liberty = next(iter(liberties))
            tactical_points.add(liberty)
            if board[y][x] == color:
                rescue_targets.setdefault(liberty, []).append(((x, y), len(group)))

    result: dict[Point, tuple[int, int]] = {}
    for point in tactical_points & legal:
        played = play_move(board, *point, color, previous_board, history)
        if not played.legal:
            continue
        rescued = 0
        for representative, group_size in rescue_targets.get(point, ()):
            rx, ry = representative
            if played.board[ry][rx] != color:
                continue
            _, liberties = group_and_liberties(played.board, rx, ry)
            if len(liberties) > 1:
                rescued += group_size
        if played.captured or rescued:
            result[point] = (played.captured, rescued)
    return result


class PolicyValueAI:
    """Policy の上位候補とパスを、次手番視点の Value で再評価する。"""

    def __init__(
        self,
        policy_model,
        value_model=None,
        top_k: int = 5,
        policy_weight: float = 1.0,
        value_weight: float = 0.001,
    ):
        self.policy_ai = PolicyAI(policy_model)
        self.value_model = value_model
        if value_model is not None:
            if not hasattr(value_model, "board_size"):
                raise ValueError("value model must define board_size")
            if value_model.board_size != policy_model.board_size:
                raise ValueError("policy and value model board sizes do not match")
            value_model.eval()
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        if not math.isfinite(policy_weight) or not math.isfinite(value_weight):
            raise ValueError("weights must be finite")
        self.top_k = top_k
        self.policy_weight = policy_weight
        self.value_weight = value_weight
        self.last_analysis = None

    def get_move(self, board: Board, color: int, previous_board=None, history=None):
        """着手を (x, y) で返す。パスは None。"""
        self.last_analysis = None
        if self.value_model is None:
            return self.policy_ai.get_move(board, color, previous_board, history)
        if color not in (BLACK, WHITE):
            raise ValueError("color must be BLACK (1) or WHITE (-1)")
        size = self.policy_ai.model.board_size
        if len(board) != size or any(len(row) != size for row in board):
            raise ValueError("board size does not match policy model")

        # ジェネレーターで渡された履歴を全候補の判定に再利用する。
        history = tuple(history) if history is not None else None
        legal = legal_moves(board, color, previous_board, history)
        if not legal:
            return None

        with torch.inference_mode():
            logits = self.policy_ai.model(encode_board(board, color).unsqueeze(0))
        if logits.shape != (1, size * size + 1):
            raise ValueError("policy model returned incorrect logits shape")
        if not torch.isfinite(logits).all().item():
            raise ValueError("policy model returned non-finite logits")

        scores = logits[0]
        ranked = sorted(
            legal,
            key=lambda point: (
                -scores[point_to_index(point, size)].item(),
                point_to_index(point, size),
            ),
        )
        tactical = _tactical_moves(
            board, color, set(legal), previous_board=previous_board, history=history
        )
        candidates = list(dict.fromkeys(ranked[:self.top_k] + sorted(tactical))) + [None]
        legal_indices = [point_to_index(point, size) for point in legal] + [size * size]
        probabilities = torch.softmax(scores[legal_indices], dim=0)
        policy_scores = dict(zip(legal_indices, probabilities.tolist()))

        next_boards = []
        for point in candidates:
            if point is None:
                next_boards.append(board)
            else:
                result = play_move(board, *point, color, previous_board, history)
                next_boards.append(result.board)
        value_inputs = torch.stack(
            [encode_board(next_board, -color) for next_board in next_boards]
        )
        with torch.inference_mode():
            values = self.value_model(value_inputs)
        if values.shape != (len(candidates), 1):
            raise ValueError("value model returned incorrect values shape")
        if not torch.isfinite(values).all().item() or (values.abs() > 1).any().item():
            raise ValueError("value model returned non-finite or out-of-range values")

        best_move = None
        best_score = float("-inf")
        evaluations = []
        for point, value in zip(candidates, values[:, 0].tolist()):
            captured, rescued = tactical.get(point, (0, 0))
            # 救出石数を優先点にする。Valueの重みを上げれば、戦術候補
            # 同士を学習済みValueで比較する余地も維持される。
            rescue_priority = float(rescued)
            score = (
                self.policy_weight * policy_scores[point_to_index(point, size)]
                - self.value_weight * value
                + rescue_priority
            )
            evaluations.append(CandidateEvaluation(
                move=point,
                policy_probability=policy_scores[point_to_index(point, size)],
                value=value,
                combined_score=score,
                captured_stones=captured,
                rescued_stones=rescued,
                rescue_priority=rescue_priority,
            ))
            if score > best_score:
                best_move, best_score = point, score
        self.last_analysis = MoveAnalysis(
            selected_move=best_move,
            policy_weight=self.policy_weight,
            value_weight=self.value_weight,
            candidates=tuple(evaluations),
        )
        return best_move
