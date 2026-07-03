import io
from contextlib import redirect_stdout
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from builder.main import build
from builder.config import settings as builder_settings
from builder.utils import BuildError

from panel.config import settings as panel_settings


app = FastAPI(title=f"{builder_settings.ENGINE_NAME} Panel")

@app.get("/")
def index() -> FileResponse:
    """
    Отдаёт HTML-страницу панели.
    Returns:
        FileResponse: HTML-страница панели.
    """
    return FileResponse(panel_settings.STATIC_DIR / "index.html")


@app.post("/api/build")
def api_build() -> JSONResponse:
    """
    Запускает сборку билдера и возвращает её лог/ошибку.
    Returns:
        JSONResponse: Результат сборки.
    """
    log = io.StringIO()
    try:
        with redirect_stdout(log):
            build()
        return JSONResponse({
            "ok": True, 
            "log": log.getvalue()
        })
    except BuildError as e:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False, 
                "log": log.getvalue(), 
                "error": str(e)
            },
        )


app.mount("/static", StaticFiles(directory=panel_settings.STATIC_DIR), name="static")
