"""Chat API with SSE streaming."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from database import get_db
from database.session import SessionLocal
from models.user import User
from models.project import Project, Dataset, Conversation, Message
from services.auth import get_current_user
from agents.controller import AgentController

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    project_id: str
    message: str


def save_assistant_message(conv_id: str, content: str, sql: str | None, columns: list | None, rows: list | None, row_count: int | None):
    db = SessionLocal()
    try:
        msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=content,
            metadata_={
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
            },
        )
        db.add(msg)
        db.commit()
    finally:
        db.close()


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == req.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = (
        db.query(Dataset)
        .filter(Dataset.project_id == req.project_id)
        .order_by(Dataset.created_at.desc())
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=400, detail="No dataset uploaded")

    conv = Conversation(project_id=req.project_id, title=req.message[:80])
    db.add(conv)
    db.commit()
    db.refresh(conv)
    conv_id = conv.id

    user_msg = Message(conversation_id=conv_id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()

    controller = AgentController(req.project_id, req.message)

    async def event_stream():
        full_response = ""
        last_event = {}
        async for event in controller.run():
            last_event = event
            if event["event"] == "insight":
                full_response = event.get("summary", "")
            yield {
                "event": event["event"],
                "data": json.dumps(event, default=str),
            }

        save_assistant_message(
            conv_id=conv_id,
            content=full_response,
            sql=last_event.get("sql"),
            columns=last_event.get("columns"),
            rows=last_event.get("rows"),
            row_count=last_event.get("row_count"),
        )

    return EventSourceResponse(event_stream())
