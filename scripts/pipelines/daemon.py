#!/usr/bin/env python3
"""
scripts/pipelines/daemon.py — Proactive Background Daemons Engine (SPEC-20)
Monitoraggio proattivo autonomo per Aure System:
- MPSDaemon: sentinella consumabili multifunzione e telelettura SNMP (alert se toner <= 15%)
- SLADaemon: sentinella monte ore e scadenze contrattuali (alert se ore < 20% o scadenza < 30gg)
"""

import datetime
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Configura encoding UTF-8 su Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.core.config import get_clients_dir
from scripts.core.trigger_engine import TriggerEngine


class MPSDaemon:
    """Demone proattivo per il monitoraggio continuo dei consumabili multifunzione."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def check_all(self) -> Dict[str, Any]:
        """Esegue un ciclo di controllo deterministico su tutte le stampanti censite."""
        alerts: List[Dict[str, Any]] = []
        scanned_count = 0

        for cdir in self.clients_root.iterdir():
            if not cdir.is_dir() or cdir.name.startswith(("_", ".")):
                continue

            slug = cdir.name
            mps_dir = cdir / "mps"
            if not mps_dir.is_dir():
                continue

            for mf in mps_dir.glob("*.yaml"):
                try:
                    with open(mf, "r", encoding="utf-8") as fp:
                        mdata = yaml.safe_load(fp) or {}

                    # Controllo formato 1 (printers list)
                    for p in mdata.get("printers", []):
                        scanned_count += 1
                        cnts = p.get("current_counters", {})
                        tbk = cnts.get("toner_black_pct", 100)
                        tc = cnts.get("toner_cyan_pct", 100)
                        tm = cnts.get("toner_magenta_pct", 100)
                        ty = cnts.get("toner_yellow_pct", 100)

                        crit = []
                        if tbk <= 15: crit.append(f"Black: {tbk}%")
                        if tc <= 15: crit.append(f"Cyan: {tc}%")
                        if tm <= 15: crit.append(f"Magenta: {tm}%")
                        if ty <= 15: crit.append(f"Yellow: {ty}%")

                        if crit:
                            alerts.append({
                                "slug": slug,
                                "printer": p.get("model", "Stampante"),
                                "serial": p.get("serial_number", ""),
                                "ip": p.get("ip_address", ""),
                                "low_supplies": crit,
                                "severity": "HIGH",
                            })

                    # Controllo formato 2 (device_info singolo con readings)
                    dinfo = mdata.get("device_info", {})
                    if dinfo and "serial_number" in dinfo:
                        scanned_count += 1
                        readings = mdata.get("readings", [])
                        if readings:
                            last_r = readings[-1]
                            tbk = last_r.get("toner_black_percent", 100)
                            tc = last_r.get("toner_cyan_percent", 100)
                            tm = last_r.get("toner_magenta_percent", 100)
                            ty = last_r.get("toner_yellow_percent", 100)

                            crit = []
                            if tbk <= 15: crit.append(f"Black: {tbk}%")
                            if tc <= 15: crit.append(f"Cyan: {tc}%")
                            if tm <= 15: crit.append(f"Magenta: {tm}%")
                            if ty <= 15: crit.append(f"Yellow: {ty}%")

                            if crit:
                                alerts.append({
                                    "slug": slug,
                                    "printer": dinfo.get("model", "Stampante"),
                                    "serial": dinfo.get("serial_number", ""),
                                    "ip": dinfo.get("ip_address", ""),
                                    "low_supplies": crit,
                                    "severity": "HIGH",
                                })
                except Exception:
                    pass

        # Emissione Trigger Events (SPEC-22)
        try:
            te = TriggerEngine(clients_root=self.clients_root)
            for a in alerts:
                te.emit_event(
                    event_type="telemetry.mps.consumable_low",
                    slug=a["slug"],
                    source="daemon:mps",
                    payload={"model": a["printer"], "toner_info": ", ".join(a["low_supplies"]), "serial": a.get("serial")},
                    auto_evaluate=True,
                )
        except Exception:
            pass

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "scanned_printers": scanned_count,
            "alerts_count": len(alerts),
            "alerts": alerts,
        }

    def run_loop(self, interval_seconds: int = 3600, once: bool = False) -> None:
        """Esegue il demone in polling continuo o modalità --once."""
        print(f"[*] Avvio MPSDaemon (intervallo: {interval_seconds}s, once={once})...")
        while True:
            res = self.check_all()
            print(f"[{res['timestamp']}] MPS Check: {res['scanned_printers']} apparati analizzati, {res['alerts_count']} allarmi.")
            for a in res["alerts"]:
                print(f"  [ALLARME TONER] {a['slug'].upper()} | {a['printer']} ({a['serial']}): {', '.join(a['low_supplies'])}")
            if once:
                break
            time.sleep(interval_seconds)


class SLADaemon:
    """Demone proattivo per il monitoraggio continuo dei contratti SLA e monte ore."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def check_all(self) -> Dict[str, Any]:
        """Esegue un ciclo di controllo sul consumo del monte ore e scadenze."""
        alerts: List[Dict[str, Any]] = []
        scanned_contracts = 0
        today = datetime.date.today()

        for cdir in self.clients_root.iterdir():
            if not cdir.is_dir() or cdir.name.startswith(("_", ".")):
                continue

            slug = cdir.name
            contracts_dir = cdir / "contracts"
            if not contracts_dir.is_dir():
                continue

            for cf in contracts_dir.glob("*.yaml"):
                try:
                    with open(cf, "r", encoding="utf-8") as fp:
                        cdata = yaml.safe_load(fp) or {}
                    if cdata.get("status") != "active":
                        continue

                    scanned_contracts += 1
                    fin = cdata.get("financial", {})
                    hb = cdata.get("hours_bank", {})
                    total_h = float(fin.get("total_hours_included", hb.get("total_purchased", 0.0)))
                    consumed_h = float(fin.get("consumed_hours", hb.get("consumed", 0.0)))
                    remaining_h = max(0.0, total_h - consumed_h)
                    pct = round((remaining_h / total_h * 100.0), 1) if total_h > 0 else 0.0

                    # 1. Verifica Monte Ore
                    if total_h > 0 and (pct < 20.0 or remaining_h < 5.0):
                        alerts.append({
                            "slug": slug,
                            "contract_id": cdata.get("contract_id", cf.stem),
                            "type": "HOURS_DEPLETION",
                            "severity": "CRITICAL" if remaining_h < 3.0 else "WARNING",
                            "message": f"Monte ore residuo critico: {remaining_h}h / {total_h}h ({pct}%)",
                        })

                    # 2. Verifica Scadenza
                    exp_str = cdata.get("valid_to") or cdata.get("valid_until")
                    if exp_str:
                        try:
                            exp_date = datetime.date.fromisoformat(exp_str)
                            days_left = (exp_date - today).days
                            if days_left <= 30:
                                alerts.append({
                                    "slug": slug,
                                    "contract_id": cdata.get("contract_id", cf.stem),
                                    "type": "CONTRACT_EXPIRING",
                                    "severity": "HIGH" if days_left <= 15 else "MEDIUM",
                                    "message": f"Contratto in scadenza tra {days_left} giorni (scade il {exp_str})",
                                })
                        except Exception:
                            pass
                except Exception:
                    pass

        # Emissione Trigger Events (SPEC-22)
        try:
            te = TriggerEngine(clients_root=self.clients_root)
            for a in alerts:
                if a.get("type") == "HOURS_DEPLETION":
                    te.emit_event(
                        event_type="telemetry.sla.hours_low",
                        slug=a["slug"],
                        source="daemon:sla",
                        payload={"contract_id": a.get("contract_id"), "message": a.get("message")},
                        auto_evaluate=True,
                    )
        except Exception:
            pass

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "scanned_contracts": scanned_contracts,
            "alerts_count": len(alerts),
            "alerts": alerts,
        }

    def run_loop(self, interval_seconds: int = 3600, once: bool = False) -> None:
        """Esegue il demone in polling continuo o modalità --once."""
        print(f"[*] Avvio SLADaemon (intervallo: {interval_seconds}s, once={once})...")
        while True:
            res = self.check_all()
            print(f"[{res['timestamp']}] SLA Check: {res['scanned_contracts']} contratti analizzati, {res['alerts_count']} allarmi.")
            for a in res["alerts"]:
                print(f"  [{a['severity']} - {a['type']}] {a['slug'].upper()} | {a['contract_id']}: {a['message']}")
            if once:
                break
            time.sleep(interval_seconds)


class CreditDaemon:
    """
    Demone proattivo per il monitoraggio dei crediti attivi, insoluti ex D.Lgs. 231/2002
    e scadenze contrattuali preventive a 60 e 30 giorni (SPEC-24).
    """

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def check_all(self) -> Dict[str, Any]:
        """Esegue un ciclo di controllo deterministico su fatture e contratti."""
        from scripts.core.italian_compliance import ItalianComplianceGuard
        alerts: List[Dict[str, Any]] = []
        scanned_invoices = 0
        scanned_contracts = 0
        today = datetime.date.today()

        for cdir in self.clients_root.iterdir():
            if not cdir.is_dir() or cdir.name.startswith(("_", ".")):
                continue

            slug = cdir.name

            # 1. Scansione Scadenzario Fatture
            inv_dir = cdir / "invoices"
            if inv_dir.is_dir():
                for inv_file in inv_dir.glob("*.yaml"):
                    try:
                        with open(inv_file, "r", encoding="utf-8") as fp:
                            idata = yaml.safe_load(fp) or {}
                        scanned_invoices += 1
                        inv_draft = idata.get("invoice_draft", {})
                        inv_num = inv_draft.get("invoice_number", inv_file.stem)
                        inv_date = inv_draft.get("invoice_date", today.isoformat())

                        # Controlla rate scadenzario
                        scad = idata.get("scadenzario", {})
                        installments = scad.get("installments", [])
                        for inst in installments:
                            st = inst.get("status", "unpaid")
                            if st in ("unpaid", "reminded_1", "reminded_2"):
                                d_str = inst.get("due_date")
                                amt = float(inst.get("amount", 0.0))
                                if d_str:
                                    calc = ItalianComplianceGuard.calculate_dlgs231_interest(amt, d_str)
                                    days = calc.get("days_overdue", 0)
                                    if days >= 7:
                                        stage = 1 if days <= 14 else (2 if days <= 30 else 3)
                                        alerts.append({
                                            "slug": slug,
                                            "type": "INVOICE_OVERDUE",
                                            "invoice_number": inv_num,
                                            "invoice_date": inv_date,
                                            "due_date": d_str,
                                            "amount": amt,
                                            "days_overdue": days,
                                            "stage": stage,
                                            "interest_mora": calc.get("interest_mora", 0.0),
                                            "lump_sum_fee": calc.get("lump_sum_fee", 0.0),
                                            "total_due": calc.get("total_due_dlgs231", amt),
                                            "severity": "CRITICAL" if stage == 3 else ("HIGH" if stage == 2 else "MEDIUM"),
                                            "message": f"Fattura {inv_num} scaduta da {days} gg. Capitale: € {amt:.2f}, Mora: € {calc.get('interest_mora', 0.0):.2f}, Totale: € {calc.get('total_due_dlgs231', amt):.2f} (Stadio {stage})"
                                        })
                    except Exception:
                        pass

            # 2. Scansione Scadenze Contratti a 60 e 30 giorni
            ctr_dir = cdir / "contracts"
            if ctr_dir.is_dir():
                for cf in ctr_dir.glob("*.yaml"):
                    try:
                        with open(cf, "r", encoding="utf-8") as fp:
                            cdata = yaml.safe_load(fp) or {}
                        scanned_contracts += 1
                        exp_str = cdata.get("valid_to") or cdata.get("valid_until")
                        if exp_str:
                            exp_date = datetime.date.fromisoformat(exp_str)
                            days_left = (exp_date - today).days
                            if 0 <= days_left <= 60:
                                reminder_type = "RENEWAL_30D" if days_left <= 30 else "RENEWAL_60D"
                                alerts.append({
                                    "slug": slug,
                                    "type": reminder_type,
                                    "contract_id": cdata.get("contract_id", cf.stem),
                                    "days_left": days_left,
                                    "valid_to": exp_str,
                                    "severity": "HIGH" if days_left <= 30 else "MEDIUM",
                                    "message": f"Contratto {cdata.get('contract_id', cf.stem)} in scadenza tra {days_left} gg ({exp_str}). Necessaria trattativa rinnovo/disdetta."
                                })
                    except Exception:
                        pass

        # Emissione Trigger Events (SPEC-22 & SPEC-24)
        try:
            te = TriggerEngine(clients_root=self.clients_root)
            for a in alerts:
                if a.get("type") == "INVOICE_OVERDUE":
                    te.emit_event(
                        event_type="finance.invoice.overdue",
                        slug=a["slug"],
                        source="daemon:credit",
                        payload=a,
                        auto_evaluate=True,
                    )
                elif a.get("type") in ("RENEWAL_60D", "RENEWAL_30D"):
                    te.emit_event(
                        event_type=f"contract.renewal.{a['type'].lower()}",
                        slug=a["slug"],
                        source="daemon:credit",
                        payload=a,
                        auto_evaluate=True,
                    )
        except Exception:
            pass

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "scanned_invoices": scanned_invoices,
            "scanned_contracts": scanned_contracts,
            "alerts_count": len(alerts),
            "alerts": alerts,
        }

    def run_loop(self, interval_seconds: int = 3600, once: bool = False) -> None:
        """Esegue il demone in polling continuo o modalità --once."""
        print(f"[*] Avvio CreditDaemon (intervallo: {interval_seconds}s, once={once})...")
        while True:
            res = self.check_all()
            print(f"[{res['timestamp']}] Credit Check: {res['scanned_invoices']} fatture, {res['scanned_contracts']} contratti, {res['alerts_count']} allarmi.")
            for a in res["alerts"]:
                print(f"  [{a['severity']} - {a['type']}] {a['slug'].upper()}: {a['message']}")
            if once:
                break
            time.sleep(interval_seconds)
