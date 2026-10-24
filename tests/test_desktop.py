"""Pruebas con el renderizador y eventos de ratón reales de Qt."""
import os
from pathlib import Path
import sys
import time

import pytest

os.environ.setdefault("QSG_RENDER_LOOP", "basic")
pytestmark = pytest.mark.skipif(sys.platform == "linux" and not os.environ.get("DISPLAY"), reason="Usa tools/headless.py para verificar la interfaz 3D")

from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickItem, QQuickView, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from mascota.controller import PetController
from mascota.domain import Preferences
from mascota.geometry import WingGeometry


@pytest.fixture(scope="module")
def app():
    QQuickWindow.setDefaultAlphaBuffer(True)
    QQuickStyle.setStyle("Basic")
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    application = QGuiApplication.instance() or QGuiApplication([])
    qmlRegisterType(WingGeometry, "Mascota", 1, 0, "WingGeometry")
    yield application


@pytest.fixture
def desktop(app, tmp_path):
    settings = Preferences(tmp_path / "preferences.json")
    settings.roaming = False
    controller = PetController(settings)
    view = QQuickView()
    view.setColor(Qt.transparent)
    view.setFlags(Qt.FramelessWindowHint | Qt.Tool)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.rootContext().setContextProperty("pet", controller)
    source = Path(__file__).parents[1] / "mascota" / "qml" / "Main.qml"
    view.setSource(QUrl.fromLocalFile(str(source)))
    assert view.status() == QQuickView.Ready, [error.toString() for error in view.errors()]
    view.resize(460, 520)
    controller.attach_window(view)
    view.show()
    controller.centerOnScreen()
    QTest.qWait(800)
    yield view, controller
    controller._timer.stop()
    controller._status_timer.stop()
    view.setSource(QUrl())
    view.close()
    view.deleteLater()
    app.processEvents()


def click_item(view, name):
    def find_visual(parent):
        if parent.objectName() == name:
            return parent
        for child in parent.childItems():
            found = find_visual(child)
            if found is not None:
                return found
        return None
    item = find_visual(view.contentItem())
    assert item is not None, name
    point = item.mapToScene(QPointF(item.width()/2, item.height()/2)).toPoint()
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, point)
    QTest.qWait(150)


def test_real_3d_render_and_character_selection_via_menu(desktop):
    view, controller = desktop
    first = view.grabWindow()
    assert not first.isNull()
    geometry_pixels = sum(first.pixelColor(x,y).alpha() > 20 for x in range(60,400,8) for y in range(30,340,8))
    assert geometry_pixels > 180
    # The 3D viewport must not paint over the companion's name or controls.
    assert first.pixelColor(190,410).alpha() > 100
    assert any(first.pixelColor(x,y).red() > 150 for x in range(195,270) for y in range(401,421))
    # Camera rotation must change rendered geometry rather than a static picture.
    view.rootObject().setProperty("orbit", 30)
    QTest.qWait(150)
    assert first != view.grabWindow()
    click_item(view, "action2")
    assert controller._menu_open
    click_item(view, "chooseNimbo")
    assert controller.characterId == "nimbo"
    assert controller.characterKind == "spirit"
    assert not controller._menu_open
    assert Preferences(controller.preferences.path).character == "nimbo"
    assert first != view.grabWindow()
    click_item(view, "action2")
    click_item(view, "chooseBrote")
    assert controller.characterId == "brote"


def test_sleep_pet_and_drag_via_mouse(desktop):
    view, controller = desktop
    click_item(view, "action1")
    assert controller.petState == "sleeping"
    click_item(view, "action0")
    assert controller.petState == "happy"
    initial = view.position()
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, QPoint(220,170))
    QTest.mouseMove(view, QPoint(255,140), 40)
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(255,140))
    QTest.qWait(100)
    assert view.position() != initial
    assert controller.petState == "idle"
    assert not controller._dragging


def test_flight_can_be_interrupted_and_walk_stays_on_screen(desktop):
    view, controller = desktop
    original_y = view.y()
    controller.fly()
    QTest.qWait(350)
    assert view.y() < original_y
    controller.selectCharacter("brote")
    assert controller.petState == "idle"
    assert view.y() == original_y
    controller._set_state("walking")
    area = view.screen().availableGeometry()
    view.setX(area.x() + area.width() - view.width())
    controller._direction = 1
    controller._deadline = time.monotonic() + 10
    controller._last_tick = time.monotonic() - .033
    controller._tick()
    assert view.x() + view.width() <= area.x() + area.width()
    assert controller._direction == -1
