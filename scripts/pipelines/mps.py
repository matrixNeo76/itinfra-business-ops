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

        # Previsione predittiva esaurimento consumabili (Remaining Useful Life - RUL)
        prediction = self.predict_toner_depletion(mps_data)
        for rec in prediction.get("reorder_recommendations", []):
            alerts.append(f"ORDINE PREVENTIVO CONSUMABILE: {rec['action']}")

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
            "predictive_maintenance": prediction,
            "alerts": alerts
        }

    @staticmethod
    def predict_toner_depletion(mps_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcola la velocità media di consumo pagine/giorno e stima i giorni residui
        di vita utile (Remaining Useful Life - RUL) per ciascun consumabile toner.
        Emette un alert proattivo di riordino se RUL <= 10 giorni lavorativi.
        """
        readings = mps_data.get("readings", [])
        if len(readings) < 2:
            return {
                "daily_rate_pages": 0.0,
                "days_analyzed": 0,
                "toner_rul_days": {},
                "reorder_recommendations": []
            }

        first_r = readings[0]
        last_r = readings[-1]

        try:
            d_first = datetime.date.fromisoformat(first_r.get("reading_date", ""))
            d_last = datetime.date.fromisoformat(last_r.get("reading_date", ""))
            delta_days = max(1, (d_last - d_first).days)
        except Exception:
            delta_days = 30

        total_pages_produced = (last_r.get("mono_total", 0) + last_r.get("color_total", 0)) - \
                               (first_r.get("mono_total", 0) + first_r.get("color_total", 0))
        daily_pages = round(total_pages_produced / delta_days, 1) if delta_days > 0 else 0.0

        toner_rul = {}
        reorder = []
        colors = ["black", "cyan", "magenta", "yellow"]

        for c in colors:
            lvl_first = float(first_r.get(f"toner_{c}_percent", 100))
            lvl_last = float(last_r.get(f"toner_{c}_percent", 100))
            consumed_pct = lvl_first - lvl_last

            if consumed_pct > 0 and delta_days > 0:
                daily_pct = consumed_pct / delta_days
                days_left = int(lvl_last / daily_pct) if daily_pct > 0 else 999
            else:
                days_left = int((lvl_last / 10.0) * 15)

            toner_rul[c] = days_left
            if days_left <= 10 or lvl_last <= 15:
                reorder.append({
                    "color": c.upper(),
                    "current_level_percent": int(lvl_last),
                    "estimated_days_remaining": days_left,
                    "action": f"Emettere ordine toner {c.upper()} entro {max(1, days_left)} giorni per evitare fermo macchina."
                })

        return {
            "daily_rate_pages": daily_pages,
            "days_analyzed": delta_days,
            "toner_rul_days": toner_rul,
            "reorder_recommendations": reorder
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

    def poll_device(self, slug: str, mps_id: Optional[str] = None, ip_override: Optional[str] = None) -> Dict[str, Any]:
        """Interroga la stampante fisica via SNMP e registra automaticamente la telelettura se raggiungibile."""
        from scripts.core.snmp import SNMPPoller
        poller = SNMPPoller()

        contracts = self.list_mps_contracts(slug)
        if not contracts:
            return {"status": "error", "message": f"Nessun contratto MPS trovato per {slug}"}

        target_contract = None
        for c in contracts:
            if not mps_id or c.get("mps_contract_id") == mps_id:
                target_contract = c
                break

        if not target_contract:
            return {"status": "error", "message": f"Contratto {mps_id} non trovato"}

        cid = target_contract.get("mps_contract_id")
        ip = ip_override or target_contract.get("device_info", {}).get("ip_address")
        if not ip:
            return {"status": "error", "message": f"Indirizzo IP non specificato per {cid}"}

        snmp_cfg = target_contract.get("snmp_config", {})
        comm = snmp_cfg.get("community", "public")

        res = poller.poll_ip(ip, community=comm)
        if res["reachable"]:
            telem = res.get("telemetry", {})
            st = self.record_reading(
                slug=slug,
                mps_id=cid,
                mono_total=telem.get("mono_total", 0),
                color_total=telem.get("color_total", 0),
                method="snmp_auto"
            )
            return {"status": "success", "ip": ip, "reachable": True, "settlement": st}
        else:
            return {
                "status": "warning",
                "ip": ip,
                "reachable": False,
                "snmp_status": res["snmp_status"],
                "message": f"Dispositivo {ip} non ha risposto alla query SNMP UDP 161 ({res['snmp_status']}). È possibile registrare la lettura manuale con 'it-ops mps {slug} read'."
            }

    def predict_toner_depletion(
        self,
        readings: List[Dict[str, Any]],
        current_toner_percent: Optional[float] = None,
        toner_color: str = "black"
    ) -> Dict[str, Any]:
        """
        Algoritmo di manutenzione predittiva toner:
        Calcola il consumo medio giornaliero (burn rate) e stima la vita utile residua (Remaining Useful Life - RUL).
        Attiva l'allarme di riordino automatico quando RUL <= 10 giorni o percentuale toner <= 15%.
        """
        if not readings:
            return {
                "daily_burn_rate_pages": 0.0,
                "remaining_useful_life_days": 999,
                "reorder_triggered": False,
                "message": "Nessuna lettura disponibile per la stima"
            }

        sorted_readings = sorted(readings, key=lambda r: r.get("reading_date", ""))
        
        burn_rate = 100.0
        if len(sorted_readings) >= 2:
            first = sorted_readings[0]
            last = sorted_readings[-1]
            d_start = datetime.date.fromisoformat(first.get("reading_date"))
            d_end = datetime.date.fromisoformat(last.get("reading_date"))
            days = max(1, (d_end - d_start).days)
            delta_pages = max(0, int(last.get("mono_total", 0)) - int(first.get("mono_total", 0)))
            if delta_pages > 0 and days > 0:
                burn_rate = round(delta_pages / days, 1)

        pct = current_toner_percent
        if pct is None:
            pct = float(sorted_readings[-1].get(f"toner_{toner_color}_percent", 50.0))

        yield_total_pages = 10000.0
        remaining_pages = (pct / 100.0) * yield_total_pages
        rul_days = round(remaining_pages / max(1.0, burn_rate), 1)

        reorder = (pct <= 15.0) or (rul_days <= 10.0)

        return {
            "toner_color": toner_color,
            "current_toner_percent": pct,
            "daily_burn_rate_pages": burn_rate,
            "estimated_pages_remaining": int(remaining_pages),
            "remaining_useful_life_days": rul_days,
            "reorder_triggered": reorder,
            "recommendation": "Ordinare nuova cartuccia toner" if reorder else "Livello consumabile ottimale"
        }

