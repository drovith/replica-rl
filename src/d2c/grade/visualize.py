from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from d2c.grade.embed import global_similarity
from d2c.grade.introspect import browser_session, introspect
from d2c.grade.match import match_blocks
from d2c.grade.score import page_score, score_page

MATCHED = (46, 160, 67)
MISSING = (207, 34, 46)
EXTRA = (219, 109, 0)
HEADER_H = 90
GAP = 24


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_boxes(image: Image.Image, blocks: list[dict], indices, color) -> None:
    draw = ImageDraw.Draw(image)
    for i in indices:
        b = blocks[i]
        draw.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]], outline=color, width=3)


def visualize_page(reference_dir: Path, candidate_dir: Path, page: str, out_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        ref_png, cand_png = Path(tmp) / "ref.png", Path(tmp) / "cand.png"
        with browser_session() as p:
            ref = introspect(p, (reference_dir / page).resolve().as_uri(), ref_png)
            cand = introspect(p, (candidate_dir / page).resolve().as_uri(), cand_png)
        ref_img = Image.open(ref_png).convert("RGB")
        cand_img = Image.open(cand_png).convert("RGB")

    rd, ad = (ref["width"], ref["height"]), (cand["width"], cand["height"])
    matched, missing, extra = match_blocks(ref["blocks"], cand["blocks"], rd, ad)
    dims = score_page(ref["blocks"], cand["blocks"], matched, extra, rd, ad)
    g = global_similarity(ref_png, cand_png) if ref_png.exists() else None
    score = page_score(dims, g)

    _draw_boxes(ref_img, ref["blocks"], [m[0] for m in matched], MATCHED)
    _draw_boxes(ref_img, ref["blocks"], missing, MISSING)
    _draw_boxes(cand_img, cand["blocks"], [m[1] for m in matched], MATCHED)
    _draw_boxes(cand_img, cand["blocks"], extra, EXTRA)

    body_h = max(ref_img.height, cand_img.height)
    canvas = Image.new("RGB", (ref_img.width + GAP + cand_img.width, HEADER_H + body_h), "white")
    canvas.paste(ref_img, (0, HEADER_H))
    canvas.paste(cand_img, (ref_img.width + GAP, HEADER_H))

    draw = ImageDraw.Draw(canvas)
    title = _font(30)
    small = _font(20)
    draw.text((16, 14), f"REFERENCE", fill=(20, 20, 20), font=title)
    draw.text((ref_img.width + GAP + 16, 14), "CANDIDATE", fill=(20, 20, 20), font=title)
    breakdown = (
        f"score {score:.3f}   layout {dims['layout']:.2f}   content {dims['content']:.2f}   "
        f"color {dims['color']:.2f}   typo {dims['typography']:.2f}   "
        f"global {g:.2f}" if g is not None else f"score {score:.3f}"
    )
    draw.text((16, 52), breakdown, fill=(60, 60, 60), font=small)
    legend = f"matched {len(matched)} (green)   missing {len(missing)} (red)   extra {len(extra)} (orange)"
    draw.text((ref_img.width + GAP + 16, 52), legend, fill=(60, 60, 60), font=small)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return {"page": page, "score": score, "matched": len(matched), "missing": len(missing), "extra": len(extra)}
