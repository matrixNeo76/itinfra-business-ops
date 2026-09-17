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

    def debit_hours(self, slug: str, contract_id: str, hours: float, report_id: str = "") -> Dict[str, float]:
        """
        Aggiorna e salva fisicamente le ore consumate sul file YAML del contratto.
        Se le ore richieste superano il monte ore residuo, scorpora automaticamente:
        - ore a canone (fino a esaurimento monte ore)
        - ore extra-soglia (da fatturare con tariffa extra)
        """
        cdir = self.get_contracts_dir(slug)
        result = {"debited_contract_hours": 0.0, "extra_hours": 0.0}
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("contract_id") == contract_id:
                    fin = data.setdefault("financial", {})
                    total_included = float(fin.get("total_hours_included", 0.0))
                    current_consumed = float(fin.get("consumed_hours", 0.0))
                    remaining = max(0.0, total_included - current_consumed)

                    if hours <= remaining:
                        debited = hours
                        extra = 0.0
                    else:
                        debited = remaining
                        extra = round(hours - remaining, 2)

                    fin["consumed_hours"] = round(current_consumed + debited, 2)
                    if extra > 0:
                        fin["extra_hours_billed"] = round(float(fin.get("extra_hours_billed", 0.0)) + extra, 2)

                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    result["debited_contract_hours"] = debited
                    result["extra_hours"] = extra
                    return result
            except Exception:
                pass
        return result

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

    def export_contract(self, slug: str, contract_id: str, formats: Optional[List[str]] = None) -> Dict[str, Path]:
        """Esporta il contratto SLA nei formati richiesti (docx, pdf). Default: tutti."""
        from scripts.core.document_renderer import DocumentRenderer

        cdir = self.get_contracts_dir(slug)
        contract_data = None
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("contract_id") == contract_id or f.stem == contract_id.lower() or f.stem == f"ctr-{slug}-2026":
                    contract_data = data
                    break
            except Exception:
                pass

        if not contract_data:
            return {}

        selected_formats = [fmt.strip().lower() for fmt in formats] if formats else ["docx", "pdf"]
        if "all" in selected_formats:
            selected_formats = ["docx", "pdf"]

        results = {}
        cid_clean = contract_data.get("contract_id", contract_id).lower().replace(":", "_")

        if "docx" in selected_formats:
            out_docx = cdir / f"{cid_clean}.docx"
            DocumentRenderer.render_contract_to_docx(contract_data, out_docx)
            results["docx"] = out_docx

            if "pdf" in selected_formats:
                out_pdf = cdir / f"{cid_clean}.pdf"
                DocumentRenderer.render_contract_to_pdf(contract_data, out_pdf)
                results["pdf"] = out_pdf

        return results

    # Festività nazionali italiane fisse
    ITALIAN_HOLIDAYS_FIXED = {
        (1, 1),   # Capodanno
        (1, 6),   # Epifania
        (4, 25),  # Liberazione
        (5, 1),   # Festa del Lavoro
        (6, 2),   # Festa della Repubblica
        (8, 15),  # Ferragosto
        (11, 1),  # Ognissanti
        (12, 8),  # Immacolata
        (12, 25), # Natale
        (12, 26), # Santo Stefano
    }

    @classmethod
    def is_italian_holiday_or_weekend(cls, d: datetime.date) -> bool:
        """Verifica se una data cade di sabato, domenica o festività nazionale italiana."""
        if d.weekday() in (5, 6): # Sabato = 5, Domenica = 6
            return True
        if (d.month, d.day) in cls.ITALIAN_HOLIDAYS_FIXED:
            return True
        return False

    @classmethod
    def compute_business_hours_sla(
        cls,
        start_dt: Any,
        end_dt: Any,
        window_start_str: str = "09:00",
        window_end_str: str = "18:00"
    ) -> float:
        """
        Calcola deterministamente le ore lavorative effettive trascorse tra due timestamp,
        escludendo weekend, festività nazionali e ore al di fuori della finestra giornaliera (es. 09:00 - 18:00).
        """
        if isinstance(start_dt, str):
            start_dt = datetime.datetime.fromisoformat(start_dt)
        if isinstance(end_dt, str):
            end_dt = datetime.datetime.fromisoformat(end_dt)

        if end_dt <= start_dt:
            return 0.0

        w_start = datetime.datetime.strptime(window_start_str, "%H:%M").time()
        w_end = datetime.datetime.strptime(window_end_str, "%H:%M").time()

        total_seconds = 0.0
        current = start_dt

        while current < end_dt:
            cur_date = current.date()
            if not cls.is_italian_holiday_or_weekend(cur_date):
                day_open = datetime.datetime.combine(cur_date, w_start)
                day_close = datetime.datetime.combine(cur_date, w_end)

                eff_start = max(current, day_open)
                eff_end = min(end_dt, day_close)

                if eff_end > eff_start:
                    total_seconds += (eff_end - eff_start).total_seconds()

            # Avanza all'inizio del giorno successivo
            current = datetime.datetime.combine(cur_date + datetime.timedelta(days=1), datetime.time(0, 0))

        return round(total_seconds / 3600.0, 2)

    def apply_istat_adjustment(
        self,
        target: Any,
        contract_id_or_rate: Any = None,
        istat_rate_percent: float = 0.0,
        inflation_rate_percent: Optional[float] = None,
        foi_coefficient: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Applica la rivalutazione ISTAT FOI (Famiglie Operai e Impiegati) al canone annuo o mensile.
        Supporta sia il calcolo analitico su un importo base numerico, sia l'aggiornamento su file contratto YAML.
        """
        if isinstance(target, (int, float)):
            base_fee = float(target)
            rate = float(inflation_rate_percent if inflation_rate_percent is not None else (contract_id_or_rate if contract_id_or_rate is not None else istat_rate_percent))
            adj = round(base_fee * (rate / 100.0) * foi_coefficient, 2)
            revised = round(base_fee + adj, 2)
            return {
                "original_fee": base_fee,
                "adjustment_amount": adj,
                "revised_fee": revised,
                "rate_percent": rate,
                "foi_coefficient": foi_coefficient
            }

        slug = str(target)
        contract_id = str(contract_id_or_rate)
        rate = float(inflation_rate_percent if inflation_rate_percent is not None else istat_rate_percent)

        cdir = self.get_contracts_dir(slug)
        for f in cdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("contract_id") == contract_id:
                    fin = data.setdefault("financial", {})
                    base_fee = float(fin.get("annual_fee", fin.get("monthly_fee", 0.0)))
                    if base_fee <= 0:
                        return None

                    adjustment_multiplier = 1.0 + ((rate * foi_coefficient) / 100.0)
                    revised_fee = round(base_fee * adjustment_multiplier, 2)

                    fee_key = "annual_fee" if "annual_fee" in fin else "monthly_fee"
                    fin[f"original_{fee_key}"] = base_fee
                    fin[fee_key] = revised_fee
                    fin["istat_rate_applied"] = rate
                    fin["istat_applied_date"] = datetime.date.today().isoformat()

                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    return {
                        "contract_id": contract_id,
                        "fee_key": fee_key,
                        "original_fee": base_fee,
                        "revised_fee": revised_fee,
                        "istat_rate_percent": rate,
                        "applied_date": fin["istat_applied_date"]
                    }
            except Exception:
                pass
        return None

    def route_asset_to_contract(self, slug: str, asset_serial_or_role: str) -> Optional[Dict[str, Any]]:
        """
        Determina a quale contratto attivo addebitare un intervento,
        cercando per seriale hardware o ruolo apparato negli asset coperti.
        """
        contracts = self.list_contracts(slug)
        needle = asset_serial_or_role.strip().upper()

        for c in contracts:
            if c.get("status") != "active":
                continue
            cid = c.get("contract_id")
            for asset in c.get("covered_assets", []):
                s = str(asset.get("serial_number", "")).strip().upper()
                r = str(asset.get("role", "")).strip().upper()
                h = str(asset.get("hostname", "")).strip().upper()
                if needle in (s, r, h):
                    return {
                        "contract_id": cid,
                        "formula": c.get("formula", "msp_flat"),
                        "matched_asset": asset,
                        "remaining_hours": float(c.get("financial", {}).get("total_hours_included", 0)) - float(c.get("financial", {}).get("consumed_hours", 0))
                    }

        # Fallback: primo contratto attivo con monte ore residuo
        for c in contracts:
            if c.get("status") == "active":
                return {
                    "contract_id": c.get("contract_id"),
                    "formula": c.get("formula", "msp_flat"),
                    "matched_asset": None,
                    "remaining_hours": float(c.get("financial", {}).get("total_hours_included", 0)) - float(c.get("financial", {}).get("consumed_hours", 0))
                }
        return None
