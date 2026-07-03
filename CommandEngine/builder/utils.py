import json
from pathlib import Path


class BuildError(Exception):
    """
    Ошибка уровня билдера (неверный манифест, пересечение интентов и т.п.)."""
    pass


def load_json(path: Path) -> dict:
    """
    Загружает JSON-файл и возвращает его содержимое как словарь.
    Args:
        path (Path): Путь к JSON-файлу.
    Returns:
        dict: Содержимое JSON-файла как словарь.
    Raises:
        BuildError: Если происходит ошибка при декодировании JSON.
    """
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise BuildError(f"Error decoding JSON from {path}: {e}")


def get_full_intent(cmd: dict) -> str:
    """
    Формирует полное имя интента в формате 'module_intent'.
    Args:
        cmd (dict): Словарь с информацией о команде.
    Returns:
        str: Полное имя интента.
    """
    return f"{cmd['module']}_{cmd['intent']}"


def get_form_name(cmd: dict) -> str:
    """
    Формирует имя формы в формате 'full_intent_form'.
    Args:
        cmd (dict): Словарь с информацией о команде.
    Returns:
        str: Имя формы.
    """
    return f"{get_full_intent(cmd)}_form"


def get_command_type(cmd: dict) -> str:
    """
    Определяет тип команды на основе её свойств.
    Args:
        cmd (dict): Словарь с информацией о команде.
    Returns:
        str: Тип команды ('form', 'dynamic', 'static').
    Raises:
        BuildError: Если команда не соответствует ни одному из известных типов.
    """
    if "form" in cmd and "handler" in cmd:
        return "form"
    if "handler" in cmd:
        return "dynamic"
    if "response" in cmd:
        return "static"
    raise BuildError(f"The module '{cmd['module']}': command without 'handler', 'form' and 'response'")


def as_list(value) -> list:
    """
    Преобразует значение в список. Если значение уже является списком, возвращает его как есть, иначе оборачивает его в список.
    Args:
        value: Значение для преобразования.
    Returns:
        list: Преобразованное значение в виде списка.
    """
    return value if isinstance(value, list) else [value]


def manifest_to_commands(manifest: dict) -> list[dict]:
    """
    Преобразует манифест в список команд.
    Args:
        manifest (dict): Словарь с информацией о манифесте.
    Returns:
        list[dict]: Список команд.
    """
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