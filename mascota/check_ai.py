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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default=DEFAULT_URL)
    parser.add_argument('--model',default=DEFAULT_MODEL)
    parser.add_argument('--capture',type=Path)
    args=parser.parse_args()
    os.environ.setdefault('QSG_RENDER_LOOP','basic')
    QQuickStyle.setStyle('Basic')
    app=QGuiApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='mascota-live-') as temporary:
        pet=PetController(Preferences(Path(temporary)/'preferences.json'))
        window=ChatWindow(pet,app)
        client=window.chat
        if not client.configure(args.url,args.model) or not window.open(check_connection=False):
            return 1
        phase=['probe']
        def finish():
            row=client.messages.rows[-1] if client.messages.rows else {}
            if row.get('messageState')!='done' or not row.get('body','').strip():
                print(json.dumps({'ok':False,'status':client.status},ensure_ascii=False))
                app.exit(1)
                return
            if args.capture:
                args.capture.parent.mkdir(parents=True,exist_ok=True)
                image=window.view.grabWindow()
                if image.isNull() or not image.save(str(args.capture)):
                    app.exit(1)
                    return
            print(json.dumps({'ok':True,'provider':'Ollama local','model':args.model,'answer':row['body']},ensure_ascii=False))
            app.quit()
        def progress():
            if client.busy: return
            if phase[0]=='probe':
                if not client.ready:
                    print(json.dumps({'ok':False,'status':client.status},ensure_ascii=False))
                    app.exit(1)
                    return
                phase[0]='reply'
                QTimer.singleShot(0,lambda:client.send('Hola. Preséntate en una sola frase en español.'))
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
