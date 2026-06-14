from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from d2c.render.capture import (
    _FREEZE_CSS,
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)

_EXTRACT_JS = r"""
() => {
  const docW = document.documentElement.scrollWidth;
  const docH = document.documentElement.scrollHeight;
  const directText = (el) => {
    let t = "";
    for (const n of el.childNodes) if (n.nodeType === 3) t += n.nodeValue;
    return t.replace(/\s+/g, " ").trim();
  };
  const effectiveBg = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage.includes("gradient")) return s.backgroundImage;
      const bg = s.backgroundColor;
      if (bg && !bg.startsWith("rgba(0, 0, 0, 0") && bg !== "transparent") return bg;
    }
    return "rgb(255, 255, 255)";
  };
  const blocks = [];
  for (const el of document.body.querySelectorAll("*")) {
    const st = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (st.display === "none" || st.visibility === "hidden" || parseFloat(st.opacity) === 0) continue;
    if (r.top > docH || r.left > docW || r.top + r.height < 0) continue;

    const tag = el.tagName.toLowerCase();
    let kind = null, text = null, imgKey = null, childCount = 0;
    if (tag === "img") {
      kind = "image";
      imgKey = (el.getAttribute("src") || "").split("/").pop();
    } else if (tag === "svg") {
      kind = "graphic";
      childCount = el.querySelectorAll("*").length;
    } else {
      const bg = st.backgroundImage;
      const dt = directText(el);
      if (!dt && bg && bg.startsWith("url(")) {
        kind = "image";
        imgKey = bg.replace(/^url\(["']?/, "").replace(/["']?\)$/, "").split("/").pop();
      } else if (dt) {
        kind = "text";
        text = dt;
      }
    }
    if (!kind) continue;
    blocks.push({
      kind, text, imgKey, childCount,
      x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height,
      color: st.color, background: effectiveBg(el),
      fontFamily: st.fontFamily, fontSize: parseFloat(st.fontSize) || 0, fontWeight: st.fontWeight,
      fontStyle: st.fontStyle, textAlign: st.textAlign, textTransform: st.textTransform,
      lineHeight: parseFloat(st.lineHeight) || 0,
      borderRadius: parseFloat(st.borderTopLeftRadius) || 0,
      borderWidth: parseFloat(st.borderTopWidth) || 0,
      boxShadow: st.boxShadow,
    });
  }
  return { width: docW, height: docH, blocks };
}
"""


@contextmanager
def browser_session(viewport_width: int = DEFAULT_VIEWPORT_WIDTH):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": viewport_width, "height": DEFAULT_VIEWPORT_HEIGHT},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = context.new_page()
        try:
            yield page
        finally:
            browser.close()


def introspect(page, url: str, screenshot_path: Path) -> dict:
    page.goto(url, wait_until="networkidle")
    page.add_style_tag(content=_FREEZE_CSS)
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(200)
    page.screenshot(path=str(screenshot_path), full_page=True)
    return page.evaluate(_EXTRACT_JS)
