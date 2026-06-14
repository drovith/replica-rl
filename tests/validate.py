"""Grader validation harness (free-form, not pytest).

Runs the grader across a degradation sweep and reports the properties that make
it a trustworthy RL reward: monotonicity (more damage -> lower score),
orthogonality (each degradation hits its own dimension), and determinism.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from degrade import KINDS, make_degraded

from d2c.grade.grade import grade_site

SEVERITIES = [0.0, 0.25, 0.5, 0.75, 1.0]
DIMENSION_FOR = {
    "lorem": "content", "garble": "content", "color": "color", "bgcolor": "color",
    "shift": "layout", "typo": "typography", "svg": "content", "shape": "shape",
    "drop": "content", "scramble": "layout", "combo": "content",
}


def _is_monotone(values: list[float], eps: float = 0.02) -> bool:
    return all(values[i] + eps >= values[i + 1] for i in range(len(values) - 1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the grader on a degradation sweep.")
    parser.add_argument("--reference", type=Path, default=Path("sites/observability-saas"))
    parser.add_argument("--pages", type=str, default=None, help="Comma-separated page subset (default: all).")
    parser.add_argument("--kinds", type=str, default=",".join(KINDS))
    args = parser.parse_args()

    pages = args.pages.split(",") if args.pages else None
    kinds = args.kinds.split(",")

    print(f"Reference: {args.reference}  pages: {pages or 'all'}\n")
    header = "kind".ljust(10) + "".join(f"s={s:<6}" for s in SEVERITIES) + "  monotone  target-dim @ s=1.0"
    print(header)
    print("-" * len(header))

    def dim_mean(pages_result: list[dict], key: str) -> float:
        vals = [p[key] for p in pages_result if key in p]
        return sum(vals) / len(vals) if vals else 0.0

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "candidate"
        for kind in kinds:
            rewards, target_curve, global_curve = [], [], []
            target = DIMENSION_FOR.get(kind, "layout")
            for severity in SEVERITIES:
                make_degraded(args.reference, out, kind, severity, pages=pages)
                result = grade_site(args.reference, out, pages=pages)
                rewards.append(result["reward"])
                target_curve.append(dim_mean(result["pages"], target))
                global_curve.append(dim_mean(result["pages"], "global"))
            mono = "PASS" if _is_monotone(rewards) else "FAIL"
            print(kind.ljust(10) + "".join(f"{r:<8.3f}" for r in rewards) + f"  {mono}")
            print("  ".ljust(10) + "".join(f"{r:<8.3f}" for r in target_curve) + f"  ({target})")
            print("  ".ljust(10) + "".join(f"{r:<8.3f}" for r in global_curve) + "  (global)")

        make_degraded(args.reference, out, "lorem", 0.5, pages=pages)
        a = grade_site(args.reference, out, pages=pages)["reward"]
        b = grade_site(args.reference, out, pages=pages)["reward"]
        print(f"\ndeterminism (lorem @0.5 graded twice): {a:.6f} vs {b:.6f} -> {'identical' if a == b else 'DIFFERS'}")


if __name__ == "__main__":
    main()
