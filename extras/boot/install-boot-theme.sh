#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
wallpapers="$(dirname -- "$(dirname -- "$package")")/wallpaper-variants"
variant=default
show_assets=false

while (( $# )); do
    case "$1" in
        --variant)
            (( $# >= 2 )) || { printf 'Missing wallpaper name after --variant\n' >&2; exit 2; }
            variant=$2
            shift
            ;;
        --list)
            printf '%s\n' default
            for image in "$package"/variants/*.png; do
                [[ -f "$image" ]] || continue
                name=${image##*/}
                [[ -f "$wallpapers/$name" ]] && printf '%s\n' "${name%.png}"
            done
            exit 0
            ;;
        --show-assets) show_assets=true ;;
        --help|-h)
            printf 'Usage: bash %s [--variant NAME] [--show-assets]\n       bash %s --list\n' "${0##*/}" "${0##*/}"
            exit 0
            ;;
        *) printf 'Unknown option %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

if [[ "$variant" == default ]]; then
    grub_background="$package/grub-background.png"
    plymouth_background="$package/plymouth/wallpaper.png"
elif [[ "$variant" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    grub_background="$package/variants/$variant.png"
    plymouth_background="$wallpapers/$variant.png"
else
    printf 'Invalid wallpaper name %s\n' "$variant" >&2
    exit 2
fi
if [[ ! -s "$grub_background" || ! -s "$plymouth_background" ]]; then
    printf 'Wallpaper %s is unavailable. Use --list to see the bundled variants.\n' "$variant" >&2
    exit 2
fi
if "$show_assets"; then
    printf 'GRUB %s\nPlymouth %s\n' "$grub_background" "$plymouth_background"
    exit 0
fi

if (( EUID != 0 )); then
    printf 'Запустите этот файл через sudo в обычном терминале.\n' >&2
    exit 1
fi

theme_name=ceratopsian-matte-desktop
theme_dir="/usr/share/plymouth/themes/$theme_name"
dropin=/etc/default/grub.d/99-ceratopsian-wallpaper.cfg
grub_image=/boot/grub/ceratopsian-matte.png
grub_cfg=/boot/grub/grub.cfg
theme_files=(
    "$theme_name.plymouth"
    "$theme_name.script"
    password_dot.png
    password_field.png
)

for tool in plymouth-set-default-theme update-initramfs lsinitramfs grub-script-check update-grub linux-version; do
    command -v "$tool" >/dev/null
done
sh -n "$package/99-ceratopsian-wallpaper.cfg"
for file in "${theme_files[@]}"; do
    test -s "$package/plymouth/$file"
done

kernels=()
while IFS= read -r release; do
    if [[ -f "/boot/initrd.img-$release" ]]; then
        kernels+=("$release")
    fi
done < <(linux-version list)
if (( ${#kernels[@]} == 0 )); then
    printf 'В /boot не нашлось установленных initramfs. Параметры загрузки ещё не изменены.\n' >&2
    exit 1
fi
grub-script-check "$grub_cfg"

targets=(
    "$grub_cfg" "$grub_image" "$dropin"
    "$theme_dir/wallpaper.png"
    /etc/plymouth/plymouthd.conf /usr/share/plymouth/themes/default.plymouth
)
for release in "${kernels[@]}"; do
    targets+=("/boot/initrd.img-$release" "/boot/initrd.img-$release.bak")
done
for file in "${theme_files[@]}"; do
    targets+=("$theme_dir/$file")
done

backup=$(mktemp -d /var/backups/ceratopsian-boot.XXXXXXXX)
for target in "${targets[@]}"; do
    if [[ -e "$target" || -L "$target" ]]; then
        (cd / && cp -a --reflink=auto --parents -- "${target#/}" "$backup")
    fi
done
printf 'Резервная копия сохранена в %s\n' "$backup"

restore_on_error() {
    local code=$? target saved temp restore_failed=0
    trap - EXIT
    if (( code == 0 )); then
        return
    fi
    set +e
    for target in "${targets[@]}"; do
        saved="$backup$target"
        if [[ -e "$saved" || -L "$saved" ]]; then
            temp=$(mktemp -- "${target}.restore.XXXXXXXX") &&
                cp -aT --remove-destination -- "$saved" "$temp" &&
                mv -fT -- "$temp" "$target" || restore_failed=1
        else
            rm -f -- "$target" || restore_failed=1
        fi
    done
    if (( restore_failed )); then
        printf 'Установка прервана, часть файлов нужно восстановить из %s\n' "$backup" >&2
    else
        printf 'Установка прервана, прежние файлы восстановлены из %s\n' "$backup" >&2
    fi
    exit "$code"
}
trap restore_on_error EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

install -d -m 0755 "$theme_dir" /etc/default/grub.d
for file in "${theme_files[@]}"; do
    install -m 0644 -- "$package/plymouth/$file" "$theme_dir/$file"
done
install -m 0644 -- "$grub_background" "$grub_image"
install -m 0644 -- "$plymouth_background" "$theme_dir/wallpaper.png"
install -m 0644 -- "$package/99-ceratopsian-wallpaper.cfg" "$dropin"
plymouth-set-default-theme "$theme_name"
test "$(plymouth-set-default-theme)" = "$theme_name"

for release in "${kernels[@]}"; do
    update-initramfs -u -k "$release"
    lsinitramfs "/boot/initrd.img-$release" |
        awk -v dir="${theme_dir#/}" -v name="$theme_name" '
            index($0, dir "/wallpaper.png") {image = 1}
            index($0, dir "/" name ".script") {script = 1}
            END {exit !(image && script)}
        '
done

update-grub
grub-script-check "$grub_cfg"
grep -Eq '^[[:space:]]*(if[[:space:]]+)?background_image[[:space:]].*ceratopsian-matte\.png' "$grub_cfg"
awk -v image="vmlinuz-$(uname -r)" '
    $1 ~ /^linux(efi)?$/ && index($2, image) && $0 ~ /[[:space:]]splash([[:space:]]|$)/ {found = 1}
    END {exit !found}
' "$grub_cfg"

printf 'Тема GRUB и заставка Plymouth установлены. Они появятся при следующей загрузке.\n'
