"""Límites y normalización de recuerdos explícitos del usuario."""
import unicodedata

MAX_MEMORIES = 12
MAX_MEMORY_LENGTH = 240


def clean_memory(value):
    if not isinstance(value, str):
        raise ValueError('Escribe el dato que quieres recordar.')
    value = ' '.join(value.split())
    value = ''.join(c for c in value if not unicodedata.category(c).startswith('C')).strip()
    if not value:
        raise ValueError('Escribe el dato que quieres recordar.')
    if len(value) > MAX_MEMORY_LENGTH:
        raise ValueError('Resume el recuerdo en un máximo de 240 caracteres.')
    return value
