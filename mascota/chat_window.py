"""Ventana de conversación independiente: no bloquea la mascota ni el renderizador."""
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Qt, Slot
from PySide6.QtQuick import QQuickView

from .chat import ChatController


class ChatWindow(QObject):
    def __init__(self, pet, parent=None):
        super().__init__(parent)
        self.pet = pet
        self.chat = ChatController(pet, self)
        self.view = QQuickView()
        self.view.setTitle('Mascota · conversación local')
        self.view.setColor('#0d1420')
        self.view.setMinimumWidth(440)
        self.view.setMinimumHeight(600)
        self.view.setResizeMode(QQuickView.SizeRootObjectToView)
        self.view.rootContext().setContextProperty('pet', pet)
        self.view.rootContext().setContextProperty('chat', self.chat)
        self.view.rootContext().setContextProperty('chatWindow', self)
        self.view.visibilityChanged.connect(lambda _: self._visibility())
        pet.chatRequested.connect(self.open)
        self.chat.busyChanged.connect(lambda: pet.set_chat_thinking(self.chat.busy and self.chat.operation == 'chat'))
        self.chat.answerReady.connect(lambda: pet._say('¡Te respondí en la conversación!'))

    def open(self, check_connection=True):
        if self.view.source().isEmpty():
            self.view.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / 'Chat.qml')))
            if self.view.status() == QQuickView.Error:
                self.pet._say('No pude abrir la ventana de conversación.')
                return False
            self.view.resize(500, 700)
        self.view.show()
        self.view.requestActivate()
        if check_connection and not self.chat.busy:
            self.chat.checkConnection()
        return True

    def _visibility(self):
        visible = self.view.isVisible()
        self.pet.set_chat_open(visible)
        if not visible:
            self.chat.cancel()

    @Slot()
    def close(self):
        self.view.close()

    def shutdown(self):
        self.chat.cancel()
        self.view.close()
        self.view.setSource(QUrl())
