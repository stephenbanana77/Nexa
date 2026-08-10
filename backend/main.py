"""Nexa V0 - AI-powered data analysis workspace."""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from models import User, ApiKey, Project, Dataset, Conversation, Message, Insight, Chart, Notebook, Cell, Skill, SkillExecution, Resource, ResourceReference, Run, RunStep, Workflow, WorkflowStep, SemanticMetric, SemanticDimension, AnalysisReport
from api import auth_router, projects_router, chat_router, insights_router, notebooks_router, skills_router, resources_router, runs_router, workflows_router, connections_router, search_router, semantic_router, reports_router
from middleware import rate_limit_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from skills.builtin import register_builtin_skills
    register_builtin_skills()
    yield
    # Graceful shutdown: close DB connections and engine registry
    from tools.query_engine import engine_registry
    engine_registry.clear()
    from database.session import engine as db_engine
    db_engine.dispose()


from utils.config import settings

app = FastAPI(title="Nexa API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(insights_router)
app.include_router(notebooks_router)
app.include_router(skills_router)
app.include_router(resources_router)
app.include_router(runs_router)
app.include_router(workflows_router)
app.include_router(connections_router)
app.include_router(search_router)
app.include_router(semantic_router)
app.include_router(reports_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/api/health/ready")
async def readiness_check():
    """Readiness probe: verifies database connectivity."""
    from database.session import SessionLocal
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
