from builder.config import settings
from builder.utils import *


# ------------ Scanning data ------------
def scan() -> tuple[list[dict], dict]:
    """
    Сканирование модулей и сбор их манифестов, а также общих данных из _shared.
    Returns:
        tuple[list[dict], dict]: Список манифестов модулей и общий словарь с данными из _shared.
    Raises:
        BuildError: Директория модулей не существует.
    """
    if not settings.MODULES_DIR.exists():
        raise BuildError(f"The modules directory does not exist: {settings.MODULES_DIR}")
    
    manifests = []
    for directory in sorted(settings.MODULES_DIR.iterdir()):
        if not directory.is_dir() or directory.name == "_shared":
            continue

        manifest_file = directory / "manifest.json"
        if not manifest_file.exists():
            print(f"Warning: skipping '{directory.name}': manifest.json not found")
            continue
        manifest_json = load_json(manifest_file)
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
    file_from_shared = settings.SHARED_DIR / name
    return load_json(file_from_shared) if file_from_shared.exists() else default_json