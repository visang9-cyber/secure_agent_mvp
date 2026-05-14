import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.super_agent import super_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    result = await super_agent.run(message=req.message)
    return {"session_id": session_id, **result}
