"""Resource registry and helper functions."""
from database.session import SessionLocal
from models.resource import Resource, ResourceReference, ResourceType


def make_uri(resource_type: str, resource_id: str) -> str:
    return f"{resource_type}://{resource_id}"


def parse_uri(uri: str) -> tuple[str, str]:
    """Parse a resource URI into (type, id). Returns ('unknown', uri) if invalid."""
    if "://" in uri:
        parts = uri.split("://", 1)
        return parts[0], parts[1]
    return "unknown", uri


def register_resource(
    resource_type: str,
    resource_id: str,
    name: str,
    project_id: str,
    description: str = "",
    metadata: dict | None = None,
    tags: list | None = None,
    ref_id: str | None = None,
    created_by: str | None = None,
) -> dict:
    """Register a new resource. Auto-generates URI."""
    db = SessionLocal()
    try:
        uri = make_uri(resource_type, resource_id)
        existing = db.query(Resource).filter(Resource.uri == uri).first()
        if existing:
            # Update existing
            existing.name = name
            existing.description = description or existing.description
            existing.metadata_ = metadata or existing.metadata_
            existing.tags = tags or existing.tags
            db.commit()
            return {"uri": existing.uri, "type": existing.type, "name": existing.name}

        resource = Resource(
            uri=uri,
            type=resource_type,
            name=name,
            description=description,
            project_id=project_id,
            metadata_=metadata or {},
            tags=tags or [],
            ref_id=ref_id,
            created_by=created_by,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return {"uri": resource.uri, "type": resource.type, "name": resource.name, "id": resource.id}
    finally:
        db.close()


def add_reference(source_uri: str, target_uri: str, relation: str = "references"):
    """Add a reference between two resources."""
    db = SessionLocal()
    try:
        ref = ResourceReference(source_uri=source_uri, target_uri=target_uri, relation=relation)
        db.add(ref)
        db.commit()
    finally:
        db.close()


def get_resource(uri: str) -> dict | None:
    """Get a resource by URI or name (fuzzy match)."""
    db = SessionLocal()
    try:
        resource = db.query(Resource).filter(
            (Resource.uri == uri) | (Resource.name.ilike(f"%{uri}%"))
        ).first()
        if resource:
            return _resource_to_dict(resource)
    finally:
        db.close()
    return None


def resolve_resource(query: str, project_id: str = None) -> list[dict]:
    """Fuzzy search for resources by name, type, or tag."""
    db = SessionLocal()
    try:
        q = db.query(Resource).filter(
            (Resource.name.ilike(f"%{query}%"))
            | (Resource.type.ilike(f"%{query}%"))
        )
        if project_id:
            q = q.filter(Resource.project_id == project_id)
        results = q.order_by(Resource.updated_at.desc()).limit(20).all()
        return [_resource_to_dict(r) for r in results]
    finally:
        db.close()


def list_resources(project_id: str, resource_type: str = None) -> list[dict]:
    """List resources for a project, optionally filtered by type."""
    db = SessionLocal()
    try:
        q = db.query(Resource).filter(Resource.project_id == project_id)
        if resource_type:
            q = q.filter(Resource.type == resource_type)
        results = q.order_by(Resource.updated_at.desc()).all()
        return [_resource_to_dict(r) for r in results]
    finally:
        db.close()


def get_references(uri: str) -> list[dict]:
    """Get resources referenced by this resource."""
    db = SessionLocal()
    try:
        refs = db.query(ResourceReference).filter(ResourceReference.source_uri == uri).all()
        result = []
        for ref in refs:
            target = db.query(Resource).filter(Resource.uri == ref.target_uri).first()
            if target:
                result.append({**_resource_to_dict(target), "relation": ref.relation})
        return result
    finally:
        db.close()


def get_referrers(uri: str) -> list[dict]:
    """Get resources that reference this resource."""
    db = SessionLocal()
    try:
        refs = db.query(ResourceReference).filter(ResourceReference.target_uri == uri).all()
        result = []
        for ref in refs:
            source = db.query(Resource).filter(Resource.uri == ref.source_uri).first()
            if source:
                result.append({**_resource_to_dict(source), "relation": ref.relation})
        return result
    finally:
        db.close()


def delete_resource(uri: str) -> bool:
    """Delete a resource."""
    db = SessionLocal()
    try:
        db.query(ResourceReference).filter(
            (ResourceReference.source_uri == uri) | (ResourceReference.target_uri == uri)
        ).delete()
        result = db.query(Resource).filter(Resource.uri == uri).delete()
        db.commit()
        return result > 0
    finally:
        db.close()


def _resource_to_dict(r: Resource) -> dict:
    return {
        "uri": r.uri,
        "type": r.type,
        "name": r.name,
        "description": r.description,
        "project_id": r.project_id,
        "tags": r.tags or [],
        "metadata": r.metadata_ or {},
        "ref_id": r.ref_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
