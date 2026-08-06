"""Resource API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from models.user import User
from services.auth import get_current_user
from resources.registry import (
    list_resources,
    get_resource,
    resolve_resource,
    get_references,
    get_referrers,
    delete_resource,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


class ResolveRequest(BaseModel):
    query: str
    project_id: str | None = None


@router.get("/{project_id}")
def list_project_resources(
    project_id: str,
    current_user: User = Depends(get_current_user),
    type: str | None = Query(None, alias="type"),
):
    return list_resources(project_id, resource_type=type)


@router.get("/detail/{uri:path}")
def get_resource_detail(uri: str, current_user: User = Depends(get_current_user)):
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource["references"] = get_references(uri)
    resource["referrers"] = get_referrers(uri)
    return resource


@router.get("/references/{uri:path}")
def get_resource_references(uri: str):
    return get_references(uri)


@router.post("/resolve")
def search_resources(req: ResolveRequest):
    return resolve_resource(req.query, req.project_id)


@router.delete("/{uri:path}")
def remove_resource(uri: str):
    if not delete_resource(uri):
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"status": "deleted", "uri": uri}
