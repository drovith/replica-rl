from __future__ import annotations

import difflib
import statistics

from d2c.grade.color import delta_e, parse_rgb
from d2c.grade.match import Dims, content_similarity, position_distance

# Priority tiers, not measured constants. Monotonicity is independent of the exact
# weights (each dimension is independently monotone), so they only tune emphasis.
WEIGHTS = {"layout": 0.20, "content": 0.20, "color": 0.15, "typography": 0.15, "shape": 0.10, "global": 0.20}
DOM_KEYS = ["layout", "content", "color", "typography", "shape"]

COLOR_DELTA_E_MAX = 30.0
RADIUS_MAX = 24.0
BORDER_MAX = 4.0
CONSISTENCY_PENALTY = 0.5  # lambda on cross-page std
CLUTTER_CAP = 0.5


def _ratio(a: float, b: float) -> float:
    return min(a, b) / max(a, b) if max(a, b) else 1.0


def _size(ref: dict, agent: dict) -> float:
    return 0.5 * (_ratio(ref["w"], agent["w"]) + _ratio(ref["h"], agent["h"]))


def _layout(ref: dict, agent: dict, rd: Dims, ad: Dims) -> float:
    return 0.5 * (1.0 - position_distance(ref, agent, rd, ad)) + 0.5 * _size(ref, agent)


def _color_pair(ref_value: str | None, agent_value: str | None) -> float | None:
    if ref_value is None or agent_value is None:
        return None
    rc, ac = parse_rgb(ref_value), parse_rgb(agent_value)
    if rc is not None and ac is not None:
        return max(0.0, 1.0 - delta_e(rc, ac) / COLOR_DELTA_E_MAX)
    if rc is not None or ac is not None:
        return 0.0  # one solid colour, one gradient -> mismatch
    return difflib.SequenceMatcher(None, ref_value, agent_value).ratio()  # both gradients


def _color(ref: dict, agent: dict) -> float | None:
    parts = [
        _color_pair(ref.get("color"), agent.get("color")),
        _color_pair(ref.get("background"), agent.get("background")),
    ]
    parts = [p for p in parts if p is not None]
    return sum(parts) / len(parts) if parts else None


def _weight(value: str | None) -> float:
    text = (value or "400").lower()
    named = {"normal": 400.0, "bold": 700.0, "bolder": 700.0, "lighter": 300.0}
    if text in named:
        return named[text]
    try:
        return float(text)
    except ValueError:
        return 400.0


def _typography(ref: dict, agent: dict) -> float:
    size = _ratio(ref.get("fontSize") or 0, agent.get("fontSize") or 0)
    rf = (ref.get("fontFamily") or "").split(",")[0].strip().strip('"').lower()
    af = (agent.get("fontFamily") or "").split(",")[0].strip().strip('"').lower()
    family = 1.0 if rf and rf == af else 0.0
    weight = 1.0 - min(abs(_weight(ref.get("fontWeight")) - _weight(agent.get("fontWeight"))) / 400.0, 1.0)
    style = 1.0 if ref.get("fontStyle") == agent.get("fontStyle") else 0.0
    align = 1.0 if ref.get("textAlign") == agent.get("textAlign") else 0.0
    transform = 1.0 if ref.get("textTransform") == agent.get("textTransform") else 0.0
    rlh = (ref.get("lineHeight") or 0) / (ref.get("fontSize") or 1)
    alh = (agent.get("lineHeight") or 0) / (agent.get("fontSize") or 1)
    line_height = _ratio(rlh, alh)
    return 0.30 * size + 0.20 * family + 0.15 * weight + 0.10 * style + 0.10 * align + 0.05 * transform + 0.10 * line_height


def _shape(ref: dict, agent: dict) -> float:
    radius = 1.0 - min(abs((ref.get("borderRadius") or 0) - (agent.get("borderRadius") or 0)) / RADIUS_MAX, 1.0)
    border = 1.0 - min(abs((ref.get("borderWidth") or 0) - (agent.get("borderWidth") or 0)) / BORDER_MAX, 1.0)
    shadow = 1.0 if (ref.get("boxShadow", "none") != "none") == (agent.get("boxShadow", "none") != "none") else 0.0
    return (radius + border + shadow) / 3.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 1.0


def score_page(
    ref: list[dict],
    agent: list[dict],
    matched: list[tuple[int, int]],
    extra: list[int],
    rd: Dims,
    ad: Dims,
) -> dict:
    match_map = dict(matched)
    layout, content, color, typography, shape = [], [], [], [], []
    for i, rb in enumerate(ref):
        ab = agent[match_map[i]] if i in match_map else None
        if ab is not None:
            layout.append(_layout(rb, ab, rd, ad))
            content.append(content_similarity(rb, ab))
            shape.append(_shape(rb, ab))
            if rb["kind"] == "text":
                c = _color(rb, ab)
                if c is not None:
                    color.append(c)
                typography.append(_typography(rb, ab))
        else:
            layout.append(0.0)
            content.append(0.0)
            shape.append(0.0)
            if rb["kind"] == "text":
                color.append(0.0)
                typography.append(0.0)

    page_height = _ratio(rd[1], ad[1])
    return {
        "layout": 0.9 * _mean(layout) + 0.1 * page_height,
        "content": _mean(content),
        "color": _mean(color),
        "typography": _mean(typography),
        "shape": _mean(shape),
        "clutter": min(CLUTTER_CAP, CLUTTER_CAP * len(extra) / max(len(ref), 1)),
        "matched": len(matched),
        "missing": len(ref) - len(matched),
        "extra": len(extra),
    }


def page_score(dims: dict, global_score: float | None) -> float:
    weights = {k: WEIGHTS[k] for k in DOM_KEYS}
    if global_score is not None:
        weights["global"] = WEIGHTS["global"]
    total = sum(weights.values())
    base = sum(WEIGHTS[k] * dims[k] for k in DOM_KEYS)
    if global_score is not None:
        base += WEIGHTS["global"] * global_score
    base /= total
    return base * (1.0 - dims["clutter"])


def aggregate(page_scores: list[float]) -> float:
    if not page_scores:
        return 0.0
    mean = statistics.mean(page_scores)
    spread = statistics.pstdev(page_scores) if len(page_scores) > 1 else 0.0
    return max(0.0, min(1.0, mean - CONSISTENCY_PENALTY * spread))
