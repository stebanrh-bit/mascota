"""Conversación asíncrona con Ollama. Solo envía tráfico a este equipo."""
import json

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Property, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest

from .ai import DEFAULT_MODEL, DEFAULT_URL, MAX_ANSWER, JsonLines, chat_payload, local_endpoint, model_name, personality
from .domain import CHARACTERS
from .memories import MemoryController


class Conversation(QAbstractListModel):
    roles = {Qt.UserRole+1: b'speaker', Qt.UserRole+2: b'body', Qt.UserRole+3: b'messageState'}

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
        key = self.roles.get(role)
        return self.rows[index.row()].get(key.decode()) if key else None

    def use(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def append(self, speaker, body, state='done'):
        if len(self.rows) >= 40:
            self.beginRemoveRows(QModelIndex(), 0, 1)
            del self.rows[:2]
            self.endRemoveRows()
        n = len(self.rows)
        self.beginInsertRows(QModelIndex(), n, n)
        self.rows.append({'speaker': speaker, 'body': body, 'messageState': state})
        self.endInsertRows()

    def update_answer(self, text, state):
        if self.rows and self.rows[-1]['speaker'] == 'assistant':
            self.rows[-1].update(body=text, messageState=state)
            i = self.index(len(self.rows)-1, 0)
            self.dataChanged.emit(i, i, list(self.roles))


class ChatController(QObject):
    changed = Signal()
    busyChanged = Signal()
    answerReady = Signal()

    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self.messages = Conversation(self)
        self.manager = QNetworkAccessManager(self)
        self.manager.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
        self._history = {key: [] for key in CHARACTERS}
        self._conversations = {key: [] for key in CHARACTERS}
        self._identity = (pet.characterId, pet.characterName)
        self.messages.use(self._conversations[pet.characterId])
        settings = pet.preferences.ai
        self._url, self._model = settings['url'], settings['model']
        self._connected = False
        self._models = []
        self._status = 'Conecta Ollama para conversar con tu compañero.'
        self._busy = False
        self._kind = ''
        self._reply = None
        self._serial = 0
        self._progress = -1
        self._answer = ''
        self._prompt = ''
        self._wire_bytes = 0
        self._buffer = b''
        self._done = False
        self._decoder = JsonLines()
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(lambda: self._fail('La IA tardó demasiado. Puedes volver a intentarlo.'))
        self.timeout_ms = 120000
        pet.changed.connect(self._sync_identity)
        self.memory = MemoryController(pet.preferences, lambda: not self.busy, self)
        self.memory.contextReset.connect(self._reset_memory_context)
        self.memory.notice.connect(self._memory_notice)

    @Property(QObject, constant=True)
    def memoryManager(self):
        return self.memory

    def _memory_notice(self, text):
        self._status = text
        self.changed.emit()

    def _reset_memory_context(self, character):
        if self._identity[0] == character and self._kind == 'chat':
            self.cancel()
        self._history[character].clear()
        if self._identity[0] == character and self.messages.rowCount():
            self.messages.append('notice', 'Recuerdos actualizados. Los próximos mensajes empiezan con un contexto nuevo.', 'notice')

    @Property(QObject, constant=True)
    def conversation(self):
        return self.messages

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def operation(self):
        return self._kind

    @Property(bool, notify=changed)
    def connected(self):
        return self._connected

    @Property(bool, notify=changed)
    def ready(self):
        def canonical(value):
            return value if ':' in value.rsplit('/', 1)[-1] else value + ':latest'
        return self._connected and canonical(self._model) in {canonical(value) for value in self._models}

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(str, notify=changed)
    def endpoint(self):
        return self._url

    @Property(str, notify=changed)
    def modelName(self):
        return self._model

    @Property(list, notify=changed)
    def availableModels(self):
        return self._models.copy()

    @Property(int, notify=changed)
    def progress(self):
        return self._progress

    def _sync_identity(self):
        identity = (self.pet.characterId, self.pet.characterName)
        if identity == self._identity:
            return
        if self._kind == 'chat':
            self.cancel()
        self._identity = identity
        self.messages.use(self._conversations[identity[0]])
        self.memory.select_character(identity[0])
        self.changed.emit()

    @Slot(str, str, result=bool)
    def configure(self, url, model):
        if self.busy:
            return False
        try:
            url, model = local_endpoint(url), model_name(model)
        except ValueError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self._url, self._model = url, model
        self.pet.preferences.ai = {'url': url, 'model': model}
        try:
            self.pet.preferences.save()
        except OSError:
            self._status = 'Configuración aplicada, pero no se pudo guardar para la próxima vez.'
        else:
            self._status = 'Configuración guardada. Comprueba la conexión.'
        self._connected = False
        self._models = []
        self.changed.emit()
        return True

    def _begin(self, kind, path, data=None):
        if self.busy:
            return False
        self._serial += 1
        token = self._serial
        self._kind = kind
        self._decoder = JsonLines()
        self._wire_bytes = 0
        self._buffer = b''
        self._done = False
        self._progress = -1
        request = QNetworkRequest(QUrl(self._url + path))
        request.setTransferTimeout(90000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        if data is None:
            reply = self.manager.get(request)
        else:
            request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
            reply = self.manager.post(request, QByteArray(json.dumps(data, ensure_ascii=False).encode('utf-8')))
        self._reply = reply
        self._busy = True
        reply.readyRead.connect(lambda: self._consume(reply, token))
        reply.finished.connect(lambda: self._finish(reply, token))
        self._timeout.start(15*60*1000 if kind == 'pull' else self.timeout_ms)
        self.busyChanged.emit()
        self.changed.emit()
        return True

    @Slot()
    def checkConnection(self):
        if not self.busy:
            self._status = 'Buscando Ollama en este equipo…'
            self._begin('probe', '/api/tags')

    @Slot()
    def downloadModel(self):
        if not self.busy and self._connected:
            self._status = 'Preparando la descarga del modelo…'
            self._begin('pull', '/api/pull', {'model': self._model, 'stream': True})

    @Slot(str, result=bool)
    def send(self, prompt):
        if self.busy:
            return False
        if not self.ready:
            self._status = 'Primero conecta Ollama y prepara el modelo en Configuración.'
            self.changed.emit()
            return False
        who = CHARACTERS[self.pet.characterId]
        system = personality(self.pet.characterName, who.kind, who.description)
        try:
            memories = self.memory.facts()
            if not self.memory.available:
                self._status = 'La memoria local no está disponible. Abre Recuerdos y vuelve a intentarlo.'
                self.changed.emit()
                return False
            payload = chat_payload(self._model, system, self._history[self.pet.characterId], prompt, memories)
        except ValueError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self._prompt, self._answer = prompt.strip(), ''
        self.messages.append('user', self._prompt)
        self.messages.append('assistant', '', 'pending')
        self._status = f'{self.pet.characterName} está pensando…'
        return self._begin('chat', '/api/chat', payload)

    def _consume(self, reply, token):
        if token != self._serial:
            return
        data = bytes(reply.readAll())
        self._wire_bytes += len(data)
        if self._wire_bytes > (8*1024*1024 if self._kind == 'pull' else 1024*1024):
            self._fail('El servicio local envió demasiados datos. Inténtalo de nuevo.')
            return
        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if http_status and not 200 <= http_status < 300:
            return  # HTTP errors are classified in _finish, never as chat frames.
        if self._kind == 'probe':
            self._buffer += data
            return
        try:
            for frame in self._decoder.feed(data):
                self._frame(frame)
                if token != self._serial:
                    break
        except ValueError as error:
            self._fail(str(error))

    def _frame(self, frame):
        if self._done:
            raise ValueError('El servicio envió datos después de terminar la respuesta.')
        if 'error' in frame:
            self._fail('Ollama no pudo completar la solicitud. Comprueba el modelo y vuelve a intentarlo.')
            return
        if self._kind == 'chat':
            message = frame.get('message', {})
            if not isinstance(message, dict) or not isinstance(message.get('content', ''), str):
                raise ValueError('El servicio local devolvió una respuesta no válida.')
            piece = message.get('content', '')
            if len(self._answer) + len(piece) > MAX_ANSWER:
                raise ValueError('La respuesta es demasiado larga. Prueba con una pregunta más breve.')
            self._answer += piece
            self.messages.update_answer(self._answer, 'pending')
            if frame.get('done') is True:
                self._done = True
        elif self._kind == 'pull':
            status = frame.get('status', '')
            if not isinstance(status, str):
                raise ValueError('El servicio local devolvió una respuesta no válida.')
            if status == 'success':
                self._done, self._progress = True, 100
            elif status.startswith('verifying'):
                self._status = 'Verificando el modelo descargado…'
            elif isinstance(frame.get('total'), (int, float)) and frame['total'] > 0:
                completed = frame.get('completed', 0)
                if isinstance(completed, (int, float)):
                    self._progress = max(0, min(100, round(completed/frame['total']*100)))
                    self._status = f'Descargando el modelo… {self._progress}%'
            self.changed.emit()

    def _finish(self, reply, token):
        if token != self._serial:
            return
        self._consume(reply, token)
        if token != self._serial:
            return
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if reply.error() != QNetworkReply.NoError or not status or not 200 <= status < 300:
            self._connected = False
            if status == 404:
                self._fail('No encuentro ese modelo o servicio. Comprueba la configuración o descarga el modelo.')
            else:
                self._fail('No pude comunicarme con Ollama. Ábrelo en tu equipo y comprueba la conexión.')
            return
        try:
            if self._kind == 'probe':
                body = json.loads(self._buffer)
                if not isinstance(body, dict) or not isinstance(body.get('models'), list):
                    raise ValueError('Ese servicio no parece ser Ollama.')
                models = []
                for entry in body['models'][:100]:
                    if isinstance(entry, dict):
                        try: models.append(model_name(entry.get('name', entry.get('model'))))
                        except ValueError: pass
                self._models = sorted(set(models))
                self._connected = True
                self._status = 'Listo para conversar.' if self.ready else 'Ollama conectado. Elige o descarga un modelo.'
            else:
                for frame in self._decoder.feed(b'', final=True):
                    self._frame(frame)
                    if token != self._serial:
                        return
                if not self._done:
                    raise ValueError('La respuesta se interrumpió. Puedes intentarlo de nuevo.')
                if self._kind == 'chat':
                    if not self._answer.strip():
                        raise ValueError('El modelo no devolvió texto. Prueba con otro modelo.')
                    self.messages.update_answer(self._answer, 'done')
                    history = self._history[self.pet.characterId]
                    history.extend([{'role': 'user', 'content': self._prompt}, {'role': 'assistant', 'content': self._answer}])
                    del history[:-8]
                    self._status = 'Listo. ¿Qué más te gustaría preguntar?'
        except (ValueError, UnicodeError, TypeError):
            self._fail('La respuesta del servicio local no es válida o quedó incompleta. Vuelve a intentarlo.')
            return
        kind = self._kind
        self._release()
        if kind == 'chat':
            self.answerReady.emit()
        elif kind == 'pull':
            self.checkConnection()

    def _release(self):
        self._serial += 1
        reply, self._reply = self._reply, None
        self._timeout.stop()
        self._kind = ''
        self._busy = False
        if reply:
            reply.deleteLater()
        self.busyChanged.emit()
        self.changed.emit()

    def _fail(self, message, cancelled=False):
        if self._kind == 'chat':
            text = self._answer + '\n\n' + message if self._answer else message
            self.messages.update_answer(text, 'cancelled' if cancelled else 'error')
        reply = self._reply
        self._status = message
        self._release()  # invalidate callbacks before abort(), which may emit finished
        if reply:
            reply.abort()

    @Slot()
    def cancel(self):
        if self.busy:
            self._fail('Respuesta cancelada.' if self._kind == 'chat' else 'Operación cancelada.', True)

    @Slot()
    def clear(self):
        self.cancel()
        self._history[self.pet.characterId].clear()
        rows = self._conversations[self.pet.characterId]
        self.messages.use([])
        rows.clear()
        self.messages.use(rows)
        self._status = 'Conversación vaciada. Los mensajes solo se conservan mientras la aplicación está abierta.'
        self.changed.emit()
