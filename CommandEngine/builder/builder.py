import sys

from config import settings


class BuildError(Exception):
    pass


def build():
    print(f"BUILDER: {settings.BUILDER}")
    print(f"CORE: {settings.CORE}")
    print(f"MODULES: {settings.MODULES}")
    print(f"SHARED: {settings.SHARED}")
    print(f"RASA: {settings.RASA}")
    print(f"DATA: {settings.DATA}")
    print(f"SCHEMA_FILE: {settings.SCHEMA_FILE}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        # print(f"\nОШИБКА СБОРКИ: {e}", file=sys.stderr)
        # sys.exit(1)
        print("error")