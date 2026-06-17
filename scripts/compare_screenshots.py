#!/usr/bin/env python3
"""Compare two screenshots and optionally write a visual diff image."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two screenshots using Pillow and report pixel-level differences."
    )
    parser.add_argument("source", type=Path, help="Path to the source screenshot")
    parser.add_argument("rendered", type=Path, help="Path to the rendered screenshot")
    parser.add_argument(
        "--diff",
        type=Path,
        help="Optional output path for a magnified visual diff PNG",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=16.0,
        help="Per-pixel RGB distance threshold counted as visibly different",
    )
    return parser.parse_args()


def load_pillow():
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        print(
            "Pillow is required. Install it with: python3 -m pip install pillow",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return Image, ImageChops, ImageStat


def ensure_rgb(image):
    if image.mode == "RGB":
        return image
    if image.mode == "RGBA":
        background = image.__class__.new("RGBA", image.size, (255, 255, 255, 255))
        return image.__class__.alpha_composite(background, image).convert("RGB")
    return image.convert("RGB")


def main() -> int:
    args = parse_args()
    Image, ImageChops, ImageStat = load_pillow()

    if not args.source.exists():
        print(f"Source screenshot not found: {args.source}", file=sys.stderr)
        return 2
    if not args.rendered.exists():
        print(f"Rendered screenshot not found: {args.rendered}", file=sys.stderr)
        return 2

    source = ensure_rgb(Image.open(args.source))
    rendered = ensure_rgb(Image.open(args.rendered))

    if source.size != rendered.size:
        print(f"size_match: false")
        print(f"source_size: {source.size[0]}x{source.size[1]}")
        print(f"rendered_size: {rendered.size[0]}x{rendered.size[1]}")
        width = min(source.size[0], rendered.size[0])
        height = min(source.size[1], rendered.size[1])
        source = source.crop((0, 0, width, height))
        rendered = rendered.crop((0, 0, width, height))
        print(f"compared_crop_size: {width}x{height}")
    else:
        print("size_match: true")
        print(f"size: {source.size[0]}x{source.size[1]}")

    diff = ImageChops.difference(source, rendered)
    stat = ImageStat.Stat(diff)
    rms = math.sqrt(sum(value * value for value in stat.rms) / len(stat.rms))
    mean = sum(stat.mean) / len(stat.mean)

    pixels = list(diff.getdata())
    visible = 0
    for red, green, blue in pixels:
        distance = math.sqrt(red * red + green * green + blue * blue)
        if distance > args.threshold:
            visible += 1

    total = len(pixels)
    visible_percent = (visible / total) * 100 if total else 0

    print(f"mean_channel_difference: {mean:.2f}")
    print(f"rms_channel_difference: {rms:.2f}")
    print(f"visible_difference_percent: {visible_percent:.2f}")
    print(f"threshold: {args.threshold:.2f}")

    if args.diff:
        diff_rgb = diff.point(lambda value: min(255, value * 4))
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        diff_rgb.save(args.diff)
        print(f"diff_image: {args.diff}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
