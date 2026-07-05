import jsonschema

from builder.config import settings
from builder.utils import *


# ------------ Validation ------------
def validate(manifests: list[dict], shared: dict):
    """
    Валидирует модули и общие данные.
    Args:
        manifests (list[dict]): Список манифестов модулей.
        shared (dict): Общие данные из директории _shared.
    Raises:
        BuildError: Манифест не соответствует схеме или содержит ошибки.
    """
    validate_each(manifests)
    check_collisions(manifests, shared)


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
            # Проверка на наличие всех сущностей, используемых в примерах, в объявленных сущностях (и в общих сущностях)
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