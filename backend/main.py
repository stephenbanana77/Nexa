"""Nexa V0 - AI-powered data analysis workspace."""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from models import User, ApiKey, Project, Dataset, Conversation, Message, Insight, Chart, Notebook, Cell, Skill, SkillExecution, Resource, ResourceReference, Run, RunStep, Workflow, WorkflowStep
from api import auth_router, projects_router, chat_router, insights_router, notebooks_router, skills_router, resources_router, runs_router, workflows_router, connections_router, search_router
from middleware import rate_limit_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Register built-in skills
    from skills.builtin import register_builtin_skills
    register_builtin_skills()
    yield


app = FastAPI(title="Nexa API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
