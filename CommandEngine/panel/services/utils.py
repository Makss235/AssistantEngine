from pathlib import Path

import builder.utils as builder_utils

from builder.config import settings as builder_settings
from panel.config import settings as panel_settings


class PanelError(Exception):
    """
    Ошибка уровня панели (некорректный запрос, недоступный путь и т.п.).
    """
    pass


def _module_info(directory: Path) -> dict:
    """
    Собирает краткую сводку по каталогу модуля.
    Args:
        directory (Path): Каталог модуля.
    Returns:
        dict: Сводка по модулю.
    """
    info = {
        "module_name": directory.name,
        "is_shared": directory.name == "_shared",
        "has_manifest": (directory / "manifest.json").exists(),
        "has_handler": (directory / "handler.py").exists(),
        "manifest_valid": None,
        "intents": [],
        "error": None,
    }

    manifest_file = directory / "manifest.json"
    if manifest_file.exists():
        try:
            manifest = builder_utils.load_json(manifest_file)
            manifest["__dir"] = directory
            info["manifest_valid"] = True
            info["intents"] = [
                cmd["intent"] for cmd in builder_utils.manifest_to_commands(manifest) if "intent" in cmd
            ]
        except builder_utils.BuildError as e:
            info["manifest_valid"] = False
            info["error"] = str(e)
    return info


def _resolve_module_dir(module_name: str) -> Path:
    """
    Резолвит каталог модуля с защитой от выхода за пределы MODULES_DIR.
    Args:
        module_name (str): Имя модуля.
    Returns:
        Path: Путь к каталогу модуля.
    Raises:
        PanelError: Некорректное имя модуля.
        FileNotFoundError: Модуль не найден.
    """
    if not module_name or module_name in (".", "..") or "/" in module_name or "\\" in module_name:
        raise PanelError(f"Invalid module name: {module_name!r}")

    base = builder_settings.MODULES_DIR.resolve()
    target = (base / module_name).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PanelError(f"Path escapes modules directory: {module_name!r}")

    if not target.is_dir():
        raise FileNotFoundError(f"Module not found: {module_name}")
    return target


def _resolve_module_file(module_name: str, file_name: str) -> Path:
    """
    Резолвит файл модуля с защитой от path traversal и проверкой типа.
    Args:
        module_name (str): Имя модуля.
        file_name (str): Имя файла внутри модуля.
    Returns:
        Path: Путь к файлу модуля.
    Raises:
        PanelError: Некорректное имя файла.
        FileNotFoundError: Файл не найден.
    """
    directory = _resolve_module_dir(module_name)

    if not file_name or "/" in file_name or "\\" in file_name or ".." in file_name:
        raise PanelError(f"Invalid file name: {file_name!r}")

    base = builder_settings.MODULES_DIR.resolve()
    target = (directory / file_name).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PanelError(f"Path escapes modules directory: {file_name!r}")

    if target.suffix not in panel_settings.ALLOWED_EXT:
        raise PanelError(f"File type not allowed: {target.suffix!r}")
    return target