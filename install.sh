#!/usr/bin/env bash
set -euo pipefail
unset CDPATH
phase="Checking prerequisites"
trap 'printf "\nInstallation failed: %s (line %s). See the error above.\n" "$phase" "$LINENO" >&2' ERR
accent='' reset=''
if [[ -t 2 && ${TERM:-dumb} != dumb && -z ${NO_COLOR+x} ]]; then
    accent=$'\033[1;35m' reset=$'\033[0m'
fi
heading() {
    printf '\n%s== %s ==%s\n' "$accent" "$1" "$reset" >&2
}
step() {
    phase=$1
    heading "$phase"
}

SOURCE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TPOT_COMMIT=39d7f375253b446305d7941ad2f09d66a6968c96
TPOT_DIR="$HOME/tpotce"
UI_ONLY=false
if [[ ${1:-} == "--ui-only" && $# == 1 ]]; then
    UI_ONLY=true
elif [[ $# != 0 ]]; then
    echo "Usage: bash install.sh [--ui-only]" >&2
    exit 1
fi
heading "T-Pot Mobile"
if $UI_ONLY; then
    echo "UI update | T-Pot stays unchanged" >&2
else
    echo "Fresh installation | Raspberry Pi OS Lite" >&2
fi
if [[ $EUID == 0 ]]; then
    echo "Run as your Raspberry Pi login user, not root." >&2
    exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ ${VERSION_CODENAME:-} != trixie || $(dpkg --print-architecture) != arm64 ]]; then
    echo "Raspberry Pi OS Lite Trixie ARM64 is required. Bookworm migration is not supported." >&2
    exit 1
fi
if [[ ! -f "$SOURCE/qml/Main.qml" ]]; then
    echo "Run the installer from a complete checkout of this UI revision." >&2
    exit 1
fi
if [[ ! $TPOT_DIR =~ ^/[a-zA-Z0-9_./-]+$ ]]; then
    echo "The home path must not contain spaces or systemd/sed metacharacters." >&2
    exit 1
fi
if $UI_ONLY; then
    if [[ ! -f /etc/tpotmobile.ini ]]; then
        echo "--ui-only requires an existing installation of this Qt UI." >&2
        exit 1
    fi
elif [[ -e "$TPOT_DIR" ]]; then
    echo "$TPOT_DIR already exists. This fresh-install path will not overwrite T-Pot." >&2
    exit 1
fi
if id tpotui >/dev/null 2>&1; then
    ui_uid=$(id -u tpotui)
    if ((ui_uid == 0 || ui_uid >= 1000)) || [[ $(getent passwd tpotui | cut -d: -f6) != /var/lib/tpotmobile ]] \
        || [[ " $(id -nG tpotui) " == *" docker "* ]]; then
        echo "Existing tpotui account is not the expected isolated system account; review it before installation." >&2
        exit 1
    fi
fi
upstream_args=(-s -t m -b "$TPOT_COMMIT" -r https://github.com/telekom-security/tpotce)
secure_mode=false
if ! $UI_ONLY; then
    heading "Display"
    printf '  1) Waveshare 4.3-inch\n  2) Waveshare 8-inch\n' >&2
    read -r -p "Select display [1/2]: " choice
    case "$choice" in
        1) display=43; display_label="Waveshare 4.3-inch" ;;
        2) display=8; display_label="Waveshare 8-inch" ;;
        *) echo "Invalid display choice." >&2; exit 1 ;;
    esac
    heading "sudo after installation"
    printf '  1) Require a password (default)\n  2) Allow passwordless sudo\n' >&2
    read -r -p "Select sudo mode [1]: " choice
    case "$choice" in
        1|"") secure_mode=true ;;
        2) upstream_args+=(--sudo-nopasswd) ;;
        *) echo "Invalid sudo mode." >&2; exit 1 ;;
    esac
fi

password_file=
if $secure_mode; then
    if [[ $(LC_ALL=C passwd -S "$(id -un)" | awk '{print $2}') != P ]]; then
        echo "Secure sudo needs a login password. Set one with passwd before installing." >&2
        exit 1
    fi
fi
if $secure_mode || ! sudo -n -k true 2>/dev/null; then
    # The upstream installer accepts a private file with -B. Keep it in RAM.
    set +x
    password_file=$(mktemp /dev/shm/tpotmobile-password.XXXXXXXX)
    trap 'rm -f -- "$password_file"' EXIT
    trap 'exit 1' HUP INT TERM
    IFS= read -rs -p "Login password for sudo: " password
    printf '\n' >&2
    printf '%s\n' "$password" > "$password_file"
    unset password
    # The login user owns the password file and opens it before sudo starts.
    # shellcheck disable=SC2024
    sudo -k -S -p '' -v < "$password_file"
    upstream_args+=(-B "$password_file")
fi
heading "Review before starting"
if $UI_ONLY; then
    printf '  Update and restart the display UI and compositor only.\n  T-Pot configuration and images will not change.\n' >&2
else
    sudo_label="Passwordless"
    if $secure_mode; then sudo_label="Password required"; fi
    printf '  Display:   %s\n  sudo:      %s\n  T-Pot:     Mobile (%s)\n' "$display_label" "$sudo_label" "${TPOT_COMMIT:0:8}" >&2
fi
read -r -p "Start installation now? [y/N]: " answer
case "$answer" in
    y|Y) ;;
    *) echo "Installation cancelled."; exit 1 ;;
esac

# Keep command stdin available (notably for tee) even after sudo's cache expires.
sudo() {
    if [[ -n $password_file ]]; then
        command sudo -S -p '' -v < "$password_file" || return
    fi
    command sudo -n "$@"
}
exec </dev/null
export GIT_TERMINAL_PROMPT=0 DEBIAN_FRONTEND=noninteractive
step "Installing system packages"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get -o Dpkg::Options::=--force-confold install -y --no-install-recommends \
    git python3 python3-venv python3-pip python3-pyqt6 python3-pyqt6.qtquick \
    qt6-wayland qml6-module-qtquick qml6-module-qtquick-window \
    qml6-module-qtquick-controls qml6-module-qtquick-layouts \
    qml6-module-qtquick-templates qml6-module-qtquick-shapes libqt6svg6 qt6-svg-plugins qml6-module-qtqml-workerscript \
    qml6-module-qtqml-models weston seatd libgl1-mesa-dri \
    network-manager iproute2 sudo fonts-dejavu-core

if ! $UI_ONLY; then
    # Upstream's Ansible deb822_repository task imports debian.deb822 from system Python.
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-debian
    step "Configuring the display hardware"
    sudo python3 "$SOURCE/tools/configure.py" boot /boot/firmware/config.txt --display "$display"
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_spi 1
    step "Installing T-Pot Mobile and pulling images"
    git clone --no-checkout https://github.com/telekom-security/tpotce "$TPOT_DIR"
    git -C "$TPOT_DIR" checkout --detach "$TPOT_COMMIT"
    echo "T-Pot development baseline: $TPOT_COMMIT"
    (cd "$TPOT_DIR" && bash install.sh "${upstream_args[@]}")
    if [[ $(git -C "$TPOT_DIR" rev-parse HEAD) != "$TPOT_COMMIT" ]]; then
        echo "Upstream checkout changed unexpectedly; aborting integration." >&2
        exit 1
    fi
    # Keep the source fingerprint in the compose file generated by the installer.
    if ! grep -qx '# T-Pot: MOBILE' "$TPOT_DIR/docker-compose.yml"; then
        echo "Upstream installer did not generate the Mobile compose file." >&2
        exit 1
    fi
    (umask 077; python3 "$SOURCE/tools/configure.py" env "$TPOT_DIR/.env")
    # A pull here is intentional: bootstrap must verify ARM64 image availability.
    (cd "$TPOT_DIR" && sudo docker compose config --quiet && sudo docker compose pull)
else
    step "Stopping the display UI and compositor"
    sudo systemctl stop tpotdisplay.service tpotweston.service
fi

step "Installing the display UI"
if ! id tpotui >/dev/null 2>&1; then
    sudo useradd --system --user-group --home-dir /var/lib/tpotmobile --create-home --shell /usr/sbin/nologin tpotui
fi
for group in video render input i2c; do
    getent group "$group" >/dev/null || { echo "Required device group missing: $group" >&2; exit 1; }
done
sudo install -d -m 755 /opt/tpotmobile /usr/local/libexec
sudo install -m 644 "$SOURCE/display.py" "$SOURCE/requirements.txt" /opt/tpotmobile/
for directory in modules qml images flags; do
    sudo install -d -m 755 "/opt/tpotmobile/$directory"
    if [[ $directory == modules ]]; then
        sudo install -m 644 "$SOURCE"/modules/*.py /opt/tpotmobile/modules/
    else
        sudo cp -R "$SOURCE/$directory/." "/opt/tpotmobile/$directory/"
    fi
done
sudo chown -R root:root /opt/tpotmobile
sudo chmod -R a+rX,go-w /opt/tpotmobile
sudo python3 -m venv --system-site-packages /opt/tpotmobile/.venv
sudo /opt/tpotmobile/.venv/bin/pip --no-input install -r /opt/tpotmobile/requirements.txt
sudo install -m 755 "$SOURCE/tools/system_control.py" /usr/local/libexec/tpotmobile-control
sudo install -d -m 755 /opt/tpotmobile/tools
sudo install -m 755 "$SOURCE/tools/start-display.sh" "$SOURCE/tools/wait4net.sh" /opt/tpotmobile/tools/
sudo install -m 644 "$SOURCE/settings/tpotweston.service" "$SOURCE/settings/tpotdisplay.service" /etc/systemd/system/
sudo install -m 644 "$SOURCE/settings/weston.ini" /etc/tpotmobile-weston.ini
sudo install -m 440 "$SOURCE/settings/tpotmobile.sudoers" /etc/sudoers.d/tpotmobile
sudo visudo -cf /etc/sudoers.d/tpotmobile
if ! $UI_ONLY; then
    project=$(cd "$TPOT_DIR" && sudo docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')
    if [[ ! $project =~ ^[a-z0-9][a-z0-9_-]{0,63}$ ]]; then
        echo "Invalid effective compose project; cannot configure scoped container status." >&2
        exit 1
    fi
    printf '[tpot]\nproject=%s\n' "$project" | sudo tee /etc/tpotmobile.ini >/dev/null
    sudo chmod 644 /etc/tpotmobile.ini
    sed "s|@TPOT_DIR@|$TPOT_DIR|g" "$SOURCE/settings/tpot.service" | sudo tee /etc/systemd/system/tpot.service >/dev/null
fi
step "Configuring services"
sudo systemctl daemon-reload
sudo systemctl enable seatd.service tpotweston.service tpotdisplay.service
if $UI_ONLY; then
    sudo systemctl start tpotweston.service tpotdisplay.service
else
    sudo systemctl enable tpot.service
fi
step "Checking the runtime and recording versions"
sudo /opt/tpotmobile/.venv/bin/python3 -c 'from PyQt6.QtQuick import QQuickWindow; import elasticsearch'
dpkg-query -W python3-pyqt6 python3-pyqt6.qtquick qt6-wayland weston | sudo tee /var/lib/tpotmobile/runtime-versions.txt
if ! $UI_ONLY; then
    image_names=$(cd "$TPOT_DIR" && sudo docker compose config --images)
    if [[ -z "$image_names" ]]; then
        echo "Mobile compose returned no images; cannot record bootstrap versions." >&2
        exit 1
    fi
    mapfile -t images <<< "$image_names"
    sudo docker image inspect "${images[@]}" | python3 -c \
        'import json,sys; print(json.dumps([{key: image[key] for key in ("Id", "RepoTags", "RepoDigests", "Architecture")} for image in json.load(sys.stdin)], indent=2))' \
        | sudo tee /var/lib/tpotmobile/image-versions.json
fi
heading "Installation complete"
if $UI_ONLY; then
    echo "Display UI and compositor restarted. Check the display; no reboot is needed."
else
    echo "Reboot when ready, then check the display and UPS. T-Pot pulls missing images only."
fi
