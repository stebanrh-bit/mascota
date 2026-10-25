# Mascota · Desktop AI Pet 🐉

Un pequeño compañero **3D real** para el escritorio: **Sombra**, un dragón bebé de cuerpo negro, alas azules y dos pequeños colmillos. La versión **0.3** incorpora conversación con IA local mediante Ollama. No requiere claves de API para el modelo recomendado; una vez descargado, puede responder sin conexión a Internet.

El personaje del prototipo está construido con geometría 3D y articulaciones animadas: alas suaves, cuernos y cola curvos, escamas en la frente, parpadeo y ojos que siguen el cursor. Las imágenes de `assets/` son referencias de diseño: el modelo actual es más sencillo y todavía no reproduce sus escamas detalladas.

![Captura real del prototipo Sombra](docs/prototipo-sombra.png)

[Ver la llamarada azul del modelo 3D](docs/prototipo-llamarada.png).

[Ver una conversación real con la IA local](docs/conversacion-local.png).

## Probar en Windows 11

1. Instala **Python 3.12 de 64 bits** desde [python.org](https://www.python.org/downloads/windows/), incluyendo el lanzador `py`.
2. Descarga este repositorio desde **Code → Download ZIP** y **extrae la carpeta completa**.
3. Haz doble clic en **`iniciar.cmd`**. La primera vez descargará las dependencias; las siguientes arranca directamente.

La mascota aparece sobre el escritorio, con fondo transparente y sin bordes. Para cerrarla, usa **clic derecho → Salir** o **Esc**. No hace falta abrir un navegador para usarla.

### Controles

| Acción | Cómo hacerlo |
| --- | --- |
| Acariciar | Clic en la mascota o botón **Acariciar** |
| Moverla | Arrastrar con el botón izquierdo |
| Girar el modelo 3D | Rueda del ratón sobre el personaje |
| Dormir / despertar | Botón **Dormir** / **Despertar** |
| Cambiar de personaje | Botón **Personajes** o clic derecho |
| Volar | Clic derecho → **Volar un ratito** |
| Saltar | Clic derecho → **Dar un salto** |
| Llamarada / magia | Clic derecho → **Lanzar llama azul** / **Hacer magia** |
| Ponerle un nombre | Clic derecho → **Cambiar su nombre** |
| Conversar con IA | Botón **Hablar** |
| Activar / desactivar paseos | Clic derecho → **Pasear por el escritorio** |
| Recuperar la posición | Clic derecho → **Volver al centro** |

Incluye **Sombra** (dragón negro y azul), **Brote** (dragón verde) y **Nimbo** (espíritu flotante). Puedes cambiar sin reiniciar la aplicación. Cada personaje conserva su propio nombre, de hasta 24 caracteres. Los nombres, la selección y la preferencia de paseos se guardan localmente en la carpeta de configuración de tu usuario. La llamarada es una animación visual, todavía sin sonido.

## Conversar con tu mascota

1. Instala y abre [Ollama para Windows](https://ollama.com/download/windows).
2. En Mascota, pulsa **Hablar → Configurar**.
3. Deja el modelo **`qwen2.5:0.5b`** y pulsa **Guardar y comprobar**.
4. Pulsa **Descargar modelo** y espera a que aparezca **Listo para conversar**. La descarga es de unos 400 MB y Ollama verifica sus archivos.
5. Pulsa **Volver**, escribe tu mensaje y usa **Enviar** o **Enter**. **Shift+Enter** añade una línea; **Detener** cancela una respuesta.

El ejecutable de Mascota y Ollama son instalaciones separadas. Ollama debe estar activo en tu equipo para generar respuestas. También puedes elegir otro modelo local instalado desde Configurar. La conexión avanzada admite exclusivamente direcciones de este equipo, sin claves ni contraseñas.

Las respuestas aparecen progresivamente y cada personaje mantiene su propia conversación durante la sesión. **Vaciar** borra la conversación del personaje actual; cerrar la aplicación termina el historial. Esta aplicación guarda la configuración, pero no el texto de los mensajes en disco. Cambiar de personaje o cerrar el chat cancela una respuesta pendiente y la mascota sigue abierta.

`qwen2.5:0.5b` es una opción ligera; su calidad es limitada y sus respuestas pueden contener errores. La ventana de conversación no ejecuta acciones sobre archivos ni crea recordatorios.

## Ejecutable portable para Windows

En GitHub, abre **Actions → Crear Mascota para Windows**. Cada cambio del programa lanza una compilación; también puedes elegir **Run workflow**. Si la ejecución termina correctamente, descarga **Mascota-Windows** desde sus artefactos, extrae **todo** el ZIP y abre `Mascota.exe`. Conserva `Mascota.exe` junto a la carpeta `_internal`.

Ese paquete no requiere instalar Python. Es una carpeta portable, aún no un instalador firmado. El flujo comprueba las pruebas, el renderizado y que el ejecutable empaquetado pueda abrir el personaje y la conversación antes de ofrecer el artefacto.

Para generarlo manualmente **en Windows**:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pyinstaller==6.16.0
.venv\Scripts\python tools/build_windows.py
```

## Desarrollo y pruebas

Python 3.12, PySide6 / Qt Quick 3D 6.9.3. Las dependencias de desarrollo están fijadas en `uv.lock`.

```bash
uv sync --frozen
uv run --frozen python -m mascota
uv run --frozen python -m pytest -q
```

Para probar sin una pantalla física en el entorno cloud Debian:

```bash
bash tools/setup-cloud.sh
.venv/bin/python tools/headless.py .venv/bin/python -m pytest -q
.venv/bin/python tools/headless.py .venv/bin/python -m mascota --smoke-test --capture .local/captura.png
.venv/bin/python tools/headless.py .venv/bin/python -m mascota --pose roaring --capture .local/llamarada.png
```

`tools/headless.py` crea una pantalla Xvfb solo durante el comando, usa Mesa/OpenGL y la cierra al terminar. No expone puertos de red. `setup-headless.sh` descarga Xvfb desde los repositorios Debian verificados y lo extrae en `/workspace/.cache`, sin instalar paquetes en el sistema. El archivo de dependencias y el código no se modifican durante el setup.

Las pruebas comprueban renderizado 3D, controles, nombres, geometría y el contrato HTTP de Ollama contra un servidor local de prueba: fragmentos UTF-8, cancelación, tiempos de espera, errores, descargas y separación de conversaciones. En Linux sin pantalla se omiten las pruebas que necesitan Qt GUI; usa `headless.py` para ejecutar la suite completa. Esas pruebas de contrato no generan respuestas de IA.

### Validar la IA real en el entorno cloud

Además de la suite, la conversación se ha comprobado con Ollama CPU **0.40.11** y el modelo real **qwen2.5:0.5b**. La captura de `docs/conversacion-local.png` corresponde a esa inferencia.

Para reproducirla en Linux x86_64:

```bash
uv run --frozen --group cloud-ai python tools/setup_ollama.py
bash tools/start-ollama.sh
/workspace/.cache/ollama/bin/ollama pull qwen2.5:0.5b
.venv/bin/python tools/headless.py .venv/bin/python -m mascota.check_ai --capture .local/chat-real.png
```

El helper verifica el SHA-256 del archivo oficial antes de extraer el runtime CPU a `/workspace/.cache/ollama`. La primera instalación descarga el archivo Linux oficial de unos 1,5 GB; conserva solo los componentes CPU y elimina el archivo comprimido después de verificarlo. Los modelos se conservan también en la caché; los procesos deben arrancarse de nuevo después de restaurar el entorno. Ollama crea su propia configuración local en la carpeta normal de usuario, sin cambiar `HOME`.

La preparación del modelo necesita acceso a `registry.ollama.ai` y `dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com`. El runtime se descarga desde GitHub. `mascota.check_ai` exige una respuesta completada y no vacía del servicio real y devuelve `ok=true`; no sustituye el modelo con respuestas prefijadas.

## Alcance de esta versión

- Animación procedural de respiración, parpadeo, mirada, patas, cabeza, cola y alas; sueño, caricias, saltos, llamarada y vuelo corto.
- Ventana transparente sobre el escritorio y paseos dentro del área útil del monitor actual.
- Tres personajes, nombres y preferencias locales.
- Conversación por personaje con Ollama, respuestas progresivas, cancelación y preparación del modelo desde la interfaz.
- Preparación de paquete Windows con PyInstaller.

La integración con el escritorio y las transparencias de Windows deben comprobarse también en un equipo Windows 11 real. La pantalla virtual de Linux no valida ese comportamiento específico. La inferencia real se ha probado en Linux; el flujo Windows prueba la interfaz y el protocolo con un servidor de prueba. Todavía no incluye voz, recordatorios, un modelo artístico detallado ni detección para sentarse sobre otras ventanas.
