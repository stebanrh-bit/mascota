"""Contrato HTTP real contra un servidor local de prueba; no simula inferencia."""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from mascota.chat import ChatController
from mascota.chat_window import ChatWindow
from mascota.controller import PetController
from mascota.domain import Preferences

pytestmark = pytest.mark.skipif(sys.platform == 'linux' and not os.environ.get('DISPLAY'), reason='Usa tools/headless.py para las pruebas de Qt')


def until(predicate, timeout=5000):
    deadline=time.monotonic()+timeout/1000
    while not predicate() and time.monotonic()<deadline:
        QTest.qWait(20)
    assert predicate(), 'La operación de Qt no terminó a tiempo'


@pytest.fixture
def service():
    state=SimpleNamespace(models=['qwen2.5:0.5b'], requests=[], delay=0, status=200,
                          frames=[{'message':{'content':'¡Hola! Soy tu dragón.'}},{'done':True}],
                          raw=None, started=threading.Event(), redirect=False)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            state.requests.append((self.path,None))
            if state.redirect:
                self.send_response(302)
                self.send_header('Location','https://example.invalid/no-se-debe-seguir')
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'models':[{'name':name} for name in state.models]}).encode())
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.requests.append((self.path,body))
            status,delay,raw=state.status,state.delay,state.raw
            frames=list(state.frames)
            if self.path=='/api/pull':
                frames=[{'status':'pulling manifest'},{'status':'pulling test layer','completed':25,'total':100},
                        {'status':'verifying sha256 digest'},{'status':'success'}]
            self.send_response(status)
            self.send_header('Content-Type','application/x-ndjson')
            self.end_headers()
            state.started.set()
            try:
                if status!=200:
                    self.wfile.write(b'{"error":"model not found"}\n')
                    return
                if raw is not None:
                    self.wfile.write(raw)
                    return
                for frame in frames:
                    time.sleep(delay)
                    if self.path=='/api/pull' and frame.get('status')=='success': state.models=[body['model']]
                    encoded=(json.dumps(frame,ensure_ascii=False)+'\n').encode()
                    # Split frames, including UTF-8 characters, as real networks may do.
                    for i in range(0,len(encoded),3):
                        self.wfile.write(encoded[i:i+3])
                        self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    state.url='http://127.0.0.1:'+str(server.server_port)
    yield state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def client(app,tmp_path,service):
    pet=PetController(Preferences(tmp_path/'prefs.json'))
    chat=ChatController(pet)
    assert chat.configure(service.url,'qwen2.5:0.5b')
    chat.checkConnection()
    until(lambda:not chat.busy)
    assert chat.connected
    yield chat,pet
    chat.cancel()
    pet._status_timer.stop()
    pet._timer.stop()
    chat.deleteLater()
    app.processEvents()


def test_streamed_reply_uses_personality_and_sends_only_completed_context(client,service):
    chat,pet=client
    assert chat.ready and chat.send('Hola')
    until(lambda:not chat.busy)
    assert chat.messages.rows[-1]['body']=='¡Hola! Soy tu dragón.'
    assert chat.messages.rows[-1]['messageState']=='done'
    payload=[body for path,body in service.requests if path=='/api/chat'][-1]
    assert payload['stream'] is True
    assert payload['messages'][0]['role']=='system'
    assert 'Sombra' in payload['messages'][0]['content']
    assert chat.send('¿Recuerdas mi saludo?')
    until(lambda:not chat.busy)
    payload=[body for path,body in service.requests if path=='/api/chat'][-1]
    assert [message['role'] for message in payload['messages']]==['system','user','assistant','user']
    assert len(chat._history['sombra'])==4
    assert 'messages' not in json.loads(pet.preferences.path.read_text())


def test_cancel_and_character_switch_ignore_late_callbacks(client,service):
    chat,pet=client
    service.delay=.2
    assert chat.send('Una respuesta lenta')
    until(service.started.is_set)
    pet.selectCharacter('nimbo')
    assert not chat.busy
    assert chat.messages.rowCount()==0
    QTest.qWait(500)
    assert not chat._history['sombra']
    assert not chat._history['nimbo']
    pet.selectCharacter('sombra')
    assert chat.messages.rows[-1]['messageState']=='cancelled'
    chat.clear()
    assert chat.messages.rowCount()==0


@pytest.mark.parametrize('raw', [b'{broken}\n', b'{"message":{"content":"partial"}}\n',
                                 b'{"message":{"content":12},"done":true}\n',
                                 b'{"done":true}\n{"done":true}\n'])
def test_malformed_incomplete_and_empty_replies_are_not_committed(client,service,raw):
    chat,_=client
    service.raw=raw
    assert chat.send('Hola')
    until(lambda:not chat.busy)
    assert chat.messages.rows[-1]['messageState']=='error'
    assert chat._history['sombra']==[]


def test_download_model_reports_progress_then_verifies_available_models(client,service):
    chat,_=client
    service.models=[]
    chat.checkConnection()
    until(lambda:not chat.busy)
    assert chat.connected and not chat.ready
    chat.downloadModel()
    until(lambda:not chat.busy)
    assert chat.ready
    assert any(path=='/api/pull' for path,_ in service.requests)
    assert service.requests[-1][0]=='/api/tags'


def test_timeout_never_commits_partial_turns(client,service):
    chat,_=client
    chat.timeout_ms=35
    service.delay=.2
    assert chat.send('Hola')
    until(lambda:not chat.busy)
    assert 'tardó demasiado' in chat.status
    assert chat.messages.rows[-1]['messageState']=='error'
    assert chat._history['sombra']==[]


def test_model_not_found_and_remote_redirect_are_handled(client,service):
    chat,_=client
    service.status=404
    assert chat.send('Hola')
    until(lambda:not chat.busy)
    assert chat.messages.rows[-1]['messageState']=='error'
    assert chat._history['sombra']==[]
    service.redirect=True
    chat.checkConnection()
    until(lambda:not chat.busy)
    assert not chat.connected
    assert service.requests[-1][0]=='/api/tags'


def find_visual(parent,name):
    if parent.objectName()==name: return parent
    for child in parent.childItems():
        found=find_visual(child,name)
        if found is not None: return found


def click(view,name):
    item=find_visual(view.contentItem(),name)
    assert item is not None, name
    point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    QTest.mouseClick(view,Qt.LeftButton,Qt.NoModifier,point)
    QTest.qWait(80)


def test_chat_window_send_button_and_close_keep_pet_running(desktop,service):
    view,pet=desktop
    assistant=ChatWindow(pet)
    try:
        assert assistant.chat.configure(service.url,'qwen2.5:0.5b')
        click(view,'action3')
        until(lambda:not assistant.chat.busy)
        assert assistant.view.status()==QQuickView.Ready
        assert assistant.chat.ready
        assert pet._chat_open
        input_field=find_visual(assistant.view.contentItem(),'chatInput')
        input_field.forceActiveFocus()
        for char in 'Hola':
            key=Qt.Key(ord(char.upper()))
            QGuiApplication.sendEvent(assistant.view,QKeyEvent(QEvent.KeyPress,key,Qt.NoModifier,char))
            QGuiApplication.sendEvent(assistant.view,QKeyEvent(QEvent.KeyRelease,key,Qt.NoModifier,char))
        assert input_field.property('text')=='Hola'
        click(assistant.view,'sendChat')
        until(lambda:not assistant.chat.busy)
        assert assistant.chat.messages.rows[-1]['messageState']=='done'
        assert input_field.property('text')==''
        assert not assistant.view.grabWindow().isNull()
        service.delay=.3
        assert assistant.chat.send('Otra pregunta')
        assistant.close()
        assert not assistant.chat.busy and not pet._chat_open
        assert pet.petState != 'thinking'
        assert view.isVisible()
    finally:
        assistant.shutdown()
        assistant.view.deleteLater()


def test_chat_pauses_roaming_but_timed_expressions_still_finish(desktop):
    _,pet=desktop
    pet.preferences.roaming=True
    pet.set_chat_open(True)
    pet._next_action=time.monotonic()-1
    pet._tick()
    assert pet.petState=='idle'
    pet.roar()
    pet._deadline=time.monotonic()-1
    pet._tick()
    assert pet.petState=='idle'
    pet.set_chat_thinking(True)
    assert pet.petState=='thinking'
    pet.set_chat_open(False)
    assert pet.petState=='idle'
