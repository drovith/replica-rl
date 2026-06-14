"""Synthetic degradations for validating the grader.

Each kind perturbs a reference site in a way that should hit one dimension hard
and leave the others mostly intact — which is how we check the dimensions are
orthogonal and that the reward moves monotonically with severity.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from d2c.grade.introspect import browser_session

KINDS = ["lorem", "garble", "color", "bgcolor", "shift", "typo", "svg", "shape", "drop", "scramble", "combo"]

_MUTATE_JS = r"""
(params) => {
  const {kind, severity, seed} = params;
  let s = seed >>> 0;
  const rnd = () => {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const directText = (el) => {
    let t = "";
    for (const n of el.childNodes) if (n.nodeType === 3) t += n.nodeValue;
    return t.trim();
  };
  const leaves = [...document.body.querySelectorAll("*")].filter((el) => directText(el).length > 0);
  const LOREM = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
                 + "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis").split(" ");

  if (kind === "lorem") {
    // In place so structure/whitespace is preserved and severity 0 is a true identity.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.nodeValue.trim()) nodes.push(n);
    for (const n of nodes) {
      n.nodeValue = n.nodeValue.replace(/\S+/g, (w) => (rnd() < severity ? LOREM[Math.floor(rnd() * LOREM.length)] : w));
    }
  } else if (kind === "garble") {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.nodeValue.trim()) nodes.push(n);
    for (const n of nodes) if (rnd() < severity) {
      n.nodeValue = n.nodeValue.replace(/\S+/g, () => LOREM[Math.floor(rnd() * LOREM.length)]);
    }
  } else if (kind === "color") {
    for (const el of leaves) if (rnd() < severity) el.style.setProperty("color", "#cc00aa", "important");
  } else if (kind === "bgcolor") {
    for (const el of document.body.querySelectorAll("*")) {
      const bg = getComputedStyle(el).backgroundColor;
      if (bg && !bg.startsWith("rgba(0, 0, 0, 0") && rnd() < severity) {
        el.style.setProperty("background-color", "#3a5f8a", "important");
      }
    }
  } else if (kind === "shift") {
    for (const el of leaves) if (rnd() < severity) {
      el.style.setProperty("position", "relative");
      el.style.setProperty("left", "40px");
      el.style.setProperty("top", "25px");
    }
  } else if (kind === "typo") {
    for (const el of leaves) if (rnd() < severity) {
      el.style.setProperty("font-weight", "900", "important");
      el.style.setProperty("font-style", "italic", "important");
      el.style.setProperty("text-transform", "uppercase", "important");
      el.style.setProperty("text-align", "center", "important");
    }
  } else if (kind === "svg") {
    for (const el of document.body.querySelectorAll("svg")) if (rnd() < severity) el.remove();
  } else if (kind === "shape") {
    for (const el of document.body.querySelectorAll("*")) if (rnd() < severity) {
      el.style.setProperty("border-radius", "0", "important");
      el.style.setProperty("box-shadow", "none", "important");
      el.style.setProperty("border", "none", "important");
    }
  } else if (kind === "combo") {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.nodeValue.trim()) nodes.push(n);
    for (const n of nodes) n.nodeValue = n.nodeValue.replace(/\S+/g, (w) => (rnd() < severity ? LOREM[Math.floor(rnd() * LOREM.length)] : w));
    for (const el of leaves) {
      if (rnd() < severity) el.style.setProperty("color", "#cc00aa", "important");
      if (rnd() < severity) {
        el.style.setProperty("position", "relative");
        el.style.setProperty("left", "40px");
        el.style.setProperty("top", "25px");
      }
    }
  } else {
    // Descend past single-child wrappers so drop/scramble hit real sections.
    let container = document.body;
    while (container.children.length === 1 && container.firstElementChild) {
      container = container.firstElementChild;
    }
    if (kind === "drop") {
      for (const el of [...container.children]) if (rnd() < severity) el.remove();
    } else if (kind === "scramble") {
      const kids = [...container.children];
      for (let i = kids.length - 1; i > 0; i--) if (rnd() < severity) {
        const j = Math.floor(rnd() * (i + 1));
        container.insertBefore(kids[j], kids[i]);
      }
    }
  }
  return document.documentElement.outerHTML;
}
"""


def make_degraded(
    reference_dir: Path, out_dir: Path, kind: str, severity: float, seed: int = 7, pages: list[str] | None = None
) -> Path:
    manifest = json.loads((reference_dir / "manifest.json").read_text())
    pages = pages or [p["path"] for p in manifest["pages"]]

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(reference_dir, out_dir, ignore=shutil.ignore_patterns("screenshots"))

    with browser_session() as page:
        for page_path in pages:
            page.goto((reference_dir / page_path).resolve().as_uri(), wait_until="networkidle")
            html = page.evaluate(_MUTATE_JS, {"kind": kind, "severity": severity, "seed": seed})
            (out_dir / page_path).write_text("<!doctype html>\n" + html)
    return out_dir
