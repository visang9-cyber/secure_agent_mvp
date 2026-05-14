from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Secure Agent MVP"}
