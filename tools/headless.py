"""Ejecuta un comando en una pantalla X virtual con OpenGL de Mesa.

Uso: python tools/headless.py .venv/bin/python -m mascota --smoke-test ...
No abre un servidor de red y siempre cierra la pantalla que ha creado.
"""
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile


def main():
    binary = shutil.which("Xvfb")
    if not binary:
        candidate = Path("/workspace/.cache/headless/usr/bin/Xvfb")
        if candidate.is_file():
            binary = str(candidate)
    if not binary:
        print("Instala Xvfb o ejecuta bash tools/setup-headless.sh", file=sys.stderr)
        return 1
    if len(sys.argv) < 2:
        print("Uso: python tools/headless.py COMANDO [ARGUMENTOS]", file=sys.stderr)
        return 2
    with tempfile.TemporaryFile() as log:
        server = subprocess.Popen([binary, "-displayfd", "1", "-screen", "0", "1280x900x24", "-nolisten", "tcp"], stdout=subprocess.PIPE, stderr=log)
        try:
            readable, _, _ = select.select([server.stdout], [], [], 10)
            display = server.stdout.readline().decode().strip() if readable else ""
            if not display.isdecimal():
                log.seek(0)
                print(log.read().decode(errors="replace"), file=sys.stderr)
                return 1
            environment = os.environ.copy()
            environment.update(DISPLAY=f":{display}", QT_QPA_PLATFORM="xcb", QSG_RHI_BACKEND="opengl", LIBGL_ALWAYS_SOFTWARE="1", LP_NUM_THREADS="2")
            environment.setdefault("XDG_CACHE_HOME", "/workspace/.cache" if Path("/workspace").is_dir() else str(Path.home() / ".cache"))
            return subprocess.run(sys.argv[1:], env=environment).returncode
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    raise SystemExit(main())
