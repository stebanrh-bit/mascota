import pytest

from mascota.domain import CHARACTERS, Preferences, clamp_position


def test_new_preferences_choose_black_dragon(tmp_path):
    preferences = Preferences(tmp_path / "new" / "preferences.json")
    assert preferences.character == "sombra"
    assert CHARACTERS[preferences.character].body == "#11141e"
    assert preferences.roaming is True


def test_choice_survives_restart(tmp_path):
    path = tmp_path / "nested" / "preferences.json"
    preferences = Preferences(path)
    preferences.character = "nimbo"
    preferences.roaming = False
    preferences.save()
    restored = Preferences(path)
    assert restored.character == "nimbo"
    assert restored.roaming is False
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize("content", ['broken json', '[]', '{"character": ["sombra"]}', '{"character":"unknown","roaming":"yes"}'])
def test_invalid_preferences_recover_without_overwriting_file(tmp_path, content):
    path = tmp_path / "preferences.json"
    path.write_text(content)
    preferences = Preferences(path)
    assert preferences.character == "sombra"
    assert preferences.roaming is True
    assert path.read_text() == content


@pytest.mark.parametrize("position,size,bounds,expected", [
    ((-2000, 600), (460, 520), (-1920, 0, 1920, 1080), (-1920, 560)),
    ((2000, -200), (460, 520), (0, 0, 1920, 1080), (1460, 0)),
    ((600, 600), (460, 520), (20, 30, 200, 200), (20, 30)),
])
def test_visible_position_on_multiple_monitors(position, size, bounds, expected):
    assert clamp_position(*position, *size, bounds) == expected
