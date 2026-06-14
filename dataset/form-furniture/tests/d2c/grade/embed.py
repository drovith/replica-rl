from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# A full page squished to CLIP's 224px loses almost everything. Instead we tile
# both renders into a normalized grid and compare cells, so each cell is only
# lightly downscaled — sharper, more monotone, and locally sensitive.
CELL_PX = 700
COLS = 2
MAX_ROWS = 8
COSINE_FLOOR = 0.80
COSINE_CEIL = 0.98
BLANK_STD = 6.0


@lru_cache(maxsize=1)
def _load_model():
    import os

    import open_clip

    cache_dir = os.environ.get("D2C_CLIP_CACHE")
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai", cache_dir=cache_dir
    )
    model.eval()
    return model, preprocess


def _cells(image, rows: int, cols: int) -> list:
    w, h = image.size
    return [
        image.crop((j * w / cols, i * h / rows, (j + 1) * w / cols, (i + 1) * h / rows))
        for i in range(rows)
        for j in range(cols)
    ]


def global_similarity(image_a: Path, image_b: Path) -> float | None:
    """Patch-wise calibrated CLIP cosine over a normalized grid. None if unavailable."""
    try:
        import numpy as np
        import torch
        from PIL import Image
    except ImportError:
        return None
    try:
        model, preprocess = _load_model()
    except Exception:
        return None

    img_a = Image.open(image_a).convert("RGB")
    img_b = Image.open(image_b).convert("RGB")
    rows = max(1, min(MAX_ROWS, round(max(img_a.height, img_b.height) / CELL_PX)))

    def is_blank(cell) -> bool:
        return float(np.asarray(cell.convert("L")).std()) < BLANK_STD

    pairs = [
        (ca, cb)
        for ca, cb in zip(_cells(img_a, rows, COLS), _cells(img_b, rows, COLS))
        if not (is_blank(ca) and is_blank(cb))
    ]
    if not pairs:
        return None

    batch = torch.stack([preprocess(im) for pair in pairs for im in pair])
    with torch.no_grad():
        features = model.encode_image(batch)
        features = features / features.norm(dim=-1, keepdim=True)

    scores = []
    for k in range(len(pairs)):
        cosine = float(features[2 * k] @ features[2 * k + 1])
        scores.append(
            max(0.0, min(1.0, (cosine - COSINE_FLOOR) / (COSINE_CEIL - COSINE_FLOOR)))
        )
    return sum(scores) / len(scores)
