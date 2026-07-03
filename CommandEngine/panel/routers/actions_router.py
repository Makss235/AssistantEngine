from fastapi import APIRouter
from fastapi.responses import JSONResponse

import panel.services.actions_service as actions_service


router = APIRouter(prefix="/api", tags=["actions"])


def _respond(result: dict) -> JSONResponse:
    """
    Отдаёт результат действия билдера с корректным статусом.
    Args:
        result (dict): Результат действия билдера.
    Returns:
        JSONResponse: Результат действия билдера с корректным статусом.
    """
    return JSONResponse(status_code=200 if result["ok"] else 400, content=result)


@router.post("/scan")
def api_scan() -> JSONResponse:
    """
    Запускает сканирование модулей.
    Returns:
        JSONResponse: Результат сканирования модулей.
    """
    return _respond(actions_service.run_scan())


@router.post("/validate")
def api_validate() -> JSONResponse:
    """
    Запускает валидацию модулей без генерации файлов.
    Returns:
        JSONResponse: Результат валидации модулей.
    """
    return _respond(actions_service.run_validate())


@router.post("/build")
def api_build() -> JSONResponse:
    """
    Запускает полную сборку проекта.
    Returns:
        JSONResponse: Результат сборки проекта.
    """
    return _respond(actions_service.run_build())
