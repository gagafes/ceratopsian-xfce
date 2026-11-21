#!/usr/bin/env python3
"""Regenerate the icon modifications from the elementary-xfce 0.21-1 package."""

import argparse
from itertools import chain
from pathlib import Path
import re

from PIL import Image, ImageOps


FOLDER_TONES = (
    (0, (0, 0, 0)),
    (95, (38, 55, 65)),
    (140, (53, 78, 92)),
    (172, (66, 96, 111)),
    (215, (88, 121, 137)),
    (243, (119, 151, 165)),
    (255, (140, 168, 181)),
)
GRAYSCALE_TONES = (
    (0, (10, 16, 20)),
    (55, (30, 44, 53)),
    (116, (57, 82, 95)),
    (169, (97, 126, 139)),
    (212, (147, 176, 188)),
    (255, (232, 241, 245)),
)
FOLDER_ACTIONS = {
    "archive-insert-directory", "folder-copy", "folder-move", "folder-new",
}
APP_ALIASES = {
    "org.xfce.settings.manager": "preferences-desktop",
    "preferences-system-services": "mx-tools",
    "user-info": "avatar-default",
}
# The release uses other icon names or symbolic glyphs for these categories.
OMITTED_CATEGORIES = {
    "applications-development", "applications-games", "applications-graphics",
    "applications-internet", "applications-multimedia", "applications-office",
    "applications-other", "applications-science", "applications-system",
    "preferences-desktop", "preferences-system", "preferences-system-network",
}


def read_png(path):
    with Image.open(path) as image:
        return image.convert("RGBA")


def tint_folder_pixel(pixel):
    red, green, blue, alpha = pixel
    if not alpha or not (red > green > blue and red - blue >= 8):
        return pixel

    luminance = .2126 * red + .7152 * green + .0722 * blue
    for (start, low), (end, high) in zip(FOLDER_TONES, FOLDER_TONES[1:]):
        if luminance <= end:
            fraction = (luminance - start) / (end - start)
            return tuple(round(a + (b - a) * fraction) for a, b in zip(low, high)) + (alpha,)
    return pixel


def folder_images(upstream):
    places = upstream.glob("places/[0-9]*/*.png")
    actions = upstream.glob("actions/[0-9]*/*.png")
    originals = chain(
        (path for path in places if path.stem.startswith(("folder", "user-home"))),
        (path for path in actions if path.stem in FOLDER_ACTIONS),
    )
    changed = {}
    for path in originals:
        if path.is_symlink():
            continue
        image = read_png(path)
        pixels = list(image.getdata())
        tinted = [tint_folder_pixel(pixel) for pixel in pixels]
        if tinted != pixels:
            image.putdata(tinted)
            changed[path] = image
    return changed


def grayscale_lookup():
    tones = []
    for (start, low), (end, high) in zip(GRAYSCALE_TONES, GRAYSCALE_TONES[1:]):
        for level in range(start, end):
            fraction = (level - start) / (end - start)
            tones.append(tuple(round(a + (b - a) * fraction) for a, b in zip(low, high)))
    tones.append(GRAYSCALE_TONES[-1][1])
    return tuple(zip(*tones))


def tint_grayscale(image, channels):
    luminance = ImageOps.grayscale(image)
    rgb = tuple(luminance.point(channel) for channel in channels)
    return Image.merge("RGBA", (*rgb, image.getchannel("A")))


def render_pngs(upstream):
    folders = folder_images(upstream)
    aliases = chain(upstream.glob("places/*/*.png"), upstream.glob("actions/*/*.png"))
    for path in sorted(aliases):
        image = folders.get(path.resolve())
        if image is not None:
            yield path.relative_to(upstream), image

    channels = grayscale_lookup()
    for path in sorted(upstream.glob("apps/*/*.png")):
        if not path.is_file():
            continue
        # Some app aliases point to Places artwork that was already recoloured.
        source = folders.get(path.resolve())
        image = tint_grayscale(source if source is not None else read_png(path), channels)
        yield path.relative_to(upstream), image

        alias = APP_ALIASES.get(path.stem)
        if alias:
            target = path.with_name(alias + ".png")
            if not target.is_file():
                yield target.relative_to(upstream), image

    for path in sorted(upstream.glob("categories/*/*.png")):
        if path.is_file() and path.stem not in OMITTED_CATEGORIES:
            source = path.with_name("preferences-other.png") if path.stem == "applications-accessories" else path
            yield path.relative_to(upstream), tint_grayscale(read_png(source), channels)

    for path in sorted(upstream.glob("emblems/*/emblem-default.png")):
        yield path.relative_to(upstream), tint_grayscale(read_png(path), channels)


def render_network_icons(upstream):
    names = {
        "nm-no-connection": "status/symbolic/network-offline",
        "nm-device-wired": "devices/symbolic/network-wired",
        "nm-device-wireless": "status/symbolic/network-wireless-connected",
        "nm-device-wwan": "status/symbolic/network-cellular-connected",
    }
    levels = (
        ("0", "none"), ("00", "none"), ("25", "weak"), ("50", "ok"),
        ("75", "good"), ("100", "excellent"),
    )
    for number, strength in levels:
        path = f"status/symbolic/network-wireless-signal-{strength}"
        names[f"nm-signal-{number}"] = path
        if strength != "none":
            names[f"nm-signal-{number}-secure"] = path + "-secure"

    for name, path in sorted(names.items()):
        source = upstream / f"{path}-symbolic.svg"
        data = source.read_bytes()
        tinted, changes = re.subn(rb'(?<=fill:)#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', b"#8eacbc", data)
        if not changes:
            tinted, changes = re.subn(rb'(?<=fill=")#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', b"#8eacbc", data)
        if not changes:
            raise ValueError(f"No tintable fill found in {source}")
        yield Path("status/ceratopsian-network") / f"{name}.svg", tinted


def matches(path, content):
    if not path.is_file():
        return False
    if isinstance(content, bytes):
        return path.read_bytes() == content
    actual = read_png(path)
    return actual.size == content.size and actual.tobytes() == content.tobytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="elementary-xfce icon directory from version 0.21-1")
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--check", type=Path, metavar="THEME", help="verify against a Ceratopsian-Icons directory")
    destination.add_argument("--output", type=Path, metavar="DIRECTORY", help="write the generated icon overlay")
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    if not (upstream / "index.theme").is_file():
        parser.error(f"No icon theme index in {upstream}")
    if args.check and not args.check.is_dir():
        parser.error(f"No icon theme directory at {args.check}")

    count = 0
    mismatches = []
    try:
        for relative, content in chain(render_pngs(upstream), render_network_icons(upstream)):
            count += 1
            if args.check:
                if not matches(args.check / relative, content):
                    mismatches.append(relative)
                continue
            path = args.output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                content.save(path)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")

    if mismatches:
        paths = "\n".join(str(path) for path in mismatches[:12])
        parser.exit(1, f"{len(mismatches)} of {count} generated icons differ or are missing.\n{paths}\n")
    action = "Verified" if args.check else "Generated"
    print(f"{action} {count} icons.")


if __name__ == "__main__":
    main()
