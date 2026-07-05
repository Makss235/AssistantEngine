from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from builder.config import settings as builder_settings
from panel.config import settings as panel_settings

from panel.routers import actions_router
from panel.routers import modules_router


app = FastAPI(title=f"{builder_settings.ENGINE_NAME} Panel")

@app.get("/")
def index() -> FileResponse:
    """
    Отдаёт HTML-страницу панели.
    Returns:
        FileResponse: HTML-страница панели.
    """
    return FileResponse(panel_settings.STATIC_DIR / "index.html")


app.include_router(actions_router.router)
app.include_router(modules_router.router)

app.mount("/static", StaticFiles(directory=panel_settings.STATIC_DIR), name="static")
