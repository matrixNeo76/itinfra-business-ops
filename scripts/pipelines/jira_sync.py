import datetime
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir

class JiraSyncPipeline:
    """Pipeline D: Task Giornalieri Jira & Schedulazione Appuntamenti."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def get_sync_file(self, slug: str) -> Path:
        return self.clients_root / slug / "jira_sync.yaml"

    def create_appointment(self, slug: str, issue_key: str, summary: str, start_dt: str, duration_hours: float = 2.0, technician: str = "Tecnico") -> Dict[str, Any]:
        """Crea o aggiorna uno slot appuntamento schedulato agganciato a un task Jira."""
        start = datetime.datetime.fromisoformat(start_dt)
        end = start + datetime.timedelta(hours=duration_hours)

        record = {
            "sync_id": f"SYNC-{issue_key}",
            "slug": slug,
            "jira_issue_key": issue_key,
            "issue_type": "Task",
            "priority": "High",
            "summary": summary,
            "assignee": technician,
            "appointment": {
                "start_datetime": start.isoformat(),
                "end_datetime": end.isoformat(),
                "location": f"Presso sede cliente {slug}",
                "calendar_event_id": f"CAL-{issue_key}",
                "confirmation_sent": True
            },
            "execution": {
                "status": "scheduled",
                "rapportino_ref": "",
                "actual_time_minutes": 0
            }
        }

        sfile = self.get_sync_file(slug)
        with open(sfile, "w", encoding="utf-8") as f:
            yaml.safe_dump(record, f, sort_keys=False, allow_unicode=True)

        return record
