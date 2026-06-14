"""Renders reference-vs-replica visual proofs from a completed run into report/.

Reads the agents' HTML from jobs/<job>/<trial>/artifacts/app and the target
screenshots from dataset/<site>/environment/design, renders each replica at
1440px, and composes labelled side-by-side panels used in the README results.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from d2c.render.capture import _FREEZE_CSS

REPORT = Path("report")
PANEL_W = 460          # width each column is scaled to
CROP_H = 1400          # vertical crop so panels are comparable
HEADER = 54

BLUE = "#2c6fbb"
GREY = "#7f8c8d"
DARK = "#1a2330"


def _font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_html(html_path: Path, out_png: Path, width: int = 1440) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=1, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.add_style_tag(content=_FREEZE_CSS)
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(200)
        page.screenshot(path=str(out_png), full_page=True)
        browser.close()


def _column(img_path: Path, title: str, subtitle: str, accent: str) -> Image.Image:
    src = Image.open(img_path).convert("RGB")
    scale = PANEL_W / src.width
    scaled = src.resize((PANEL_W, int(src.height * scale)))
    body = scaled.crop((0, 0, PANEL_W, min(CROP_H, scaled.height)))

    col = Image.new("RGB", (PANEL_W, HEADER + body.height), "white")
    draw = ImageDraw.Draw(col)
    draw.rectangle([0, 0, PANEL_W, HEADER], fill=accent)
    draw.text((12, 7), title, font=_font(20), fill="white")
    draw.text((12, 31), subtitle, font=_font(14), fill="white")
    col.paste(body, (0, HEADER))
    draw.rectangle([0, 0, PANEL_W - 1, col.height - 1], outline="#d0d0d0")
    return col


def compose(out_name: str, columns: list[tuple[Path, str, str, str]]) -> None:
    cols = [_column(*c) for c in columns]
    gap = 16
    h = max(c.height for c in cols)
    w = sum(c.width for c in cols) + gap * (len(cols) - 1)
    out = Image.new("RGB", (w, h), "white")
    x = 0
    for c in cols:
        out.paste(c, (x, 0))
        x += c.width + gap
    out.save(REPORT / out_name)
    print(f"wrote report/{out_name}")


def main() -> None:
    REPORT.mkdir(exist_ok=True)
    tmp = REPORT / "_replicas"
    tmp.mkdir(exist_ok=True)

    jobs = {
        # site: (opus_low_trial, opus_high_trial, haiku_trial)
        "vault-wallet": ("vault-wallet__TCUdQVn", "vault-wallet__bgnoUUm", None),
        "bright-smiles-pedo": ("bright-smiles-pedo__kpSv5bq", "bright-smiles-pedo__PmbVoXa", None),
        "observability-saas": (None, "observability-saas__rYRkHK3", "observability-saas__ejUMzEo"),
    }

    def replica(job_trial: str, job: str, page="index.html") -> Path:
        out = tmp / f"{job_trial}.png"
        if not out.exists():
            render_html(Path(f"jobs/{job}/{job_trial}/artifacts/app/{page}"), out)
        return out

    # 1) Model gap — Reference | Opus | Haiku  (observability-saas)
    ref = Path("dataset/observability-saas/environment/design/index.png")
    compose("proof_modelgap.png", [
        (ref, "Reference", "target design", DARK),
        (replica("observability-saas__rYRkHK3", "modal-opus"), "Opus 4.7", "grade 0.78", BLUE),
        (replica("observability-saas__ejUMzEo", "modal-haiku"), "Haiku 4.5", "grade 0.28", GREY),
    ])

    # 2) Within-model: vault-wallet 0.615 (over-generated) vs 0.762
    ref = Path("dataset/vault-wallet/environment/design/index.png")
    compose("proof_vault.png", [
        (ref, "Reference", "target design", DARK),
        (replica("vault-wallet__TCUdQVn", "modal-opus"), "Opus attempt", "grade 0.615  (+117 extra blocks)", "#b5651d"),
        (replica("vault-wallet__bgnoUUm", "modal-opus"), "Opus attempt", "grade 0.762", BLUE),
    ])

    # 3) Within-model monotone: bright-smiles 0.756 vs 0.901
    ref = Path("dataset/bright-smiles-pedo/environment/design/index.png")
    compose("proof_bright.png", [
        (ref, "Reference", "target design", DARK),
        (replica("bright-smiles-pedo__kpSv5bq", "modal-opus"), "Opus attempt", "grade 0.756", "#5a8fbf"),
        (replica("bright-smiles-pedo__PmbVoXa", "modal-opus"), "Opus attempt", "grade 0.901", BLUE),
    ])


if __name__ == "__main__":
    main()
