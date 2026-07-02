import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Callable

from config import settings
from utils import *


def _import_handler_module(module_path: Path, module_name: str) -> ModuleType:
    """
    Импортирует модуль handler.py из указанного пути и возвращает его как объект ModuleType.
    Args:
        module_path: Путь к директории модуля.
        module_name: Имя модуля.
    Returns:
        ModuleType: Импортированный модуль handler.py.
    """
    handler_path = module_path / "handler.py"
    spec = importlib.util.spec_from_file_location(f"ce_handler_{module_name}", handler_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_http_handler(url: str) -> Callable:
    """
    Создает функцию-обработчик, которая отправляет POST-запрос на указанный URL с данными слотов и сущностей.
    Args:
        url: URL для отправки POST-запроса.
    Returns:
        Callable: Функция-обработчик.
    """
    def run(slots: dict, entities: dict) -> dict:
        import requests

        response = requests.post(url, json={"slots": slots, "entities": entities}, timeout=10)
        response.raise_for_status()
        return response.json()

    return run


def build_registry() -> dict[str, Callable]:
    """
    Строит реестр обработчиков команд на основе манифестов модулей.
    Returns:
        dict[str, Callable]: Реестр обработчиков команд.
    """
    registry: dict[str, Callable] = {}

    for module in sorted(settings.MODULES_DIR.iterdir()):
        if not module.is_dir() or module.name == "_shared":
            continue
        manifest_file = module / "manifest.json"
        if not manifest_file.exists():
            continue
        with manifest_file.open(encoding="utf-8") as f:
            manifest = json.load(f)

        handler_module: ModuleType | None = None
        for cmd in manifest_to_commands(manifest):
            handler = cmd.get("handler")
            if not handler:
                continue

            key = get_full_intent(cmd)
            if handler["type"] == "function":
                if handler_module is None:
                    handler_module = _import_handler_module(module, manifest["module"])
                func_name = handler.get("name", "run")
                if not hasattr(handler_module, func_name):
                    raise RuntimeError(f"The module '{manifest['module']}': in handler.py there is no function '{func_name}' (for intent '{cmd['intent']}')")
                registry[key] = getattr(handler_module, func_name)

            elif handler["type"] == "http":
                registry[key] = _make_http_handler(handler["url"])
    return registry


REGISTRY: dict[str, Callable] = build_registry()
