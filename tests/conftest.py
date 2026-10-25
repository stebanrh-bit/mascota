import os
from pathlib import Path

import pytest

os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQuick import QQuickView, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from mascota.controller import PetController
from mascota.domain import Preferences
from mascota.geometry import register_geometry


@pytest.fixture(scope='session')
def app():
    QQuickWindow.setDefaultAlphaBuffer(True)
    QQuickStyle.setStyle('Basic')
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    application = QGuiApplication.instance() or QGuiApplication([])
    application.setQuitOnLastWindowClosed(False)
    register_geometry()
    yield application


@pytest.fixture
def desktop(app, tmp_path):
    settings = Preferences(tmp_path / 'preferences.json')
    settings.roaming = False
    controller = PetController(settings)
    view = QQuickView()
    view.setColor(Qt.transparent)
    view.setFlags(Qt.FramelessWindowHint | Qt.Tool)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.rootContext().setContextProperty('pet', controller)
    source = Path(__file__).parents[1] / 'mascota' / 'qml' / 'Main.qml'
    view.setSource(QUrl.fromLocalFile(str(source)))
    assert view.status() == QQuickView.Ready, [error.toString() for error in view.errors()]
    view.resize(460, 520)
    controller.attach_window(view)
    view.show()
    controller.centerOnScreen()
    QTest.qWait(500)
    yield view, controller
    controller._timer.stop()
    controller._status_timer.stop()
    view.setSource(QUrl())
    view.close()
    view.deleteLater()
    app.processEvents()
