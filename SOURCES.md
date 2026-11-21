# Asset sources

The checked-in CSS, SVGs, XPMs, configuration and image assets are the inputs to the Debian package. The build copies them using debhelper and can run offline. The upstream source archive in the GitHub release contains the exact Debian sources for the inherited material.

| Component | Debian source | Local editable files |
| --- | --- | --- |
| GTK | Yaru `24.04.3-1` | `themes/Ceratopsian-Dark/gtk-2.0`, `gtk-3.0` and `gtk-4.0`. The edits use the Yaru Sage Dark CSS and assets as a baseline, with blue-grey colours, compact rounded controls and Xfce selectors. |
| Xfwm | Orchis `2024-11-03+ds-1` | `themes/Ceratopsian-Dark/xfwm4`. The SVGs, XPMs and `themerc` preserve the edited borders, active and inactive frames, and close-button hover. |
| Icons | elementary-xfce `0.21-1` | `icons/Ceratopsian-Icons` and the tint recipe in `sources`. |
| Cursors | DMZ `0.4.5.2` | `icons/Ceratopsian-Cursors*` and the tint recipe in `sources`. |
| Wallpaper and boot | desktop-base `13.0.4` | The exported wallpapers derive from Elise Couper's `ceratopsian-theme/login/background.svg`. The two SVGs, render recipe and Plymouth script are in this repository. |

The release supplies the Debian source package for Ceratopsian alongside the binary package. The upstream reference archives retain their source-package descriptors, checksums and copyright notices. [Release downloads](https://github.com/gagafes/ceratopsian-xfce/releases)

## Verify the generated assets

On Debian 13, install the pinned Elementary Xfce and DMZ icon packages for the source images. The scripts use Python 3 and Pillow. The wallpaper renderer also uses PyGObject, Cairo integration and librsvg (packages `python3-gi`, `python3-gi-cairo` and `gir1.2-rsvg-2.0`).

```sh
/usr/bin/python3 sources/render-elementary.py /usr/share/icons/elementary-xfce --check icons/Ceratopsian-Icons
/usr/bin/python3 sources/render-cursors.py --verify
/usr/bin/python3 sources/render-wallpapers.py --verify
```

Each script also accepts `--output DIRECTORY` to write regenerated assets. The package build uses the staged files directly.
