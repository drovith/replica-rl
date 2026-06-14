from __future__ import annotations

import hashlib
import mimetypes
import re
import shutil
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# Unsplash photos and any image-extension URL; fonts and icon CDNs are left alone.
_IMAGE_URL_RE = re.compile(
    r"https://(?:images\.unsplash\.com/[^\"'()\s]+"
    r"|[^\"'()\s]+\.(?:jpg|jpeg|png|webp|avif|gif)(?:\?[^\"'()\s]*)?)"
)

_SOURCE_GLOBS = ("*.html", "*.css")


def _source_files(site_dir: Path) -> list[Path]:
    return [p for glob in _SOURCE_GLOBS for p in site_dir.rglob(glob)]


def _local_name(url: str, content_type: str | None) -> str:
    digest = hashlib.sha1(url.encode()).hexdigest()[:12]
    ext = mimetypes.guess_extension((content_type or "").split(";")[0]) or ".jpg"
    return f"{digest}{'.jpg' if ext == '.jpe' else ext}"


def _download(url: str) -> tuple[bytes, str | None] | None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=60) as response:
            return response.read(), response.headers.get_content_type()
    except (URLError, OSError):
        return None


def _rewrite(site_dir: Path, url_to_name: dict[str, str]) -> None:
    for file in _source_files(site_dir):
        text = file.read_text()
        depth = len(file.relative_to(site_dir).parts) - 1
        prefix = "../" * depth
        for url, name in url_to_name.items():
            text = text.replace(url, f"{prefix}assets/{name}")
        file.write_text(text)


def freeze_assets(site_dir: Path) -> tuple[int, list[str]]:
    """Download external images into assets/ and relink. Returns (localised, failed_urls)."""
    urls = sorted({m.group(0) for f in _source_files(site_dir) for m in _IMAGE_URL_RE.finditer(f.read_text())})
    if not urls:
        return 0, []

    (site_dir / "assets").mkdir(exist_ok=True)
    url_to_name: dict[str, str] = {}
    failed: list[str] = []
    for url in urls:
        downloaded = _download(url)
        if downloaded is None:
            failed.append(url)
            continue
        data, content_type = downloaded
        name = _local_name(url, content_type)
        (site_dir / "assets" / name).write_bytes(data)
        url_to_name[url] = name

    _rewrite(site_dir, url_to_name)
    return len(url_to_name), failed


def substitute_failures(site_dir: Path, failed_urls: list[str], pool: list[Path]) -> int:
    """Replace un-fetchable (hallucinated) image URLs with valid images from `pool`."""
    if not failed_urls or not pool:
        return 0
    (site_dir / "assets").mkdir(exist_ok=True)
    url_to_name: dict[str, str] = {}
    for url in failed_urls:
        choice = pool[int(hashlib.sha1(url.encode()).hexdigest(), 16) % len(pool)]
        name = f"sub-{hashlib.sha1(url.encode()).hexdigest()[:12]}{choice.suffix}"
        shutil.copyfile(choice, site_dir / "assets" / name)
        url_to_name[url] = name
    _rewrite(site_dir, url_to_name)
    return len(url_to_name)
