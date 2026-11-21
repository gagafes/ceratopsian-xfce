#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install the Ceratopsian theme in the current user's Xfce profile."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


PACKAGE = Path(__file__).resolve().parent
HOME = Path.home()
THEME = "Ceratopsian-Dark"
ICONS = "Ceratopsian-Icons"
CURSORS = "Ceratopsian-Cursors"
LIGHT_CURSORS = "Ceratopsian-Cursors-Light"
WALLPAPER_VARIANTS = PACKAGE / "wallpaper-variants"


def xdg_home(variable, default):
    path = Path(os.environ.get(variable, ""))
    return path if path.is_absolute() else HOME / default


DATA = xdg_home("XDG_DATA_HOME", ".local/share")
STATE = xdg_home("XDG_STATE_HOME", ".local/state") / "ceratopsian-xfce"
JOURNAL = STATE / "install.json"
ASSETS = {
    "theme": (PACKAGE / "themes" / THEME, HOME / ".themes" / THEME),
    "icons": (PACKAGE / "icons" / ICONS, DATA / "icons" / ICONS),
    "cursors": (PACKAGE / "icons" / CURSORS, HOME / ".icons" / CURSORS),
    "light_cursors": (PACKAGE / "icons" / LIGHT_CURSORS, HOME / ".icons" / LIGHT_CURSORS),
    "wallpaper": (PACKAGE / "wallpapers", DATA / "backgrounds/ceratopsian-xfce"),
    "wallpaper_variants": (WALLPAPER_VARIANTS, DATA / "backgrounds/ceratopsian-variants"),
    "terminal": (
        PACKAGE / "terminal/ceratopsian.theme",
        DATA / "xfce4/terminal/colorschemes/ceratopsian.theme",
    ),
}


def xfconf(*args, check=True):
    return subprocess.run(
        ("xfconf-query", *args), check=check, text=True, capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )


def read_setting(channel, key):
    result = xfconf("-c", channel, "-p", key, check=False)
    if result.returncode == 0:
        return result.stdout.rstrip("\n")
    if "does not exist" in result.stderr:
        return None
    raise RuntimeError(result.stderr.strip() or f"Could not read {channel}{key}")


def put_setting(channel, key, value):
    args = ("-c", channel, "-p", key)
    current = read_setting(channel, key)
    if current == value:
        return
    if value is None:
        xfconf(*args, "--reset")
    elif current is None:
        xfconf(*args, "--create", "--type", "string", "--set", value)
    else:
        xfconf(*args, "--set", value)
    if read_setting(channel, key) != value:
        raise RuntimeError(f"Could not set {channel}{key}")


def fingerprint(root):
    digest = hashlib.sha256()
    paths = [root]
    if root.is_dir() and not root.is_symlink():
        paths.extend(sorted(root.rglob("*")))
    for path in paths:
        name = str(path.relative_to(root))
        if path.is_symlink():
            kind, value = "link", os.readlink(path)
        elif path.is_dir():
            kind, value = "dir", ""
        elif path.is_file():
            with path.open("rb") as file:
                kind, value = "file", hashlib.file_digest(file, "sha256").hexdigest()
        else:
            raise RuntimeError(f"Unsupported theme entry {path}")
        digest.update(os.fsencode(f"{name}\0{kind}\0{value}\0"))
    return digest.hexdigest()


def place(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ceratopsian-", dir=dest.parent) as temp:
        staged = Path(temp) / dest.name
        if source.is_dir():
            shutil.copytree(source, staged, symlinks=True)
        else:
            shutil.copy2(source, staged)
        if dest.exists() or dest.is_symlink():
            raise RuntimeError(f"{dest} already exists")
        staged.rename(dest)


def save(journal):
    with tempfile.NamedTemporaryFile(mode="w", dir=STATE, delete=False) as file:
        json.dump(journal, file, indent=2)
        file.write("\n")
        path = Path(file.name)
    path.replace(JOURNAL)


def restore_settings(settings):
    for channel, key, previous, installed in reversed(settings):
        if read_setting(channel, key) == installed:
            # Xfwm 4.20 needs a valid theme value to reload its decorations.
            if (channel, key) == ("xfwm4", "/general/theme") and previous is None:
                previous = "Default"
            put_setting(channel, key, previous)


def remove_files(files):
    for label, (path, expected) in files.items():
        dest = ASSETS[label][1]
        if Path(path) != dest:
            raise RuntimeError(f"Use the original XDG directories to remove {path}")
        if not dest.exists() and not dest.is_symlink():
            continue
        if fingerprint(dest) != expected:
            print(f"Preserved local edits in {dest}")
        elif dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()


def selections(options):
    if options.assets_only:
        return {}
    xfconf("--list")
    values = {
        ("xsettings", "/Net/ThemeName"): THEME,
        ("xfwm4", "/general/theme"): THEME,
        ("xfce4-notifyd", "/theme"): THEME,
    }
    if not options.keep_icons:
        values["xsettings", "/Net/IconThemeName"] = ICONS
    if options.cursor or not options.keep_icons:
        values["xsettings", "/Gtk/CursorThemeName"] = (
            LIGHT_CURSORS if options.cursor == "light" else CURSORS
        )
    if options.wallpaper:
        properties = xfconf("-c", "xfce4-desktop", "--list").stdout.splitlines()
        keys = [
            key for key in properties
            if re.fullmatch(r"/backdrop/screen\d+/monitor[^/]+/workspace\d+/last-image", key)
        ]
        if not keys:
            raise RuntimeError("Choose the installed wallpaper in Xfce Desktop Settings")
        if options.wallpaper == "default":
            image = ASSETS["wallpaper"][1] / "ceratopsian-matte.svg"
        else:
            image = ASSETS["wallpaper_variants"][1] / f"{options.wallpaper}.svg"
        for key in keys:
            values["xfce4-desktop", key] = str(image)
    return values


def install(options, old_state):
    pending = {}
    for label, (source, dest) in ASSETS.items():
        expected = fingerprint(source)
        if dest.exists() or dest.is_symlink():
            if fingerprint(dest) != expected:
                raise RuntimeError(f"{dest} already exists with different contents")
        else:
            pending[label] = [str(dest), expected]

    known_settings = {tuple(record[:2]): record for record in old_state["settings"]}
    changes = []
    for (channel, key), value in selections(options).items():
        previous = read_setting(channel, key)
        if previous != value:
            changes.append([channel, key, previous, value])
            original = known_settings.get((channel, key))
            if original and original[3] == previous:
                previous = original[2]
            known_settings[channel, key] = [channel, key, previous, value]
    save({
        "files": {**old_state["files"], **pending},
        "settings": list(known_settings.values()),
    })
    try:
        for label in pending:
            place(*ASSETS[label])
        for channel, key, _, value in changes:
            put_setting(channel, key, value)
    except BaseException:
        restore_settings(changes)
        remove_files(pending)
        save(old_state)
        raise
    print(f"Installed {THEME}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("install")
    add.add_argument("--assets-only", action="store_true", help="copy theme files only")
    add.add_argument("--keep-icons", action="store_true", help="use the current icons and cursor at activation")
    add.add_argument("--cursor", choices=("dark", "light"), help="select the matching cursor theme")
    variants = sorted(path.stem for path in WALLPAPER_VARIANTS.glob("*.svg"))
    add.add_argument(
        "--wallpaper", nargs="?", const="default", choices=["default", *variants],
        help="apply the selected wallpaper to configured desktops",
    )
    commands.add_parser("uninstall")
    options = parser.parse_args()

    if os.geteuid() == 0:
        parser.error("Run this with your desktop user account.")
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / "install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old_state = (
            json.loads(JOURNAL.read_text()) if JOURNAL.is_file()
            else {"files": {}, "settings": []}
        )
        if options.command == "install":
            install(options, old_state)
        else:
            restore_settings(old_state["settings"])
            remove_files(old_state["files"])
            JOURNAL.unlink(missing_ok=True)
            print(f"Restored the previous theme settings.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.stderr.strip() or str(error))
    except (OSError, RuntimeError) as error:
        sys.exit(str(error))
