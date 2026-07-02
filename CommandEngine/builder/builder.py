import sys

from config import settings
from utils import *
from scanner import *
from validator import *
from aggregator import *
from serializator import *


def build():
    print(f"{settings.ENGINE_NAME} builder, version {settings.ENGINE_VERSION}")
    manifests, shared = scan()
    print(f"Found {len(manifests)} modules, {len(shared['entities'])} shared entities, {len(shared['rules'])} shared rules, "
          f"{len(shared['stories'])} shared stories, {len(shared['responses'])} shared responses")

    validate_each(manifests)
    check_collisions(manifests, shared)
    print("Validation passed, generating Rasa files...")

    ir = aggregate_in_ir(manifests, shared)
    settings.RASA_DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    serialize_nlu(ir)
    serialize_domain(ir)
    serialize_rules(ir)
    serialize_stories(ir)

    print(f"Rasa files successfully generated in {settings.RASA_DATA_PATH} and {settings.RASA_PATH}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as e:
        print(f"\nBUILDING ERROR: {e}", file=sys.stderr)
        sys.exit(1)