"""Chat API with SSE streaming and conversation memory."""
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
    conversation_id: str | None = None  # None = create new conversation


def get_conversation_history(conv_id: str) -> list[dict]:
    """Load previous messages from a conversation."""
    db = SessionLocal()
    try:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
    finally:
        db.close()


def save_message(conv_id: str, role: str, content: str, meta: dict | None = None):
    """Save a message to the conversation."""
    db = SessionLocal()
    try:
        msg = Message(
            conversation_id=conv_id,
            role=role,
            content=content,
            metadata_=meta or {},
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

    # Conversation management: reuse or create
    conv_id = req.conversation_id
    if conv_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.project_id == req.project_id,
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(project_id=req.project_id, title=req.message[:80])
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # Save user message
    save_message(conv_id, "user", req.message)

    # Load history for context
    history = get_conversation_history(conv_id)

    # Run agent with history
    controller = AgentController(req.project_id, req.message, history=history, user_id=current_user.id)

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

        # Save assistant response
        save_message(conv_id, "assistant", full_response, {
            "sql": last_event.get("sql"),
            "columns": last_event.get("columns"),
            "rows": last_event.get("rows"),
            "row_count": last_event.get("row_count"),
            "conversation_id": conv_id,
        })

        # Register chart as Resource if generated
        chart_config = last_event.get("chart_config")
        if chart_config:
            import uuid
            from resources.registry import register_resource
            chart_id = str(uuid.uuid4())
            register_resource(
                resource_type="chart",
                resource_id=chart_id,
                name=chart_config.get("title", "Chat Chart"),
                project_id=req.project_id,
                description=f"Auto-generated from chat analysis",
                metadata={"chart_config": chart_config},
            )

        # Send conversation_id in done event for frontend
        yield {
            "event": "conversation_created",
            "data": json.dumps({"event": "conversation_created", "conversation_id": conv_id}),
        }

    return EventSourceResponse(event_stream())


@router.get("/conversations/{project_id}")
def list_conversations(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversations for a project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    convs = (
        db.query(Conversation)
        .filter(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
        }
        for c in convs
    ]
