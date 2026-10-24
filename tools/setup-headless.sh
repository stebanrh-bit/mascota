#!/usr/bin/env bash
# Requisitos gráficos para las pruebas de Codex; no modifica el sistema.
set -euo pipefail
if command -v Xvfb >/dev/null 2>&1 || test -x /workspace/.cache/headless/usr/bin/Xvfb; then
    exit 0
fi
. /etc/os-release
if [[ "${ID:-}" != debian || "${VERSION_CODENAME:-}" != trixie ]]; then
    echo 'Instala Xvfb con el gestor de paquetes del sistema para ejecutar las pruebas gráficas.' >&2
    exit 1
fi
mascota_cache=/workspace/.cache/debian
mkdir -p "$mascota_cache/lists/partial" "$mascota_cache/archives/partial" "$mascota_cache/packages" "$mascota_cache/empty" /workspace/.cache/headless
cat > "$mascota_cache/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://security.debian.org/debian-security trixie-security main
SOURCES
cat > "$mascota_cache/apt.conf" <<CONFIG
Dir::Etc::parts "$mascota_cache/empty";
Dir::Etc::main "-";
Dir::Etc::sourcelist "$mascota_cache/sources.list";
Dir::Etc::sourceparts "$mascota_cache/empty";
Dir::State::lists "$mascota_cache/lists";
Dir::Cache::archives "$mascota_cache/archives";
Debug::NoLocking "true";
APT::Sandbox::User "$(id -un)";
CONFIG
export APT_CONFIG="$mascota_cache/apt.conf"
# apt verifica firmas del archivo Release y hashes de paquetes antes de extraer.
apt-get update
cd "$mascota_cache/packages"
apt-get download xvfb
for package in xvfb_*.deb; do
    dpkg-deb -x "$package" /workspace/.cache/headless
done
