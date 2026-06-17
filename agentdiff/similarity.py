"""Per-step similarity scorers used by the alignment algorithm.

The default ``lexical_similarity`` is offline and dependency-light (rapidfuzz,
a pure wheel). ``semantic_similarity`` is opt-in (the ``[semantic]`` extra) and
the only path that may download a model. Tool-name agreement is blended into the
score because an exact tool match is a strong "these steps correspond" signal.
"""

from __future__ import annotations

from functools import lru_cache

from rapidfuzz import fuzz

from agentdiff.models import Step

# Weight split between content similarity and tool-name agreement.
_CONTENT_WEIGHT = 0.7
_TOOL_WEIGHT = 0.3


def blended_score(content_sim: float, step_a: Step, step_b: Step) -> float:
    """Combine content similarity with a tool-name agreement signal → [0,1]."""
    if step_a.tool_name or step_b.tool_name:
        tool_match = 1.0 if step_a.tool_name == step_b.tool_name else 0.0
        return _CONTENT_WEIGHT * content_sim + _TOOL_WEIGHT * tool_match
    return content_sim


def lexical_similarity(step_a: Step, step_b: Step) -> float:
    """Token/string similarity on content (rapidfuzz), blended with tool match."""
    content_sim = fuzz.token_set_ratio(step_a.content, step_b.content) / 100.0
    return blended_score(content_sim, step_a, step_b)


@lru_cache(maxsize=1)
def _embedder():
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "semantic similarity requires the optional dependency. "
            "Install it with: pip install 'agentdiff[semantic]'"
        ) from exc
    return TextEmbedding()


def semantic_similarity(step_a: Step, step_b: Step) -> float:
    """Cosine similarity of content embeddings (requires ``[semantic]`` extra)."""
    model = _embedder()
    vecs = list(model.embed([step_a.content or " ", step_b.content or " "]))
    va, vb = vecs[0], vecs[1]
    dot = sum(x * y for x, y in zip(va, vb, strict=False))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(y * y for y in vb) ** 0.5
    content_sim = dot / (na * nb) if na and nb else 0.0
    return blended_score(max(0.0, content_sim), step_a, step_b)


def get_scorer(semantic: bool = False):
    """Return the scorer function for the requested mode."""
    return semantic_similarity if semantic else lexical_similarity
