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


# ------------ Aggregation in IR ------------
def aggregate(manifests: list[dict], shared: dict) -> dict:
    """
    Агрегация всех манифестов и общих данных в промежуточное представление (IR).
    Args:
        manifests (list[dict]): Список манифестов модулей.
        shared (dict): Общие данные из директории _shared.
    Returns:
        dict: Промежуточное представление (IR).
    """
    ir = {
        "intents": [],
        "entities": dict(shared["entities"]),
        "slots": {},
        "responses": dict(shared["responses"]),
        "forms": {},
        "nlu": [],
        "rules": list(shared["rules"]),
        "stories": list(shared["stories"]),
        "actions": ["action_dispatch"],
        "entity_names": set(),
    }

    for manifest in manifests:
        for cmd in manifest_to_commands(manifest):
            full_intent = get_full_intent(cmd)
            command_type = get_command_type(cmd)
            ir["intents"].append(full_intent)

            # NLU
            ir["nlu"].append((
                "intent", 
                {
                    "module": cmd["module"], 
                    "name": full_intent, 
                    "examples": cmd["examples"]
                }
            ))

            # Entities (локальные)
            for entity_name, entity_def in cmd.get("entities", {}).items():
                if entity_name not in ir["entities"]:
                    ir["entities"][entity_name] = entity_def
            
            # Entity names (из примеров и локальные)
            for example in cmd["examples"]:
                ir["entity_names"].update(settings.ENTITY_RE.findall(example))
            ir["entity_names"].update(cmd.get("entities", {}).keys())

            # Slots (обновление слотов и добавление entity_names из слотов)
            for slot_name, slot_def in cmd.get("slots", {}).items():
                ir["slots"][slot_name] = slot_def
                if slot_def.get("from") == "entity":
                    ir["entity_names"].add(slot_def.get("entity", slot_name))
            
            # Responses and Rules
            if command_type == "static":
                utter = f"utter_{full_intent}"
                ir["responses"][utter] = [
                    {"text": t} for t in as_list(cmd["response"])
                ]
                ir["rules"].append({
                    "rule": full_intent, 
                    "steps": [
                        { "intent": full_intent }, 
                        { "action": utter }
                    ]
                })

            elif command_type == "dynamic":
                ir["rules"].append({
                    "rule": full_intent, 
                    "steps": [
                        { "intent": full_intent }, 
                        { "action": "action_dispatch" }
                    ]
                })

            elif command_type == "form":
                form_name = get_form_name(cmd)
                ir["forms"][form_name] = {
                    "required_slots": list(cmd["form"]["required"])
                }
                for slot, question in cmd["form"]["ask"].items():
                    ir["responses"][f"utter_ask_{slot}"] = [
                        { "text": question }
                    ]
                ir["rules"].append({
                    "rule": f"activate {form_name}",
                    "steps": [
                        { "intent": full_intent }, 
                        { "action": form_name }, 
                        { "active_loop": form_name }
                    ],
                })
                ir["rules"].append({
                    "rule": f"submit {form_name}",
                    "condition": [
                        { "active_loop": form_name }
                    ],
                    "steps": [
                        { "action": form_name },
                        { "active_loop": None },
                        { "slot_was_set": [{"requested_slot": None}] },
                        { "action": "action_dispatch" },
                    ],
                })
            
            # Локальные истории команды
            for story in cmd.get("stories", []):
                ir["stories"].append(story)
                    
    for entity_name, entity_def in ir["entities"].items():
        _add_entity_nlu(ir, entity_name, entity_def)

    ir["entity_names"] = sorted(ir["entity_names"])
    return ir


def _add_entity_nlu(ir: dict, entity_name: str, entity_def: dict):
    if entity_def.get("lookup"):
        ir["nlu"].append((
            "lookup", 
            {
                "name": entity_name, 
                "examples": entity_def["lookup"]
            }
        ))
    for canon, variants in (entity_def.get("synonyms") or {}).items():
        ir["nlu"].append((
            "synonym", 
            {
                "name": canon, 
                "examples": variants
            }
        ))


def build():
    manifests, shared = scan()
    # print(manifests)
    validate_each(manifests)
    check_collisions(manifests, shared)
    ir = aggregate(manifests, shared)
    print(json.dumps(ir, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        print(f"\nBUILDING ERROR: {e}", file=sys.stderr)
        sys.exit(1)