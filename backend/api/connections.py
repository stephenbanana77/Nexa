"""Connections API — manage external data sources."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.project import Project
from services.auth import get_current_user
from tools.query_engine import engine_registry
from connections.postgresql import PostgreSQLConnector
from connections.googlesheets import GoogleSheetsConnector
from resources.registry import register_resource

router = APIRouter(prefix="/api/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    project_id: str
    name: str
    engine: str  # "postgresql" | "mysql" | "googlesheets"
    host: str = ""
    port: int = 5432
    user: str = ""
    password: str = ""
    database: str = ""
    sheet_url: str = ""


@router.post("")
def create_connection(
    req: ConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == req.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.engine == "postgresql":
        connector = PostgreSQLConnector(
            host=req.host, port=req.port, user=req.user,
            password=req.password, database=req.database,
        )
        if not connector.health_check():
            raise HTTPException(status_code=400, detail="Connection failed")
        engine_registry.register(req.project_id, connector)
    elif req.engine == "mysql":
        from tools import register_mysql, get_engine
        register_mysql(req.project_id, req.host, req.port, req.user, req.password, req.database)
        connector = get_engine(req.project_id)
    elif req.engine == "googlesheets":
        if not req.sheet_url:
            raise HTTPException(status_code=400, detail="sheet_url is required for Google Sheets")
        connector = GoogleSheetsConnector(sheet_url=req.sheet_url)
        if not connector.health_check():
            raise HTTPException(status_code=400, detail="Failed to load Google Sheet")
        engine_registry.register(req.project_id, connector)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {req.engine}")

    tables = connector.get_tables()

    # Register as Resource
    conn_id = f"conn-{req.engine}-{req.host or 'gsheets'}-{req.database or 'sheet'}"
    resource = register_resource(
        resource_type="connection",
        resource_id=conn_id,
        name=req.name,
        project_id=req.project_id,
        description=f"{req.engine}://{req.host}:{req.port}/{req.database}",
        metadata={"engine": req.engine, "host": req.host, "port": req.port, "database": req.database},
    )

    return {
        "uri": resource["uri"],
        "name": req.name,
        "engine": req.engine,
        "tables": tables,
    }


@router.get("/{project_id}")
def list_connections(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    from resources.registry import list_resources
    resources = list_resources(project_id, resource_type="connection")
    return resources


@router.delete("/{project_id}/{conn_id}")
def delete_connection(
    project_id: str,
    conn_id: str,
    current_user: User = Depends(get_current_user),
):
    from resources.registry import delete_resource
    delete_resource(f"connection://{conn_id}")
    return {"status": "deleted"}
