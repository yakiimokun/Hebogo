"""自殺手禁止ルールにおけるBensonの無条件生き判定。

生きと認定されない連の死活は未判定。領域には相手石も含めるが、
着手の減点に使う眼領域は相手石を含まないものに限定する。
参考: D. B. Benson, Life in the Game of Go (1976), sections 4, 7.
"""

from dataclasses import dataclass

from .rules import (
    BLACK, WHITE, EMPTY, Board, Point, _copy_board, _neighbors,
    _group_and_liberties,
)


@dataclass(frozen=True)
class BensonResult:
    """一色の無条件生きと、その証明を支える領域。"""

    color: int
    alive_chains: tuple[frozenset[Point], ...]
    vital_regions: tuple[frozenset[Point], ...]
    alive_stones: frozenset[Point]
    empty_eye_points: frozenset[Point]


@dataclass(frozen=True)
class _Region:
    """自色石で囲まれる領域と連への依存関係。"""

    points: frozenset[Point]
    empty_points: frozenset[Point]
    boundary_chains: frozenset[int]
    vital_to: frozenset[int]


def analyze_benson(board: Board, color: int) -> BensonResult:
    """相手だけが打ち続けても取れない連を、盤面を変更せず返す。"""
    current = _copy_board(board)
    if color not in (BLACK, WHITE):
        raise ValueError("color must be BLACK (1) or WHITE (-1)")
    size = len(current)
    chains = []
    liberties = []
    chain_at = {}
    for y in range(size):
        for x in range(size):
            if current[y][x] != color or (x, y) in chain_at:
                continue
            group, group_liberties = _group_and_liberties(current, x, y)
            chain_id = len(chains)
            chains.append(frozenset(group))
            liberties.append(group_liberties)
            chain_at.update((point, chain_id) for point in group)

    # 自色石以外を洪水探索する。相手石を空点と別の壁にしない。
    regions = []
    visited = set(chain_at)
    for y in range(size):
        for x in range(size):
            if (x, y) in visited:
                continue
            points, empty, boundary = set(), set(), set()
            pending = [(x, y)]
            visited.add((x, y))
            while pending:
                point = pending.pop()
                px, py = point
                points.add(point)
                if current[py][px] == EMPTY:
                    empty.add(point)
                for neighbor in _neighbors(px, py, size):
                    if neighbor in chain_at:
                        boundary.add(chain_at[neighbor])
                    elif neighbor not in visited:
                        visited.add(neighbor)
                        pending.append(neighbor)
            vital_to = {i for i in boundary if empty and empty <= liberties[i]}
            if vital_to:
                regions.append(_Region(
                    frozenset(points), frozenset(empty),
                    frozenset(boundary), frozenset(vital_to),
                ))

    active = set(range(len(chains)))
    while True:
        surviving = {
            i for i in active
            if sum(i in region.vital_to for region in regions) >= 2
        }
        if surviving == active:
            break
        active = surviving
        regions = [region for region in regions
                   if region.boundary_chains <= active]

    alive_chains = tuple(chains[i] for i in sorted(active))
    return BensonResult(
        color=color,
        alive_chains=alive_chains,
        vital_regions=tuple(region.points for region in regions),
        alive_stones=frozenset(point for chain in alive_chains for point in chain),
        empty_eye_points=frozenset(
            point for region in regions if region.points == region.empty_points
            for point in region.empty_points
        ),
    )


@dataclass(frozen=True)
class BensonMoveAssessment:
    """Benson生きを使った着手評価。減点は棋力向上用のヒューリスティック。"""

    fills_own_eye: bool
    invades_alive_eye: bool
    lost_alive_stones: int
    penalty: float

    @classmethod
    def evaluate(cls, board_after: Board, move: Point | None,
                 own: BensonResult, opponent: BensonResult):
        fills_own_eye = move in own.empty_eye_points
        invades_alive_eye = move in opponent.empty_eye_points
        lost = 0
        if fills_own_eye:
            after = analyze_benson(board_after, own.color)
            # 生きの保証を失った石数であり、死石数ではない。
            lost = len(own.alive_stones - after.alive_stones)
        penalty = float(max(1, lost)) if fills_own_eye or invades_alive_eye else 0.0
        return cls(fills_own_eye, invades_alive_eye, lost, penalty)
