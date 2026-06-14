from __future__ import annotations

import argparse
from pathlib import Path

from d2c.render.capture import render_site


def main() -> None:
    parser = argparse.ArgumentParser(description="Render reference screenshots for generated sites.")
    parser.add_argument("--sites", type=Path, default=Path("sites"))
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated subset of ids.")
    parser.add_argument("--force", action="store_true", help="Re-render even if screenshots exist.")
    args = parser.parse_args()

    site_dirs = sorted(d for d in args.sites.iterdir() if (d / "manifest.json").exists())
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",")}
        site_dirs = [d for d in site_dirs if d.name in wanted]

    print(f"Rendering {len(site_dirs)} site(s).")
    for site_dir in site_dirs:
        out_dir = site_dir / "screenshots"
        if out_dir.exists() and any(out_dir.glob("*.png")) and not args.force:
            print(f"  [{site_dir.name}] skipped (already rendered)")
            continue
        try:
            pages = render_site(site_dir, out_dir)
            print(f"  [{site_dir.name}] OK ({len(pages)} pages + thumb)")
        except Exception as exc:
            print(f"  [{site_dir.name}] ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
