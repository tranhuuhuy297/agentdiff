"""Step alignment via Needleman–Wunsch global sequence alignment.

Agent runs share a long common prefix then diverge; global alignment with a
similarity-weighted scoring matrix yields the diff-style pairing users expect
from ``git diff``. The core is pure and dependency-free — the scorer is injected
(lexical by default, semantic opt-in), so this module never does I/O.

Complexity: O(n·m) time and space, where n,m are step counts. Fine for the
tens–hundreds of steps a typical agent run contains.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from agentdiff.models import Step
from agentdiff.similarity import get_scorer

Scorer = Callable[[Step, Step], float]

# Default tuning. A diagonal move scores ``similarity - MATCH_OFFSET`` so that
# dissimilar pairs are penalized relative to opening a gap.
DEFAULT_GAP_PENALTY = 0.5
DEFAULT_MATCH_THRESHOLD = 0.6
MATCH_OFFSET = 0.5


class Op(StrEnum):
    MATCH = "match"
    SUBSTITUTE = "substitute"
    INSERT_B = "insert_b"  # present in B, absent in A
    DELETE_A = "delete_a"  # present in A, absent in B


@dataclass
class AlignedPair:
    a: Step | None
    b: Step | None
    op: Op
    score: float = 0.0


def needleman_wunsch(
    a: list[Step],
    b: list[Step],
    score_fn: Scorer,
    gap_penalty: float,
) -> list[tuple[int | None, int | None, float]]:
    """Return ordered (i, j, score) moves; ``None`` index marks a gap."""
    n, m = len(a), len(b)
    # Score matrix with gap-initialized first row/column.
    f = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        f[i][0] = -i * gap_penalty
    for j in range(1, m + 1):
        f[0][j] = -j * gap_penalty

    sim = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            sim[i][j] = score_fn(a[i], b[j])

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = f[i - 1][j - 1] + (sim[i - 1][j - 1] - MATCH_OFFSET)
            up = f[i - 1][j] - gap_penalty
            left = f[i][j - 1] - gap_penalty
            f[i][j] = max(diag, up, left)

    # Traceback from bottom-right to origin.
    moves: list[tuple[int | None, int | None, float]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            s = sim[i - 1][j - 1]
            if f[i][j] == f[i - 1][j - 1] + (s - MATCH_OFFSET):
                moves.append((i - 1, j - 1, s))
                i, j = i - 1, j - 1
                continue
        if i > 0 and f[i][j] == f[i - 1][j] - gap_penalty:
            moves.append((i - 1, None, 0.0))
            i -= 1
            continue
        moves.append((None, j - 1, 0.0))
        j -= 1
    moves.reverse()
    return moves


def align(
    a: list[Step],
    b: list[Step],
    *,
    semantic: bool = False,
    scorer: Scorer | None = None,
    gap_penalty: float = DEFAULT_GAP_PENALTY,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> list[AlignedPair]:
    """Align two step lists into ordered ``AlignedPair``s."""
    score_fn = scorer or get_scorer(semantic)
    pairs: list[AlignedPair] = []
    for i, j, score in needleman_wunsch(a, b, score_fn, gap_penalty):
        if i is not None and j is not None:
            op = Op.MATCH if score >= match_threshold else Op.SUBSTITUTE
            pairs.append(AlignedPair(a=a[i], b=b[j], op=op, score=score))
        elif i is not None:
            pairs.append(AlignedPair(a=a[i], b=None, op=Op.DELETE_A))
        else:
            pairs.append(AlignedPair(a=None, b=b[j], op=Op.INSERT_B))
    return pairs
