# Optional integrations

## Qt Widgets

This preview uses the GTK 2 platform style where your distribution provides it. On the MX/Debian test system, Qt 5 uses `qt5-gtk2-platformtheme`, and Qt 6 uses `qt6gtk2`. With Ceratopsian selected in Xfce, test the matching plugin in an application you already have.

```sh
QT_QPA_PLATFORMTHEME=gtk2 your-qt-application
```

Qt applications that accept KDE colour schemes can use [Ceratopsian.colors](Ceratopsian.colors). Select it through your application's appearance settings.

## Synaptic

Synaptic runs under the administrator account. The Debian package installs the theme and icons in the system directories. For a per-user installation from the source archive, run this from the unpacked bundle in a system terminal.

```sh
sudo /usr/bin/python3 -I -B extras/install-system-theme.py
```

Reopen Synaptic to load the theme.

## LightDM GTK Greeter

The greeter uses system-wide themes. Back up the current greeter configuration before editing it. If you installed the Debian package, the theme, icons and cursors are already in the system directories, and the wallpaper path is `/usr/share/backgrounds/ceratopsian-xfce/ceratopsian-matte.png`. For the source archive, place the themes and wallpaper in the system directories first.

```sh
sudo cp -a themes/Ceratopsian-Dark /usr/share/themes/
sudo cp -a icons/Ceratopsian-Icons icons/Ceratopsian-Cursors /usr/share/icons/
sudo install -Dm644 wallpapers/ceratopsian-matte.png /usr/share/backgrounds/ceratopsian-xfce/ceratopsian-matte.png
```

In `/etc/lightdm/lightdm-gtk-greeter.conf`, set these values in the existing `[greeter]` section. They take effect the next time LightDM starts the greeter.

```ini
theme-name = Ceratopsian-Dark
icon-theme-name = Ceratopsian-Icons
cursor-theme-name = Ceratopsian-Cursors
background = /usr/share/backgrounds/ceratopsian-xfce/ceratopsian-matte.png
user-background = false
```

To restore the previous appearance, restore the greeter configuration backup.

## GRUB and Plymouth on Debian

The boot add-on contains the Debian 13 Ceratopsian Matte and Clean artwork. The installer requires GRUB, Plymouth and `initramfs-tools` on Debian-family systems. Run it from the root of this archive on a test system. [Boot add-on files](boot/)

```sh
bash extras/boot/install-boot-theme.sh --list
sudo bash extras/boot/install-boot-theme.sh --variant clean
```

The selection applies to both stages. Use `--variant clean` for the unbranded artwork or omit `--variant` for the Debian 13 edition. Use `--show-assets --variant clean` to find the two image files for a manual installation.

After installing the Debian package, the same script is at `/usr/share/ceratopsian-xfce/extras/boot/install-boot-theme.sh`.

The installer backs up the previous boot files to `/var/backups/ceratopsian-boot.*`. It regenerates the existing initramfs images and GRUB configuration, then checks the resulting files. The artwork appears at the next boot.

## Google Chrome

In **Settings → Appearance**, select **Use GTK theme** to pick up Ceratopsian from your desktop.
