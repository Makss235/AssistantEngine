import sys

from config import settings
from utils import BuildError, load_json


def scan() -> tuple[list[dict], dict]:
    if not settings.MODULES.exists():
        raise BuildError(f"The modules directory does not exist: {settings.MODULES}")
    
    manifests = []
    for directory in sorted(settings.MODULES.iterdir()):
        if not directory.is_dir() or directory.name == "_shared":
            continue
        manifest = directory / "manifest.json"
        if not manifest.exists():
            print(f"Warning: skipping '{directory.name}': manifest.json not found")
            continue
        m = load_json(manifest)
        m["__dir"] = directory
        manifests.append(m)

    shared = {
        "entities": _load_shared("entities.json", {}),
        "rules": _load_shared("rules.json", []),
        "stories": _load_shared("stories.json", []),
        "responses": _load_shared("responses.json", {}),
    }
    return manifests, shared


def _load_shared(name: str, default_json: dict | list) -> dict | list:
    path = settings.SHARED / name
    return load_json(path) if path.exists() else default_json


def build():
    print(scan())


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        print(f"\nBUILDING ERROR: {e}", file=sys.stderr)
        sys.exit(1)