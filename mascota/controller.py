"""Conecta acciones de la mascota, movimiento del escritorio y preferencias."""
import math
import random
import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from .domain import CHARACTERS, Preferences, clamp_position


class PetController(QObject):
    changed = Signal()
    stateChanged = Signal()
    messageChanged = Signal()

    def __init__(self, preferences: Preferences):
        super().__init__()
        self.preferences = preferences
        self._state = "idle"
        self._message = "Arrástrame · clic derecho para opciones"
        self._window = None
        self._dragging = False
        self._menu_open = False
        self._last_tick = time.monotonic()
        self._next_action = self._last_tick + 10
        self._direction = 1
        self._deadline = 0.0
        self._flight_origin = 0
        self._phase = 0.0
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._restore_message)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def attach_window(self, window):
        self._window = window
        self._timer.start()

    @Property(str, notify=changed)
    def characterId(self):
        return self.preferences.character

    @Property(str, notify=changed)
    def characterName(self):
        return CHARACTERS[self.characterId].name

    @Property(str, notify=changed)
    def characterKind(self):
        return CHARACTERS[self.characterId].kind

    @Property(str, notify=changed)
    def bodyColor(self):
        return CHARACTERS[self.characterId].body

    @Property(str, notify=changed)
    def bellyColor(self):
        return CHARACTERS[self.characterId].belly

    @Property(str, notify=changed)
    def accentColor(self):
        return CHARACTERS[self.characterId].accent

    @Property(str, notify=changed)
    def eyeColor(self):
        return CHARACTERS[self.characterId].eyes

    @Property(bool, notify=changed)
    def roaming(self):
        return self.preferences.roaming

    @Property(str, notify=stateChanged)
    def petState(self):
        return self._state

    @Property(str, notify=messageChanged)
    def message(self):
        return self._message

    def _set_state(self, value):
        if value != self._state:
            self._state = value
            self.stateChanged.emit()

    def _say(self, value, seconds=4):
        self._message = value
        self.messageChanged.emit()
        self._status_timer.start(int(seconds * 1000))

    def _restore_message(self):
        self._message = CHARACTERS[self.characterId].description
        self.messageChanged.emit()

    def _save(self):
        try:
            self.preferences.save()
        except OSError:
            self._say("No pude guardar la elección; puedes seguir jugando.")

    @Slot(str)
    def selectCharacter(self, character):
        if character not in CHARACTERS:
            return
        self.preferences.character = character
        self._stop_motion()
        self._save()
        self.changed.emit()
        self._say(f"¡Hola! Soy {self.characterName}.")

    @Slot()
    def pet(self):
        self._stop_motion()
        self._set_state("happy")
        self._deadline = time.monotonic() + 2.2
        self._say("¡Eso me gusta! ♡" if self.characterKind == "spirit" else "Grrr… ¡otra caricia! ♡")

    @Slot()
    def toggleSleep(self):
        if self._state == "sleeping":
            self._stop_motion()
            self._say("¡Ya estoy despierto!")
        else:
            self._stop_motion()
            self._set_state("sleeping")
            self._say("Zzz… estoy recargando mi magia.")

    @Slot()
    def toggleRoaming(self):
        self.preferences.roaming = not self.roaming
        if not self.roaming and self._state == "walking":
            self._stop_motion()
        self._save()
        self.changed.emit()
        self._say("Exploración activada" if self.roaming else "Me quedo contigo aquí")

    @Slot()
    def fly(self):
        self._stop_motion()
        if self._window:
            self._flight_origin = self._window.y()
        self._phase = 0.0
        self._deadline = time.monotonic() + 3.2
        self._set_state("flying")
        self._say("¡Cuidado, dragón en vuelo!" if self.characterKind == "dragon" else "¡Voy flotando!")

    @Slot(bool)
    def setDragging(self, value):
        if value:
            self._stop_motion()
            self._set_state("held")
        else:
            self._set_state("idle")
            self._next_action = time.monotonic() + 8
            self._clamp()
        self._dragging = value

    @Slot(bool)
    def setMenuOpen(self, value):
        self._menu_open = value
        if value:
            self._stop_motion()

    @Slot(int, int)
    def moveBy(self, dx, dy):
        if self._window:
            self._window.setPosition(self._window.x() + dx, self._window.y() + dy)

    @Slot()
    def centerOnScreen(self):
        if not self._window:
            return
        screen = self._window.screen() or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self._stop_motion()
        self._window.setPosition(area.x() + (area.width() - self._window.width()) // 2,
                                 area.bottom() - self._window.height() + 1)
        self._clamp()

    def _clamp(self):
        if not self._window:
            return
        screen = self._window.screen() or QGuiApplication.primaryScreen()
        a = screen.availableGeometry()
        x, y = clamp_position(self._window.x(), self._window.y(), self._window.width(),
                              self._window.height(), (a.x(), a.y(), a.width(), a.height()))
        self._window.setPosition(x, y)

    def _stop_motion(self):
        if self._state == "flying" and self._window:
            self._window.setY(self._flight_origin)
        self._set_state("idle")
        self._next_action = time.monotonic() + 8

    def _tick(self):
        now = time.monotonic()
        elapsed = min(now - self._last_tick, .1)
        self._last_tick = now
        if self._dragging or self._menu_open or not self._window:
            return
        if self._state in ("happy", "walking", "flying") and now >= self._deadline:
            self._stop_motion()
        if self._state == "flying":
            self._phase += elapsed
            self._window.setY(self._flight_origin - round(65 * math.sin(min(self._phase / 3.2, 1) * math.pi)))
            self._clamp()
        elif self._state == "walking":
            old_x = self._window.x()
            self._window.setX(old_x + self._direction * max(1, round(45 * elapsed)))
            self._clamp()
            if self._window.x() == old_x:
                self._direction *= -1
        elif self._state == "idle" and self.roaming and now >= self._next_action:
            self._direction = random.choice((-1, 1))
            self._deadline = now + random.uniform(3, 5)
            self._set_state("walking")
