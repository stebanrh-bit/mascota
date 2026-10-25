"""python -m mascota. Las capturas usan el mismo renderizador 3D que la app."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QMetaObject, QObject, QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQuick import QQuickView, QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle

from .controller import PetController
from .chat_window import ChatWindow
from .domain import CHARACTERS, Preferences
from .geometry import register_geometry
from .rendering import logical_pixel
from .memory_store import MemoryStore


def main():
    parser = argparse.ArgumentParser(description="Tu compañero de escritorio 3D")
    parser.add_argument("--character", choices=CHARACTERS)
    parser.add_argument("--settings", type=Path, help="Ruta alternativa de preferencias")
    parser.add_argument("--capture", type=Path, help="Captura un fotograma 3D y sale")
    parser.add_argument("--chat-capture", type=Path, help="Captura la ventana de conversación y sale")
    parser.add_argument("--smoke-test", action="store_true", help="Ejercita la interfaz real y sale")
    parser.add_argument("--pose", choices=("idle", "sleeping", "roaring", "jumping"), default="idle", help="Acción de la captura")
    args = parser.parse_args()

    # Python-defined meshes and capture callbacks share the GUI thread.
    # Basic retains the GPU/RHI renderer and avoids threaded texture races.
    os.environ.setdefault("QSG_RENDER_LOOP", "basic")
    QQuickWindow.setDefaultAlphaBuffer(True)
    QQuickStyle.setStyle("Basic")
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        QQuickWindow.setGraphicsApi(QSGRendererInterface.OpenGL)
    surface = QSurfaceFormat()
    surface.setAlphaBufferSize(8)
    surface.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(surface)
    app = QGuiApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("Mascota")
    app.setApplicationName("Desktop AI Pet")
    failed = [False]
    previous_exception_hook = sys.excepthook

    def callback_error(kind, error, traceback):
        failed[0] = True
        previous_exception_hook(kind, error, traceback)
        QTimer.singleShot(0, lambda: app.exit(1))

    sys.excepthook = callback_error
    register_geometry()

    automated = bool(args.capture or args.chat_capture or args.smoke_test)
    temporary_settings = tempfile.TemporaryDirectory(prefix="mascota-test-") if automated and not args.settings else None
    default_dir = Path(temporary_settings.name) if temporary_settings else Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    path = args.settings or default_dir / "preferences.json"
    preferences = Preferences(path)
    if args.character:
        preferences.character = args.character
    if automated:
        preferences.roaming = False
    controller = PetController(preferences)
    view = QQuickView()
    qml_quit_seen = [False]
    view.engine().quit.connect(lambda: qml_quit_seen.__setitem__(0, True))
    view.engine().quit.connect(app.quit)
    view.setTitle("Mascota · tu compañero 3D")
    view.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    view.setColor(Qt.transparent)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.rootContext().setContextProperty("pet", controller)
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if view.status() == QQuickView.Error or failed[0]:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        sys.excepthook = previous_exception_hook
        return 1
    view.resize(460, 520)
    controller.attach_window(view)
    view.show()
    controller.centerOnScreen()
    assistant = ChatWindow(controller, app)
    def shutdown():
        controller.shutdown()
        assistant.shutdown()
        view.close()

    app.aboutToQuit.connect(shutdown)
    view.visibilityChanged.connect(lambda _: app.quit() if not view.isVisible() else None)
    if args.chat_capture:
        if not assistant.open():
            return 1
    poses = {"sleeping": controller.toggleSleep, "roaring": controller.roar, "jumping": controller.jump}
    if args.pose != "idle" and automated:
        QTimer.singleShot(1100 if args.pose != "jumping" else 1450, poses[args.pose])

    # Do not claim readiness if QML loads but rendering fails or is empty.
    view.sceneGraphError.connect(lambda _error, message: (print(message, file=sys.stderr), failed.__setitem__(0, True), app.exit(1)))
    smoke_report = {}

    def smoke_exit():
        smoke_report['pending_chat_at_exit'] = assistant.chat.busy
        item = view.rootObject().findChild(QObject, 'exitAction')
        if item is None or not QMetaObject.invokeMethod(item, 'triggered'):
            failed[0] = True
            app.exit(1)

    def capture():
        image = view.grabWindow()
        if image.isNull() or image.deviceIndependentSize().width() < 400:
            print("No se pudo renderizar la escena 3D", file=sys.stderr)
            app.exit(1)
            return
        if args.capture:
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(args.capture)):
                app.exit(1)
                return
        if args.chat_capture:
            chat_image = assistant.view.grabWindow()
            args.chat_capture.parent.mkdir(parents=True, exist_ok=True)
            if chat_image.isNull() or not chat_image.save(str(args.chat_capture)):
                print('No se pudo renderizar la conversación', file=sys.stderr)
                app.exit(1)
                return
        if args.smoke_test:
            try:
                # Rendered pixels must contain geometry above the interface labels.
                nonempty = sum(logical_pixel(image, x, y).alpha() > 20 for x in range(30, 430, 8) for y in range(30, 350, 8))
                assert nonempty > 180, f"Escena vacía: {nonempty} píxeles"
                assert logical_pixel(image, 190, 410).alpha() > 100, "Nombre no visible"
                assert controller.characterId == "sombra"
                root = view.rootObject()
                assert root.findChild(object, "petTouch") is not None
                controller.selectCharacter("brote")
                assert controller.bodyColor == CHARACTERS["brote"].body
                controller.selectCharacter("nimbo")
                assert controller.characterKind == "spirit"
                controller.toggleSleep()
                assert controller.petState == "sleeping"
                controller.pet()
                assert controller.petState == "happy"
                controller.fly()
                assert controller.petState == "flying"
                controller.jump()
                assert controller.petState == "jumping"
                controller.roar()
                assert controller.petState == "roaring"
                controller.setDragging(True)
                controller.moveBy(-50, -30)
                controller.setDragging(False)
                assert controller.petState == "idle"
                controller.selectCharacter("sombra")
                original_name = controller.characterName
                assert controller.renameCharacter("Sombra de prueba")
                assert Preferences(path).names["sombra"] == "Sombra de prueba"
                controller.renameCharacter(original_name)
                assert Preferences(path).character == "sombra"
                assert assistant.open(check_connection=False)
                assert assistant.view.status() == QQuickView.Ready
                assert assistant.view.rootObject().findChild(object, 'sendChat') is not None
                assert assistant.chat.memory.available
                assert assistant.view.rootObject().findChild(object, 'openMemories') is not None
                # An isolated database also checks SQLite in the frozen executable.
                with tempfile.TemporaryDirectory(prefix='mascota-memory-check-') as memory_dir:
                    memory_path = Path(memory_dir) / 'memories.sqlite3'
                    saved = MemoryStore(memory_path)
                    key = saved.add('sombra', 'Mi color favorito es el turquesa.')
                    restored = MemoryStore(memory_path)
                    assert restored.snapshot('sombra')[2][0]['body'] == 'Mi color favorito es el turquesa.'
                    assert restored.snapshot('nimbo')[2] == []
                    restored.set_enabled('sombra', False)
                    assert not saved.snapshot('sombra')[0]
                    restored.remove('sombra', key)
                    assert saved.snapshot('sombra')[2] == []
                assistant.close()
                assert view.isVisible() and not controller._chat_open
                smoke_report.update({"rendered_samples": nonempty, "characters": 3, "checks": ["QML", "3D render", "character switching", "sleep", "pet", "fly", "jump", "flame", "drag", "names", "preferences", "chat window", "local memories"]})
                assert assistant.open()
                QTimer.singleShot(100, smoke_exit)
            except Exception as error:
                print(f"Smoke test falló: {error}", file=sys.stderr)
                app.exit(1)
                return
            return  # Only the menu's QML quit signal may complete the smoke test.
        app.quit()

    def startup_timeout():
        failed[0] = True
        print('La comprobación de arranque o salida excedió el tiempo disponible.', file=sys.stderr)
        app.exit(1)

    if automated:
        QTimer.singleShot(1800, capture)
        QTimer.singleShot(15000, startup_timeout)
    result = app.exec()
    if args.smoke_test:
        closed = not view.isVisible() and not assistant.view.isVisible() and not assistant.chat.busy
        success = bool(smoke_report) and result == 0 and not failed[0] and qml_quit_seen[0] and closed
        smoke_report.update(ok=success, windows_closed=closed)
        if success:
            smoke_report['checks'].append('menu exit')
        else:
            failed[0] = True
        print(json.dumps(smoke_report))
    # Destroy QML bindings before their Python context disappears.
    view.setSource(QUrl())
    if temporary_settings:
        temporary_settings.cleanup()
    sys.excepthook = previous_exception_hook
    return 1 if failed[0] else result


if __name__ == "__main__":
    raise SystemExit(main())
