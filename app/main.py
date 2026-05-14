from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router as api_router
from app.api.mock_schedule import router as mock_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(api_router, prefix="/api/v1")
app.include_router(mock_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
