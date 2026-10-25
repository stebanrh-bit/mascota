from pathlib import Path
import sqlite3

import pytest

from mascota.memory_store import MAX_MEMORIES, MemoryStore, MemoryStoreError, clean_memory


def test_memories_survive_restart_and_are_separate_by_character(tmp_path):
    path=tmp_path/'memories.sqlite3'
    store=MemoryStore(path)
    store.add('sombra','Mi color favorito es el turquesa.')
    store.add('nimbo','Me gusta leer por las noches.')
    restored=MemoryStore(path)
    assert restored.snapshot('sombra')[2][0]['body']=='Mi color favorito es el turquesa.'
    assert restored.snapshot('nimbo')[2][0]['body']=='Me gusta leer por las noches.'
    assert restored.snapshot('brote')[2]==[]


def test_edit_delete_and_pause_are_persistent(tmp_path):
    path=tmp_path/'memories.sqlite3'
    store=MemoryStore(path)
    key=store.add('sombra','Mi color favorito es el azul.')
    first_revision=store.snapshot('sombra')[1]
    assert store.update('sombra',key,'Mi color favorito es el turquesa.')
    assert store.snapshot('sombra')[1]>first_revision
    store.set_enabled('sombra',False)
    restored=MemoryStore(path)
    assert restored.snapshot('sombra')[0] is False
    assert restored.snapshot('sombra')[2][0]['id']==key
    restored.remove('sombra',key)
    assert MemoryStore(path).snapshot('sombra')[2]==[]


def test_cross_character_delete_does_not_touch_original(tmp_path):
    store=MemoryStore(tmp_path/'memories.sqlite3')
    key=store.add('sombra','Me gusta dibujar.')
    before=store.snapshot('sombra')
    with pytest.raises(ValueError): store.remove('nimbo',key)
    with pytest.raises(ValueError): store.update('nimbo',key,'Otro texto')
    assert store.snapshot('sombra')==before


def test_duplicate_edit_rolls_back_without_losing_records(tmp_path):
    store=MemoryStore(tmp_path/'memories.sqlite3')
    first=store.add('sombra','Me gusta dibujar.')
    store.add('sombra','Me gusta leer.')
    before=store.snapshot('sombra')
    with pytest.raises(MemoryStoreError): store.update('sombra',first,'ME GUSTA LEER.')
    assert store.snapshot('sombra')==before
    with pytest.raises(MemoryStoreError): store.add('sombra','  me gusta dibujar.  ')
    assert store.snapshot('sombra')==before


def test_store_enforces_limit_without_partial_writes(tmp_path):
    store=MemoryStore(tmp_path/'memories.sqlite3')
    for i in range(MAX_MEMORIES): store.add('sombra',f'Dato número {i}.')
    before=store.snapshot('sombra')
    with pytest.raises(ValueError): store.add('sombra','Un dato adicional.')
    assert store.snapshot('sombra')==before
    store.add('nimbo','Este personaje tiene otro cupo.')
    assert len(store.snapshot('nimbo')[2])==1


@pytest.mark.parametrize('value',[None,'',' \t\n ','x'*241,'\x00\u202e'],ids=['missing','empty','whitespace','too-long','controls'])
def test_invalid_memory_is_not_saved(tmp_path,value):
    store=MemoryStore(tmp_path/'memories.sqlite3')
    with pytest.raises(ValueError): store.add('sombra',value)
    assert store.snapshot('sombra')[2]==[]


def test_unicode_and_whitespace_are_normalized():
    assert clean_memory('  Me gusta\n dibujar 🐉.  ')=='Me gusta dibujar 🐉.'


def test_corrupted_or_foreign_database_is_preserved(tmp_path):
    corrupt=tmp_path/'broken.sqlite3'
    corrupt.write_bytes(b'User file, not a database')
    before=corrupt.read_bytes()
    with pytest.raises(MemoryStoreError): MemoryStore(corrupt)
    assert corrupt.read_bytes()==before
    foreign=tmp_path/'other.sqlite3'
    with sqlite3.connect(foreign) as connection:
        connection.execute('CREATE TABLE original(value TEXT)')
        connection.execute("INSERT INTO original VALUES('preserve this')")
    before=foreign.read_bytes()
    with pytest.raises(MemoryStoreError): MemoryStore(foreign)
    assert foreign.read_bytes()==before


def test_two_store_instances_do_not_overwrite_each_other(tmp_path):
    path=tmp_path/'memories.sqlite3'
    first,second=MemoryStore(path),MemoryStore(path)
    first.add('sombra','Me gusta dibujar.')
    second.add('sombra','Me gusta leer.')
    assert len(first.snapshot('sombra')[2])==2
    assert first.snapshot('sombra')==second.snapshot('sombra')


def test_locked_database_does_not_report_a_successful_write(tmp_path):
    path=tmp_path/'memories.sqlite3'
    store=MemoryStore(path)
    with sqlite3.connect(path) as locker:
        locker.execute('BEGIN EXCLUSIVE')
        with pytest.raises(MemoryStoreError): store.add('sombra','No debe guardarse.')
        locker.rollback()
    assert store.snapshot('sombra')[2]==[]
