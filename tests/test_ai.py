import json

import pytest

from mascota.ai import DEFAULT_MODEL, DEFAULT_URL, JsonLines, chat_payload, local_endpoint, model_name, personality
from mascota.domain import Preferences


@pytest.mark.parametrize('value,expected', [
    ('http://localhost', 'http://localhost:11434'),
    ('http://127.0.0.1:12345/', 'http://127.0.0.1:12345'),
    ('http://[::1]:11434', 'http://[::1]:11434'),
])
def test_only_local_endpoints_are_accepted(value, expected):
    assert local_endpoint(value) == expected


@pytest.mark.parametrize('value', [
    'https://example.com', 'http://192.168.0.2:11434', 'http://127.0.0.1.evil.test',
    'http://user:password@localhost:11434', 'http://localhost/api',
    'http://localhost:0', 'http://localhost:99999', 'http://localhost/?token=x',
    'file:///tmp/anything', 'http://localhost/#secret', None,
])
def test_external_addresses_and_embedded_credentials_are_rejected(value):
    with pytest.raises(ValueError): local_endpoint(value)


@pytest.mark.parametrize('value', ['', '../ secret', 'x' * 129, None])
def test_invalid_model_names_are_rejected(value):
    with pytest.raises(ValueError): model_name(value)


def test_stream_decoder_preserves_split_unicode_and_last_line():
    raw=(json.dumps({'message':{'content':'¡Hola, dragón! 🐉'}},ensure_ascii=False)+'\n'+json.dumps({'done':True})).encode()
    decoder=JsonLines()
    frames=[]
    for value in raw:
        frames.extend(decoder.feed(bytes([value])))
    frames.extend(decoder.feed(b'',final=True))
    assert frames==[{'message':{'content':'¡Hola, dragón! 🐉'}},{'done':True}]


@pytest.mark.parametrize('data', [b'{broken}\n', b'[]\n', b'\xff\n', b'x'*65537])
def test_stream_decoder_rejects_invalid_or_unbounded_data(data):
    with pytest.raises(ValueError): JsonLines().feed(data)


def test_context_retains_only_complete_turns_and_personality():
    history=[]
    for i in range(12):
        history.extend([{'role':'user','content':str(i)}, {'role':'assistant','content':f'Answer {i}'}])
    system=personality('Bruma','dragon','Bebé, pero con carácter.')
    payload=chat_payload(DEFAULT_MODEL, system, history, ' Hola ')
    assert payload['messages'][0]['role']=='system'
    assert 'Bruma' in payload['messages'][0]['content']
    assert payload['messages'][1]['content']=='8'
    assert len(payload['messages'])==10
    assert payload['messages'][-1]=={'role':'user','content':'Hola'}
    assert len(history)==24
    assert payload['stream'] is True


@pytest.mark.parametrize('prompt',['', '  ', 'x'*2001, None])
def test_empty_or_oversized_questions_are_rejected(prompt):
    with pytest.raises(ValueError): chat_payload(DEFAULT_MODEL,'system',[],prompt)


def test_ai_preferences_survive_and_never_store_messages(tmp_path):
    path=tmp_path/'preferences.json'
    settings=Preferences(path)
    settings.ai={'url':'http://localhost:11434','model':'qwen2.5:0.5b'}
    settings.names['sombra']='Bruma'
    settings.save()
    restored=Preferences(path)
    assert restored.ai==settings.ai
    assert restored.names==settings.names
    data=json.loads(path.read_text())
    assert set(data)=={'character','roaming','names','ai'}
    path.write_text('{"ai":{"url":"https://outside.example","model":"qwen2.5:0.5b"}}')
    assert Preferences(path).ai=={'url':DEFAULT_URL,'model':DEFAULT_MODEL}
