"""Comprueba una respuesta real del modelo local; no usa un servidor simulado.

python -m mascota.check_ai [--capture captura.png]
En Linux sin escritorio, ejecutar mediante tools/headless.py.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle

from .ai import DEFAULT_MODEL, DEFAULT_URL
from .chat_window import ChatWindow
from .controller import PetController
from .domain import Preferences
from .memory_store import MemoryStore


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default=DEFAULT_URL)
    parser.add_argument('--model',default=DEFAULT_MODEL)
    parser.add_argument('--capture',type=Path)
    parser.add_argument('--memory-demo',action='store_true',help='Guarda un dato en un perfil temporal y comprueba que el modelo lo usa al iniciar otra sesión')
    parser.add_argument('--memory-capture',type=Path,help='Captura el panel de recuerdos de la demostración')
    args=parser.parse_args()
    if args.memory_capture and not args.memory_demo:
        parser.error('--memory-capture requiere --memory-demo')
    os.environ.setdefault('QSG_RENDER_LOOP','basic')
    QQuickStyle.setStyle('Basic')
    app=QGuiApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='mascota-live-') as temporary:
        profile=Path(temporary)
        fact='Mi color favorito es el turquesa.'
        if args.memory_demo:
            MemoryStore(profile/'memories.sqlite3').add('sombra',fact)
        pet=PetController(Preferences(profile/'preferences.json'))
        window=ChatWindow(pet,app)
        client=window.chat
        restored=client.memory.facts()==[fact] if args.memory_demo else False
        if args.memory_demo and not restored:
            print(json.dumps({'ok':False,'memory_restored':False}))
            return 1
        if not client.configure(args.url,args.model) or not window.open(check_connection=False):
            return 1
        phase=['probe']
        def report(row):
            result={'ok':True,'provider':'Ollama local','model':args.model,'answer':row['body']}
            if args.memory_demo:
                result.update(memory_restored=restored,remembered_fact_used=True)
            print(json.dumps(result,ensure_ascii=False))
            app.quit()
        def finish():
            row=client.messages.rows[-1] if client.messages.rows else {}
            if row.get('messageState')!='done' or not row.get('body','').strip():
                print(json.dumps({'ok':False,'status':client.status},ensure_ascii=False))
                app.exit(1)
                return
            if args.memory_demo and 'turquesa' not in row['body'].casefold():
                print(json.dumps({'ok':False,'memory_restored':restored,'answer':row['body']},ensure_ascii=False))
                app.exit(1)
                return
            if args.capture:
                args.capture.parent.mkdir(parents=True,exist_ok=True)
                image=window.view.grabWindow()
                if image.isNull() or not image.save(str(args.capture)):
                    app.exit(1)
                    return
            if args.memory_capture:
                window.view.rootObject().setProperty('remembering',True)
                client.memory.refresh()
                def capture_memories():
                    args.memory_capture.parent.mkdir(parents=True,exist_ok=True)
                    image=window.view.grabWindow()
                    if image.isNull() or not image.save(str(args.memory_capture)):
                        app.exit(1)
                        return
                    report(row)
                QTimer.singleShot(300,capture_memories)
            else:
                report(row)
        def progress():
            if client.busy: return
            if phase[0]=='probe':
                if not client.ready:
                    print(json.dumps({'ok':False,'status':client.status},ensure_ascii=False))
                    app.exit(1)
                    return
                phase[0]='reply'
                question='¿Cuál es mi color favorito? Responde en una sola frase en español.' if args.memory_demo else 'Hola. Preséntate en una sola frase en español.'
                QTimer.singleShot(0,lambda:client.send(question))
            elif phase[0]=='reply':
                phase[0]='complete'
                QTimer.singleShot(300,finish)
        client.busyChanged.connect(progress)
        app.aboutToQuit.connect(window.shutdown)
        QTimer.singleShot(0,client.checkConnection)
        QTimer.singleShot(180000,lambda:app.exit(1))
        return app.exec()


if __name__=='__main__':
    raise SystemExit(main())
