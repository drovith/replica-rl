from __future__ import annotations

import argparse
from pathlib import Path

from d2c.grade.visualize import visualize_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a side-by-side grading visualization for one page.")
    parser.add_argument("reference", type=Path, help="Reference site dir.")
    parser.add_argument("candidate", type=Path, help="Candidate site dir.")
    parser.add_argument("page", type=str, help="Page filename, e.g. index.html")
    parser.add_argument("--out", type=Path, default=Path("viz.png"))
    args = parser.parse_args()

    info = visualize_page(args.reference, args.candidate, args.page, args.out)
    print(f"wrote {args.out}  (score={info['score']:.3f}, "
          f"matched={info['matched']} missing={info['missing']} extra={info['extra']})")


if __name__ == "__main__":
    main()
