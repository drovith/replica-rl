from __future__ import annotations

import json
import tempfile
from pathlib import Path

from d2c.grade.embed import global_similarity
from d2c.grade.introspect import browser_session, introspect
from d2c.grade.match import match_blocks
from d2c.grade.score import aggregate, page_score, score_page


def _grade_page(page, reference_dir: Path, candidate_dir: Path, page_path: str, work: Path) -> dict:
    candidate_file = candidate_dir / page_path
    if not candidate_file.exists():
        return {"page": page_path, "score": 0.0, "missing_output": True}

    ref_png = work / f"ref_{page_path.replace('/', '__')}.png"
    cand_png = work / f"cand_{page_path.replace('/', '__')}.png"
    ref = introspect(page, (reference_dir / page_path).resolve().as_uri(), ref_png)
    cand = introspect(page, candidate_file.resolve().as_uri(), cand_png)

    ref_dims = (ref["width"], ref["height"])
    cand_dims = (cand["width"], cand["height"])
    matched, missing, extra = match_blocks(ref["blocks"], cand["blocks"], ref_dims, cand_dims)
    dims = score_page(ref["blocks"], cand["blocks"], matched, extra, ref_dims, cand_dims)
    g = global_similarity(ref_png, cand_png)
    score = page_score(dims, g)
    return {"page": page_path, "score": score, "global": g, **dims}


def grade_site(reference_dir: Path, candidate_dir: Path, pages: list[str] | None = None) -> dict:
    manifest = json.loads((reference_dir / "manifest.json").read_text())
    pages = pages or [p["path"] for p in manifest["pages"]]

    per_page: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        with browser_session() as page:
            for page_path in pages:
                per_page.append(_grade_page(page, reference_dir, candidate_dir, page_path, work))

    reward = aggregate([p["score"] for p in per_page])
    return {"reward": reward, "pages": per_page}
