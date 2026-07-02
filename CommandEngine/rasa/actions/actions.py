import sys
from pathlib import Path
from typing import Any

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# Добавление пути к каталогу CommandEngine в sys.path для корректного импорта модулей
CORE_ENGINE_DIR = Path(__file__).resolve().parents[2]
if str(CORE_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_ENGINE_DIR))

from registry import REGISTRY


class ActionDispatch(Action):
    def name(self) -> str:
        return "action_dispatch"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: dict[str, Any]) -> list[dict[str, Any]]:
        intent = (tracker.latest_message or {}).get("intent", {}).get("name")
        slots = {k: v for k, v in tracker.current_slot_values().items() if v is not None}
        entities = {
            e["entity"]: e["value"]
            for e in (tracker.latest_message or {}).get("entities", [])
        }

        handler = REGISTRY.get(intent)
        if handler is None:
            dispatcher.utter_message(text="Команда пока не поддерживается.")
            return []

        result = handler(slots, entities) or {}
        if result.get("text"):
            dispatcher.utter_message(text=result["text"])
        return result.get("events", [])