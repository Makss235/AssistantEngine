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


@router.get("/{module_name}")
def module_detail(module_name: str) -> dict:
    """
    Возвращает подробности модуля: файлы и разобранный манифест.
    Args:
        module_name (str): Имя модуля.
    Returns:
        dict: {ok, data} - подробности модуля.
    Raises:
        HTTPException: 400 - некорректное имя модуля, 404 - модуль не найден.
    """
    try:
        return {"ok": True, "data": modules_service.module_detail(module_name)}
    except panel_utils.PanelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{module_name}/files/{file_name}")
def read_file(module_name: str, file_name: str) -> dict:
    """
    Возвращает содержимое файла модуля для просмотра/подсветки.
    Args:
        module_name (str): Имя модуля.
        file_name (str): Имя файла внутри модуля.
    Returns:
        dict: {ok, data} - содержимое файла.
    Raises:
        HTTPException: 400 - некорректное имя модуля или файла, 404 - модуль или файл не найден.
    """
    try:
        return {"ok": True, "data": modules_service.read_module_file(module_name, file_name)}
    except panel_utils.PanelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{module_name}/files/{file_name}")
def write_file(module_name: str, file_name: str) -> dict:
    """
    Сохранение файла модуля (пока не реализовано).
    Args:
        module_name (str): Имя модуля.
        file_name (str): Имя файла внутри модуля.
    Returns:
        dict: {ok, data} - результат сохранения.
    Raises:
        HTTPException: 501 - не реализовано.
    """
    raise HTTPException(status_code=501, detail="File editing is not implemented yet")
