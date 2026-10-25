"""Instala el runtime CPU oficial de Ollama, con verificación de SHA-256.

Solo Linux x86_64. No arranca procesos ni descarga modelos; los archivos quedan
fuera del checkout en /workspace/.cache/ollama. Windows usa el instalador oficial.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tarfile
import urllib.request

VERSION='0.40.11'
SHA256='7bedab90dd122661be78798e9f0edf37fccf0cccf2699d2c58ea1a3afdc04b6d'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/workspace/.cache/ollama'))
    args=parser.parse_args()
    if sys.platform!='linux' or platform.machine() not in ('x86_64','amd64'):
        raise SystemExit('Este helper es para Linux x86_64. Usa el instalador oficial en Windows.')
    import zstandard
    root=args.root.resolve()
    stamp=root/'runtime.json'
    expected={'version':VERSION,'archive_sha256':SHA256}
    if stamp.is_file() and json.loads(stamp.read_text())==expected and (root/'bin/ollama').is_file():
        print('Ollama CPU ya está preparado:',VERSION)
        return
    root.mkdir(parents=True,exist_ok=True)
    archive=root/f'ollama-linux-amd64-{VERSION}.tar.zst'
    if not archive.exists():
        temporary=archive.with_suffix('.partial')
        checksum=hashlib.sha256()
        url=f'https://github.com/ollama/ollama/releases/download/v{VERSION}/ollama-linux-amd64.tar.zst'
        print('Descargando runtime oficial (aprox. 1,5 GB)…',flush=True)
        with urllib.request.urlopen(url,timeout=60) as response,temporary.open('wb') as output:
            while chunk:=response.read(2*1024*1024):
                checksum.update(chunk)
                output.write(chunk)
        if checksum.hexdigest()!=SHA256:
            temporary.unlink()
            raise SystemExit('Checksum incorrecto; se descartó la descarga.')
        temporary.replace(archive)
    else:
        with archive.open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=SHA256:
                raise SystemExit('El archivo existente no pasó la verificación; no se usará.')
    with archive.open('rb') as source,zstandard.ZstdDecompressor().stream_reader(source) as stream:
        with tarfile.open(fileobj=stream,mode='r|') as tar:
            for member in tar:
                relative=Path(member.name.removeprefix('./'))
                if relative.is_absolute() or '..' in relative.parts: raise ValueError('Ruta inválida en el archivo')
                selected=str(relative)=='bin/ollama' or (str(relative).startswith('lib/ollama/') and len(relative.parts)==3)
                if not selected: continue  # omit CUDA/ROCm/MLX bundles: this machine uses CPU
                target=root/relative
                if not target.resolve().is_relative_to(root): raise ValueError('Destino fuera de la caché')
                target.parent.mkdir(parents=True,exist_ok=True)
                if member.issym():
                    resolved=(target.parent/member.linkname).resolve()
                    if not resolved.is_relative_to(root): raise ValueError('Enlace externo no permitido')
                    if target.is_symlink() or target.exists(): target.unlink()
                    target.symlink_to(member.linkname)
                elif member.isfile():
                    with tar.extractfile(member) as data,target.open('wb') as output:
                        while chunk:=data.read(2*1024*1024): output.write(chunk)
                    os.chmod(target,member.mode & 0o777)
    ctypes.CDLL(str(root/'lib/ollama/libggml-cpu-x64.so'))
    stamp.write_text(json.dumps(expected),encoding='utf-8')
    archive.unlink()  # keep the verified CPU runtime, not the 1.5 GB GPU download
    print('Ollama CPU preparado y bibliotecas verificadas:',VERSION)


if __name__=='__main__':
    main()
