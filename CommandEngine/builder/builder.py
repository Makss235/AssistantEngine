import sys

import jsonschema

from config import settings
from utils import *


# ------------ Scanning data ------------
def scan() -> tuple[list[dict], dict]:
    """
    Сканирование модулей и сбор их манифестов, а также общих данных из _shared.
    Returns:
        tuple[list[dict], dict]: Список манифестов модулей и общий словарь с данными из _shared.
    Raises:
        BuildError: Директория модулей не существует.
    """
    if not settings.MODULES.exists():
        raise BuildError(f"The modules directory does not exist: {settings.MODULES}")
    
    manifests = []
    for directory in sorted(settings.MODULES.iterdir()):
        if not directory.is_dir() or directory.name == "_shared":
            continue

        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            print(f"Warning: skipping '{directory.name}': manifest.json not found")
            continue
        manifest_json = load_json(manifest_path)
        manifest_json["__dir"] = directory
        manifests.append(manifest_json)

    shared = {
        "entities": _load_shared("entities.json", {}),
        "rules": _load_shared("rules.json", []),
        "stories": _load_shared("stories.json", []),
        "responses": _load_shared("responses.json", {}),
    }
    return manifests, shared


def _load_shared(name: str, default_json: dict | list) -> dict | list:
    """
    Загрузка общих данных из директории _shared.
    Args:
        name (str): Имя файла в директории _shared.
        default_json (dict | list): Значение по умолчанию, если файл не найден.
    Returns:
        dict | list: Загруженные данные или значение по умолчанию.
    """
    path = settings.SHARED / name
    return load_json(path) if path.exists() else default_json


# ------------ Validation ------------
def validate_each(manifests: list[dict]):
    """
    Проверка каждого манифеста на соответствие схеме и корректность данных.
    Args:
        manifests (list[dict]): Список манифестов модулей.
    Raises:
        BuildError: Манифест не соответствует схеме или содержит ошибки.
    """
    schema = load_json(settings.SCHEMA_FILE)
    for manifest in manifests:
        # Проверка на соответствие схеме, если таковая имеется
        if schema is not None:
            payload = {k: v for k, v in manifest.items() if not k.startswith("__")}
            try:
                jsonschema.validate(payload, schema)
            except jsonschema.ValidationError as e:
                loc = " -> ".join(str(p) for p in e.absolute_path) or "(root)"
                raise BuildError(f"The module '{manifest.get('module', manifest['__dir'].name)}': {loc}: {e.message}")
        else:
            print(f"Warning: schema file '{settings.SCHEMA_FILE}' not found, skipping schema validation")
        
        # Проверка на соответствие имени модуля имени каталога
        if manifest["module"] != manifest["__dir"].name:
            raise BuildError(f"The module '{manifest['module']}': name in manifest does not match folder name '{manifest['__dir'].name}'")
        
        # Проверка команд на пересечение внутренних и верхнего уровня интентов
        if "commands" in manifest and ("intent" in manifest or "examples" in manifest):
            raise BuildError(f"The module '{manifest['module']}': there are both 'commands' and top-level 'intent'/'examples'")
        
        # Проверка каждой команды на наличие необходимых полей
        for cmd in manifest_to_commands(manifest):
            if "intent" not in cmd or "examples" not in cmd:
                raise BuildError(f"The module '{manifest['module']}': command without required 'intent' or 'examples'")


def check_collisions(manifests: list[dict], shared: dict):
    """
    Проверка на пересечение сущностей, слотов и интентов между модулями и общими данными.
    Args:
        manifests (list[dict]): Список манифестов модулей.
        shared (dict): Общие данные из директории _shared.
    Raises:
        BuildError: Найдено пересечение сущностей, слотов или интентов.
    """
    for manifest in manifests:
        for cmd in manifest_to_commands(manifest):
            # Проверка на наличие всех сущностей, используемых в примерах, в объявленных сущностях
            declared = set(cmd.get("entities", {})) | set(shared["entities"])
            for example in cmd["examples"]:
                for entity in settings.ENTITY_RE.findall(example):
                    if entity not in declared:
                        raise BuildError(f"The module '{cmd['module']}', intent '{cmd['intent']}': entity '{entity}' in example not declared: {example!r}")

            if "form" in cmd:
                if cmd.get("slots") is None:
                    raise BuildError(f"The module '{cmd['module']}', intent '{cmd['intent']}': form without slots")
                
                # Проверка на наличие всех слотов, используемых в форме, в объявленных слотах
                for slot in cmd["form"]["required"]:
                    if slot not in cmd.get("slots", {}):
                        raise BuildError(f"The module '{cmd['module']}', intent '{cmd['intent']}': form slot '{slot}' not declared in 'slots'")
                
                # Проверка на наличие всех слотов, используемых в ask, в required
                for slot in cmd["form"]["ask"]:
                    if slot not in cmd["form"]["required"]:
                        raise BuildError(f"The module '{cmd['module']}', intent '{cmd['intent']}': form slot '{slot}' not in required")

            # Проверка на наличие handler.py, если handler.type=function      
            handler = cmd.get("handler")
            if handler and handler["type"] == "function" and not (cmd["__dir"] / "handler.py").exists():
                raise BuildError(f"The module '{cmd['module']}': handler.type=function, but not exists handler.py")


def build():
    manifests, shared = scan()
    # print(manifests)
    validate_each(manifests)
    check_collisions(manifests, shared)


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        print(f"\nBUILDING ERROR: {e}", file=sys.stderr)
        sys.exit(1)