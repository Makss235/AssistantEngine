import pytest

from builder.utils import *


def test_get_full_intent():
    assert get_full_intent({
        "module": "music", 
        "intent": "play"
    }) == "music_play"


def test_get_form_name():
    assert get_form_name({
        "module": "taxi", 
        "intent": "order"
    }) == "taxi_order_form"


@pytest.mark.parametrize(
    "cmd, expected",
    [
        ({"response": ["hi"]}, "static"),
        ({"handler": {"type": "function"}}, "dynamic"),
        ({"form": {}, "handler": {"type": "function"}}, "form")
    ],
)
def test_get_command_type(cmd, expected):
    cmd = {
        "module": "m", 
        "intent": "i", 
        **cmd
    }
    assert get_command_type(cmd) == expected


def test_get_command_type_form_requires_handler():
    cmd = {
        "module": "m", 
        "intent": "i", 
        "form": {}
    }
    with pytest.raises(BuildError):
        get_command_type(cmd)


def test_get_command_type_empty_raises():
    cmd = {
        "module": "m", 
        "intent": "i"
    }
    with pytest.raises(BuildError):
        get_command_type(cmd)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("x", ["x"]),
        (["a", "b"], ["a", "b"]),
        ([], []),
        (1, [1]),
    ],
)
def test_as_list(value, expected):
    assert as_list(value) == expected


def test_load_json_ok(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    assert load_json(p) == {"k": 1}


def test_load_json_broken_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ bad json", encoding="utf-8")
    with pytest.raises(BuildError):
        load_json(p)


# ------------ manifest_to_commands ------------
def test_single_command_manifest():
    manifest = {
        "module": "greeting", 
        "intent": "hi", 
        "examples": ["привет"]
    }
    cmds = manifest_to_commands(manifest)
    assert cmds == [manifest]


def test_commands_list_gets_module_and_dir():
    manifest = {
        "module": "music",
        "__dir": "/some/dir",
        "commands": [
            {
                "intent": "play", 
                "examples": ["e"]
            },
            {
                "intent": "stop", 
                "examples": ["e"]
            },
        ],
    }
    cmds = manifest_to_commands(manifest)
    assert len(cmds) == 2
    assert all(c["module"] == "music" for c in cmds)
    assert all(c["__dir"] == "/some/dir" for c in cmds)
    assert [c["intent"] for c in cmds] == ["play", "stop"]


def test_global_entities_merged_into_each_command():
    manifest = {
        "module": "music",
        "entities": {
            "artist": {
                "lookup": ["queen"]
            }
        },
        "commands": [
            {
                "intent": "play", 
                "examples": ["e"]
            }
        ],
    }
    cmds = manifest_to_commands(manifest)
    assert cmds[0]["entities"] == {
        "artist": {
            "lookup": ["queen"]
        }
    }


def test_local_entity_overrides_global():
    manifest = {
        "module": "music",
        "entities": {
            "artist": {
                "lookup": ["queen"]
            }
        },
        "commands": [
            {
                "intent": "play",
                "examples": ["e"],
                "entities": {
                    "artist": {
                        "lookup": ["кино"]
                    }
                },
            }
        ],
    }
    cmds = manifest_to_commands(manifest)
    # локальное определение переопределяет глобальное
    assert cmds[0]["entities"] == {
        "artist": {
            "lookup": ["кино"]
        }
    }


def test_no_entities_key_when_none_declared():
    manifest = {
        "module": "m",
        "commands": [
            {
                "intent": "i", 
                "examples": ["e"]
            }
        ],
    }
    cmds = manifest_to_commands(manifest)
    assert "entities" not in cmds[0]
