import json
from pathlib import Path


class BuildError(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise BuildError(f"Error decoding JSON from {path}: {e}")


def get_full_intent(cmd: dict) -> str:
    return f"{cmd['module']}_{cmd['intent']}"


def get_form_name(cmd: dict) -> str:
    return f"{get_full_intent(cmd)}_form"


def get_command_type(cmd: dict) -> str:
    if "form" in cmd and "handler" in cmd:
        return "form"
    if "handler" in cmd:
        return "dynamic"
    if "response" in cmd:
        return "static"
    raise BuildError(f"The module '{cmd['module']}': command without 'handler', 'form' and 'response'")


def as_list(value) -> list:
    return value if isinstance(value, list) else [value]


def iter_commands(manifest: dict) -> list[dict]:
    if "commands" not in manifest:
        return [manifest]

    module_name = manifest["module"]
    entities = manifest.get("entities", {})
    base = {
        "module": module_name, 
        "__dir": manifest.get("__dir")
    }
    out = []

    for cmd in manifest["commands"]:
        merged = {**base, **cmd}
        if entities or "entities" in cmd:
            merged["entities"] = {**entities, **cmd.get("entities", {})}
        out.append(merged)
    return out