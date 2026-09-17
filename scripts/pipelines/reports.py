import datetime
import math
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir
from scripts.core.bridge import ITInfraBridge

class ReportsPipeline:
    """Pipeline B: Rapportini di Assistenza, Time-Tracking & Ledger Debit."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.bridge = ITInfraBridge()

    def get_timesheets_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "timesheets"

    @staticmethod
    def calculate_rounded_hours(clock_in: str, clock_out: str, break_minutes: int = 0, step_minutes: int = 30) -> Dict[str, float]:
        """Calcola ore lorde e arrotondate a scatti prestabiliti (es. 30 min)."""
        t_in = datetime.datetime.strptime(clock_in, "%H:%M")
        t_out = datetime.datetime.strptime(clock_out, "%H:%M")
        diff_minutes = (t_out - t_in).total_seconds() / 60.0 - break_minutes
        if diff_minutes < 0:
            diff_minutes = 0

        raw_hours = round(diff_minutes / 60.0, 2)
        # Arrotondamento al multiplo superiore di step_minutes
        steps = math.ceil(diff_minutes / step_minutes)
        rounded_minutes = steps * step_minutes
        rounded_hours = round(rounded_minutes / 60.0, 2)

        return {
            "raw_hours": raw_hours,
            "rounded_hours": rounded_hours,
            "net_minutes": int(diff_minutes)
        }

    def list_reports(self, slug: str) -> List[Dict[str, Any]]:
        tdir = self.get_timesheets_dir(slug)
        if not tdir.is_dir():
            return []
        reports = []
        for f in sorted(tdir.glob("*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    reports.append(data)
            except Exception:
                pass
        return reports

    def get_ledger_summary(self, slug: str) -> Dict[str, Any]:
        reports = self.list_reports(slug)
        summary = {
            "slug": slug,
            "total_reports": len(reports),
            "contract_debit_hours": 0.0,
            "invoice_spot_hours": 0.0,
            "included_flat_hours": 0.0,
            "unbilled_spot_reports": []
        }

        for r in reports:
            hours = float(r.get("total_hours_rounded", 0.0))
            action = r.get("ledger_action", "debit_contract")
            rid = r.get("report_id", r.get("_file"))

            if action == "debit_contract":
                summary["contract_debit_hours"] += hours
            elif action == "invoice_spot":
                summary["invoice_spot_hours"] += hours
                summary["unbilled_spot_reports"].append({
                    "report_id": rid,
                    "date": r.get("date"),
                    "hours": hours,
                    "technician": r.get("technician"),
                    "description": r.get("description", "").split("\n")[0]
                })
            elif action == "included_flat":
                summary["included_flat_hours"] += hours

        summary["contract_debit_hours"] = round(summary["contract_debit_hours"], 2)
        summary["invoice_spot_hours"] = round(summary["invoice_spot_hours"], 2)
        summary["included_flat_hours"] = round(summary["included_flat_hours"], 2)
        return summary
