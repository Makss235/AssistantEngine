import pytest

from builder.scanner import scan
from builder.validator import validate, validate_each, check_collisions
from builder.utils import BuildError
from conftest import static_cmd, dynamic_cmd


def _scan_and_validate(project):
    manifests, shared = scan()
    validate(manifests, shared)
    return manifests, shared


# ------------ Positive ------------
def test_valid_static_module_passes(project):
    project.write_module("greeting", {
        "module": "greeting", 
        **static_cmd("hi")
    })
    _scan_and_validate(project)


def test_valid_entity_declared_in_shared_passes(project):
    project.write_module("weather", {
        "module": "weather",
        "intent": "ask",
        "examples": ["погода в [москве](city)"],
        "response": ["Солнечно"],
    })
    project.write_shared("entities.json", {
        "city": {
            "lookup": ["москва"]
        }
    })
    _scan_and_validate(project)


def test_valid_function_handler_with_handlerpy_passes(project):
    project.write_module("act",{
            "module": "act", 
            **dynamic_cmd("go")
        },
        handler="def run(slots, entities):\n    return {'text': 'ok'}\n",
    )
    _scan_and_validate(project)


# ------------ validate_each ------------
def test_module_name_mismatch_folder(project):
    project.write_module("greeting", {
        "module": "hello", 
        **static_cmd()
    })
    with pytest.raises(BuildError, match="does not match folder name"):
        _scan_and_validate(project)


def test_commands_and_toplevel_fields_conflict(project):
    project.write_module("m", {
        "module": "m",
        "intent": "top",
        "examples": ["e"],
        "commands": [static_cmd("c")],
    })
    with pytest.raises(BuildError, match="both 'commands' and top-level"):
        _scan_and_validate(project)


def test_command_without_intent_or_examples(project):
    manifest = {
        "module": "m",
        "__dir": project.modules_dir / "m",
        "commands": [{
            "intent": "i"
        }],
    }
    with pytest.raises(BuildError):
        validate_each([manifest])


def test_schema_rejects_unknown_field(project):
    project.write_module("m", {
        "module": "m", 
        "bogus": 1, **static_cmd()
    })
    with pytest.raises(BuildError):
        _scan_and_validate(project)


def test_schema_rejects_bad_intent_name(project):
    project.write_module("m", {
        "module": "m", 
        "intent": "Bad-Name", 
        "examples": ["e"], 
        "response": ["r"]
    })
    with pytest.raises(BuildError):
        _scan_and_validate(project)


# ------------ check_collisions: entities ------------
def test_undeclared_entity_in_example(project):
    project.write_module("m", {
        "module": "m",
        "intent": "i",
        "examples": ["включи [queen](artist)"],
        "response": ["ok"],
    })
    with pytest.raises(BuildError, match="entity 'artist' in example not declared"):
        _scan_and_validate(project)


def test_declared_local_entity_ok(project):
    project.write_module("m", {
        "module": "m",
        "intent": "i",
        "examples": ["включи [queen](artist)"],
        "entities": {"artist": {"lookup": ["queen"]}},
        "response": ["ok"],
    })
    _scan_and_validate(project)


# ------------ check_collisions: form ------------
def _form_module(form=None, slots=None):
    return {
        "module": "taxi",
        "intent": "order",
        "examples": ["вызови такси"],
        "slots": slots if slots is not None else {},
        "form": form
        if form is not None
        else {
            "required": ["from_city"], 
            "ask": {"from_city": "Откуда?"}
        },
        "handler": {
            "type": "function", 
            "name": "run"
        },
    }


def test_form_without_slots_raises(project):
    module = _form_module()
    del module["slots"]
    project.write_module("taxi", module, handler="def run(s, e):\n return {}\n")
    with pytest.raises(BuildError, match="form without slots"):
        _scan_and_validate(project)


def test_form_required_slot_not_declared(project):
    module = _form_module(
        form={
            "required": ["from_city"], 
            "ask": {"from_city": "Откуда?"}
        },
        slots={
            "other": {"from": "entity"}
        },
    )
    project.write_module("taxi", module, handler="def run(s, e):\n return {}\n")
    with pytest.raises(BuildError, match="not declared in 'slots'"):
        _scan_and_validate(project)


def test_form_ask_slot_not_in_required(project):
    module = _form_module(
        form={
            "required": ["from_city"], 
            "ask": {"to_city": "Куда?"}
        },
        slots={
            "from_city": {"from": "entity"}, 
            "to_city": {"from": "entity"}
        },
    )
    project.write_module("taxi", module, handler="def run(s, e):\n return {}\n")
    with pytest.raises(BuildError, match="not in required"):
        _scan_and_validate(project)


def test_valid_form_passes(project):
    module = _form_module(
        form={
            "required": ["from_city"], 
            "ask": {"from_city": "Откуда?"}
        },
        slots={
            "from_city": {
                "from": "entity", 
                "entity": "city"
            }
        },
    )
    module["examples"] = ["вызови такси из [москвы](city)"]
    module["entities"] = {"city": {"lookup": ["москва"]}}
    project.write_module("taxi", module, handler="def run(s, e):\n return {}\n")
    _scan_and_validate(project)


# ------------ check_collisions: handler.py ------------
def test_function_handler_without_handlerpy(project):
    project.write_module("act", {
        "module": "act", 
        **dynamic_cmd("go")
    })
    with pytest.raises(BuildError, match="not exists handler.py"):
        _scan_and_validate(project)


def test_http_handler_needs_no_handlerpy(project):
    project.write_module("act", {
        "module": "act",
        "intent": "go",
        "examples": ["сделай"],
        "handler": {"type": "http", "url": "https://x/y"},
    })
    _scan_and_validate(project)
