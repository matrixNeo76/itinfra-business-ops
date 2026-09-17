import datetime
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir, load_config
from scripts.core.bridge import ITInfraBridge
from scripts.core.validator import validate_yaml_file

class ContractsPipeline:
    """Pipeline A: Gestione Contratti SLA & Monte Ore."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()
        self.bridge = ITInfraBridge()

    def get_contracts_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "contracts"

    def list_contracts(self, slug: str) -> List[Dict[str, Any]]:
        cdir = self.get_contracts_dir(slug)
        if not cdir.is_dir():
            return []
        contracts = []
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    contracts.append(data)
            except Exception:
                pass
        return contracts

    def get_contract_summary(self, slug: str) -> Dict[str, Any]:
        contracts = self.list_contracts(slug)
        today = datetime.date.today()
        summary = {
            "slug": slug,
            "total_contracts": len(contracts),
            "active_contracts": [],
            "alerts": []
        }

        for c in contracts:
            cid = c.get("contract_id", c.get("_file"))
            status = c.get("status", "draft")
            formula = c.get("formula", "msp_flat")
            v_to_str = c.get("valid_to")
            
            # Calcolo giorni a scadenza
            days_to_expiry = None
            if v_to_str:
                try:
                    v_to = datetime.date.fromisoformat(str(v_to_str))
                    days_to_expiry = (v_to - today).days
                except Exception:
                    pass

            fin = c.get("financial", {})
            total_h = float(fin.get("total_hours_included", 0.0))
            cons_h = float(fin.get("consumed_hours", 0.0))
            rem_h = total_h - cons_h

            c_info = {
                "contract_id": cid,
                "status": status,
                "formula": formula,
                "valid_to": v_to_str,
                "days_to_expiry": days_to_expiry,
                "total_hours": total_h,
                "consumed_hours": cons_h,
                "remaining_hours": rem_h,
                "sla": c.get("sla", {}),
                "covered_assets": c.get("covered_assets", [])
            }

            if status == "active":
                summary["active_contracts"].append(c_info)

            # Controllo alert scadenza
            if days_to_expiry is not None:
                if 0 <= days_to_expiry <= 60:
                    summary["alerts"].append(f"[{cid}] In scadenza tra {days_to_expiry} giorni ({v_to_str})")
                elif days_to_expiry < 0:
                    summary["alerts"].append(f"[{cid}] CONTRATTO SCADUTO il {v_to_str}")

            # Controllo alert consumo ore
            if total_h > 0:
                pct = (cons_h / total_h) * 100
                if pct >= 80:
                    summary["alerts"].append(f"[{cid}] Monte ore al {pct:.1f}% ({cons_h}/{total_h} h)")

        return summary

    def check_asset_coverage(self, slug: str) -> Dict[str, Any]:
        """Cross-check tra gli apparati coperti dal contratto e l'As-Built di itinfra."""
        contracts = self.list_contracts(slug)
        known_serials = self.bridge.get_known_serials(slug)
        tech_exists = self.bridge.project_exists(slug)

        report = {
            "slug": slug,
            "itinfra_project_found": tech_exists,
            "itinfra_known_serials": list(known_serials),
            "checks": []
        }

        for c in contracts:
            cid = c.get("contract_id", c.get("_file"))
            for asset in c.get("covered_assets", []):
                serial = str(asset.get("serial_number", "")).strip().upper()
                is_matched = serial in known_serials if known_serials else None
                report["checks"].append({
                    "contract_id": cid,
                    "serial_number": serial,
                    "role": asset.get("role", ""),
                    "hostname": asset.get("hostname", ""),
                    "verified_in_as_built": is_matched
                })

        return report

    def debit_hours(self, slug: str, contract_id: str, hours: float, report_id: str = "") -> bool:
        """Aggiorna e salva fisicamente le ore consumate sul file YAML del contratto."""
        cdir = self.get_contracts_dir(slug)
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("contract_id") == contract_id:
                    fin = data.setdefault("financial", {})
                    current_consumed = float(fin.get("consumed_hours", 0.0))
                    fin["consumed_hours"] = round(current_consumed + hours, 2)
                    
                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)
                    return True
            except Exception:
                pass
        return False

    def renew_contract(self, slug: str, contract_id: str) -> Optional[Path]:
        """Duplica e crea una bozza di rinnovo per l'anno successivo."""
        cdir = self.get_contracts_dir(slug)
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("contract_id") == contract_id:
                    # Calcolo date nuovo anno
                    old_v_to = datetime.date.fromisoformat(str(data.get("valid_to", "2026-12-31")))
                    new_v_from = old_v_to + datetime.timedelta(days=1)
                    new_v_to = datetime.date(new_v_from.year, 12, 31)
                    new_year = str(new_v_from.year)
                    new_id = f"CTR-{new_year}-{slug.upper()}"

                    data["contract_id"] = new_id
                    data["status"] = "draft"
                    data["valid_from"] = new_v_from.isoformat()
                    data["valid_to"] = new_v_to.isoformat()
                    data.setdefault("financial", {})["consumed_hours"] = 0.0

                    new_file = cdir / f"ctr-{slug}-{new_year}.yaml"
                    with open(new_file, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)
                    return new_file
            except Exception:
                pass
        return None
