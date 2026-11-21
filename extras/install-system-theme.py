#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Make the packaged GTK theme and icons available to all users."""

import os
from pathlib import Path
import shutil
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from install import ICONS, PACKAGE, THEME, fingerprint, place


def install_system_theme(data_dir):
    pending = []
    for category, name in (("themes", THEME), ("icons", ICONS)):
        source = PACKAGE / category / name
        target = data_dir / category / name
        if not source.is_dir():
            raise RuntimeError(f"Missing package directory {source}")
        for path in source.rglob("*"):
            if path.is_symlink() and not path.resolve(strict=True).is_relative_to(source):
                raise RuntimeError(f"Link points outside the package directory: {path}")
        expected = fingerprint(source)
        if target.exists() or target.is_symlink():
            if fingerprint(target) != expected:
                raise RuntimeError(f"{target} already exists with different contents")
        else:
            pending.append((source, target, expected))

    added = []
    try:
        for source, target, expected in pending:
            place(source, target)
            added.append(target)
            if fingerprint(target) != expected:
                raise RuntimeError(f"System copy differs from the package: {target}")
            print(f"Installed {target}")
    except BaseException:
        for target in reversed(added):
            shutil.rmtree(target)
        raise


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Run this installer with sudo from a system terminal.")
    try:
        install_system_theme(Path("/usr/share"))
    except (OSError, RuntimeError) as error:
        sys.exit(str(error))
