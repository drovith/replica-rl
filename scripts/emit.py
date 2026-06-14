from __future__ import annotations

import argparse
from pathlib import Path

from d2c.emit.task import build_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit Harbor tasks from generated sites.")
    parser.add_argument("--sites", type=Path, default=Path("sites"))
    parser.add_argument("--out", type=Path, default=Path("dataset"))
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated subset of ids.")
    args = parser.parse_args()

    site_dirs = sorted(
        d for d in args.sites.iterdir()
        if (d / "manifest.json").exists() and (d / "screenshots").exists()
    )
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",")}
        site_dirs = [d for d in site_dirs if d.name in wanted]

    print(f"Emitting {len(site_dirs)} Harbor task(s) to {args.out}/")
    for site_dir in site_dirs:
        try:
            build_task(site_dir, args.out / site_dir.name)
            print(f"  [{site_dir.name}] OK")
        except Exception as exc:
            print(f"  [{site_dir.name}] ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
