import uvicorn

from panel.config import settings


def start() -> None:
    """
    Точка входа CLI
    """
    uvicorn.run(
        "panel.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )


if __name__ == "__main__":
    start()
