"""Builds the figures embedded in the README into report/."""

from __future__ import annotations

import json
import shutil
import statistics as st
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

from d2c.grade.visualize import _font
from d2c.grade.visualize import visualize_page

REPORT = Path("report")
SITES = Path("sites")
ORDER = [
    "observability-saas", "harbor-law", "pulse-festival", "bright-smiles-pedo", "form-furniture",
    "hearth-table", "vault-wallet", "coastal-marine-lab", "still-point-retreat", "offgrid-streetwear",
]

# The validated 11-kind reward curves (severity 0 -> 1), from tests/validate.py.
SEVERITIES = [0.0, 0.25, 0.5, 0.75, 1.0]
CURVES = {
    "lorem": [1.000, 0.905, 0.826, 0.730, 0.658],
    "garble": [1.000, 0.897, 0.855, 0.724, 0.651],
    "color": [1.000, 0.978, 0.944, 0.900, 0.854],
    "bgcolor": [1.000, 0.974, 0.953, 0.921, 0.909],
    "shift": [1.000, 0.989, 0.971, 0.938, 0.919],
    "typo": [1.000, 0.919, 0.884, 0.847, 0.824],
    "svg": [1.000, 0.992, 0.987, 0.983, 0.981],
    "shape": [1.000, 0.999, 0.998, 0.993, 0.990],
    "drop": [1.000, 0.093, 0.093, 0.093, 0.003],
    "scramble": [1.000, 0.930, 0.930, 0.930, 0.930],
    "combo": [1.000, 0.848, 0.750, 0.651, 0.580],
}


def distribution_grid() -> None:
    cell_w, cell_h, label_h, cols = 480, 300, 32, 5
    rows = (len(ORDER) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), "white")
    draw = ImageDraw.Draw(canvas)
    font = _font(22)
    for i, site in enumerate(ORDER):
        r, c = divmod(i, cols)
        thumb = Image.open(SITES / site / "screenshots" / "thumb.png").convert("RGB").resize((cell_w, cell_h))
        x, y = c * cell_w, r * (cell_h + label_h)
        canvas.paste(thumb, (x, y))
        draw.text((x + 8, y + cell_h + 6), site, fill=(40, 40, 40), font=font)
    canvas.save(REPORT / "distribution_grid.png")


def monotonicity_chart() -> None:
    plt.figure(figsize=(9, 5.5))
    for kind, ys in CURVES.items():
        plt.plot(SEVERITIES, ys, marker="o", markersize=3, linewidth=1.5, label=kind)
    plt.ylim(0, 1.03)
    plt.xlabel("degradation severity")
    plt.ylabel("reward")
    plt.title("Reward vs. degradation severity — every curve is monotone")
    plt.legend(ncol=2, fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(REPORT / "monotonicity.png", dpi=130)
    plt.close()


def anchors() -> None:
    reference = SITES / "observability-saas"
    oracle_path = REPORT / "_oracle.png"
    floor_path = REPORT / "_floor.png"
    visualize_page(reference, reference, "index.html", oracle_path)
    with tempfile.TemporaryDirectory() as tmp:
        blank = Path(tmp)
        (blank / "index.html").write_text("<!doctype html><html><head></head><body></body></html>")
        visualize_page(reference, blank, "index.html", floor_path)

    crop = 1100
    oracle = Image.open(oracle_path)
    floor = Image.open(floor_path)
    top_o = oracle.crop((0, 0, oracle.width, min(crop, oracle.height)))
    top_f = floor.crop((0, 0, floor.width, min(crop, floor.height)))
    width = max(top_o.width, top_f.width)
    gap = 24
    out = Image.new("RGB", (width, top_o.height + gap + top_f.height), "white")
    out.paste(top_o, (0, 0))
    out.paste(top_f, (0, top_o.height + gap))
    out.save(REPORT / "anchors.png")
    oracle_path.unlink()
    floor_path.unlink()


def model_comparison() -> None:
    scores = json.loads((REPORT / "scores.json").read_text())
    opus, haiku = scores["opus"], scores["haiku"]
    sites = sorted(opus, key=lambda s: -st.mean(opus[s]))

    def mean_sd(vals):
        return st.mean(vals), (st.pstdev(vals) if len(vals) > 1 else 0.0)

    om = [mean_sd(opus[s]) for s in sites]
    hm = [mean_sd(haiku[s]) for s in sites]

    x = range(len(sites))
    w = 0.38
    plt.figure(figsize=(12, 6))
    plt.bar([i - w / 2 for i in x], [m for m, _ in hm], w, yerr=[s for _, s in hm],
            capsize=3, color="#bdc3c7", label="Claude Haiku 4.5  (n=2)")
    plt.bar([i + w / 2 for i in x], [m for m, _ in om], w, yerr=[s for _, s in om],
            capsize=3, color="#2c6fbb", label="Claude Opus 4.7  (n=3)")
    for i, (m, s) in zip(x, hm):
        plt.text(i - w / 2, m + s + 0.02, f"{m:.2f}", ha="center", va="bottom", fontsize=7, color="#555")
    for i, (m, s) in zip(x, om):
        plt.text(i + w / 2, m + s + 0.02, f"{m:.2f}", ha="center", va="bottom", fontsize=7, color="#1a4d80")
    plt.ylim(0, 1.0)
    plt.ylabel("grade (reward)")
    plt.title("Replication fidelity by site — Opus 4.7 vs Haiku 4.5\nbar = mean across attempts, whisker = ±1 std")
    plt.xticks(list(x), sites, rotation=30, ha="right", fontsize=8)
    plt.legend()
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(REPORT / "model_comparison.png", dpi=130)
    plt.close()


def main() -> None:
    REPORT.mkdir(exist_ok=True)
    shutil.copyfile(SITES / "observability-saas" / "screenshots" / "thumb.png", REPORT / "site_observability.png")
    distribution_grid()
    monotonicity_chart()
    anchors()
    model_comparison()
    print("wrote report/: distribution_grid.png, site_observability.png, monotonicity.png, anchors.png, model_comparison.png")


if __name__ == "__main__":
    main()
