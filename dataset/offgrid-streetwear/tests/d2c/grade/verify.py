"""Harbor verifier entrypoint.

Runs inside the task sandbox: grades the agent's output (/app) against the hidden
reference (/tests/reference) and writes the scalar reward Harbor reads, plus a
full per-dimension breakdown for our own analysis. Fails safe — any error still
produces a 0.0 reward rather than crashing the trial.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from d2c.grade.grade import grade_site

REFERENCE = Path("/tests/reference")
CANDIDATE = Path("/app")
VERIFIER_DIR = Path("/logs/verifier")


def main() -> None:
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    reward_path = VERIFIER_DIR / "reward.txt"
    try:
        result = grade_site(REFERENCE, CANDIDATE)
    except Exception:
        reward_path.write_text("0.0")
        (VERIFIER_DIR / "error.txt").write_text(traceback.format_exc())
        return

    reward_path.write_text(f"{result['reward']:.6f}")
    (VERIFIER_DIR / "grade.json").write_text(json.dumps(result, indent=2))
    print(f"reward: {result['reward']:.6f}")


if __name__ == "__main__":
    main()
