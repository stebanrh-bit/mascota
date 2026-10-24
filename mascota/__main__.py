"""python -m mascota. Las capturas usan el mismo renderizador 3D que la app."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickView, QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle

from .controller import PetController
from .domain import CHARACTERS, Preferences
from .geometry import WingGeometry


def main():
    parser = argparse.ArgumentParser(description="Tu compañero de escritorio 3D")
    parser.add_argument("--character", choices=CHARACTERS)
    parser.add_argument("--settings", type=Path, help="Ruta alternativa de preferencias")
    parser.add_argument("--capture", type=Path, help="Captura un fotograma 3D y sale")
    parser.add_argument("--smoke-test", action="store_true", help="Ejercita la interfaz real y sale")
    args = parser.parse_args()

    QQuickWindow.setDefaultAlphaBuffer(True)
    QQuickStyle.setStyle("Basic")
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        QQuickWindow.setGraphicsApi(QSGRendererInterface.OpenGL)
    surface = QSurfaceFormat()
    surface.setAlphaBufferSize(8)
    surface.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(surface)
    app = QGuiApplication(sys.argv[:1])
    app.setOrganizationName("Mascota")
    app.setApplicationName("Desktop AI Pet")
    qmlRegisterType(WingGeometry, "Mascota", 1, 0, "WingGeometry")

    temporary_settings = tempfile.TemporaryDirectory(prefix="mascota-test-") if (args.capture or args.smoke_test) and not args.settings else None
    default_dir = Path(temporary_settings.name) if temporary_settings else Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    path = args.settings or default_dir / "preferences.json"
    preferences = Preferences(path)
    if args.character:
        preferences.character = args.character
    if args.capture or args.smoke_test:
        preferences.roaming = False
    controller = PetController(preferences)
    view = QQuickView()
    view.setTitle("Mascota · tu compañero 3D")
    view.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    view.setColor(Qt.transparent)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.rootContext().setContextProperty("pet", controller)
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if view.status() == QQuickView.Error:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        return 1
    view.resize(460, 520)
    controller.attach_window(view)
    view.show()
    controller.centerOnScreen()

    # Do not claim readiness if QML loads but rendering fails or is empty.
    failed = [False]
    view.sceneGraphError.connect(lambda _error, message: (print(message, file=sys.stderr), failed.__setitem__(0, True), app.exit(1)))

    def capture():
        image = view.grabWindow()
        if image.isNull() or image.width() < 400:
            print("No se pudo renderizar la escena 3D", file=sys.stderr)
            app.exit(1)
            return
        if args.capture:
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(args.capture)):
                app.exit(1)
                return
        if args.smoke_test:
            try:
                # Rendered pixels must contain geometry above the interface labels.
                nonempty = sum(image.pixelColor(x, y).alpha() > 20 for x in range(30, 430, 8) for y in range(30, 350, 8))
                assert nonempty > 180, f"Escena vacía: {nonempty} píxeles"
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
                controller.setDragging(True)
                controller.moveBy(-50, -30)
                controller.setDragging(False)
                assert controller.petState == "idle"
                controller.selectCharacter("sombra")
                assert Preferences(path).character == "sombra"
                print(json.dumps({"ok": True, "rendered_samples": nonempty, "characters": 3, "checks": ["QML", "3D render", "character switching", "sleep", "pet", "fly", "drag", "preferences"]}))
            except Exception as error:
                print(f"Smoke test falló: {error}", file=sys.stderr)
                app.exit(1)
                return
        app.quit()

    if args.capture or args.smoke_test:
        QTimer.singleShot(1800, capture)
        QTimer.singleShot(15000, lambda: app.exit(1))
    result = app.exec()
    # Destroy QML bindings before their Python context disappears.
    view.setSource(QUrl())
    if temporary_settings:
        temporary_settings.cleanup()
    return 1 if failed[0] else result


if __name__ == "__main__":
    raise SystemExit(main())
