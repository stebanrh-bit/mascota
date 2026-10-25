"""Modelo de recuerdos y operaciones explícitas para la interfaz de la mascota."""
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, Signal, Slot

from .memory_store import MemoryStore, MemoryStoreError


class MemoryList(QAbstractListModel):
    roles = {Qt.UserRole+1: b'memoryId', Qt.UserRole+2: b'body'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def roleNames(self):
        return self.roles

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        key = {Qt.UserRole+1: 'id', Qt.UserRole+2: 'body'}.get(role)
        return self.rows[index.row()].get(key) if key else None

    def use(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class MemoryController(QObject):
    changed = Signal()
    contextReset = Signal(str)
    notice = Signal(str)

    def __init__(self, preferences, can_edit, parent=None):
        super().__init__(parent)
        self._path = preferences.path.with_name('memories.sqlite3')
        self._character = preferences.character
        self._can_edit = can_edit
        self._store = None
        self._available = False
        self._enabled = True
        self._status = 'Guarda los datos que quieras recordar entre sesiones.'
        self._revisions = {}
        self.items = MemoryList(self)
        self.refresh()

    @Property(QObject, constant=True)
    def entries(self):
        return self.items

    @Property(int, notify=changed)
    def count(self):
        return self.items.rowCount()

    @Property(bool, notify=changed)
    def enabled(self):
        return self._enabled

    @Property(bool, notify=changed)
    def available(self):
        return self._available

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(str, notify=changed)
    def summary(self):
        if not self._available:
            return 'Memoria no disponible'
        if not self._enabled:
            return 'Memoria pausada'
        if self.count == 1:
            return '1 recuerdo guardado'
        return f'{self.count} recuerdos guardados' if self.count else 'Sin recuerdos guardados'

    def select_character(self, character):
        self._character = character
        self.refresh()

    def _message(self, text):
        self._status = text
        self.changed.emit()
        self.notice.emit(text)

    def _reload(self, reset_on_change=True):
        try:
            if self._store is None:
                self._store = MemoryStore(self._path)
            enabled, revision, rows = self._store.snapshot(self._character)
            previous = self._revisions.get(self._character)
            self._revisions[self._character] = revision
            self._enabled, self._available = enabled, True
            self.items.use(rows)
            self.changed.emit()
            if reset_on_change and previous is not None and previous != revision:
                self.contextReset.emit(self._character)
            return True
        except (MemoryStoreError, OSError) as error:
            was_available = self._available
            self._store = None
            self._available = False
            self.items.use([])
            self._message(str(error) if isinstance(error, MemoryStoreError) else 'No se pudo abrir la memoria local. Revisa los permisos de la carpeta de configuración.')
            if was_available:
                self.contextReset.emit(self._character)
            return False

    @Slot(result=bool)
    def refresh(self):
        return self._reload()

    def facts(self):
        if not self.refresh() or not self._enabled:
            return []
        return [row['body'] for row in self.items.rows]

    def _editable(self, character):
        if character != self._character:
            self._message('Cambiaste de personaje. Abre de nuevo el editor de recuerdos.')
            return False
        if not self._can_edit():
            self._message('Detén la respuesta antes de cambiar los recuerdos.')
            return False
        return self.refresh()

    @Slot(int, str, str, result=bool)
    def save(self, memory_id, text, character):
        if not self._editable(character):
            return False
        try:
            if memory_id < 0:
                self._store.add(character, text)
                updated = True
            else:
                updated = self._store.update(character, memory_id, text)
            if not self._reload(reset_on_change=memory_id >= 0):
                return False
        except (ValueError, MemoryStoreError) as error:
            self._message(str(error))
            return False
        self._message('Recuerdo guardado en este equipo.' if memory_id < 0 else
                      'Recuerdo actualizado. Empezamos un contexto de conversación nuevo.' if updated else
                      'El recuerdo sigue guardado sin cambios.')
        return True

    @Slot(int, str, result=bool)
    def remove(self, memory_id, character):
        if not self._editable(character):
            return False
        try:
            self._store.remove(character, memory_id)
            if not self._reload():
                return False
        except (ValueError, MemoryStoreError) as error:
            self._message(str(error))
            return False
        self._message('Recuerdo eliminado. Los próximos mensajes usarán un contexto nuevo.')
        return True

    @Slot(bool, str, result=bool)
    def setEnabled(self, enabled, character):
        if not self._editable(character):
            return False
        try:
            self._store.set_enabled(character, enabled)
            if not self._reload():
                return False
        except (ValueError, MemoryStoreError) as error:
            self._message(str(error))
            return False
        self._message('Recuerdos activados.' if enabled else 'Memoria pausada. Los recuerdos siguen guardados y no se enviarán al modelo.')
        return True
