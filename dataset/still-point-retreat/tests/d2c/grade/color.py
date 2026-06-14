from __future__ import annotations

import re

_NUM_RE = re.compile(r"[\d.]+")


def parse_rgb(value: str | None) -> tuple[float, float, float] | None:
    if not value:
        return None
    nums = _NUM_RE.findall(value)
    if len(nums) < 3:
        return None
    if len(nums) >= 4 and float(nums[3]) == 0.0:
        return None
    return tuple(float(n) for n in nums[:3])


def _srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def linear(c: float) -> float:
        c /= 255.0
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    r, g, b = (linear(v) for v in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]) -> float:
    lab1, lab2 = _srgb_to_lab(rgb1), _srgb_to_lab(rgb2)
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5
