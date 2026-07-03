from fastapi import APIRouter, HTTPException

import panel.services.modules_service as modules_service

import panel.services.utils as panel_utils


router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("")
def list_modules() -> dict:
    """
    Возвращает список модулей с метаданными.
    Returns:
        dict: {ok, data} - список модулей.
    """
    return {"ok": True, "data": modules_service.list_modules()}


@router.get("/{name}")
def module_detail(name: str) -> dict:
    """
    Возвращает подробности модуля: файлы и разобранный манифест.
    Args:
        name (str): Имя модуля.
    Returns:
        dict: {ok, data} - подробности модуля.
    Raises:
        HTTPException: 400 - некорректное имя модуля, 404 - модуль не найден.
    """
    try:
        return {"ok": True, "data": modules_service.module_detail(name)}
    except panel_utils.PanelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/files/{filename}")
def read_file(name: str, filename: str) -> dict:
    """
    Возвращает содержимое файла модуля для просмотра/подсветки.
    Args:
        name (str): Имя модуля.
        filename (str): Имя файла внутри модуля.
    Returns:
        dict: {ok, data} - содержимое файла.
    Raises:
        HTTPException: 400 - некорректное имя модуля или файла, 404 - модуль или файл не найден.
    """
    try:
        return {"ok": True, "data": modules_service.read_module_file(name, filename)}
    except panel_utils.PanelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{name}/files/{filename}")
def write_file(name: str, filename: str) -> dict:
    """
    Сохранение файла модуля (пока не реализовано).
    Args:
        name (str): Имя модуля.
        filename (str): Имя файла внутри модуля.
    Returns:
        dict: {ok, data} - результат сохранения.
    Raises:
        HTTPException: 501 - не реализовано.
    """
    raise HTTPException(status_code=501, detail="File editing is not implemented yet")
