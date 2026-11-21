#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the desktop, Plymouth and GRUB backgrounds from the wallpaper SVGs."""

import argparse
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import cairo
import gi
from PIL import Image, ImageOps

gi.require_version("Rsvg", "2.0")
from gi.repository import GLib, Rsvg


ROOT = Path(__file__).resolve().parents[1]
WALLPAPER_SIZE = (1920, 1200)
GRUB_SIZE = (1024, 768)
LANCZOS = Image.Resampling.LANCZOS
MATTE_SVG = Path("wallpapers/ceratopsian-matte.svg")
CLEAN_SVG = Path("wallpaper-variants/clean.svg")


def render_svg(path):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *WALLPAPER_SIZE)
    viewport = Rsvg.Rectangle()
    viewport.width, viewport.height = WALLPAPER_SIZE
    handle = Rsvg.Handle.new_from_data(path.read_bytes())
    if not handle.render_document(cairo.Context(surface), viewport):
        raise ValueError(f"Could not render {path}")

    with BytesIO() as png:
        surface.write_to_png(png)
        png.seek(0)
        with Image.open(png) as image:
            return image.convert("RGBA")


def render_assets():
    matte = render_svg(ROOT / MATTE_SVG)
    matte_rgb = matte.convert("RGB")
    clean_rgb = render_svg(ROOT / CLEAN_SVG).convert("RGB")
    return {
        MATTE_SVG.with_suffix(".png"): matte,
        CLEAN_SVG.with_suffix(".png"): clean_rgb,
        Path("extras/boot/plymouth/wallpaper.png"): matte_rgb,
        Path("extras/boot/grub-background.png"): ImageOps.fit(matte_rgb, GRUB_SIZE, LANCZOS),
        Path("extras/boot/variants/clean.png"): clean_rgb.crop((160, 0, 1760, 1200)).resize(
            GRUB_SIZE, LANCZOS
        ),
    }


def matches(path, rendered):
    try:
        with Image.open(path, formats=("PNG",)) as original:
            return (
                original.mode == rendered.mode
                and original.size == rendered.size
                and original.tobytes() == rendered.tobytes()
            )
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="write PNGs under this directory")
    mode.add_argument("--verify", action="store_true", help="compare PNG pixels with the source tree")
    args = parser.parse_args()

    try:
        assets = render_assets()
        if args.verify:
            differences = [str(path) for path, image in assets.items() if not matches(ROOT / path, image)]
            if differences:
                parser.exit(1, "Missing or different PNG pixels: " + ", ".join(differences) + "\n")
            print(f"Verified {len(assets)} PNGs against the source tree.")
        else:
            for path, image in assets.items():
                target = args.output / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with TemporaryDirectory(prefix=".wallpaper-", dir=target.parent) as staging:
                    staged = Path(staging) / target.name
                    image.save(staged, optimize=True)
                    staged.replace(target)
            print(f"Rendered {len(assets)} PNGs under {args.output}.")
    except (GLib.Error, OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
