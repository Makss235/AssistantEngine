import yaml

from builder.config import settings
from builder.utils import *


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
    (settings.RASA_DATA_DIR / "nlu.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    (settings.RASA_DIR / "domain.yml").write_text(settings.GEN_HEADER + _dump(domain), encoding="utf-8")


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
    (settings.RASA_DATA_DIR / "rules.yml").write_text(
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
    stories_file = settings.RASA_DATA_DIR / "stories.yml"
    if ir["stories"]:
        stories_file.write_text(
            settings.GEN_HEADER + _dump({
                "version": settings.RASA_VERSION, 
                "stories": ir["stories"]
            }), encoding="utf-8"
        )
    elif stories_file.exists():
        stories_file.unlink()


def _dump(data: dict) -> str:
    """
    Сериализация словаря в YAML.
    Args:
        data (dict): Словарь для сериализации.
    Returns:
        str: Строка в формате YAML.
    """
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)