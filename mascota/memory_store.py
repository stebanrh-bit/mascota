"""Recuerdos elegidos por el usuario, con transacciones SQLite por personaje."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from .domain import CHARACTERS
from .memory_data import MAX_MEMORIES, MAX_MEMORY_LENGTH, clean_memory

APPLICATION_ID = 0x4D504554


class MemoryStoreError(RuntimeError):
    pass


class MemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            existing = self.path.exists() and self.path.stat().st_size > 0
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as connection:
                application_id = connection.execute('PRAGMA application_id').fetchone()[0]
                version = connection.execute('PRAGMA user_version').fetchone()[0]
                if existing:
                    if application_id != APPLICATION_ID or version != 1:
                        raise MemoryStoreError('El archivo de recuerdos tiene otro formato. Se conservó sin cambios.')
                    connection.execute('SELECT id, character, body, normalized FROM memories LIMIT 0')
                    connection.execute('SELECT character, enabled, revision FROM memory_settings LIMIT 0')
                else:
                    connection.execute('BEGIN IMMEDIATE')
                    connection.execute('CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, character TEXT NOT NULL, body TEXT NOT NULL, normalized TEXT NOT NULL, UNIQUE(character, normalized))')
                    connection.execute('CREATE TABLE memory_settings (character TEXT PRIMARY KEY, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), revision INTEGER NOT NULL)')
                    connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    connection.execute('PRAGMA user_version=1')
                    connection.commit()
        except OSError:
            raise MemoryStoreError('No se pudo abrir la memoria local. Revisa los permisos de la carpeta de configuración.') from None

    @contextmanager
    def _connection(self):
        connection = None
        try:
            connection = sqlite3.connect(str(self.path), timeout=.5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            yield connection
        except sqlite3.IntegrityError:
            if connection: connection.rollback()
            raise MemoryStoreError('Ese recuerdo ya está guardado para este personaje.') from None
        except sqlite3.Error:
            if connection: connection.rollback()
            raise MemoryStoreError('No se pudo leer o modificar la memoria local. Tus archivos se conservan; vuelve a intentarlo.') from None
        finally:
            if connection: connection.close()

    def _character(self, character):
        if character not in CHARACTERS:
            raise ValueError('Elige un personaje válido.')

    @contextmanager
    def _write(self, character):
        self._character(character)
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _bump(connection, character):
        connection.execute('INSERT INTO memory_settings(character, enabled, revision) VALUES(?,1,1) ON CONFLICT(character) DO UPDATE SET revision=revision+1', (character,))

    def snapshot(self, character):
        self._character(character)
        with self._connection() as connection:
            connection.execute('BEGIN')
            options = connection.execute('SELECT enabled, revision FROM memory_settings WHERE character=?', (character,)).fetchone()
            rows = connection.execute('SELECT id, body FROM memories WHERE character=? ORDER BY id', (character,)).fetchall()
            try:
                if len(rows) > MAX_MEMORIES or any(clean_memory(row['body']) != row['body'] for row in rows):
                    raise ValueError()
            except ValueError:
                raise MemoryStoreError('El archivo de recuerdos contiene datos inválidos. Se conservó sin cambios.') from None
            return (bool(options['enabled']) if options else True,
                    options['revision'] if options else 0,
                    [{'id': row['id'], 'body': row['body']} for row in rows])

    def add(self, character, text):
        text = clean_memory(text)
        with self._write(character) as connection:
            count = connection.execute('SELECT COUNT(*) FROM memories WHERE character=?', (character,)).fetchone()[0]
            if count >= MAX_MEMORIES:
                raise ValueError('Puedes guardar hasta 12 recuerdos por personaje. Edita o elimina uno para añadir otro.')
            cursor = connection.execute('INSERT INTO memories(character, body, normalized) VALUES(?,?,?)', (character, text, text.casefold()))
            self._bump(connection, character)
            return cursor.lastrowid

    def update(self, character, memory_id, text):
        text = clean_memory(text)
        with self._write(character) as connection:
            row = connection.execute('SELECT body FROM memories WHERE character=? AND id=?', (character, memory_id)).fetchone()
            if row is None:
                raise ValueError('Ese recuerdo ya no existe para este personaje. Actualiza la lista.')
            if row['body'] == text:
                return False
            connection.execute('UPDATE memories SET body=?, normalized=? WHERE character=? AND id=?', (text, text.casefold(), character, memory_id))
            self._bump(connection, character)
            return True

    def remove(self, character, memory_id):
        with self._write(character) as connection:
            cursor = connection.execute('DELETE FROM memories WHERE character=? AND id=?', (character, memory_id))
            if not cursor.rowcount:
                raise ValueError('Ese recuerdo ya no existe para este personaje. Actualiza la lista.')
            self._bump(connection, character)

    def set_enabled(self, character, enabled):
        with self._write(character) as connection:
            row = connection.execute('SELECT enabled FROM memory_settings WHERE character=?', (character,)).fetchone()
            current = bool(row['enabled']) if row else True
            if current == bool(enabled):
                return False
            self._bump(connection, character)
            connection.execute('UPDATE memory_settings SET enabled=? WHERE character=?', (int(bool(enabled)), character))
            return True
