import io
from contextlib import redirect_stdout

from builder.main import build
from builder.scanner import scan
from builder.validator import validate
from builder.utils import BuildError


def run_scan() -> dict:
    """
    Запускает сканирование модулей.
    Returns:
        dict: {ok, log, data?, error?} — сводка по найденным модулям и общим данным.
    """
    log = io.StringIO()
    try:
        with redirect_stdout(log):
            manifests, shared = scan()
        data = {
            "modules": len(manifests),
            "shared_entities": len(shared["entities"]),
            "shared_rules": len(shared["rules"]),
            "shared_stories": len(shared["stories"]),
            "shared_responses": len(shared["responses"]),
        }
        return {
            "ok": True, 
            "log": log.getvalue(), 
            "data": data
        }
    except BuildError as e:
        return {
            "ok": False, 
            "log": log.getvalue(), 
            "error": str(e)
        }


def run_validate() -> dict:
    """
    Сканирует и валидирует модули.
    Returns:
        dict: {ok, log, error?}.
    """
    log = io.StringIO()
    try:
        with redirect_stdout(log):
            manifests, shared = scan()
            validate(manifests, shared)
            print("Validation passed.")
        return {
            "ok": True, 
            "log": log.getvalue()
        }
    except BuildError as e:
        return {
            "ok": False, 
            "log": log.getvalue(), 
            "error": str(e)
        }


def run_build() -> dict:
    """
    Запускает полную сборку проекта.
    Returns:
        dict: {ok, log, error?}.
    """
    log = io.StringIO()
    try:
        with redirect_stdout(log):
            build()
        return {
            "ok": True, 
            "log": log.getvalue()
        }
    except BuildError as e:
        return {
            "ok": False, 
            "log": log.getvalue(), 
            "error": str(e)
        }