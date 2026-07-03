# TODO переименовать name в module_name, filename в file_name, ext в file_ext, content в file_content

import builder.utils as builder_utils
import panel.services.utils as panel_utils

from builder.config import settings as builder_settings
from panel.config import settings as panel_settings


def list_modules() -> list[dict]:
    """
    Перечисляет каталоги модулей с метаданными.
    Returns:
        list[dict]: Список модулей с полями name, has_manifest, has_handler, intents и т.п.
    """
    base = builder_settings.MODULES_DIR
    if not base.exists():
        return []

    modules = []
    for directory in sorted(base.iterdir()):
        if not directory.is_dir():
            continue
        modules.append(panel_utils._module_info(directory))
    return modules


def module_detail(name: str) -> dict:
    """
    Возвращает подробности по модулю: метаданные, список файлов и разобранный манифест.
    Args:
        name (str): Имя модуля.
    Returns:
        dict: Детали модуля.
    Raises:
        PanelError: Некорректное имя модуля.
        FileNotFoundError: Модуль не найден.
    """
    directory = panel_utils._resolve_module_dir(name)
    info = panel_utils._module_info(directory)
    info["files"] = [
        f.name for f in sorted(directory.iterdir()) if f.is_file() and f.suffix in panel_settings.ALLOWED_EXT
    ]

    manifest_file = directory / "manifest.json"
    if manifest_file.exists():
        try:
            info["manifest"] = builder_utils.load_json(manifest_file)
        except builder_utils.BuildError as e:
            info["manifest"] = None
            info["error"] = str(e)
    else:
        info["manifest"] = None
    return info


def read_module_file(name: str, filename: str) -> dict:
    """
    Читает содержимое файла внутри модуля.
    Args:
        name (str): Имя модуля.
        filename (str): Имя файла внутри модуля.
    Returns:
        dict: {name, filename, ext, content}.
    Raises:
        PanelError: Некорректный путь или недопустимый тип файла.
        FileNotFoundError: Файл не существует.
    """
    target = panel_utils._resolve_module_file(name, filename)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {name}/{filename}")
    return {
        "name": name,
        "filename": filename,
        "ext": target.suffix,
        "content": target.read_text(encoding="utf-8"),
    }