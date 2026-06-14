from __future__ import annotations

import argparse
import json
from pathlib import Path

from d2c.grade.grade import grade_site


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grade a candidate site against a reference site."
    )
    parser.add_argument(
        "reference", type=Path, help="Reference site dir (contains manifest.json)."
    )
    parser.add_argument(
        "candidate", type=Path, help="Candidate site dir (the agent's output)."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full breakdown as JSON."
    )
    args = parser.parse_args()

    result = grade_site(args.reference, args.candidate)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"reward: {result['reward']:.4f}")
        for p in result["pages"]:
            extra = (
                ""
                if p.get("missing_output")
                else (
                    f"  layout={p['layout']:.2f} content={p['content']:.2f} "
                    f"color={p['color']:.2f} typo={p['typography']:.2f} "
                    f"global={p['global'] if p['global'] is None else round(p['global'], 2)} "
                    f"(m{p['matched']}/miss{p['missing']}/extra{p['extra']})"
                )
            )
            print(f"  {p['page']:24s} {p['score']:.4f}{extra}")


if __name__ == "__main__":
    main()
