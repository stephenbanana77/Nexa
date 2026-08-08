"""Resource API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from database.session import SessionLocal
from models.project import Project
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


def _owns_project(project_id: str, user_id: str) -> bool:
    """Check whether the project belongs to the user."""
    db = SessionLocal()
    try:
        return (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
            is not None
        )
    finally:
        db.close()


def _verify_resource_ownership(resource: dict, user_id: str) -> None:
    """Raise 404 if the resource's project is not owned by the user.

    404 (not 403) intentionally: avoid leaking existence of other users' resources.
    """
    if not _owns_project(resource.get("project_id", ""), user_id):
        raise HTTPException(status_code=404, detail="Resource not found")


class ResolveRequest(BaseModel):
    query: str
    project_id: str | None = None


@router.get("/{project_id}")
def list_project_resources(
    project_id: str,
    current_user: User = Depends(get_current_user),
    type: str | None = Query(None, alias="type"),
):
    if not _owns_project(project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    return list_resources(project_id, resource_type=type)


@router.get("/detail/{uri:path}")
def get_resource_detail(uri: str, current_user: User = Depends(get_current_user)):
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    _verify_resource_ownership(resource, current_user.id)
    resource["references"] = get_references(uri)
    resource["referrers"] = get_referrers(uri)
    return resource


@router.get("/references/{uri:path}")
def get_resource_references(uri: str, current_user: User = Depends(get_current_user)):
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    _verify_resource_ownership(resource, current_user.id)
    return get_references(uri)


@router.post("/resolve")
def search_resources(req: ResolveRequest, current_user: User = Depends(get_current_user)):
    if req.project_id and not _owns_project(req.project_id, current_user.id):
        raise HTTPException(status_code=404, detail="Project not found")
    results = resolve_resource(req.query, req.project_id)
    # Filter out resources from other users' projects when no project filter given
    if not req.project_id:
        results = [r for r in results if _owns_project(r.get("project_id", ""), current_user.id)]
    return results


@router.delete("/{uri:path}")
def remove_resource(uri: str, current_user: User = Depends(get_current_user)):
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    _verify_resource_ownership(resource, current_user.id)
    if not delete_resource(uri):
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"status": "deleted", "uri": uri}
