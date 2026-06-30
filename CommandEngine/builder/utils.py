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


def full_intent(m: dict) -> str:
    return f"{m['module']}_{m['intent']}"


def form_name(m: dict) -> str:
    return f"{full_intent(m)}_form"


def command_type(m: dict) -> str:
    if "form" in m and "handler" in m:
        return "form"
    if "handler" in m:
        return "dynamic"
    if "response" in m:
        return "static"
    raise BuildError(
        f"The module '{m['module']}': command without 'handler', 'form' and 'response'"
    )


def as_list(value) -> list:
    return value if isinstance(value, list) else [value]