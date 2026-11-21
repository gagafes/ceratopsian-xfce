#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recolor the DMZ Black and DMZ White Xcursor themes."""

import argparse
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct("<4sIII")
TOC_ENTRY = struct.Struct("<3I")
IMAGE_HEADER = struct.Struct("<9I")
IMAGE_CHUNK_TYPE = 0xFFFD0002
ARGB = struct.Struct("<I")
DARK_OUTLINE = (119, 151, 165)
LIGHT_OUTLINE = (52, 73, 84)
LIGHT_FACE = (145, 173, 186)


def frame_pixel_ranges(data):
    magic, header_size, _, count = HEADER.unpack_from(data)
    table_end = header_size + TOC_ENTRY.size * count
    if magic != b"Xcur" or header_size < HEADER.size or table_end > len(data):
        raise ValueError("Invalid Xcursor header")

    for offset in range(header_size, table_end, TOC_ENTRY.size):
        kind, nominal_size, position = TOC_ENTRY.unpack_from(data, offset)
        if kind != IMAGE_CHUNK_TYPE:
            continue
        length, image_type, image_size, _, width, height, hot_x, hot_y, _ = (
            IMAGE_HEADER.unpack_from(data, position)
        )
        start = position + length
        stop = start + ARGB.size * width * height
        if (
            position < table_end
            or length < IMAGE_HEADER.size
            or image_type != kind
            or image_size != nominal_size
            or hot_x >= width
            or hot_y >= height
            or stop > len(data)
        ):
            raise ValueError("Invalid Xcursor image frame")
        yield start, stop


def dark_colors(alpha, red, green, blue):
    if alpha and red > 0 and red == green == blue:
        # The existing premultiplied gray values encode the contour coverage.
        return tuple((red * channel + 127) // 255 for channel in DARK_OUTLINE)
    return None


def light_colors(alpha, red, green, blue):
    if alpha:
        luminance = min(alpha, (54 * red + 183 * green + 19 * blue + 128) // 256)
        return tuple(
            (shade * alpha + (face - shade) * luminance + 127) // 255
            for shade, face in zip(LIGHT_OUTLINE, LIGHT_FACE)
        )
    return None


def recolor(data, colors):
    result = bytearray(data)
    for start, stop in frame_pixel_ranges(data):
        for offset in range(start, stop, ARGB.size):
            color, = ARGB.unpack_from(data, offset)
            alpha, red, green, blue = ((color >> shift) & 255 for shift in (24, 16, 8, 0))
            replacement = colors(alpha, red, green, blue)
            if replacement is not None:
                red, green, blue = replacement
                ARGB.pack_into(result, offset, (alpha << 24) | (red << 16) | (green << 8) | blue)
    return result


def render_theme(source, colors, unchanged=()):
    entries = {}
    for asset in sorted(source.iterdir()):
        if asset.is_symlink():
            link = os.readlink(asset)
            parts = Path(link).parts
            if len(parts) != 1 or not (source / link).is_file():
                raise ValueError(f"Invalid Xcursor alias {asset} -> {link}")
            entries[asset.name] = link
        elif asset.is_file():
            data = asset.read_bytes()
            try:
                entries[asset.name] = data if asset.name in unchanged else recolor(data, colors)
            except (struct.error, ValueError) as error:
                raise ValueError(f"{asset}: {error}") from error
        else:
            raise ValueError(f"Unsupported Xcursor entry {asset}")
    if not entries:
        raise ValueError(f"No cursor files in {source}")
    return entries


def verify_theme(directory, entries):
    existing = {asset.name for asset in directory.iterdir()}
    differences = existing ^ entries.keys()
    for name in existing & entries.keys():
        asset = directory / name
        expected = entries[name]
        if isinstance(expected, str):
            matches = asset.is_symlink() and os.readlink(asset) == expected
        else:
            matches = not asset.is_symlink() and asset.is_file() and asset.read_bytes() == expected
        if not matches:
            differences.add(name)
    return [directory.relative_to(ROOT) / name for name in sorted(differences)]


def write_theme(directory, entries):
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".cursors-", dir=directory) as staging:
        temporary = Path(staging)
        for name, content in entries.items():
            asset = temporary / name
            if isinstance(content, str):
                asset.symlink_to(content)
            else:
                asset.write_bytes(content)
        # Install the cursor files before their aliases.
        for asset in sorted(temporary.iterdir(), key=Path.is_symlink):
            asset.replace(directory / asset.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="write both cursor sets under this directory")
    mode.add_argument("--verify", action="store_true", help="compare cursor files and aliases with the source tree")
    parser.add_argument(
        "--source-icons", type=Path, default=Path("/usr/share/icons"),
        help="directory containing DMZ-Black and DMZ-White (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        dark = args.source_icons / "DMZ-Black/cursors"
        light = args.source_icons / "DMZ-White/cursors"
        themes = {
            # The dial on the dark wait cursor has no pointer outline.
            Path("icons/Ceratopsian-Cursors/cursors"): render_theme(dark, dark_colors, ("watch",)),
            Path("icons/Ceratopsian-Cursors-Light/cursors"): render_theme(light, light_colors),
        }
        count = sum(len(entries) for entries in themes.values())
        if args.verify:
            differences = []
            for path, entries in themes.items():
                differences.extend(verify_theme(ROOT / path, entries))
            if differences:
                parser.exit(1, "Missing, extra or different cursor entries:\n" +
                            "\n".join(str(path) for path in differences) + "\n")
            print(f"Verified {count} cursor files and aliases against the source tree.")
        else:
            for path, entries in themes.items():
                write_theme(args.output / path, entries)
            print(f"Rendered {count} cursor files and aliases under {args.output}.")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
