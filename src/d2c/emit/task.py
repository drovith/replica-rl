from __future__ import annotations

import json
import shutil
from pathlib import Path

import d2c
from d2c.render.capture import _page_name

_D2C_SRC = Path(d2c.__file__).parent

_TASK_TOML = """\
version = "1.0"

[metadata]
id = "{id}"
recipe = "design-to-code"

[agent]
timeout_sec = 1800.0

[verifier]
timeout_sec = 900.0

[environment]
build_timeout_sec = 3600.0
"""

_DOCKERFILE = """\
FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir playwright==1.60.0 \\
 && playwright install --with-deps chromium
RUN apt-get update \\
 && apt-get install -y --no-install-recommends fonts-noto-color-emoji fonts-liberation \\
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir open-clip-torch==3.3.0 scipy==1.17.1 pillow==12.2.0 numpy==2.4.6

ENV D2C_CLIP_CACHE=/opt/clip
RUN mkdir -p /opt/clip \\
 && python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai', cache_dir='/opt/clip')" \\
 && chmod -R a+rX /opt/clip

COPY design ./design
COPY assets ./assets
"""

_TEST_SH = """\
#!/bin/bash
set -u
mkdir -p /logs/verifier
export D2C_CLIP_CACHE=/opt/clip
PYTHONPATH=/tests python -m d2c.grade.verify
"""

def _instruction(manifest: dict) -> str:
    lines = []
    for page in manifest["pages"]:
        stem = _page_name(page["path"])
        lines.append(f"- `{page['path']}` — {page['title']}  (target: `design/{stem}.png`)")
    pages_block = "\n".join(lines)
    return f"""\
# Replicate this website's design in HTML and CSS

You are given full-page screenshots of an existing multi-page website. Your goal
is **exact replication**: reproduce the target design as precisely as you can as
a static **HTML + CSS** site — the same layout, spacing, typography, colour, and
components. Functionality is out of scope and is not evaluated; design fidelity
is everything.

## What you're given
- `design/` — one full-page screenshot per page, captured in a desktop browser at
  **1440px** wide. These are your target.
- `assets/` — the image files the site uses. Use these for any imagery and
  reference them with relative paths like `assets/<filename>`.

## What to produce
Create exactly these pages in the current directory (`/app`), matching the
screenshots, and share a single stylesheet across them for consistency:

{pages_block}

Match every page closely: the same header/navigation and footer, the same colour
palette and type scale, the same section layouts and components. The result will
be viewed at 1440px wide.
"""


def _vendor_grader(tests_dir: Path) -> None:
    dst = tests_dir / "d2c"
    (dst / "grade").mkdir(parents=True)
    (dst / "render").mkdir(parents=True)
    shutil.copyfile(_D2C_SRC / "__init__.py", dst / "__init__.py")
    for name in ("__init__.py", "grade.py", "introspect.py", "match.py", "score.py", "color.py", "embed.py", "verify.py"):
        shutil.copyfile(_D2C_SRC / "grade" / name, dst / "grade" / name)
    shutil.copyfile(_D2C_SRC / "render" / "__init__.py", dst / "render" / "__init__.py")
    shutil.copyfile(_D2C_SRC / "render" / "capture.py", dst / "render" / "capture.py")


def build_task(site_dir: Path, task_dir: Path) -> None:
    manifest = json.loads((site_dir / "manifest.json").read_text())
    site_id = site_dir.name

    if task_dir.exists():
        shutil.rmtree(task_dir)
    (task_dir / "environment").mkdir(parents=True)
    (task_dir / "tests").mkdir(parents=True)

    design_dir = task_dir / "environment" / "design"
    design_dir.mkdir()
    for page in manifest["pages"]:
        stem = _page_name(page["path"])
        shutil.copyfile(site_dir / "screenshots" / f"{stem}.png", design_dir / f"{stem}.png")

    assets_dst = task_dir / "environment" / "assets"
    assets_src = site_dir / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst)
    else:
        assets_dst.mkdir()
    if not any(assets_dst.iterdir()):
        (assets_dst / ".gitkeep").touch()

    (task_dir / "environment" / "Dockerfile").write_text(_DOCKERFILE)
    (task_dir / "instruction.md").write_text(_instruction(manifest))
    (task_dir / "task.toml").write_text(_TASK_TOML.format(id=site_id))

    shutil.copytree(site_dir, task_dir / "tests" / "reference", ignore=shutil.ignore_patterns("screenshots"))
    _vendor_grader(task_dir / "tests")
    (task_dir / "tests" / "test.sh").write_text(_TEST_SH)
