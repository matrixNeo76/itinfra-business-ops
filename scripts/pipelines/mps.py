import datetime
import socket
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir
from scripts.core.bridge import ITInfraBridge

class MPSPipeline:
    """Pipeline F: Noleggio Multifunzione MPS, Costo Copia & Telemetria."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.bridge = ITInfraBridge()

    def get_mps_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "mps"

    def list_mps_contracts(self, slug: str) -> List[Dict[str, Any]]:
        mdir = self.get_mps_dir(slug)
        if not mdir.is_dir():
            return []
        contracts = []
        for f in mdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    contracts.append(data)
            except Exception:
                pass
        return contracts

    def calculate_settlement(self, mps_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcola conguaglio eccedenze copie e alert consumabili toner."""
        terms = mps_data.get("contract_terms", {})
        included = terms.get("included_copies_semestral", {"mono": 0, "color": 0})
        rates = terms.get("overage_cost_per_page", {"mono": 0.0, "color": 0.0})
        base_fee = float(terms.get("semestral_base_fee", 0.0))

        readings = mps_data.get("readings", [])
        alerts = []

        if len(readings) >= 2:
            first = readings[0]
            latest = readings[-1]
            mono_produced = latest.get("mono_total", 0) - first.get("mono_total", 0)
            color_produced = latest.get("color_total", 0) - first.get("color_total", 0)
        elif len(readings) == 1:
            latest = readings[0]
            mono_produced = 0
            color_produced = 0
        else:
            latest = {}
            mono_produced = 0
            color_produced = 0

        mono_inc = included.get("mono", 0)
        color_inc = included.get("color", 0)

        mono_excess = max(0, mono_produced - mono_inc)
        color_excess = max(0, color_produced - color_inc)

        mono_overage_cost = round(mono_excess * float(rates.get("mono", 0.0)), 2)
        color_overage_cost = round(color_excess * float(rates.get("color", 0.0)), 2)
        total_settlement = round(base_fee + mono_overage_cost + color_overage_cost, 2)

        # Controllo soglie toner
        toner_levels = {
            "Black": latest.get("toner_black_percent"),
            "Cyan": latest.get("toner_cyan_percent"),
            "Magenta": latest.get("toner_magenta_percent"),
            "Yellow": latest.get("toner_yellow_percent")
        }
        for color, lvl in toner_levels.items():
            if lvl is not None and lvl <= 15:
                alerts.append(f"CRITICO CONSUMABILE: Toner {color} al {lvl}% — Generare ordine ricambio!")

        # Cross-check con As-Built
        serial = mps_data.get("device_info", {}).get("serial_number", "").strip().upper()
        known = self.bridge.get_known_serials(mps_data.get("slug", ""))
        verified_as_built = serial in known if known else None

        return {
            "mps_contract_id": mps_data.get("mps_contract_id"),
            "serial_number": serial,
            "verified_in_as_built": verified_as_built,
            "mono_produced": mono_produced,
            "mono_included": mono_inc,
            "mono_excess": mono_excess,
            "mono_overage_cost": mono_overage_cost,
            "color_produced": color_produced,
            "color_included": color_inc,
            "color_excess": color_excess,
            "color_overage_cost": color_overage_cost,
            "base_fee": base_fee,
            "total_settlement_next_period": total_settlement,
            "toner_levels": toner_levels,
            "alerts": alerts
        }

    def record_reading(
        self,
        slug: str,
        mps_id: str,
        mono_total: int,
        color_total: int,
        toner_black: int = 80,
        toner_cyan: int = 70,
        toner_magenta: int = 65,
        toner_yellow: int = 75,
        method: str = "manual_customer"
    ) -> Optional[Dict[str, Any]]:
        """Registra e salva una nuova lettura contatori nel contratto MPS."""
        mdir = self.get_mps_dir(slug)
        for f in mdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("mps_contract_id") == mps_id:
                    readings = data.setdefault("readings", [])
                    new_reading = {
                        "reading_date": datetime.date.today().isoformat(),
                        "mono_total": mono_total,
                        "color_total": color_total,
                        "toner_black_percent": toner_black,
                        "toner_cyan_percent": toner_cyan,
                        "toner_magenta_percent": toner_magenta,
                        "toner_yellow_percent": toner_yellow,
                        "reading_method": method
                    }
                    readings.append(new_reading)
                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)
                    return self.calculate_settlement(data)
            except Exception:
                pass
        return None
