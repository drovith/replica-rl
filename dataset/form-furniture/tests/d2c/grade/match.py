from __future__ import annotations

import difflib

import numpy as np
from scipy.optimize import linear_sum_assignment

MATCH_THRESHOLD = 0.6

Dims = tuple[float, float]


def _center(block: dict, dims: Dims) -> tuple[float, float]:
    return ((block["x"] + block["w"] / 2) / dims[0], (block["y"] + block["h"] / 2) / dims[1])


def position_distance(ref: dict, agent: dict, ref_dims: Dims, agent_dims: Dims) -> float:
    rx, ry = _center(ref, ref_dims)
    ax, ay = _center(agent, agent_dims)
    return min(1.0, ((rx - ax) ** 2 + (ry - ay) ** 2) ** 0.5)


def text_similarity(a: str | None, b: str | None) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def content_similarity(ref: dict, agent: dict) -> float:
    if ref["kind"] != agent["kind"]:
        return 0.0
    if ref["kind"] == "image":
        return 1.0 if ref.get("imgKey") and ref["imgKey"] == agent.get("imgKey") else 0.0
    if ref["kind"] == "graphic":
        rc, ac = ref.get("childCount", 0), agent.get("childCount", 0)
        return (min(rc, ac) + 1) / (max(rc, ac) + 1)
    return text_similarity(ref.get("text"), agent.get("text"))


def _cost(ref: dict, agent: dict, ref_dims: Dims, agent_dims: Dims) -> float:
    if ref["kind"] != agent["kind"]:
        return 1.5
    # 50/50 so position still matches a block whose content changed, and vice versa.
    return 0.5 * (1.0 - content_similarity(ref, agent)) + 0.5 * position_distance(ref, agent, ref_dims, agent_dims)


def match_blocks(
    ref: list[dict], agent: list[dict], ref_dims: Dims, agent_dims: Dims
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Returns (matched_pairs, missing_ref_indices, extra_agent_indices)."""
    if not ref or not agent:
        return [], list(range(len(ref))), list(range(len(agent)))

    cost = np.array([[_cost(r, a, ref_dims, agent_dims) for a in agent] for r in ref])
    rows, cols = linear_sum_assignment(cost)

    matched: list[tuple[int, int]] = []
    missing = set(range(len(ref)))
    extra = set(range(len(agent)))
    for i, j in zip(rows, cols):
        if cost[i, j] <= MATCH_THRESHOLD:
            matched.append((int(i), int(j)))
            missing.discard(int(i))
            extra.discard(int(j))
    return matched, sorted(missing), sorted(extra)
