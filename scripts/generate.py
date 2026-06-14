from __future__ import annotations

import argparse
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from d2c.generate.builder import GENERATION_MODEL, generate_site

MIN_PAGES = 5


def load_briefs(path: Path) -> list[dict]:
    briefs = json.loads(path.read_text())
    seen = set()
    for b in briefs:
        if b["id"] in seen:
            raise ValueError(f"duplicate brief id: {b['id']}")
        seen.add(b["id"])
    return briefs


def is_acceptable(staging: Path, finished: bool) -> tuple[bool, str]:
    if not finished:
        return False, "agent did not call finish"
    manifest_path = staging / "manifest.json"
    if not manifest_path.exists():
        return False, "manifest.json missing"
    try:
        json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"manifest.json invalid: {exc}"
    pages = list(staging.rglob("*.html"))
    if len(pages) < MIN_PAGES:
        return False, f"only {len(pages)} html pages (need >= {MIN_PAGES})"
    return True, f"{len(pages)} pages"


def generate_one(
    brief: dict, out_dir: Path, viewport: int, effort: str
) -> tuple[str, str]:
    site_id = brief["id"]
    final = out_dir / site_id
    if final.exists():
        return site_id, "skipped (already generated)"

    staging = out_dir / ".staging" / site_id
    if staging.exists():
        shutil.rmtree(staging)

    try:
        result = generate_site(
            brief["brief"], staging, viewport_width=viewport, effort=effort
        )
        ok, detail = is_acceptable(staging, result.finished)
        if not ok:
            shutil.rmtree(staging, ignore_errors=True)
            return site_id, f"FAILED: {detail}"

        (staging / "generation.json").write_text(
            json.dumps(
                {
                    "id": site_id,
                    "brief": brief["brief"],
                    "model": GENERATION_MODEL,
                    "effort": effort,
                    "viewport_width": viewport,
                    "steps": result.steps,
                    "summary": result.summary,
                    "files": result.files,
                },
                indent=2,
            )
        )
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, final)
        return site_id, f"OK ({detail}, {result.steps} steps)"
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return site_id, f"ERROR: {type(exc).__name__}: {exc}"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate websites from briefs.")
    parser.add_argument("--briefs", type=Path, default=Path("briefs.json"))
    parser.add_argument("--out", type=Path, default=Path("sites"))
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--ids", type=str, default=None, help="Comma-separated subset of ids."
    )
    parser.add_argument("--viewport", type=int, default=1440)
    parser.add_argument("--effort", type=str, default="high")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set (check your .env).")

    briefs = load_briefs(args.briefs)
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",")}
        briefs = [b for b in briefs if b["id"] in wanted]
    if args.limit is not None:
        briefs = briefs[: args.limit]

    print(f"Generating {len(briefs)} site(s) with concurrency {args.concurrency}.")
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(generate_one, b, args.out, args.viewport, args.effort)
            for b in briefs
        ]
        for future in as_completed(futures):
            site_id, status = future.result()
            print(f"  [{site_id}] {status}")


if __name__ == "__main__":
    main()
