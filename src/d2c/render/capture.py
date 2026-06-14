from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_VIEWPORT_WIDTH = 1440
DEFAULT_VIEWPORT_HEIGHT = 900

# Injected before every screenshot so a half-finished transition, a blinking
# caret, or smooth-scroll never makes one render differ from the next.
_FREEZE_CSS = """
*, *::before, *::after {
  animation-duration: 0s !important;
  animation-delay: 0s !important;
  transition-duration: 0s !important;
  transition-delay: 0s !important;
  caret-color: transparent !important;
  scroll-behavior: auto !important;
}
"""


def _page_name(relative_path: str) -> str:
    return Path(relative_path).with_suffix("").as_posix().replace("/", "__")


def _prepare(page) -> None:
    page.add_style_tag(content=_FREEZE_CSS)
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(200)


def render_site(
    site_dir: Path,
    out_dir: Path,
    *,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    device_scale_factor: int = 1,
    thumb: bool = True,
) -> list[str]:
    manifest = json.loads((site_dir / "manifest.json").read_text())
    pages = [p["path"] for p in manifest["pages"]]
    entry = manifest.get("entry", pages[0])
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=device_scale_factor,
            reduced_motion="reduce",
        )
        page = context.new_page()

        for relative in pages:
            page.goto((site_dir / relative).resolve().as_uri(), wait_until="networkidle")
            _prepare(page)
            name = _page_name(relative)
            page.screenshot(path=str(out_dir / f"{name}.png"), full_page=True)
            written.append(name)

        if thumb:
            page.goto((site_dir / entry).resolve().as_uri(), wait_until="networkidle")
            _prepare(page)
            page.screenshot(path=str(out_dir / "thumb.png"), full_page=False)

        browser.close()

    return written
