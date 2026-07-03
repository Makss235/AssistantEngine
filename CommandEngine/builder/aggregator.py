from builder.config import settings
from builder.utils import *


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