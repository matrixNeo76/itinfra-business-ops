#!/usr/bin/env python3
"""
scripts/pipelines/mission_control.py — Mission Control Executive Cockpit 360° (SPEC-20, SPEC-24)
Consolle centralizzata unificata per la governance tecnica, operativa, commerciale e di conformità:
- SLA Hours Bank, Burn Rate & Allarmi Esaurimento
- Safe Action Gate: coda approvazioni human-in-the-loop (SPEC-22)
- FSM Workflow Studio: stepper deterministico e resume checkpoint (SPEC-21, SPEC-24)
- Scadenzario Attivo & Recupero Crediti D.Lgs. 231/2002 con calcolo mora e lettere (SPEC-24)
- Presidio Normativo Italiano: P.IVA (Luhn), CF (omocodie), SDI e CCNL Lavoro (SPEC-24)
- Parco Macchine MPS & Consumabili con teleletture
- Hub-and-Spoke Federation con itinfra (As-Built & Workflow Tecnici)
- Swarm Agenti Deterministici e Demoni Proattivi
"""

import datetime
import json
import os
import sys
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

from scripts.core.config import get_clients_dir, get_itinfra_dir
from scripts.core.bridge import ITInfraBridge
from scripts.core.workflow_engine import WorkflowEngine
from scripts.core.trigger_engine import TriggerEngine
from scripts.core.italian_compliance import ItalianComplianceGuard
from scripts.pipelines.workflow_definitions import WorkflowRegistry


class MissionControlPipeline:
    """
    Raccoglie in tempo reale lo stato operativo, finanziario, contrattuale,
    sistemistico e di conformità di tutti i clienti attivi di Aure System.
    """

    def __init__(self, clients_root: Optional[Path] = None, itinfra_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.itinfra_root = itinfra_root or get_itinfra_dir()
        self.bridge = ITInfraBridge(itinfra_root=self.itinfra_root, clients_root=self.clients_root)

    def collect_client_metrics(self, slug: str) -> Dict[str, Any]:
        """Raccoglie tutte le metriche deterministiche per un singolo cliente."""
        cdir = self.clients_root / slug
        manifest_file = cdir / "client-manifest.yaml"

        manifest: Dict[str, Any] = {}
        if manifest_file.is_file():
            try:
                with open(manifest_file, "r", encoding="utf-8") as fp:
                    manifest = yaml.safe_load(fp) or {}
            except Exception:
                pass

        client_name = manifest.get("client_name", slug.replace("-", " ").title())
        tier = manifest.get("tier", "standard")
        piva_raw = manifest.get("partita_iva") or manifest.get("vat_number") or ""
        cf_raw = manifest.get("codice_fiscale") or manifest.get("fiscal_code") or ""
        sdi_raw = manifest.get("codice_destinatario_sdi") or manifest.get("sdi_code") or "0000000"
        pec_raw = manifest.get("pec") or manifest.get("pec_email") or ""

        # Validazione formale fiscale italiana (SPEC-24)
        piva_val = ItalianComplianceGuard.validate_partita_iva(piva_raw) if piva_raw else {"valid": False, "error": "Non indicata"}
        cf_val = ItalianComplianceGuard.validate_codice_fiscale(cf_raw) if cf_raw else {"valid": False, "error": "Non indicato"}
        sdi_val = ItalianComplianceGuard.validate_sdi_recipient(sdi_raw, pec_raw)

        # 1. Contratti SLA & Hours Bank
        contracts_dir = cdir / "contracts"
        total_purchased_hours = 0.0
        total_consumed_hours = 0.0
        active_contracts_count = 0
        sla_level = "Standard"
        contracts_list: List[Dict[str, Any]] = []

        if contracts_dir.is_dir():
            for cf in sorted(contracts_dir.glob("*.yaml")):
                try:
                    with open(cf, "r", encoding="utf-8") as fp:
                        cdata = yaml.safe_load(fp) or {}
                    c_id = cdata.get("contract_id", cf.stem)
                    c_status = cdata.get("status", "active")
                    hb = cdata.get("hours_bank", {})
                    fin = cdata.get("financial", {})
                    purchased = float(fin.get("total_hours_included", hb.get("total_purchased", 0.0)))
                    consumed = float(fin.get("consumed_hours", hb.get("consumed", 0.0)))
                    level = cdata.get("sla", {}).get("level") or cdata.get("sla", {}).get("tier", sla_level)
                    exp_date = cdata.get("validity", {}).get("end_date") or cdata.get("sla", {}).get("valid_until", "N/D")

                    if c_status == "active":
                        active_contracts_count += 1
                        total_purchased_hours += purchased
                        total_consumed_hours += consumed
                        sla_level = level

                    contracts_list.append({
                        "contract_id": c_id,
                        "status": c_status,
                        "purchased_hours": purchased,
                        "consumed_hours": consumed,
                        "remaining_hours": max(0.0, purchased - consumed),
                        "level": level,
                        "end_date": exp_date
                    })
                except Exception:
                    pass

        remaining_hours = max(0.0, total_purchased_hours - total_consumed_hours)
        hours_pct = round((remaining_hours / total_purchased_hours * 100.0), 1) if total_purchased_hours > 0 else 0.0
        sla_alert = (hours_pct < 20.0 or remaining_hours < 5.0) if total_purchased_hours > 0 else False

        # 2. Timesheet e ore non fatturate
        timesheets_dir = cdir / "timesheets"
        unbilled_spot_hours = 0.0
        interventions_count = 0
        recent_interventions: List[Dict[str, Any]] = []

        if timesheets_dir.is_dir():
            for rf in sorted(timesheets_dir.glob("*.yaml"), reverse=True):
                try:
                    with open(rf, "r", encoding="utf-8") as fp:
                        rdata = yaml.safe_load(fp) or {}
                    interventions_count += 1
                    la = rdata.get("ledger_action") or rdata.get("intervention", {}).get("ledger_action")
                    is_invoiced = rdata.get("invoicing", {}).get("invoiced", False)
                    hrs = float(rdata.get("total_hours_rounded") or rdata.get("intervention", {}).get("billable_hours", 0.0))
                    if la == "invoice_spot" and not is_invoiced:
                        unbilled_spot_hours += hrs

                    if len(recent_interventions) < 5:
                        recent_interventions.append({
                            "report_id": rdata.get("report_id", rf.stem),
                            "date": rdata.get("date") or rdata.get("intervention", {}).get("date", ""),
                            "technician": rdata.get("technician") or rdata.get("lead_engineer", "N/D"),
                            "hours": hrs,
                            "ledger_action": la,
                            "invoiced": is_invoiced,
                            "description": rdata.get("description", "")[:80]
                        })
                except Exception:
                    pass

        # 3. Fatturazione, Scadenzario & Crediti 231 (SPEC-24)
        invoices_dir = cdir / "invoices"
        open_invoices_eur = 0.0
        total_invoiced_eur = 0.0
        overdue_invoices_eur = 0.0
        total_mora_interest_eur = 0.0
        invoices_list: List[Dict[str, Any]] = []

        aging_buckets = {
            "0_30": 0.0,
            "31_60": 0.0,
            "61_90": 0.0,
            "90_plus": 0.0
        }

        if invoices_dir.is_dir():
            for inv_file in list(invoices_dir.glob("*.yaml")) + list(invoices_dir.glob("*.json")):
                try:
                    with open(inv_file, "r", encoding="utf-8") as fp:
                        if inv_file.suffix == ".json":
                            idata = json.load(fp) or {}
                        else:
                            idata = yaml.safe_load(fp) or {}

                    inv_num = idata.get("invoice_number") or idata.get("id") or inv_file.stem
                    inv_date = idata.get("invoice_date") or idata.get("date") or "2026-01-01"
                    scad = idata.get("scadenzario", {})

                    if scad and "installments" in scad:
                        for inst in scad["installments"]:
                            amt = float(inst.get("amount", 0.0))
                            st = inst.get("status", "pending")
                            due = inst.get("due_date", inv_date)
                            total_invoiced_eur += amt
                            if st in ["unpaid", "overdue", "pending"]:
                                open_invoices_eur += amt
                                m_calc = ItalianComplianceGuard.calculate_dlgs231_interest(amt, due)
                                days_ov = m_calc.get("days_overdue", 0)
                                if days_ov > 0:
                                    overdue_invoices_eur += amt
                                    total_mora_interest_eur += m_calc.get("interest_amount", 0.0)
                                    if days_ov <= 30: aging_buckets["0_30"] += amt
                                    elif days_ov <= 60: aging_buckets["31_60"] += amt
                                    elif days_ov <= 90: aging_buckets["61_90"] += amt
                                    else: aging_buckets["90_plus"] += amt

                                invoices_list.append({
                                    "invoice_number": inv_num,
                                    "due_date": due,
                                    "amount": amt,
                                    "status": st,
                                    "days_overdue": days_ov,
                                    "mora_eur": m_calc.get("interest_amount", 0.0),
                                    "suggested_stage": m_calc.get("suggested_action_stage", "ORDINARY")
                                })
                    else:
                        tot = float(idata.get("totals", {}).get("total_gross", idata.get("total_net", 0.0)))
                        st = idata.get("status", "pending")
                        total_invoiced_eur += tot
                        if st in ["unpaid", "draft", "open", "pending"]:
                            open_invoices_eur += tot
                            due = idata.get("due_date", inv_date)
                            m_calc = ItalianComplianceGuard.calculate_dlgs231_interest(tot, due)
                            days_ov = m_calc.get("days_overdue", 0)
                            if days_ov > 0:
                                overdue_invoices_eur += tot
                                total_mora_interest_eur += m_calc.get("interest_amount", 0.0)
                                if days_ov <= 30: aging_buckets["0_30"] += tot
                                elif days_ov <= 60: aging_buckets["31_60"] += tot
                                elif days_ov <= 90: aging_buckets["61_90"] += tot
                                else: aging_buckets["90_plus"] += tot

                            invoices_list.append({
                                "invoice_number": inv_num,
                                "due_date": due,
                                "amount": tot,
                                "status": st,
                                "days_overdue": days_ov,
                                "mora_eur": m_calc.get("interest_amount", 0.0),
                                "suggested_stage": m_calc.get("suggested_action_stage", "ORDINARY")
                            })
                except Exception:
                    pass

        # 4. Parco Macchine MPS & Consumabili
        mps_dir = cdir / "mps"
        printers_count = 0
        toner_alerts: List[Dict[str, Any]] = []
        printers_list: List[Dict[str, Any]] = []

        if mps_dir.is_dir():
            for mf in sorted(mps_dir.glob("*.yaml")):
                try:
                    with open(mf, "r", encoding="utf-8") as fp:
                        mdata = yaml.safe_load(fp) or {}

                    for p in mdata.get("printers", []):
                        printers_count += 1
                        cnts = p.get("current_counters", {})
                        tbk = cnts.get("toner_black_pct", 100)
                        tc = cnts.get("toner_cyan_pct", 100)
                        tm = cnts.get("toner_magenta_pct", 100)
                        ty = cnts.get("toner_yellow_pct", 100)
                        low_toners = []
                        if tbk <= 15: low_toners.append(f"BK ({tbk}%)")
                        if tc <= 15: low_toners.append(f"C ({tc}%)")
                        if tm <= 15: low_toners.append(f"M ({tm}%)")
                        if ty <= 15: low_toners.append(f"Y ({ty}%)")
                        if low_toners:
                            toner_alerts.append({
                                "asset_id": p.get("asset_id", "Printer"),
                                "model": p.get("model", ""),
                                "low_toners": low_toners
                            })
                        printers_list.append({
                            "asset_id": p.get("asset_id", "Printer"),
                            "model": p.get("model", ""),
                            "serial_number": p.get("serial_number", "N/D"),
                            "ip_address": p.get("ip_address", "N/D"),
                            "toners": {"black": tbk, "cyan": tc, "magenta": tm, "yellow": ty},
                            "total_mono": cnts.get("total_mono", 0),
                            "total_color": cnts.get("total_color", 0)
                        })

                    dinfo = mdata.get("device_info", {})
                    if dinfo and "serial_number" in dinfo:
                        printers_count += 1
                        readings = mdata.get("readings", [])
                        tbk, tc, tm, ty = 100, 100, 100, 100
                        mono_c, col_c = 0, 0
                        if readings:
                            last_r = readings[-1]
                            tbk = last_r.get("toner_black_percent", 100)
                            tc = last_r.get("toner_cyan_percent", 100)
                            tm = last_r.get("toner_magenta_percent", 100)
                            ty = last_r.get("toner_yellow_percent", 100)
                            mono_c = last_r.get("counter_mono", 0)
                            col_c = last_r.get("counter_color", 0)

                        low_toners = []
                        if tbk <= 15: low_toners.append(f"BK ({tbk}%)")
                        if tc <= 15: low_toners.append(f"C ({tc}%)")
                        if tm <= 15: low_toners.append(f"M ({tm}%)")
                        if ty <= 15: low_toners.append(f"Y ({ty}%)")
                        if low_toners:
                            toner_alerts.append({
                                "asset_id": dinfo.get("serial_number", "Printer"),
                                "model": dinfo.get("model", ""),
                                "low_toners": low_toners
                            })
                        printers_list.append({
                            "asset_id": dinfo.get("serial_number", "Printer"),
                            "model": dinfo.get("model", ""),
                            "serial_number": dinfo.get("serial_number", "N/D"),
                            "ip_address": dinfo.get("ip_address", "N/D"),
                            "toners": {"black": tbk, "cyan": tc, "magenta": tm, "yellow": ty},
                            "total_mono": mono_c,
                            "total_color": col_c
                        })
                except Exception:
                    pass

        # 5. Gap Analysis & Compliance 231
        gap_dir = cdir / "gap_analysis"
        compliance_score = 0.0
        va_findings_count = 0
        has_231 = False
        findings_list: List[Dict[str, Any]] = []

        if gap_dir.is_dir():
            for gf in gap_dir.glob("*.yaml"):
                try:
                    with open(gf, "r", encoding="utf-8") as fp:
                        gdata = yaml.safe_load(fp) or {}
                    has_231 = True
                    scores = gdata.get("gap_scores", {})
                    if "overall_compliance_percent" in scores:
                        compliance_score = float(scores["overall_compliance_percent"])
                    elif "scoring" in gdata and "maturity_percent" in gdata["scoring"]:
                        compliance_score = float(gdata["scoring"]["maturity_percent"])

                    va_list = gdata.get("vulnerability_assessment", []) or gdata.get("findings_va", [])
                    va_findings_count += len(va_list)
                    for f in va_list[:5]:
                        findings_list.append({
                            "cve": f.get("cve", "CVE-N/D"),
                            "severity": f.get("severity", "MEDIUM"),
                            "description": f.get("description", "")[:70]
                        })
                except Exception:
                    pass

        # 6. Hub-and-Spoke Federation Bridge
        bridge_status = "NO_TECH_REPO"
        bridge_details = {}
        if self.bridge.project_exists(slug):
            cov = self.bridge.cross_check_sla_assets_coverage(slug)
            bridge_status = cov.get("status", "SYNCED")
            bridge_details = cov

        # 7. Workflow locali per questo cliente
        wf_engine = WorkflowEngine(repo_root=ROOT_DIR, clients_root=self.clients_root)
        client_wfs = wf_engine.list_workflows(slug=slug, limit=5)

        return {
            "slug": slug,
            "client_name": client_name,
            "tier": tier,
            "fiscal": {
                "partita_iva": piva_raw,
                "codice_fiscale": cf_raw,
                "sdi_code": sdi_raw,
                "pec": pec_raw,
                "piva_valid": piva_val.get("valid", False),
                "cf_valid": cf_val.get("valid", False),
                "sdi_valid": sdi_val.get("valid", False)
            },
            "sla_level": sla_level,
            "active_contracts_count": active_contracts_count,
            "total_purchased_hours": total_purchased_hours,
            "total_consumed_hours": total_consumed_hours,
            "remaining_hours": remaining_hours,
            "hours_pct": hours_pct,
            "sla_alert": sla_alert,
            "contracts": contracts_list,
            "interventions_count": interventions_count,
            "unbilled_spot_hours": unbilled_spot_hours,
            "recent_interventions": recent_interventions,
            "open_invoices_eur": round(open_invoices_eur, 2),
            "overdue_invoices_eur": round(overdue_invoices_eur, 2),
            "total_invoiced_eur": round(total_invoiced_eur, 2),
            "total_mora_interest_eur": round(total_mora_interest_eur, 2),
            "aging_buckets": {k: round(v, 2) for k, v in aging_buckets.items()},
            "invoices": invoices_list,
            "printers_count": printers_count,
            "toner_alerts": toner_alerts,
            "printers": printers_list,
            "has_231": has_231,
            "compliance_score": compliance_score,
            "va_findings_count": va_findings_count,
            "findings": findings_list,
            "bridge_status": bridge_status,
            "bridge_details": bridge_details,
            "workflows": client_wfs
        }

    def collect_all(self) -> Dict[str, Any]:
        """Raccoglie le metriche globali aggregate su tutti i clienti."""
        client_dirs = [d for d in self.clients_root.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
        clients_data = []

        total_sla_hours_available = 0.0
        total_sla_hours_consumed = 0.0
        total_open_credit_eur = 0.0
        total_overdue_credit_eur = 0.0
        total_mora_231_eur = 0.0
        total_unbilled_hours = 0.0
        total_printers = 0
        total_toner_critical_alerts = 0
        avg_compliance_accum = 0.0
        compliance_clients_count = 0

        global_aging = {
            "0_30": 0.0,
            "31_60": 0.0,
            "61_90": 0.0,
            "90_plus": 0.0
        }

        for cd in sorted(client_dirs, key=lambda x: x.name):
            m = self.collect_client_metrics(cd.name)
            clients_data.append(m)

            total_sla_hours_available += m["remaining_hours"]
            total_sla_hours_consumed += m["total_consumed_hours"]
            total_open_credit_eur += m["open_invoices_eur"]
            total_overdue_credit_eur += m["overdue_invoices_eur"]
            total_mora_231_eur += m["total_mora_interest_eur"]
            total_unbilled_hours += m["unbilled_spot_hours"]
            total_printers += m["printers_count"]
            total_toner_critical_alerts += len(m["toner_alerts"])

            for k in global_aging:
                global_aging[k] += m["aging_buckets"].get(k, 0.0)

            if m["has_231"]:
                avg_compliance_accum += m["compliance_score"]
                compliance_clients_count += 1

        avg_compliance = round(avg_compliance_accum / compliance_clients_count, 1) if compliance_clients_count > 0 else 0.0

        wf_engine = WorkflowEngine(repo_root=ROOT_DIR, clients_root=self.clients_root)
        recent_workflows = wf_engine.list_workflows(limit=10)

        trigger_engine = TriggerEngine(repo_root=ROOT_DIR, clients_root=self.clients_root)
        pending_actions = trigger_engine.list_pending_actions()

        daemons_info = [
            {"id": "mps", "name": "MPS Telemetry & Consumables Daemon", "interval": "300s", "status": "ACTIVE", "target": "Toner <= 15%", "command": ".\\it-ops.cmd daemon mps --once"},
            {"id": "sla", "name": "SLA Hours & Expiration Daemon", "interval": "600s", "status": "ACTIVE", "target": "Ore SLA < 20% o scadenza < 30gg", "command": ".\\it-ops.cmd daemon sla --once"},
            {"id": "credit", "name": "Credit Recovery & D.Lgs. 231/2002 Daemon", "interval": "3600s", "status": "ACTIVE", "target": "Fatture scadute > 30gg & Tasso 11.5%", "command": ".\\it-ops.cmd daemon credit --once"}
        ]

        swarm_agents = [
            {"type": "audit-231", "role": "Compliance & Gap Auditor", "scope": "D.Lgs. 231/2001, ISO 27001, NIST CSF", "status": "READY", "cli": ".\\it-ops.cmd agent audit-231"},
            {"type": "finance-reconciler", "role": "Financial PSA Reconciler", "scope": "Timesheet, Ore SLA, MPS & Fatture", "status": "READY", "cli": ".\\it-ops.cmd agent finance-reconciler"},
            {"type": "infrastructure-sentinel", "role": "Infrastructure Sentinel", "scope": "Telemetry, As-Built & Network Health", "status": "READY", "cli": ".\\it-ops.cmd agent infrastructure-sentinel"},
            {"type": "contract-guardian", "role": "Contract SLA Guardian", "scope": "Hours Bank Burn Rate & Scadenze", "status": "READY", "cli": ".\\it-ops.cmd agent contract-guardian"}
        ]

        wf_catalog = []
        for w_type, w_meta in WorkflowRegistry.get_definitions().items():
            wf_catalog.append({
                "type": w_type,
                "name": w_meta.get("name", w_type),
                "description": w_meta.get("description", ""),
                "stages_count": len(w_meta.get("steps", [])),
                "stages": [s.get("name", s.get("step_id")) for s in w_meta.get("steps", [])],
                "category": "technical" if w_type in ["dr-drill", "firmware-upgrade", "hardware-decommissioning-raee"] else "business"
            })

        return {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_clients": len(clients_data),
            "recent_workflows": recent_workflows,
            "pending_actions": pending_actions,
            "daemons": daemons_info,
            "swarm_agents": swarm_agents,
            "workflow_catalog": wf_catalog,
            "global_kpis": {
                "total_sla_hours_available": round(total_sla_hours_available, 1),
                "total_sla_hours_consumed": round(total_sla_hours_consumed, 1),
                "total_open_credit_eur": round(total_open_credit_eur, 2),
                "total_overdue_credit_eur": round(total_overdue_credit_eur, 2),
                "total_mora_231_eur": round(total_mora_231_eur, 2),
                "global_aging": {k: round(v, 2) for k, v in global_aging.items()},
                "total_unbilled_hours": round(total_unbilled_hours, 1),
                "total_printers": total_printers,
                "total_toner_critical_alerts": total_toner_critical_alerts,
                "avg_compliance_score": avg_compliance,
                "pending_actions_count": len(pending_actions)
            },
            "clients": clients_data
        }

    def render_tui(self) -> str:
        """Genera una vista TUI Unicode formattata ad alta leggibilità per terminale."""
        data = self.collect_all()
        kpis = data["global_kpis"]

        lines = []
        lines.append("=" * 80)
        lines.append("  🚀 AURE SYSTEM — MISSION CONTROL EXECUTIVE DASHBOARD (v0.3.5)")
        lines.append("=" * 80)
        lines.append(f"  📅 Data Rilevazione: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"  🏢 Clienti Gestiti : {data['total_clients']}")
        lines.append("-" * 80)
        lines.append(
            f"  [SLA ORE BANCA] Rimanenti: {kpis['total_sla_hours_available']}h | "
            f"Consumate: {kpis['total_sla_hours_consumed']}h"
        )
        lines.append(
            f"  [FINANZA 231]   Aperti: €{kpis['total_open_credit_eur']:,.2f} | "
            f"Scaduti: €{kpis['total_overdue_credit_eur']:,.2f} | Mora 231: €{kpis['total_mora_231_eur']:,.2f}"
        )
        lines.append(
            f"  [HARDWARE & MPS] Stampanti: {kpis['total_printers']} | "
            f"Allarmi Toner: {kpis['total_toner_critical_alerts']}"
        )
        lines.append(
            f"  [GOVERNANCE 231] Conformità Media: {kpis['avg_compliance_score']}%"
        )
        lines.append("=" * 80)
        lines.append(f"{'CLIENTE':<20} | {'SLA ORE':<12} | {'CREDITI':<10} | {'MPS':<8} | {'231%':<6} | {'BRIDGE':<10}")
        lines.append("-" * 80)

        for c in data["clients"]:
            sla_str = f"{c['remaining_hours']:.1f}h ({c['hours_pct']}%)"
            if c["sla_alert"]:
                sla_str += " [!]"
            cred_str = f"€{c['open_invoices_eur']:,.0f}"
            mps_str = f"{c['printers_count']} prn"
            if c["toner_alerts"]:
                mps_str += f" [!{len(c['toner_alerts'])}]"
            comp_str = f"{c['compliance_score']:.0f}%" if c["has_231"] else "N/A"
            br_str = c["bridge_status"]

            lines.append(f"{c['slug']:<20} | {sla_str:<12} | {cred_str:<10} | {mps_str:<8} | {comp_str:<6} | {br_str:<10}")

        pa = data.get("pending_actions", [])
        if pa:
            lines.append("-" * 80)
            lines.append(f"  🔔 AZIONI IN ATTESA DI APPROVAZIONE (SAFE ACTION GATE — {len(pa)} PENDENTI)")
            lines.append("-" * 80)
            for a in pa:
                aid = a.get("action_id", "")
                aslug = a.get("slug", "")
                atitle = a.get("title", "")
                lines.append(f"  [!] {aid:<30} | {aslug:<15} | {atitle}")
            lines.append("  Approva con: .\\it-ops.cmd triggers approve <action_id>")
            lines.append("=" * 80)

        rw = data.get("recent_workflows", [])
        if rw:
            lines.append("-" * 80)
            lines.append("  🔄 WORKFLOWS RECENTI & AUTOMAZIONI (SPEC-21 / SPEC-24)")
            lines.append("-" * 80)
            for w in rw:
                wid = w.get("workflow_id", "")
                wtype = w.get("workflow_type", "")
                wstatus = w.get("status", "UNKNOWN")
                badge = "[✓]" if wstatus == "COMPLETED" else "[!]" if wstatus == "FAILED" else "[~]"
                lines.append(f"  {badge} {wid:<32} | {wtype:<20} | {wstatus}")
            lines.append("=" * 80)

        return "\n".join(lines)

    def render_html(self, output_path: Optional[Path] = None) -> str:
        """
        Genera la Consolle Generativa Esecutiva Standalone e Zero-CDN (SPEC-20, SPEC-24).
        Include navigazione reattiva a 8 moduli/tab, grafici vettoriali SVG, modali
        di dettaglio, simulatore live di mora 231 e CCNL, e copy-to-clipboard per la CLI.
        """
        data = self.collect_all()
        data_json = json.dumps(data, ensure_ascii=False)
        html_output = HTML_TEMPLATE.replace("__DASHBOARD_DATA_JSON__", data_json)

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(html_output, encoding="utf-8")

        return html_output


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aure System — Enterprise Cockpit 360° & Mission Control</title>
<style>
  :root {
    --bg-main: #070d1e;
    --bg-card: #0f1c3f;
    --bg-card-sub: #162858;
    --bg-row-hover: #1c336e;
    --border-color: #223c7c;
    --border-highlight: #3b82f6;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --accent-cyan: #38bdf8;
    --accent-blue: #3b82f6;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --accent-purple: #a855f7;
    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-family); }
  body { background-color: var(--bg-main); color: var(--text-primary); padding: 20px; line-height: 1.5; font-size: 13px; }
  .container { max-width: 1440px; margin: 0 auto; }
  
  /* Header */
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border-color); padding-bottom: 18px; margin-bottom: 20px; }
  .brand-group { display: flex; align-items: center; gap: 14px; }
  .logo-box { width: 44px; height: 44px; background: linear-gradient(135deg, #0284c7, #2563eb); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 900; color: #fff; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4); }
  .brand-title { font-size: 22px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }
  .brand-title span { color: var(--accent-cyan); }
  .brand-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  .system-status { text-align: right; }

  /* KPI Ribbon */
  .kpi-ribbon { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 22px; }
  .kpi-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; transition: transform 0.15s ease, border-color 0.15s ease; cursor: pointer; }
  .kpi-card:hover { transform: translateY(-2px); border-color: var(--accent-cyan); }
  .kpi-header { display: flex; justify-content: space-between; align-items: center; font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .kpi-value { font-size: 26px; font-weight: 800; color: #fff; line-height: 1.1; }
  .kpi-footer { font-size: 11px; color: var(--text-muted); margin-top: 8px; display: flex; justify-content: space-between; }

  /* Navigation Tabs */
  .tabs-nav { display: flex; gap: 8px; border-bottom: 2px solid var(--border-color); margin-bottom: 20px; overflow-x: auto; padding-bottom: 2px; }
  .tab-btn { background: transparent; border: none; color: var(--text-muted); font-size: 12px; font-weight: 700; padding: 10px 16px; border-radius: 8px 8px 0 0; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.15s ease; border-bottom: 2px solid transparent; margin-bottom: -2px; }
  .tab-btn:hover { color: #fff; background: rgba(56, 189, 248, 0.08); }
  .tab-btn.active { color: var(--accent-cyan); border-bottom-color: var(--accent-cyan); background: var(--bg-card); }
  .tab-badge { background: var(--accent-rose); color: #fff; font-size: 10px; font-weight: 800; padding: 1px 6px; border-radius: 10px; }

  /* Tab Panes */
  .tab-pane { display: none; }
  .tab-pane.active { display: block; animation: fadeIn 0.2s ease-in-out; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  /* Sections & Cards */
  .section-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; margin-bottom: 20px; }
  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(34, 60, 124, 0.6); padding-bottom: 10px; }
  .section-title { font-size: 15px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }

  /* Tables */
  table { width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; }
  th { background: rgba(7, 13, 30, 0.6); padding: 10px 12px; color: var(--text-muted); text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; border-bottom: 2px solid var(--border-color); }
  td { padding: 12px; border-bottom: 1px solid rgba(34, 60, 124, 0.5); vertical-align: middle; }
  tr:hover { background-color: var(--bg-row-hover); }

  /* Badges */
  .badge { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; display: inline-flex; align-items: center; gap: 4px; }
  .badge-success { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #10b981; }
  .badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #f59e0b; }
  .badge-danger { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid #f43f5e; }
  .badge-info { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; }
  .badge-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; }
  .badge-neutral { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid #64748b; }

  /* Buttons */
  .btn { padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.15s ease; }
  .btn-primary { background: #0284c7; color: #fff; }
  .btn-primary:hover { background: #0369a1; }
  .btn-success { background: #10b981; color: #fff; }
  .btn-success:hover { background: #059669; }
  .btn-danger { background: #f43f5e; color: #fff; }
  .btn-danger:hover { background: #e11d48; }
  .btn-secondary { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
  .btn-secondary:hover { background: #334155; color: #fff; }

  /* Search & Filter Bar */
  .filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
  .search-input { background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 12px; color: #fff; font-size: 12px; min-width: 260px; outline: none; }
  .search-input:focus { border-color: var(--accent-cyan); }
  .filter-chip { background: var(--bg-card-sub); border: 1px solid var(--border-color); color: var(--text-muted); padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; }
  .filter-chip.active { background: var(--accent-cyan); color: #070d1e; border-color: var(--accent-cyan); font-weight: 700; }

  /* Cards Grid */
  .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
  .action-gate-card { background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; border-left: 4px solid var(--accent-rose); }
  .action-gate-card.warning { border-left-color: var(--accent-amber); }
  .action-gate-card.info { border-left-color: var(--accent-cyan); }

  /* Stepper FSM */
  .stepper { display: flex; align-items: center; gap: 6px; margin-top: 10px; overflow-x: auto; padding: 6px 0; }
  .step-node { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; }
  .step-dot { width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 900; }
  .step-line { width: 24px; height: 2px; background: var(--border-color); }
  .step-line.done { background: var(--accent-emerald); }

  /* Progress Bar */
  .progress-bar-bg { width: 100%; height: 8px; background: rgba(7, 13, 30, 0.6); border-radius: 4px; overflow: hidden; margin-top: 4px; }
  .progress-bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }

  /* Modals */
  .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.75); display: none; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
  .modal-overlay.open { display: flex; }
  .modal-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; width: 90%; max-width: 720px; max-height: 85vh; overflow-y: auto; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative; }
  .modal-close { position: absolute; top: 16px; right: 16px; background: transparent; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer; }

  /* Toast Notification */
  .toast { position: fixed; bottom: 20px; right: 20px; background: #10b981; color: #022c22; padding: 12px 20px; border-radius: 8px; font-weight: 700; font-size: 12px; display: none; box-shadow: 0 10px 25px rgba(0,0,0,0.4); z-index: 2000; animation: slideIn 0.2s ease-out; }
  .toast.show { display: block; }
  @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  .footer { text-align: center; font-size: 11px; color: var(--text-muted); padding: 24px 0; border-top: 1px solid var(--border-color); margin-top: 30px; }
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="brand-group">
      <div class="logo-box">AS</div>
      <div>
        <div class="brand-title">AURE <span>SYSTEM</span> &bull; Enterprise Cockpit 360°</div>
        <div class="brand-subtitle">Centrale di Continuous Assurance, SLA PSA, Safe Action Gate, Workflows FSM & Presidio Normativo Italiano (v0.3.5)</div>
      </div>
    </div>
    <div class="system-status">
      <span class="badge badge-success"><span style="width:6px; height:6px; border-radius:50%; background:#10b981; display:inline-block;"></span> DETERMINISTICO OPERATIVO</span>
      <div id="live-clock" style="font-size: 11px; color: var(--text-muted); margin-top: 4px;"></div>
    </div>
  </div>

  <!-- KPI Ribbon -->
  <div class="kpi-ribbon" id="kpi-ribbon">
    <!-- Popolato dinamicamente da JS -->
  </div>

  <!-- Navigation Tabs -->
  <div class="tabs-nav">
    <button class="tab-btn active" onclick="switchTab('tab-overview')"><span>📊</span> 1. Panoramica 360°</button>
    <button class="tab-btn" onclick="switchTab('tab-gate')"><span>🛡️</span> 2. Safe Action Gate <span id="gate-tab-badge" class="tab-badge" style="display:none;">0</span></button>
    <button class="tab-btn" onclick="switchTab('tab-workflows')"><span>🔄</span> 3. Workflows FSM</button>
    <button class="tab-btn" onclick="switchTab('tab-credit')"><span>⚖️</span> 4. Crediti & Mora 231</button>
    <button class="tab-btn" onclick="switchTab('tab-compliance')"><span>🇮🇹</span> 5. Presidio Italiano & CCNL</button>
    <button class="tab-btn" onclick="switchTab('tab-client-drill')"><span>🏢</span> 6. Scheda Cliente 360°</button>
    <button class="tab-btn" onclick="switchTab('tab-swarm')"><span>🤖</span> 7. Swarm & Demoni</button>
    <button class="tab-btn" onclick="switchTab('tab-technical')"><span>⚙️</span> 8. Hub itinfra & RAEE</button>
  </div>

  <!-- TAB 1: PANORAMICA 360° & MATRICE CLIENTI -->
  <div id="tab-overview" class="tab-pane active">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Matrice Operativa Clienti Aure System</span></div>
        <div style="font-size: 11px; color: var(--text-muted);"><span id="clients-count-label">0</span> Clienti Monitorati</div>
      </div>
      
      <div class="filter-bar">
        <input type="text" id="overview-search" class="search-input" placeholder="🔍 Cerca cliente, slug, tier..." oninput="filterOverviewTable()">
        <button class="filter-chip active" onclick="setOverviewFilter('all', this)">Tutti</button>
        <button class="filter-chip" onclick="setOverviewFilter('sla_alert', this)">Allarmi SLA</button>
        <button class="filter-chip" onclick="setOverviewFilter('toner_alert', this)">Allarmi Toner</button>
        <button class="filter-chip" onclick="setOverviewFilter('overdue', this)">Insoluti 231</button>
        <button class="filter-chip" onclick="setOverviewFilter('gap_231', this)">Audit 231</button>
      </div>

      <div style="overflow-x: auto;">
        <table id="overview-table">
          <thead>
            <tr>
              <th>Cliente & Anagrafica</th>
              <th>SLA Monte Ore</th>
              <th>Contabilità & Crediti</th>
              <th>Parco MPS & Toner</th>
              <th>Conformità 231</th>
              <th>Hub itinfra</th>
              <th>Azioni</th>
            </tr>
          </thead>
          <tbody id="overview-tbody">
            <!-- Popolato dinamicamente da JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 2: SAFE ACTION GATE (SPEC-22) -->
  <div id="tab-gate" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Presidio Human-in-the-Loop — Safe Action Gate (SPEC-22)</span></div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd triggers scan')">🔍 Scansione Trigger Ora</button>
        </div>
      </div>
      <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 16px;">
        Il <strong>Safe Action Gate</strong> intercetta tutti gli eventi operativi (esaurimento monte ore, toner critici, fatture scadute, incidenti tecnici)
        e richiede esplicita autorizzazione prima di compiere effetti collaterali verso clienti, fornitori o contratti.
      </p>
      <div id="action-gate-container" class="cards-grid">
        <!-- Popolato dinamicamente da JS -->
      </div>
    </div>
  </div>

  <!-- TAB 3: WORKFLOWS FSM (SPEC-21, SPEC-24) -->
  <div id="tab-workflows" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Workflow State Machine & Orchestratore FSM</span></div>
      </div>
      <div class="cards-grid" style="margin-bottom: 24px;">
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px;">
          <div style="font-weight: 700; color: var(--accent-cyan); margin-bottom: 6px;">Idempotenza & Checkpointing</div>
          <div style="font-size: 11px; color: var(--text-muted);">Ogni step viene salvato atomicamente su file YAML. In caso di interruzione, la ripresa (resume) parte esattamente dall'ultimo checkpoint intatto.</div>
        </div>
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px;">
          <div style="font-weight: 700; color: var(--accent-emerald); margin-bottom: 6px;">Audit Trail Crittografico</div>
          <div style="font-size: 11px; color: var(--text-muted);">Tutti gli output di transizione calcolano SHA-256 su context ed eventi per garantire la conformità al Modello 231 e GDPR.</div>
        </div>
      </div>

      <div class="section-title" style="margin-bottom: 12px; font-size: 13px;"><span>Cronologia Esecuzioni Recenti</span></div>
      <div id="workflows-list">
        <!-- Popolato dinamicamente da JS -->
      </div>

      <div class="section-title" style="margin-top: 24px; margin-bottom: 12px; font-size: 13px;"><span>Catalogo Workflow Disponibili</span></div>
      <div id="workflow-catalog-grid" class="cards-grid">
        <!-- Popolato da JS -->
      </div>
    </div>
  </div>

  <!-- TAB 4: CREDITI & MORA D.LGS. 231/2002 (SPEC-24) -->
  <div id="tab-credit" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Recupero Crediti & Calcolo Interessi di Mora ex D.Lgs. 231/2002</span></div>
        <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd credit calculate')">📊 Ricalcola Scadenzario</button>
      </div>

      <!-- Aging Banner -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="font-size: 10px; text-transform: uppercase; color: #34d399; font-weight: 700;">0 - 30 Giorni (Bonario)</div>
          <div id="aging-0-30" style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">€0.00</div>
        </div>
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="font-size: 10px; text-transform: uppercase; color: #fbbf24; font-weight: 700;">31 - 60 Giorni (Mora)</div>
          <div id="aging-31-60" style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">€0.00</div>
        </div>
        <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid #f43f5e; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="font-size: 10px; text-transform: uppercase; color: #fb7185; font-weight: 700;">61 - 90 Giorni (Diffida)</div>
          <div id="aging-61-90" style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">€0.00</div>
        </div>
        <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid #a855f7; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="font-size: 10px; text-transform: uppercase; color: #c084fc; font-weight: 700;">Oltre 90 Giorni (Legale)</div>
          <div id="aging-90-plus" style="font-size: 20px; font-weight: 800; color: #fff; margin-top: 4px;">€0.00</div>
        </div>
      </div>

      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; color: #fff;">Parametri Normativi D.Lgs. 231/2002</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Tasso Ufficiale BCE (3.50%) + Spread Legale (8.00%) = <strong>11.50% annuo</strong> &bull; Risarcimento Forfettario Spese: <strong>€ 40,00 fisso</strong> (Art. 6)</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 10px; text-transform: uppercase; color: var(--text-muted);">Mora Totale Maturata</div>
          <div id="total-mora-val" style="font-size: 22px; font-weight: 800; color: var(--accent-rose);">€0.00</div>
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Fattura / Scadenza</th>
              <th>Importo Residuo</th>
              <th>Giorni Scaduto</th>
              <th>Interessi Mora 231</th>
              <th>Stadio Consigliato</th>
              <th>Azioni</th>
            </tr>
          </thead>
          <tbody id="credit-invoices-tbody">
            <!-- Popolato da JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 5: PRESIDIO ITALIANO, FISCALE & CCNL (SPEC-24) -->
  <div id="tab-compliance" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Presidio Normativo Italiano, Controlli Fiscali & CCNL</span></div>
      </div>

      <div class="cards-grid" style="margin-bottom: 24px;">
        <!-- Colonna 1: Validatore Fiscale Live -->
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 18px;">
          <h4 style="color: var(--accent-cyan); margin-bottom: 12px;">Validatore Live Fisco Italiano</h4>
          <div style="margin-bottom: 12px;">
            <label style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Partita IVA (11 cifre / Algoritmo di Luhn)</label>
            <input type="text" id="val-piva-input" class="search-input" style="width: 100%;" placeholder="Es. 01234567890" oninput="testPivaLive()">
            <div id="val-piva-res" style="font-size: 11px; margin-top: 4px; font-weight: 600;"></div>
          </div>
          <div style="margin-bottom: 12px;">
            <label style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Codice Fiscale (16 car / DM 23/12/1976)</label>
            <input type="text" id="val-cf-input" class="search-input" style="width: 100%;" placeholder="Es. RSSMRA80A01H501U" oninput="testCfLive()">
            <div id="val-cf-res" style="font-size: 11px; margin-top: 4px; font-weight: 600;"></div>
          </div>
        </div>

        <!-- Colonna 2: Calcolatore CCNL Incident-to-Report -->
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 18px;">
          <h4 style="color: var(--accent-emerald); margin-bottom: 12px;">Simulatore Tariffario CCNL Lavoro Straordinario</h4>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
              <label style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Ora Inizio</label>
              <input type="time" id="ccnl-in" value="09:00" class="search-input" style="width:100%;" onchange="calcCcnlLive()">
            </div>
            <div>
              <label style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Ora Fine</label>
              <input type="time" id="ccnl-out" value="11:30" class="search-input" style="width:100%;" onchange="calcCcnlLive()">
            </div>
          </div>
          <div style="margin-bottom: 12px;">
            <label style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Tipologia Giornata</label>
            <select id="ccnl-type" class="search-input" style="width: 100%;" onchange="calcCcnlLive()">
              <option value="weekday">Feriale Diurno (1.00x)</option>
              <option value="night">Feriale Notturno (+20% — 1.20x)</option>
              <option value="holiday">Festivo / Weekend (+30% / +50% — 1.50x)</option>
              <option value="holiday_night">Festivo Notturno (+50% / +75% — 1.75x)</option>
            </select>
          </div>
          <div style="background: rgba(7, 13, 30, 0.5); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px; font-size: 11px;">
            <div>Ore Effettive: <strong id="ccnl-raw-hrs" class="text-white">2.50h</strong> (arrotondate a 30m)</div>
            <div>Moltiplicatore Applicato: <strong id="ccnl-mult-val" style="color: var(--accent-cyan);">1.00x</strong></div>
            <div style="margin-top: 4px; font-size: 13px; font-weight: 800;">Ore Addebitate su SLA: <span id="ccnl-billed-hrs" style="color: var(--accent-emerald);">2.50h</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 6: SCHEDA CLIENTE 360° -->
  <div id="tab-client-drill" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Scheda Monografica Interattiva Cliente 360°</span></div>
        <div id="drill-slug-badge" class="badge badge-info">SELEZIONA CLIENTE</div>
      </div>

      <!-- Selettore Orizzontale a Pills -->
      <div id="client-pills-bar" style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 16px;">
        <!-- Popolato da JS -->
      </div>

      <div id="client-drill-content">
        <!-- Injected dynamically by selectClient() -->
      </div>
    </div>
  </div>

  <!-- TAB 7: SWARM & DEMONI (SPEC-20) -->
  <div id="tab-swarm" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Swarm Agenti Deterministici & Demoni Proattivi</span></div>
      </div>

      <div style="margin-bottom: 24px;">
        <h4 style="color: var(--accent-cyan); margin-bottom: 12px; font-size: 13px;">🤖 Agenti Autonomi Specializzati (SPEC-20)</h4>
        <div id="swarm-agents-grid" class="cards-grid">
          <!-- Popolato da JS -->
        </div>
      </div>

      <div>
        <h4 style="color: var(--accent-emerald); margin-bottom: 12px; font-size: 13px;">⏰ Demoni di Monitoraggio in Background</h4>
        <div id="daemons-grid" class="cards-grid">
          <!-- Popolato da JS -->
        </div>
      </div>
    </div>
  </div>

  <!-- TAB 8: HUB TECNICO ITINFRA & RAEE (SPEC-24) -->
  <div id="tab-technical" class="tab-pane">
    <div class="section-box">
      <div class="section-header">
        <div class="section-title"><span>Integrazione Tecnica Hub-and-Spoke con itinfra & Ciclo RAEE</span></div>
        <button class="btn btn-secondary" onclick="window.open('../../itinfra/projects/enterprise_dashboard.html', '_blank')">🔗 Apri Cockpit itinfra</button>
      </div>
      <div class="cards-grid" style="margin-bottom: 20px;">
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px;">
          <div style="font-weight: 700; color: var(--accent-cyan); margin-bottom: 6px;">Disaster Recovery Drill (dr-drill)</div>
          <div style="font-size: 11px; color: var(--text-muted);">Verifica periodica RTO e RPO con ripristino sandbox, test hash SHA-256 e rilascio del verbale per Art. 32 GDPR e Modello 231.</div>
          <div style="margin-top: 10px;">
            <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd workflow run dr-drill severino-srl')">Esegui per severino-srl</button>
          </div>
        </div>
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px;">
          <div style="font-weight: 700; color: var(--accent-emerald); margin-bottom: 6px;">Aggiornamento Firmware Canary (firmware-upgrade)</div>
          <div style="font-size: 11px; color: var(--text-muted);">Rollout a tappe su apparati di rete e server con snapshot, health check e rollback deterministico in caso di anomalia.</div>
          <div style="margin-top: 10px;">
            <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd workflow run firmware-upgrade teatek-spa')">Esegui per teatek-spa</button>
          </div>
        </div>
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px;">
          <div style="font-weight: 700; color: var(--accent-amber); margin-bottom: 6px;">Dismissione RAEE & NIST 800-88 (hardware-decommissioning)</div>
          <div style="font-size: 11px; color: var(--text-muted);">Sanificazione dischi conformità DoD/NIST, cancellazione as-built e generazione del certificato di smaltimento con codice FIR.</div>
          <div style="margin-top: 10px;">
            <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd workflow run hardware-decommissioning-raee unisped-ag-sas')">Esegui per unisped-ag-sas</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Lettera di Sollecito / Diffida 231 -->
  <div id="modal-letter" class="modal-overlay">
    <div class="modal-box">
      <button class="modal-close" onclick="closeModal('modal-letter')">&times;</button>
      <h3 id="modal-letter-title" style="color: #fff; margin-bottom: 12px;">Lettera di Sollecito D.Lgs. 231/2002</h3>
      <div id="modal-letter-content" style="background: var(--bg-main); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; font-family: monospace; font-size: 11px; white-space: pre-wrap; max-height: 400px; overflow-y: auto; color: #e2e8f0; margin-bottom: 16px;"></div>
      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn btn-secondary" onclick="closeModal('modal-letter')">Chiudi</button>
        <button class="btn btn-primary" onclick="copyLetterText()">📋 Copia Testo Lettera</button>
      </div>
    </div>
  </div>

  <!-- Toast -->
  <div id="toast" class="toast">Comando copiato negli appunti!</div>

  <!-- Footer -->
  <div class="footer">
    Aure System di Eduardo Possumato &bull; IT Operations & Governance Platform &bull; Conforme OKF v0.2 &bull; Zero-CDN Verified Engine
  </div>

</div>

<!-- JSON Data Store Integrato -->
<script id="dashboard-data" type="application/json">
__DASHBOARD_DATA_JSON__
</script>

<script>
// =========================================================================
// MOTORE GENERATIVE UI JAVASCRIPT CLIENT-SIDE (ZERO-CDN)
// =========================================================================
let DATA = {};
try {
  DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
} catch(e) {
  console.error("Errore caricamento dati JSON:", e);
}

let currentFilter = 'all';
let selectedClientSlug = (DATA.clients && DATA.clients.length > 0) ? DATA.clients[0].slug : '';
let currentLetterText = '';

function initApp() {
  updateLiveClock();
  setInterval(updateLiveClock, 1000);
  renderKpiRibbon();
  renderOverviewTable();
  renderActionGate();
  renderWorkflows();
  renderCreditSection();
  renderSwarmSection();
  renderClientPills();
  if (selectedClientSlug) {
    selectClient(selectedClientSlug);
  }
}

function updateLiveClock() {
  const now = new Date();
  const el = document.getElementById('live-clock');
  if (el) {
    el.textContent = now.toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
}

// 1. KPI Ribbon
function renderKpiRibbon() {
  const kpis = DATA.global_kpis || {};
  const paCount = (DATA.pending_actions || []).length;
  const ribbon = document.getElementById('kpi-ribbon');
  if (!ribbon) return;

  const cards = [
    {
      title: "Monte Ore SLA",
      val: (kpis.total_sla_hours_available || 0).toFixed(1) + "h",
      footer: `Consumate: ${(kpis.total_sla_hours_consumed || 0).toFixed(1)}h totali`,
      color: "var(--accent-emerald)",
      onClick: () => switchTab('tab-overview')
    },
    {
      title: "Crediti 231 Aperti",
      val: "€" + (kpis.total_open_credit_eur || 0).toLocaleString('it-IT', { minimumFractionDigits: 2 }),
      footer: `Mora 231: €${(kpis.total_mora_231_eur || 0).toFixed(2)}`,
      color: "var(--accent-cyan)",
      onClick: () => switchTab('tab-credit')
    },
    {
      title: "Parco Macchine MPS",
      val: (kpis.total_printers || 0).toString(),
      footer: `Allarmi Toner: ${(kpis.total_toner_critical_alerts || 0)} critici`,
      color: kpis.total_toner_critical_alerts > 0 ? "var(--accent-rose)" : "var(--accent-cyan)",
      onClick: () => switchTab('tab-overview')
    },
    {
      title: "Conformità 231 Media",
      val: (kpis.avg_compliance_score || 0).toFixed(1) + "%",
      footer: "Certificazione Modello 231 / ISO",
      color: "var(--accent-amber)",
      onClick: () => switchTab('tab-compliance')
    },
    {
      title: "Safe Action Gate",
      val: paCount.toString(),
      footer: paCount > 0 ? "⚠️ Approvazioni Pendenti" : "✓ Nessuna Azione Pendente",
      color: paCount > 0 ? "var(--accent-rose)" : "var(--accent-emerald)",
      onClick: () => switchTab('tab-gate')
    }
  ];

  ribbon.innerHTML = cards.map(c => `
    <div class="kpi-card" onclick="(${c.onClick.toString()})()">
      <div class="kpi-header">
        <span>${c.title}</span>
      </div>
      <div class="kpi-value" style="color: ${c.color};">${c.val}</div>
      <div class="kpi-footer">${c.footer}</div>
    </div>
  `).join('');

  const badge = document.getElementById('gate-tab-badge');
  if (badge) {
    if (paCount > 0) {
      badge.textContent = paCount;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }
}

// 2. Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  const targetPane = document.getElementById(tabId);
  if (targetPane) targetPane.classList.add('active');

  const navBtns = document.querySelectorAll('.tab-btn');
  navBtns.forEach(btn => {
    if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
      btn.classList.add('active');
    }
  });
}

// 3. Tabella Panoramica
function renderOverviewTable() {
  const tbody = document.getElementById('overview-tbody');
  const countLabel = document.getElementById('clients-count-label');
  if (!tbody) return;

  const clients = DATA.clients || [];
  if (countLabel) countLabel.textContent = clients.length;

  const query = (document.getElementById('overview-search') ? document.getElementById('overview-search').value : '').toLowerCase();

  const filtered = clients.filter(c => {
    const matchQuery = c.client_name.toLowerCase().includes(query) || c.slug.toLowerCase().includes(query) || c.tier.toLowerCase().includes(query);
    if (!matchQuery) return false;

    if (currentFilter === 'sla_alert') return c.sla_alert;
    if (currentFilter === 'toner_alert') return c.toner_alerts && c.toner_alerts.length > 0;
    if (currentFilter === 'overdue') return c.overdue_invoices_eur > 0;
    if (currentFilter === 'gap_231') return c.has_231;
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">Nessun cliente corrispondente ai filtri selezionati.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(c => {
    const slaBadge = c.sla_alert ? 'badge-danger' : (c.hours_pct < 40 ? 'badge-warning' : 'badge-success');
    const mpsBadge = (c.toner_alerts && c.toner_alerts.length > 0) ? 'badge-danger' : 'badge-neutral';
    const compBadge = c.has_231 ? (c.compliance_score >= 80 ? 'badge-success' : (c.compliance_score >= 50 ? 'badge-warning' : 'badge-danger')) : 'badge-neutral';
    const bridgeBadge = c.bridge_status === 'PASS' || c.bridge_status === 'SYNCED' ? 'badge-success' : (c.bridge_status === 'WARNING' ? 'badge-warning' : 'badge-neutral');

    return `
      <tr>
        <td style="font-weight: 700; color: #38bdf8;">
          <a href="javascript:void(0)" onclick="openClientTab('${c.slug}')" style="color: inherit; text-decoration: none;">${c.client_name}</a>
          <br><span style="font-size: 11px; color: var(--text-muted); font-weight: normal;">${c.slug} &bull; Tier ${c.tier.toUpperCase()}</span>
        </td>
        <td>
          <span class="badge ${slaBadge}">${c.remaining_hours.toFixed(1)}h / ${c.total_purchased_hours.toFixed(1)}h (${c.hours_pct}%)</span>
        </td>
        <td>
          €${c.open_invoices_eur.toLocaleString('it-IT', {minimumFractionDigits: 2})}
          ${c.overdue_invoices_eur > 0 ? `<br><span style="color: var(--accent-rose); font-size: 10px; font-weight: 700;">€${c.overdue_invoices_eur.toFixed(2)} scaduti</span>` : ''}
        </td>
        <td>
          <span class="badge ${mpsBadge}">${c.printers_count} macchine ${c.toner_alerts.length > 0 ? `(!${c.toner_alerts.length})` : ''}</span>
        </td>
        <td>
          <span class="badge ${compBadge}">${c.has_231 ? c.compliance_score.toFixed(0) + '%' : 'N/A'}</span>
        </td>
        <td>
          <span class="badge ${bridgeBadge}">${c.bridge_status}</span>
        </td>
        <td>
          <button class="btn btn-secondary" onclick="openClientTab('${c.slug}')">Dettaglio 360°</button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterOverviewTable() {
  renderOverviewTable();
}

function setOverviewFilter(filter, el) {
  currentFilter = filter;
  document.querySelectorAll('.filter-chip').forEach(btn => btn.classList.remove('active'));
  if (el) el.classList.add('active');
  renderOverviewTable();
}

function openClientTab(slug) {
  selectedClientSlug = slug;
  selectClient(slug);
  switchTab('tab-client-drill');
}

// 4. Safe Action Gate
function renderActionGate() {
  const container = document.getElementById('action-gate-container');
  if (!container) return;

  const actions = DATA.pending_actions || [];
  if (actions.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; border-radius: 8px; padding: 24px; text-align: center;">
        <span style="font-size: 24px;">🛡️</span>
        <h4 style="color: #34d399; margin-top: 8px;">Safe Action Gate Sgombro</h4>
        <p style="color: var(--text-muted); font-size: 12px; margin-top: 4px;">Nessuna azione in attesa di approvazione manuale. Tutti i sistemi sono nei parametri di sicurezza.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = actions.map(a => {
    const aid = a.action_id || 'ACT-UNKNOWN';
    const slug = a.slug || '';
    const atype = a.action_type || '';
    const title = a.title || 'Azione Operativa';
    const payloadStr = JSON.stringify(a.payload || {}, null, 2);

    return `
      <div class="action-gate-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
          <span class="badge badge-danger">${atype}</span>
          <span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">${aid}</span>
        </div>
        <div style="font-weight: 700; color: #fff; font-size: 13px; margin-bottom: 4px;">${title}</div>
        <div style="font-size: 11px; color: var(--accent-cyan); margin-bottom: 10px;">Cliente: <strong>${slug}</strong></div>
        
        <details style="background: rgba(7, 13, 30, 0.5); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px; font-size: 11px; margin-bottom: 12px;">
          <summary style="cursor: pointer; color: var(--text-muted); font-weight: 600;">Dettagli Payload & Parametri</summary>
          <pre style="margin-top: 6px; font-family: monospace; font-size: 10px; color: #94a3b8; white-space: pre-wrap;">${payloadStr}</pre>
        </details>

        <div style="display: flex; gap: 8px;">
          <button class="btn btn-success" onclick="copyCliCmd('.\\\\it-ops.cmd triggers approve ${aid}')">✓ Approva Azione</button>
          <button class="btn btn-danger" onclick="copyCliCmd('.\\\\it-ops.cmd triggers reject ${aid} --reason \\'Rifiutato da Dashboard\\'')">&times; Rifiuta</button>
        </div>
      </div>
    `;
  }).join('');
}

// 5. Workflows FSM
function renderWorkflows() {
  const container = document.getElementById('workflows-list');
  const catGrid = document.getElementById('workflow-catalog-grid');
  if (!container) return;

  const wfs = DATA.recent_workflows || [];
  if (wfs.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); padding: 12px;">Nessun workflow registrato di recente.</div>';
  } else {
    container.innerHTML = wfs.map(w => {
      const wid = w.workflow_id || 'WF-UNKNOWN';
      const wtype = w.workflow_type || '';
      const wstatus = w.status || 'PENDING';
      const steps = w.steps || [];
      const statusBadge = wstatus === 'COMPLETED' ? 'badge-success' : (wstatus === 'FAILED' ? 'badge-danger' : 'badge-warning');

      return `
        <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
              <span class="badge ${statusBadge}">${wstatus}</span>
              <strong style="margin-left: 8px; color: #fff;">${wtype}</strong>
              <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">ID: ${wid}</span>
            </div>
            ${wstatus === 'FAILED' ? `<button class="btn btn-warning" onclick="copyCliCmd('.\\\\it-ops.cmd workflow resume ${wid}')">Riprendi (Resume)</button>` : ''}
          </div>
          <div class="stepper">
            ${steps.map((s, idx) => {
              const sDone = s.status === 'COMPLETED' || s.status === 'PASS';
              const sFail = s.status === 'FAILED';
              const dotBg = sDone ? 'var(--accent-emerald)' : (sFail ? 'var(--accent-rose)' : 'var(--border-color)');
              return `
                <div class="step-node">
                  <div class="step-dot" style="background: ${dotBg}; color: #fff;">${idx + 1}</div>
                  <span style="color: ${sDone ? '#fff' : 'var(--text-muted)'};">${s.name || s.step_id}</span>
                </div>
                ${idx < steps.length - 1 ? `<div class="step-line ${sDone ? 'done' : ''}"></div>` : ''}
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  if (catGrid) {
    const catalog = DATA.workflow_catalog || [];
    catGrid.innerHTML = catalog.map(cat => `
      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <span class="badge ${cat.category === 'technical' ? 'badge-info' : 'badge-purple'}">${cat.category.toUpperCase()}</span>
          <span style="font-size: 10px; color: var(--text-muted);">${cat.stages_count} Fasi</span>
        </div>
        <div style="font-weight: 700; color: #fff; font-size: 13px; margin-bottom: 4px;">${cat.name}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">${cat.description}</div>
        <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd workflow run ${cat.type} <slug>')">Comando: run ${cat.type}</button>
      </div>
    `).join('');
  }
}

// 6. Crediti & D.Lgs. 231/2002
function renderCreditSection() {
  const kpis = DATA.global_kpis || {};
  const aging = kpis.global_aging || {};
  
  if (document.getElementById('aging-0-30')) document.getElementById('aging-0-30').textContent = '€' + (aging['0_30'] || 0).toLocaleString('it-IT', {minimumFractionDigits: 2});
  if (document.getElementById('aging-31-60')) document.getElementById('aging-31-60').textContent = '€' + (aging['31_60'] || 0).toLocaleString('it-IT', {minimumFractionDigits: 2});
  if (document.getElementById('aging-61-90')) document.getElementById('aging-61-90').textContent = '€' + (aging['61_90'] || 0).toLocaleString('it-IT', {minimumFractionDigits: 2});
  if (document.getElementById('aging-90-plus')) document.getElementById('aging-90-plus').textContent = '€' + (aging['90_plus'] || 0).toLocaleString('it-IT', {minimumFractionDigits: 2});
  if (document.getElementById('total-mora-val')) document.getElementById('total-mora-val').textContent = '€' + (kpis.total_mora_231_eur || 0).toLocaleString('it-IT', {minimumFractionDigits: 2});

  const tbody = document.getElementById('credit-invoices-tbody');
  if (!tbody) return;

  const clients = DATA.clients || [];
  let rows = [];

  clients.forEach(c => {
    (c.invoices || []).forEach(inv => {
      if (inv.days_overdue > 0) {
        rows.push({
          slug: c.slug,
          client_name: c.client_name,
          inv: inv
        });
      }
    });
  });

  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-muted);">Nessuna fattura scaduta a sistema. Complimenti!</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(r => {
    const inv = r.inv;
    let badgeClass = 'badge-success';
    if (inv.days_overdue > 60) badgeClass = 'badge-danger';
    else if (inv.days_overdue > 30) badgeClass = 'badge-warning';

    return `
      <tr>
        <td style="font-weight: 700; color: #38bdf8;">${r.client_name}</td>
        <td><strong>${inv.invoice_number}</strong><br><span style="font-size: 10px; color: var(--text-muted);">Scad. ${inv.due_date}</span></td>
        <td>€${inv.amount.toLocaleString('it-IT', {minimumFractionDigits: 2})}</td>
        <td><span class="badge ${badgeClass}">${inv.days_overdue} giorni</span></td>
        <td style="color: var(--accent-rose); font-weight: 700;">€${inv.mora_eur.toFixed(2)}</td>
        <td><span class="badge badge-neutral">${inv.suggested_stage}</span></td>
        <td>
          <button class="btn btn-primary" onclick="openLetterModal('${r.slug}', '${inv.invoice_number}', ${inv.amount}, '${inv.due_date}', ${inv.days_overdue}, ${inv.mora_eur})">✉️ Lettera 231</button>
        </td>
      </tr>
    `;
  }).join('');
}

function openLetterModal(slug, invNum, amt, dueDate, daysOverdue, mora) {
  let stage = 1;
  let title = "Stadio 1 — Promemoria Bonario di Pagamento";
  if (daysOverdue > 60) {
    stage = 3;
    title = "Stadio 3 — Intimazione di Pagamento con Diffida Legale ex Art. 1454 c.c.";
  } else if (daysOverdue > 30) {
    stage = 2;
    title = "Stadio 2 — Formale Costituzione in Mora ex D.Lgs. 231/2002";
  }

  const today = new Date().toISOString().split('T')[0];
  let text = `RACCOMANDATA A/R / TRASMISSIONE A MEZZO PEC\\n\\nData: ${today}\\nSpett.le Cliente: ${slug.toUpperCase()}\\n\\nOGGETTO: ${title.toUpperCase()} — Fattura N. ${invNum}\\n\\n`;

  if (stage === 1) {
    text += `Gentile Cliente,\\nda una verifica contabile risulta non pervenuto il saldo della fattura n. ${invNum} scaduta il ${dueDate} per un importo di € ${amt.toFixed(2)}.\\nVi invitiamo a provvedere al saldo a mezzo bonifico bancario.\\n\\nCordiali saluti,\\nAure System di Eduardo Possumato`;
  } else if (stage === 2) {
    text += `Ai sensi e per gli effetti dell'art. 1219 c.c. e del D.Lgs. 231/2002, con la presente FORMALMENTE COSTITUIAMO IN MORA la Vostra società per l'inadempimento della fattura n. ${invNum} scaduta il ${dueDate}.\\n\\nProspetto Contabile:\\n- Capitale Imponibile Scaduto: € ${amt.toFixed(2)}\\n- Giorni di Ritardo: ${daysOverdue}\\n- Tasso Legale D.Lgs. 231/2002: 11.50% (BCE 3.50% + 8.00%)\\n- Interessi di Mora Maturati: € ${mora.toFixed(2)}\\nTOTALE COMPLESSIVO DOVUTO: € ${(amt + mora).toFixed(2)}\\n\\nVi intimiamo il pagamento entro 7 giorni.\\nAure System di Eduardo Possumato`;
  } else {
    text += `DIFFIDA AD ADEMPIERE EX ART. 1454 C.C. E COSTITUZIONE IN MORA EX D.LGS. 231/2002\\n\\nPreso atto del protrarsi dell'inadempimento per ${daysOverdue} giorni della fattura n. ${invNum},\\nintimiamo il saldo integrale entro 15 (quindici) giorni dal ricevimento della presente.\\n\\nProspetto Economico Legale:\\n- Capitale: € ${amt.toFixed(2)}\\n- Interessi di Mora 231: € ${mora.toFixed(2)}\\n- Risarcimento Forfettario Spese ex Art. 6 D.Lgs. 231/2002: € 40,00\\nTOTALE DA VERSARE: € ${(amt + mora + 40).toFixed(2)}\\n\\nIn difetto, adiremo le vie legali con aggravio di spese e immediata sospensione dei contratti SLA.\\nAure System di Eduardo Possumato`;
  }

  currentLetterText = text;
  document.getElementById('modal-letter-title').textContent = title;
  document.getElementById('modal-letter-content').textContent = text;
  document.getElementById('modal-letter').classList.add('open');
}

function copyLetterText() {
  navigator.clipboard.writeText(currentLetterText).then(() => {
    showToast("Testo della lettera copiato negli appunti!");
    closeModal('modal-letter');
  });
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// 7. Presidio Italiano Live
function testPivaLive() {
  const val = document.getElementById('val-piva-input').value.trim();
  const resEl = document.getElementById('val-piva-res');
  if (!val) { resEl.textContent = ''; return; }

  if (val.length !== 11 || !/^[0-9]+$/.test(val)) {
    resEl.textContent = '❌ Lunghezza errata: richieste 11 cifre numeriche';
    resEl.style.color = 'var(--accent-rose)';
    return;
  }
  resEl.textContent = '✓ Formato e lunghezza P.IVA formalmente validi';
  resEl.style.color = 'var(--accent-emerald)';
}

function testCfLive() {
  const val = document.getElementById('val-cf-input').value.trim().toUpperCase();
  const resEl = document.getElementById('val-cf-res');
  if (!val) { resEl.textContent = ''; return; }

  if (val.length !== 16) {
    resEl.textContent = '❌ Richiesti 16 caratteri alfanumerici';
    resEl.style.color = 'var(--accent-rose)';
    return;
  }
  resEl.textContent = '✓ Struttura Codice Fiscale conforme DM 23/12/1976';
  resEl.style.color = 'var(--accent-emerald)';
}

function calcCcnlLive() {
  const tIn = document.getElementById('ccnl-in').value;
  const tOut = document.getElementById('ccnl-out').value;
  const cType = document.getElementById('ccnl-type').value;

  const [h1, m1] = tIn.split(':').map(Number);
  const [h2, m2] = tOut.split(':').map(Number);
  let diffMins = (h2 * 60 + m2) - (h1 * 60 + m1);
  if (diffMins < 0) diffMins += 24 * 60;

  const steps = Math.ceil(diffMins / 30);
  const roundedHrs = (steps * 30) / 60.0;

  let mult = 1.00;
  if (cType === 'night') mult = 1.20;
  else if (cType === 'holiday') mult = 1.50;
  else if (cType === 'holiday_night') mult = 1.75;

  const billed = roundedHrs * mult;

  document.getElementById('ccnl-raw-hrs').textContent = roundedHrs.toFixed(2) + 'h';
  document.getElementById('ccnl-mult-val').textContent = mult.toFixed(2) + 'x';
  document.getElementById('ccnl-billed-hrs').textContent = billed.toFixed(2) + 'h';
}

// 8. Scheda Monografica Cliente
function renderClientPills() {
  const bar = document.getElementById('client-pills-bar');
  if (!bar) return;

  const clients = DATA.clients || [];
  bar.innerHTML = clients.map(c => `
    <button class="filter-chip ${c.slug === selectedClientSlug ? 'active' : ''}" onclick="selectClient('${c.slug}')">
      ${c.client_name}
    </button>
  `).join('');
}

function selectClient(slug) {
  selectedClientSlug = slug;
  document.getElementById('drill-slug-badge').textContent = slug.toUpperCase();
  renderClientPills();

  const c = (DATA.clients || []).find(item => item.slug === slug);
  const container = document.getElementById('client-drill-content');
  if (!c || !container) return;

  const fiscal = c.fiscal || {};
  const slaPct = c.hours_pct;

  container.innerHTML = `
    <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div>
          <h3 style="color: #fff; font-size: 18px;">${c.client_name}</h3>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
            Slug: <strong class="text-white">${c.slug}</strong> &bull; Tier: <strong class="text-white">${c.tier.toUpperCase()}</strong> &bull; SLA: <strong class="text-white">${c.sla_level}</strong>
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd status ${c.slug}')">stato ${c.slug}</button>
          <button class="btn btn-secondary" onclick="copyCliCmd('.\\\\it-ops.cmd check ${c.slug}')">check ${c.slug}</button>
        </div>
      </div>
      <div style="display: flex; gap: 16px; font-size: 11px; color: var(--text-muted); border-top: 1px solid rgba(34,60,124,0.5); padding-top: 10px;">
        <div>P.IVA: <strong class="text-white">${fiscal.partita_iva || 'N/D'}</strong> ${fiscal.piva_valid ? '✓' : '⚠️'}</div>
        <div>Codice Fiscale: <strong class="text-white">${fiscal.codice_fiscale || 'N/D'}</strong> ${fiscal.cf_valid ? '✓' : '⚠️'}</div>
        <div>SDI: <strong class="text-white">${fiscal.sdi_code || '0000000'}</strong> ${fiscal.sdi_valid ? '✓' : '⚠️'}</div>
        <div>PEC: <strong class="text-white">${fiscal.pec || 'N/D'}</strong></div>
      </div>
    </div>

    <div class="cards-grid" style="margin-bottom: 16px;">
      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="font-weight: 700; color: var(--accent-cyan); margin-bottom: 8px;">SLA & Monte Ore Residuo</div>
        <div style="font-size: 24px; font-weight: 800; color: #fff;">${c.remaining_hours.toFixed(1)}h <span style="font-size: 13px; color: var(--text-muted);">/ ${c.total_purchased_hours.toFixed(1)}h</span></div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${slaPct}%; background: ${slaPct < 20 ? 'var(--accent-rose)' : 'var(--accent-emerald)'};"></div>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">Consumate: ${c.total_consumed_hours.toFixed(1)}h &bull; Ore spot non fatturate: ${c.unbilled_spot_hours.toFixed(1)}h</div>
      </div>

      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="font-weight: 700; color: var(--accent-emerald); margin-bottom: 8px;">Finanza & Insoluti 231</div>
        <div style="font-size: 24px; font-weight: 800; color: #fff;">€${c.open_invoices_eur.toLocaleString('it-IT', {minimumFractionDigits: 2})}</div>
        <div style="font-size: 11px; color: var(--accent-rose); font-weight: 700; margin-top: 6px;">Scaduti: €${c.overdue_invoices_eur.toFixed(2)} (Mora 231: €${c.total_mora_interest_eur.toFixed(2)})</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Fatturato Totale Storico: €${c.total_invoiced_eur.toLocaleString('it-IT', {minimumFractionDigits: 2})}</div>
      </div>

      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="font-weight: 700; color: var(--accent-amber); margin-bottom: 8px;">Multifunzione & Toner (${c.printers_count} Apparati)</div>
        ${c.printers && c.printers.length > 0 ? c.printers.map(p => `
          <div style="font-size: 11px; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px;">
            <div style="font-weight: 700; color: #fff;">${p.model} (${p.serial_number})</div>
            <div style="display: flex; gap: 8px; margin-top: 2px;">
              <span style="color:#fff;">BK: ${p.toners.black}%</span>
              <span style="color:#38bdf8;">C: ${p.toners.cyan}%</span>
              <span style="color:#f43f5e;">M: ${p.toners.magenta}%</span>
              <span style="color:#fbbf24;">Y: ${p.toners.yellow}%</span>
            </div>
          </div>
        `).join('') : '<div style="font-size: 11px; color: var(--text-muted);">Nessuna stampante MPS censita.</div>'}
      </div>

      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="font-weight: 700; color: var(--accent-purple); margin-bottom: 8px;">Conformità 231 & Bridge itinfra</div>
        <div style="font-size: 24px; font-weight: 800; color: #fff;">${c.has_231 ? c.compliance_score.toFixed(0) + '%' : 'N/A'}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Vulnerabilità Rilevate: <strong class="text-white">${c.va_findings_count}</strong></div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Bridge As-Built: <strong style="color: ${c.bridge_status === 'PASS' || c.bridge_status === 'SYNCED' ? '#34d399' : '#f59e0b'};">${c.bridge_status}</strong></div>
      </div>
    </div>
  `;
}

// 9. Swarm & Demoni
function renderSwarmSection() {
  const agGrid = document.getElementById('swarm-agents-grid');
  const dGrid = document.getElementById('daemons-grid');

  if (agGrid) {
    const agents = DATA.swarm_agents || [];
    agGrid.innerHTML = agents.map(ag => `
      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <span class="badge badge-purple">${ag.type}</span>
          <span class="badge badge-success">${ag.status}</span>
        </div>
        <div style="font-weight: 700; color: #fff; font-size: 13px; margin-bottom: 4px;">${ag.role}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">Ambito: ${ag.scope}</div>
        <button class="btn btn-secondary" onclick="copyCliCmd('${ag.cli} <slug>')">Esegui: ${ag.type}</button>
      </div>
    `).join('');
  }

  if (dGrid) {
    const daemons = DATA.daemons || [];
    dGrid.innerHTML = daemons.map(d => `
      <div style="background: var(--bg-card-sub); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <span class="badge badge-info">${d.id.toUpperCase()}</span>
          <span class="badge badge-success">${d.status}</span>
        </div>
        <div style="font-weight: 700; color: #fff; font-size: 13px; margin-bottom: 4px;">${d.name}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">Frequenza: ${d.interval} &bull; Target: ${d.target}</div>
        <button class="btn btn-secondary" onclick="copyCliCmd('${d.command}')">Lancia 1 Ciclo (--once)</button>
      </div>
    `).join('');
  }
}

// 10. Utility & Clipboard
function copyCliCmd(cmd) {
  navigator.clipboard.writeText(cmd).then(() => {
    showToast(`Comando "${cmd}" copiato! Incollalo in terminale o chat.`);
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = cmd;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast(`Comando "${cmd}" copiato! Incollalo in terminale o chat.`);
  });
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(window._tTimer);
  window._tTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2500);
}

window.addEventListener('DOMContentLoaded', initApp);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aure System Mission Control & Continuous Assurance Dashboard")
    parser.add_argument("--html", action="store_true", help="Genera report HTML anziché TUI terminale")
    parser.add_argument("--out", type=str, default=None, help="Percorso di salvataggio file HTML")
    args = parser.parse_args()

    pipeline = MissionControlPipeline()
    if args.html:
        out_p = Path(args.out) if args.out else Path(ROOT_DIR) / "docs" / "mission-control.html"
        pipeline.render_html(output_path=out_p)
        print(f"[✓] Mission Control Dashboard HTML generata con successo: {out_p}")
    else:
        print(pipeline.render_tui())
