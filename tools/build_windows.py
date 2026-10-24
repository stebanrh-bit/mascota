"""Genera una carpeta portable Mascota/Mascota.exe desde un equipo Windows."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != "win32":
        raise SystemExit("El ejecutable Windows debe compilarse en Windows, no en Linux.")
    root = Path(__file__).resolve().parents[1]
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", "Mascota", "--add-data", "mascota/qml:mascota/qml", "run_pet.py",
    ], cwd=root, check=True)


if __name__ == "__main__":
    main()
