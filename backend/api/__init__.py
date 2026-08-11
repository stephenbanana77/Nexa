from .auth import router as auth_router
from .projects import router as projects_router
from .chat import router as chat_router
from .insights import router as insights_router
from .notebooks import router as notebooks_router
from .skills import router as skills_router
from .resources import router as resources_router
from .runs import router as runs_router
from .workflows import router as workflows_router
from .connections import router as connections_router
from .search import router as search_router
from .semantic import router as semantic_router
from .reports import router as reports_router
from .settings import router as settings_router

__all__ = [
    "auth_router", "projects_router", "chat_router", "insights_router",
    "notebooks_router", "skills_router", "resources_router", "runs_router",
    "workflows_router", "connections_router", "search_router",
    "semantic_router", "reports_router", "settings_router",
]
