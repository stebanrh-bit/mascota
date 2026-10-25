#!/usr/bin/env bash
# Servicio local para desarrollo cloud; no modifica HOME ni escucha en la red.
set -euo pipefail
cd "$(dirname "$0")/.."
if .venv/bin/python - <<'PY'
import json,urllib.request
try:
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:11434/api/tags',timeout=1) as response:
        assert isinstance(json.load(response).get('models'),list)
except Exception: raise SystemExit(1)
PY
then
    echo 'Ollama ya está activo en este equipo.'
    exit 0
fi
if ! test -x /workspace/.cache/ollama/bin/ollama; then
    echo 'Prepara el runtime con uv run --frozen --group cloud-ai python tools/setup_ollama.py' >&2
    exit 1
fi
mkdir -p .local
nohup env OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/workspace/.cache/ollama/models OLLAMA_NO_CLOUD=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 /workspace/.cache/ollama/bin/ollama serve </dev/null >/dev/null 2>&1 &
mascota_ollama_pid=$!
echo "$mascota_ollama_pid" > .local/ollama.pid
.venv/bin/python - <<'PY'
import json,time,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(40):
    try:
        with opener.open('http://127.0.0.1:11434/api/tags',timeout=.5) as response:
            assert isinstance(json.load(response).get('models'),list)
            print('Ollama listo en 127.0.0.1:11434')
            break
    except Exception: time.sleep(.2)
else:
    raise SystemExit('Ollama no arrancó. Comprueba que puede crear su configuración en la carpeta de usuario y que el puerto 11434 está libre.')
PY
