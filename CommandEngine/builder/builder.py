import sys

import jsonschema
import yaml

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
    if not settings.MODULES_PATH.exists():
        raise BuildError(f"The modules directory does not exist: {settings.MODULES_PATH}")
    
    manifests = []
    for directory in sorted(settings.MODULES_PATH.iterdir()):
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
    path = settings.SHARED_PATH / name
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
def aggregate_in_ir(manifests: list[dict], shared: dict) -> dict:
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
    """
    Добавление NLU данных для сущности в промежуточное представление (IR).
    Args:
        ir (dict): Промежуточное представление.
        entity_name (str): Имя сущности.
        entity_def (dict): Определение сущности.
    """
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


# ------------ Serialization of IR to YAML ------------
def serialize_nlu(ir: dict):
    """
    Генерация файла nlu.yml из промежуточного представления (IR).
    Args:
        ir (dict): Промежуточное представление.
    """
    lines = [settings.GEN_HEADER, f'version: "{settings.RASA_VERSION}"', "", "nlu:"]
    for kind, payload in ir["nlu"]:
        if kind == "intent":
            lines.append(f"# from module: {payload['module']}")
            lines.append(f"- intent: {payload['name']}")
        elif kind == "lookup":
            lines.append(f"- lookup: {payload['name']}")
        elif kind == "synonym":
            lines.append(f"- synonym: {payload['name']}")
        lines.append("  examples: |")
        lines += [f"    - {ex}" for ex in payload["examples"]]
        lines.append("")
    (settings.RASA_DATA_PATH / "nlu.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def serialize_domain(ir: dict):
    """
    Генерация файла domain.yml из промежуточного представления (IR).
    Args:
        ir (dict): Промежуточное представление.
    """
    domain = {
        "version": settings.RASA_VERSION,
        "intents": ir["intents"],
        "entities": ir["entity_names"],
        "slots": {
            slot_name: {
                "type": slot_def.get("type", "text"),
                "mappings": [
                    _slot_mapping(slot_name, slot_def)
                ],
            }
            for slot_name, slot_def in ir["slots"].items()
        },
        "responses": ir["responses"],
        "actions": ir["actions"],
    }
    if ir["forms"]:
        domain["forms"] = ir["forms"]
    domain["session_config"] = {
        "session_expiration_time": 60,
        "carry_over_slots_to_new_session": True,
    }
    (settings.RASA_PATH / "domain.yml").write_text(settings.GEN_HEADER + _dump(domain), encoding="utf-8")


def _slot_mapping(slot_name: str, slot_def: dict) -> dict:
    """
    Создание словаря для slot mapping в domain.yml на основе определения слота.
    Args:
        slot_name (str): Имя слота.
        slot_def (dict): Определение слота.
    Returns:
        dict: Словарь для slot mapping.
    Raises:
        BuildError: Если указано неизвестное значение "from" в определении слота.
    """
    src = slot_def.get("from", "entity")
    if src == "entity":
        return {
            "type": "from_entity", 
            "entity": slot_def.get("entity", slot_name)
        }
    if src == "text":
        return {
            "type": "from_text"
        }
    if src == "intent":
        return {
            "type": "from_intent", 
            "value": slot_def.get("value", True)
        }
    raise BuildError(f"The slot '{slot_name}': unknown source from={src!r}")


def serialize_rules(ir: dict):
    """
    Генерация файла rules.yml из промежуточного представления (IR).
    Args:
        ir (dict): Промежуточное представление.
    """
    (settings.RASA_DATA_PATH / "rules.yml").write_text(
        settings.GEN_HEADER + _dump({
            "version": settings.RASA_VERSION, 
            "rules": ir["rules"]
        }), encoding="utf-8"
    )


def serialize_stories(ir: dict):
    """
    Генерация файла stories.yml из промежуточного представления (IR).
    Args:
        ir (dict): Промежуточное представление.
    """
    path = settings.RASA_DATA_PATH / "stories.yml"
    if ir["stories"]:
        path.write_text(
            settings.GEN_HEADER + _dump({
                "version": settings.RASA_VERSION, 
                "stories": ir["stories"]
            }), encoding="utf-8"
        )
    elif path.exists():
        path.unlink()


def _dump(data: dict) -> str:
    """
    Сериализация словаря в YAML.
    Args:
        data (dict): Словарь для сериализации.
    Returns:
        str: Строка в формате YAML.
    """
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)


def build():
    print(f"{settings.ENGINE_NAME} builder, version {settings.ENGINE_VERSION}")
    manifests, shared = scan()
    print(f"Found {len(manifests)} modules, {len(shared['entities'])} shared entities, {len(shared['rules'])} shared rules, "
          f"{len(shared['stories'])} shared stories, {len(shared['responses'])} shared responses")

    validate_each(manifests)
    check_collisions(manifests, shared)
    print("Validation passed, generating Rasa files...")

    ir = aggregate_in_ir(manifests, shared)
    settings.RASA_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    serialize_nlu(ir)
    serialize_domain(ir)
    serialize_rules(ir)
    serialize_stories(ir)

    print(f"Rasa files successfully generated in {settings.RASA_DATA_PATH} and {settings.RASA_PATH}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        print(f"\nBUILDING ERROR: {e}", file=sys.stderr)
        sys.exit(1)