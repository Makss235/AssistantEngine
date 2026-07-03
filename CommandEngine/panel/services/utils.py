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
        "name": directory.name,
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


def _resolve_module_dir(name: str) -> Path:
    """
    Резолвит каталог модуля с защитой от выхода за пределы MODULES_DIR.
    Args:
        name (str): Имя модуля.
    Returns:
        Path: Путь к каталогу модуля.
    Raises:
        PanelError: Некорректное имя модуля.
        FileNotFoundError: Модуль не найден.
    """
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise PanelError(f"Invalid module name: {name!r}")

    base = builder_settings.MODULES_DIR.resolve()
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PanelError(f"Path escapes modules directory: {name!r}")

    if not target.is_dir():
        raise FileNotFoundError(f"Module not found: {name}")
    return target


def _resolve_module_file(name: str, filename: str) -> Path:
    """
    Резолвит файл модуля с защитой от path traversal и проверкой типа.
    Args:
        name (str): Имя модуля.
        filename (str): Имя файла внутри модуля.
    Returns:
        Path: Путь к файлу модуля.
    Raises:
        PanelError: Некорректное имя файла.
        FileNotFoundError: Файл не найден.
    """
    directory = _resolve_module_dir(name)

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise PanelError(f"Invalid file name: {filename!r}")

    base = builder_settings.MODULES_DIR.resolve()
    target = (directory / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PanelError(f"Path escapes modules directory: {filename!r}")

    if target.suffix not in panel_settings.ALLOWED_EXT:
        raise PanelError(f"File type not allowed: {target.suffix!r}")
    return target