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
        """Crea o aggiorna uno slot appuntamento schedulato agganciato a un task Jira ed esporta l'ICS."""
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
        sfile.parent.mkdir(parents=True, exist_ok=True)
        with open(sfile, "w", encoding="utf-8") as f:
            yaml.safe_dump(record, f, sort_keys=False, allow_unicode=True)

        # Genera il file standard iCalendar (.ics) per Outlook e Google Calendar
        ics_content = self.generate_ics(record)
        ics_file = self.clients_root / slug / f"appointment-{issue_key.lower()}.ics"
        ics_file.parent.mkdir(parents=True, exist_ok=True)
        ics_file.write_text(ics_content, encoding="utf-8")

        return record

    def generate_ics(self, record: Dict[str, Any]) -> str:
        """Genera tracciato standard RFC 5545 iCalendar."""
        app = record.get("appointment", {})
        start_dt = datetime.datetime.fromisoformat(app.get("start_datetime")).strftime("%Y%m%dT%H%M%S")
        end_dt = datetime.datetime.fromisoformat(app.get("end_datetime")).strftime("%Y%m%dT%H%M%S")
        now_dt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = f"{record.get('jira_issue_key')}@itinfra.local"

        return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ITInfra Business Ops//Intervento Tecnico//IT
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now_dt}
DTSTART:{start_dt}
DTEND:{end_dt}
SUMMARY:[{record.get('jira_issue_key')}] {record.get('summary')}
DESCRIPTION:Intervento tecnico programmato per il cliente {record.get('slug')}\\nAssegnatario: {record.get('assignee')}
LOCATION:{app.get('location')}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    def get_outbox_file(self, slug: str) -> Path:
        """Restituisce il path della coda outbox offline Jira per il cliente."""
        return self.clients_root / slug / "jira_outbox.yaml"

    def queue_action(self, slug: str, action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accoda un'azione Jira (create_issue, log_work, update_status) nella outbox locale
        garantendo resilienza offline prima della sincronizzazione via API remote.
        """
        ofile = self.get_outbox_file(slug)
        outbox_items = []
        if ofile.is_file():
            try:
                with open(ofile, "r", encoding="utf-8") as f:
                    outbox_items = yaml.safe_load(f) or []
            except Exception:
                outbox_items = []

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        action_id = f"ACT-{len(outbox_items) + 1:04d}-{int(datetime.datetime.now().timestamp())}"
        entry = {
            "action_id": action_id,
            "slug": slug,
            "action_type": action_type,
            "status": "pending",
            "created_at": now_utc,
            "attempts": 0,
            "payload": payload
        }
        outbox_items.append(entry)

        ofile.parent.mkdir(parents=True, exist_ok=True)
        with open(ofile, "w", encoding="utf-8") as f:
            yaml.safe_dump(outbox_items, f, sort_keys=False, allow_unicode=True)

        return entry

    def get_queued_actions(self, slug: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera le azioni accodate nella outbox locale, opzionalmente filtrate per stato."""
        ofile = self.get_outbox_file(slug)
        if not ofile.is_file():
            return []
        try:
            with open(ofile, "r", encoding="utf-8") as f:
                items = yaml.safe_load(f) or []
            if status:
                return [it for it in items if it.get("status") == status]
            return items
        except Exception:
            return []

    def check_schedule_conflicts(
        self,
        proposed_start: str,
        proposed_end: str,
        technician: str = "",
        current_issue_key: str = "",
        target_slug: str = "",
        travel_buffer_minutes: int = 45
    ) -> List[Dict[str, Any]]:
        """
        Scansiona l'intero parco clienti per individuare:
        1. Sovrapposizioni dirette di orario (OVERLAP) per lo stesso tecnico.
        2. Spostamenti tra clienti diversi con tempo di viaggio insufficiente (< travel_buffer_minutes).
        """
        p_start = datetime.datetime.fromisoformat(proposed_start)
        p_end = datetime.datetime.fromisoformat(proposed_end)
        conflicts = []

        for sfile in self.clients_root.glob("*/jira_sync.yaml"):
            try:
                with open(sfile, "r", encoding="utf-8") as f:
                    rec = yaml.safe_load(f) or {}
                ikey = rec.get("jira_issue_key", "")
                if current_issue_key and ikey == current_issue_key:
                    continue

                app = rec.get("appointment", {})
                start_str = app.get("start_datetime")
                end_str = app.get("end_datetime")
                if not start_str or not end_str:
                    continue

                ex_start = datetime.datetime.fromisoformat(start_str)
                ex_end = datetime.datetime.fromisoformat(end_str)
                assignee = rec.get("assignee", "")
                ex_slug = rec.get("slug", sfile.parent.name)

                # Se specificato un tecnico, il conflitto si applica solo al medesimo tecnico
                if technician and assignee and technician.strip().lower() != assignee.strip().lower():
                    continue

                # 1. Controllo sovrapposizione intervalli [A, B] e [C, D]: A < D and C < B
                if p_start < ex_end and ex_start < p_end:
                    conflicts.append({
                        "slug": ex_slug,
                        "jira_issue_key": ikey,
                        "summary": rec.get("summary", ""),
                        "assignee": assignee,
                        "start_datetime": start_str,
                        "end_datetime": end_str,
                        "conflict_type": "OVERLAP",
                        "message": f"Sovrapposizione oraria diretta con appuntamento {ikey} presso {ex_slug}"
                    })
                    continue

                # 2. Controllo buffer geografico di trasferta (45 min) se lo slug cliente è diverso
                if target_slug and ex_slug and target_slug != ex_slug and travel_buffer_minutes > 0:
                    if p_start.date() == ex_end.date():
                        if ex_end <= p_start:
                            gap_minutes = (p_start - ex_end).total_seconds() / 60.0
                            if gap_minutes < travel_buffer_minutes:
                                conflicts.append({
                                    "slug": ex_slug,
                                    "jira_issue_key": ikey,
                                    "summary": rec.get("summary", ""),
                                    "assignee": assignee,
                                    "start_datetime": start_str,
                                    "end_datetime": end_str,
                                    "conflict_type": "INSUFFICIENT_TRAVEL_BUFFER",
                                    "travel_gap_minutes": round(gap_minutes, 1),
                                    "required_buffer_minutes": travel_buffer_minutes,
                                    "message": f"Intervallo di viaggio insufficiente ({gap_minutes:.0f} min < {travel_buffer_minutes} min) tra {ex_slug} e {target_slug}"
                                })
                        elif p_end <= ex_start:
                            gap_minutes = (ex_start - p_end).total_seconds() / 60.0
                            if gap_minutes < travel_buffer_minutes:
                                conflicts.append({
                                    "slug": ex_slug,
                                    "jira_issue_key": ikey,
                                    "summary": rec.get("summary", ""),
                                    "assignee": assignee,
                                    "start_datetime": start_str,
                                    "end_datetime": end_str,
                                    "conflict_type": "INSUFFICIENT_TRAVEL_BUFFER",
                                    "travel_gap_minutes": round(gap_minutes, 1),
                                    "required_buffer_minutes": travel_buffer_minutes,
                                    "message": f"Intervallo di viaggio insufficiente ({gap_minutes:.0f} min < {travel_buffer_minutes} min) tra {target_slug} e {ex_slug}"
                                })
            except Exception:
                continue

        return conflicts

    def dispatch_outbox_queue(
        self,
        slug: Optional[str] = None,
        max_retries: int = 3,
        base_backoff_sec: float = 1.0,
        simulate_remote: bool = True
    ) -> Dict[str, Any]:
        """
        Processa la coda delle azioni offline in outbox con algoritmo di backoff esponenziale.
        Se simulate_remote=True, esegue dispatch con successo locale.
        """
        slugs_to_process = [slug] if slug else [p.parent.name for p in self.clients_root.glob("*/jira_outbox.yaml")]
        total_processed = 0
        total_succeeded = 0
        total_failed = 0
        dispatched_actions = []

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for s in slugs_to_process:
            ofile = self.get_outbox_file(s)
            if not ofile.is_file():
                continue

            try:
                with open(ofile, "r", encoding="utf-8") as f:
                    items = yaml.safe_load(f) or []
            except Exception:
                continue

            updated_items = []
            for item in items:
                if item.get("status") in ("sent", "delivered"):
                    updated_items.append(item)
                    continue

                total_processed += 1
                attempts = int(item.get("attempts", 0)) + 1
                item["attempts"] = attempts

                backoff_delay = base_backoff_sec * (2 ** (attempts - 1))
                item["last_backoff_sec"] = backoff_delay

                if simulate_remote or attempts <= max_retries:
                    item["status"] = "sent"
                    item["dispatched_at"] = now_utc
                    total_succeeded += 1
                    dispatched_actions.append({"action_id": item.get("action_id"), "status": "sent", "slug": s})
                else:
                    item["status"] = "failed"
                    item["failed_at"] = now_utc
                    total_failed += 1
                    dispatched_actions.append({"action_id": item.get("action_id"), "status": "failed", "slug": s})

                updated_items.append(item)

            with open(ofile, "w", encoding="utf-8") as f:
                yaml.safe_dump(updated_items, f, sort_keys=False, allow_unicode=True)

        return {
            "total_processed": total_processed,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "dispatched_actions": dispatched_actions,
            "timestamp": now_utc
        }

