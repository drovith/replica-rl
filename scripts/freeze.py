from __future__ import annotations

import argparse
from pathlib import Path

from d2c.render.freeze import freeze_assets, substitute_failures

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Localise external images into each site's assets/ folder."
    )
    parser.add_argument("--sites", type=Path, default=Path("sites"))
    parser.add_argument(
        "--ids", type=str, default=None, help="Comma-separated subset of ids."
    )
    args = parser.parse_args()

    site_dirs = sorted(
        d for d in args.sites.iterdir() if (d / "manifest.json").exists()
    )
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",")}
        site_dirs = [d for d in site_dirs if d.name in wanted]

    print(f"Freezing assets for {len(site_dirs)} site(s).")
    failures: dict[Path, list[str]] = {}
    for site_dir in site_dirs:
        try:
            localised, failed = freeze_assets(site_dir)
            failures[site_dir] = failed
            note = f"localised {localised}" if localised else "no external images"
            note += f", {len(failed)} unreachable" if failed else ""
            print(f"  [{site_dir.name}] {note}")
        except Exception as exc:
            print(f"  [{site_dir.name}] ERROR: {type(exc).__name__}: {exc}")

    pool = sorted(
        p
        for d in site_dirs
        for p in (d / "assets").glob("*")
        if p.suffix.lower() in _IMAGE_SUFFIXES and not p.name.startswith("sub-")
    )
    for site_dir, failed in failures.items():
        if failed:
            n = substitute_failures(site_dir, failed, pool)
            print(
                f"  [{site_dir.name}] substituted {n} unreachable image(s) with valid ones"
            )


if __name__ == "__main__":
    main()
