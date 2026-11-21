# Ceratopsian Dark Theme for Xfce

A graphite and matte blue-grey theme for Xfce 4.20 on Debian 13. It includes
GTK 2, 3 and 4 styles, icons, dark and light cursors, an Xfce Terminal palette,
and the Debian 13 Matte and Clean wallpapers.

![Ceratopsian desktop](previews/desktop.png)

[Thunar](previews/thunar.png) · [Whisker menu](previews/whisker.png) · [Wallpapers](previews/wallpapers.jpg)

## Install

Download the [Debian package](https://github.com/gagafes/ceratopsian-xfce/releases/latest) and run this from your download directory.

```sh
sudo apt install ./ceratopsian-xfce_0.1.0-1_all.deb
```

In Xfce Settings, select **Ceratopsian Dark** under **Appearance → Style**,
**Ceratopsian** under **Appearance → Icons**, and **Ceratopsian-Dark** under
**Window Manager → Style** and **Notifications → Theme**.

Choose a cursor under **Mouse and Touchpad → Theme** and the **Ceratopsian**
palette in **Xfce Terminal → Preferences → Colors**. The wallpapers are in
`/usr/share/backgrounds/ceratopsian-xfce` and `/usr/share/backgrounds/ceratopsian-variants`.

Remove the package with `sudo apt remove ceratopsian-xfce`.

## More

- Install for one user with `python3 install.py install` from the source tree in
  an Xfce session with Python 3.11+ and `xfconf-query`. Remove it with `python3 install.py uninstall`.
- Build with `dpkg-buildpackage -us -uc -b` after installing `build-essential`, `debhelper` and `dpkg-dev`.
- [Qt, LightDM, GRUB and Plymouth](extras/README.md) · [Asset sources](SOURCES.md) · [Credits](CREDITS.md) · [Licences](LICENSE.md)
