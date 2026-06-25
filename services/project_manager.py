import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


class ProjectManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.projects_root = base_dir / "projects"
        self.projects_file = base_dir / "projects.json"
        self.projects_root.mkdir(exist_ok=True)
        self._migrate_legacy()
        self._ensure_default()

    # ── Migration ────────────────────────────────────────────────────────────

    def _migrate_legacy(self):
        """Move study_materials/ and .pardal_db/ to projects/default/ on first run."""
        legacy_mats = self.base_dir / "study_materials"
        legacy_db   = self.base_dir / ".pardal_db"
        new_mats    = self.projects_root / "default" / "materials"
        new_db      = self.projects_root / "default" / ".db"

        if legacy_mats.exists() and not new_mats.exists():
            new_mats.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(legacy_mats), str(new_mats))

        if legacy_db.exists() and not new_db.exists():
            new_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(legacy_db), str(new_db))

    def _ensure_default(self):
        if not self.projects_file.exists():
            self._save({
                "active": "default",
                "projects": [{
                    "id": "default",
                    "name": "Geral",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "emoji": "📚",
                }]
            })
        proj_dir = self.projects_root / "default"
        (proj_dir / "materials").mkdir(parents=True, exist_ok=True)
        (proj_dir / ".db").mkdir(parents=True, exist_ok=True)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        return json.loads(self.projects_file.read_text(encoding="utf-8"))

    def _save(self, data: dict):
        self.projects_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def list_projects(self) -> List[Dict]:
        return self._load()["projects"]

    def get_active_id(self) -> str:
        return self._load().get("active", "default")

    def get_active(self) -> Dict:
        data = self._load()
        active_id = data.get("active", "default")
        for p in data["projects"]:
            if p["id"] == active_id:
                return p
        return data["projects"][0]

    def create(self, name: str, emoji: str = "📁") -> Dict:
        data = self._load()
        new_id = str(uuid.uuid4())[:8]
        project = {
            "id": new_id,
            "name": name.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "emoji": emoji,
        }
        data["projects"].append(project)
        self._save(data)
        proj_dir = self.projects_root / new_id
        (proj_dir / "materials").mkdir(parents=True, exist_ok=True)
        (proj_dir / ".db").mkdir(parents=True, exist_ok=True)
        return project

    def rename(self, project_id: str, name: str, emoji: Optional[str] = None):
        data = self._load()
        for p in data["projects"]:
            if p["id"] == project_id:
                p["name"] = name.strip()
                if emoji:
                    p["emoji"] = emoji
                break
        self._save(data)

    def delete(self, project_id: str):
        data = self._load()
        if project_id == "default":
            raise ValueError("O projeto padrão não pode ser deletado.")
        if len(data["projects"]) <= 1:
            raise ValueError("Não é possível deletar o único projeto.")
        data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
        if data.get("active") == project_id:
            data["active"] = data["projects"][0]["id"]
        self._save(data)
        proj_dir = self.projects_root / project_id
        if proj_dir.exists():
            shutil.rmtree(proj_dir)

    def set_active(self, project_id: str):
        data = self._load()
        ids = [p["id"] for p in data["projects"]]
        if project_id not in ids:
            raise ValueError(f"Projeto '{project_id}' não encontrado.")
        data["active"] = project_id
        self._save(data)

    def materials_dir(self, project_id: Optional[str] = None) -> Path:
        pid = project_id or self.get_active_id()
        d = self.projects_root / pid / "materials"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def db_dir(self, project_id: Optional[str] = None) -> Path:
        pid = project_id or self.get_active_id()
        d = self.projects_root / pid / ".db"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def doc_count(self, project_id: str, allowed_ext: set) -> int:
        d = self.materials_dir(project_id)
        if not d.exists():
            return 0
        return sum(1 for f in d.iterdir() if f.is_file() and f.suffix.lower() in allowed_ext)
