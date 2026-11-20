"""Built-in skills registered from canonical manifests."""
from __future__ import annotations

import json
from pathlib import Path

from skills import skill_registry


def register_builtin_skills() -> None:
    """Register manifests with executable steps and declared permissions."""
    manifest_dir = Path(__file__).with_name("manifests")
    for path in sorted(manifest_dir.glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        steps = manifest.get("steps") or []
        if not steps:
            continue
        name = manifest["name"]
        skill_registry.register_runtime(name, {
            "title": manifest.get("title", name),
            "description": manifest.get("description", ""),
            "category": manifest.get("category", "analysis"),
            "icon": manifest.get("icon", "ExperimentOutlined"),
            "version": manifest.get("version", "1.0.0"),
            "is_builtin": True,
            "permissions": manifest.get("permissions", {}),
            "agent_callable": manifest.get("agent_callable", True),
            "inputs": manifest.get("inputs", {}),
            "outputs": manifest.get("outputs", {}),
            "definition": {"steps": steps},
        })
