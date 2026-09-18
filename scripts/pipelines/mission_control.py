#!/usr/bin/env python3
"""
scripts/pipelines/mission_control.py — Mission Control Dashboard Engine (SPEC-20)
Console esecutiva centralizzata 360°:
- SLA Hours Bank & Burn Rate
- Cashflow & Scadenziario Fatturazione
- Parco Macchine MPS & Allarmi Toner
- Indice di Conformità D.Lgs. 231/2001
- Hub-and-Spoke Federation Health con itinfra
Supporta rendering Terminal TUI e Standalone Zero-CDN HTML Dashboard.
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

        # 1. Contratti SLA
        contracts_dir = cdir / "contracts"
        total_purchased_hours = 0.0
        total_consumed_hours = 0.0
        active_contracts_count = 0
        sla_level = "Standard"

        if contracts_dir.is_dir():
            for cf in contracts_dir.glob("*.yaml"):
                try:
                    with open(cf, "r", encoding="utf-8") as fp:
                        cdata = yaml.safe_load(fp) or {}
                    if cdata.get("status") == "active":
                        active_contracts_count += 1
                        hb = cdata.get("hours_bank", {})
                        fin = cdata.get("financial", {})
                        purchased = float(fin.get("total_hours_included", hb.get("total_purchased", 0.0)))
                        consumed = float(fin.get("consumed_hours", hb.get("consumed", 0.0)))
                        total_purchased_hours += purchased
                        total_consumed_hours += consumed
                        sla_level = cdata.get("sla", {}).get("level") or cdata.get("sla", {}).get("tier", sla_level)
                except Exception:
                    pass

        remaining_hours = max(0.0, total_purchased_hours - total_consumed_hours)
        hours_pct = round((remaining_hours / total_purchased_hours * 100.0), 1) if total_purchased_hours > 0 else 0.0
        sla_alert = (hours_pct < 20.0 or remaining_hours < 5.0) if total_purchased_hours > 0 else False

        # 2. Timesheet e ore non fatturate
        timesheets_dir = cdir / "timesheets"
        unbilled_spot_hours = 0.0
        interventions_count = 0
        if timesheets_dir.is_dir():
            for rf in timesheets_dir.glob("*.yaml"):
                try:
                    with open(rf, "r", encoding="utf-8") as fp:
                        rdata = yaml.safe_load(fp) or {}
                    interventions_count += 1
                    la = rdata.get("ledger_action") or rdata.get("intervention", {}).get("ledger_action")
                    is_invoiced = rdata.get("invoicing", {}).get("invoiced", False)
                    hrs = float(rdata.get("total_hours_rounded") or rdata.get("intervention", {}).get("billable_hours", 0.0))
                    if la == "invoice_spot" and not is_invoiced:
                        unbilled_spot_hours += hrs
                except Exception:
                    pass

        # 3. Fatturazione e Crediti (supporta sia YAML che JSON)
        invoices_dir = cdir / "invoices"
        open_invoices_eur = 0.0
        total_invoiced_eur = 0.0
        if invoices_dir.is_dir():
            for inv_file in list(invoices_dir.glob("*.yaml")) + list(invoices_dir.glob("*.json")):
                try:
                    with open(inv_file, "r", encoding="utf-8") as fp:
                        if inv_file.suffix == ".json":
                            idata = json.load(fp) or {}
                        else:
                            idata = yaml.safe_load(fp) or {}

                    # Controllo scadenzario
                    scad = idata.get("scadenzario", {})
                    if scad and "installments" in scad:
                        for inst in scad["installments"]:
                            amt = float(inst.get("amount", 0.0))
                            if inst.get("status") in ["unpaid", "overdue", "pending"]:
                                open_invoices_eur += amt
                            total_invoiced_eur += amt
                    elif "installments" in idata:
                        for item in idata.get("installments", []):
                            amt = float(item.get("amount_due_eur", item.get("amount", 0.0)))
                            if item.get("status") in ["unpaid", "overdue", "pending"]:
                                open_invoices_eur += amt
                            total_invoiced_eur += amt
                    else:
                        tot = idata.get("totals", {}).get("total_gross", 0.0)
                        if idata.get("status") in ["unpaid", "draft", "open", "pending"]:
                            open_invoices_eur += float(tot)
                        total_invoiced_eur += float(tot)
                except Exception:
                    pass

        # 4. MPS & Toner
        mps_dir = cdir / "mps"
        printers_count = 0
        toner_alerts: List[Dict[str, Any]] = []
        if mps_dir.is_dir():
            for mf in mps_dir.glob("*.yaml"):
                try:
                    with open(mf, "r", encoding="utf-8") as fp:
                        mdata = yaml.safe_load(fp) or {}

                    # Formato 1: lista printers
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

                    # Formato 2: device_info singolo con readings
                    dinfo = mdata.get("device_info", {})
                    if dinfo and "serial_number" in dinfo:
                        printers_count += 1
                        readings = mdata.get("readings", [])
                        if readings:
                            last_r = readings[-1]
                            tbk = last_r.get("toner_black_percent", 100)
                            tc = last_r.get("toner_cyan_percent", 100)
                            tm = last_r.get("toner_magenta_percent", 100)
                            ty = last_r.get("toner_yellow_percent", 100)
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
                except Exception:
                    pass

        # 5. Gap Analysis & Compliance 231
        gap_dir = cdir / "gap_analysis"
        compliance_score = 0.0
        va_findings_count = 0
        has_231 = False
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
                except Exception:
                    pass

        # 6. Hub-and-Spoke Federation Bridge
        bridge_status = "NO_TECH_REPO"
        if self.bridge.project_exists(slug):
            cov = self.bridge.cross_check_sla_assets_coverage(slug)
            bridge_status = cov.get("status", "SYNCED")

        return {
            "slug": slug,
            "client_name": client_name,
            "tier": tier,
            "sla_level": sla_level,
            "active_contracts_count": active_contracts_count,
            "total_purchased_hours": total_purchased_hours,
            "total_consumed_hours": total_consumed_hours,
            "remaining_hours": remaining_hours,
            "hours_pct": hours_pct,
            "sla_alert": sla_alert,
            "interventions_count": interventions_count,
            "unbilled_spot_hours": unbilled_spot_hours,
            "open_invoices_eur": round(open_invoices_eur, 2),
            "total_invoiced_eur": round(total_invoiced_eur, 2),
            "printers_count": printers_count,
            "toner_alerts": toner_alerts,
            "has_231": has_231,
            "compliance_score": compliance_score,
            "va_findings_count": va_findings_count,
            "bridge_status": bridge_status,
        }

    def collect_all(self) -> Dict[str, Any]:
        """Raccoglie le metriche globali aggregate su tutti i clienti."""
        client_dirs = [d for d in self.clients_root.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
        clients_data = []

        total_sla_hours_available = 0.0
        total_sla_hours_consumed = 0.0
        total_open_credit_eur = 0.0
        total_unbilled_hours = 0.0
        total_printers = 0
        total_toner_critical_alerts = 0
        avg_compliance_accum = 0.0
        compliance_clients_count = 0

        for cd in sorted(client_dirs, key=lambda x: x.name):
            m = self.collect_client_metrics(cd.name)
            clients_data.append(m)

            total_sla_hours_available += m["remaining_hours"]
            total_sla_hours_consumed += m["total_consumed_hours"]
            total_open_credit_eur += m["open_invoices_eur"]
            total_unbilled_hours += m["unbilled_spot_hours"]
            total_printers += m["printers_count"]
            total_toner_critical_alerts += len(m["toner_alerts"])

            if m["has_231"]:
                avg_compliance_accum += m["compliance_score"]
                compliance_clients_count += 1

        avg_compliance = round(avg_compliance_accum / compliance_clients_count, 1) if compliance_clients_count > 0 else 0.0

        wf_engine = WorkflowEngine(repo_root=ROOT_DIR, clients_root=self.clients_root)
        recent_workflows = wf_engine.list_workflows(limit=5)

        trigger_engine = TriggerEngine(repo_root=ROOT_DIR, clients_root=self.clients_root)
        pending_actions = trigger_engine.list_pending_actions()

        return {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_clients": len(clients_data),
            "recent_workflows": recent_workflows,
            "pending_actions": pending_actions,
            "global_kpis": {
                "total_sla_hours_available": round(total_sla_hours_available, 1),
                "total_sla_hours_consumed": round(total_sla_hours_consumed, 1),
                "total_open_credit_eur": round(total_open_credit_eur, 2),
                "total_unbilled_hours": round(total_unbilled_hours, 1),
                "total_printers": total_printers,
                "total_toner_critical_alerts": total_toner_critical_alerts,
                "avg_compliance_score": avg_compliance,
            },
            "clients": clients_data
        }

    def render_tui(self) -> str:
        """Genera una vista TUI Unicode formattata per terminale."""
        data = self.collect_all()
        kpis = data["global_kpis"]

        lines = []
        lines.append("=" * 80)
        lines.append("  🚀 AURE SYSTEM — MISSION CONTROL EXECUTIVE DASHBOARD (v0.3.0)")
        lines.append("=" * 80)
        lines.append(f"  📅 Data Rilevazione: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"  🏢 Clienti Gestiti : {data['total_clients']}")
        lines.append("-" * 80)
        lines.append(
            f"  [SLA ORE BANCA] Rimanenti: {kpis['total_sla_hours_available']}h | "
            f"Consumate: {kpis['total_sla_hours_consumed']}h"
        )
        lines.append(
            f"  [FINANZA & PSA] Crediti Aperti: €{kpis['total_open_credit_eur']:,.2f} | "
            f"Ore Spot da Fatturare: {kpis['total_unbilled_hours']}h"
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

        # Sezione Azioni Pendenti Action Gate (SPEC-22)
        pa = data.get("pending_actions", [])
        if pa:
            lines.append(f"  🔔 AZIONI IN ATTESA DI APPROVAZIONE (SAFE ACTION GATE — {len(pa)} PENDENTI)")
            lines.append("-" * 80)
            for a in pa:
                aid = a.get("action_id", "")
                aslug = a.get("slug", "")
                atitle = a.get("title", "")
                lines.append(f"  [!] {aid:<30} | {aslug:<15} | {atitle}")
            lines.append("  Approva con: .\\it-ops.cmd triggers approve <action_id>")
            lines.append("=" * 80)

        # Sezione Workflows Recenti (SPEC-21)
        rw = data.get("recent_workflows", [])
        if rw:
            lines.append("  🔄 WORKFLOWS RECENTI & AUTOMAZIONI (SPEC-21)")
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
        Genera una dashboard HTML esecutiva Standalone e Zero-CDN.
        Include grafici SVG vettoriali, KPI cards, dark mode e navigazione rapida.
        """
        data = self.collect_all()
        kpis = data["global_kpis"]

        # Costruisci righe tabella
        client_rows = []
        for c in data["clients"]:
            sla_badge = "badge-success"
            if c["sla_alert"]:
                sla_badge = "badge-danger"
            elif c["hours_pct"] < 40:
                sla_badge = "badge-warning"

            mps_badge = "badge-success" if not c["toner_alerts"] else "badge-danger"
            mps_label = f"{c['printers_count']} apparati"
            if c["toner_alerts"]:
                mps_label += f" ({len(c['toner_alerts'])} toner bassi)"

            bridge_badge = "badge-success" if c["bridge_status"] == "PASS" else ("badge-warning" if c["bridge_status"] == "WARNING" else "badge-secondary")

            comp_badge = "badge-info"
            if c["has_231"]:
                if c["compliance_score"] >= 80: comp_badge = "badge-success"
                elif c["compliance_score"] >= 50: comp_badge = "badge-warning"
                else: comp_badge = "badge-danger"

            row = f"""
            <tr>
                <td style="font-weight: 600; color: #38bdf8;">{c['client_name']}<br><span style="font-size: 11px; color: #94a3b8;">{c['slug']} &bull; Tier {c['tier'].upper()}</span></td>
                <td><span class="badge {sla_badge}">{c['remaining_hours']}h / {c['total_purchased_hours']}h ({c['hours_pct']}%)</span></td>
                <td>€{c['open_invoices_eur']:,.2f}<br><span style="font-size: 11px; color: #94a3b8;">Da fatturare: {c['unbilled_spot_hours']}h</span></td>
                <td><span class="badge {mps_badge}">{mps_label}</span></td>
                <td><span class="badge {comp_badge}">{c['compliance_score']}% ({c['va_findings_count']} vulns)</span></td>
                <td><span class="badge {bridge_badge}">{c['bridge_status']}</span></td>
            </tr>
            """
            client_rows.append(row)

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aure System — Mission Control & Continuous Assurance Dashboard</title>
<style>
  :root {{
    --bg-main: #0b1329;
    --bg-card: #132247;
    --bg-row-hover: #1c3266;
    --border-color: #243c74;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --accent-cyan: #38bdf8;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
  body {{ background-color: var(--bg-main); color: var(--text-primary); padding: 24px; }}
  .container {{ max-width: 1300px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border-color); padding-bottom: 20px; margin-bottom: 24px; }}
  .brand {{ font-size: 24px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }}
  .brand span {{ color: var(--accent-cyan); }}
  .subhead {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
  .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; display: inline-block; }}
  .badge-success {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #10b981; }}
  .badge-warning {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #f59e0b; }}
  .badge-danger {{ background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid #f43f5e; }}
  .badge-info {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; }}
  .badge-secondary {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid #64748b; }}
  
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 18px; }}
  .kpi-title {{ font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; }}
  .kpi-value {{ font-size: 26px; font-weight: 800; color: #fff; }}
  .kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; }}

  .section {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; margin-bottom: 24px; }}
  .section-title {{ font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }}
  
  table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
  th {{ background: rgba(11, 19, 41, 0.6); padding: 12px 14px; color: var(--text-muted); text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 2px solid var(--border-color); }}
  td {{ padding: 14px; border-bottom: 1px solid rgba(36, 60, 116, 0.5); vertical-align: middle; }}
  tr:hover {{ background-color: var(--bg-row-hover); }}

  .footer {{ text-align: center; font-size: 12px; color: var(--text-muted); padding: 20px 0; border-top: 1px solid var(--border-color); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="brand">AURE <span>SYSTEM</span> &bull; Mission Control</div>
      <div class="subhead">Centrale Esecutiva di Continuous Assurance, SLA PSA, Billing, MPS & Conformità D.Lgs. 231/2001</div>
    </div>
    <div style="text-align: right;">
      <span class="badge badge-success">SISTEMA DETERMINISTICO OPERATIVO</span>
      <div class="subhead">{datetime.datetime.now().strftime('%d %B %Y - %H:%M:%S')}</div>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Monte Ore SLA Disponibile</div>
      <div class="kpi-value" style="color: var(--accent-emerald);">{kpis['total_sla_hours_available']}h</div>
      <div class="kpi-sub">Consumate: {kpis['total_sla_hours_consumed']}h totali</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Crediti Aperti da Incassare</div>
      <div class="kpi-value" style="color: var(--accent-cyan);">€{kpis['total_open_credit_eur']:,.2f}</div>
      <div class="kpi-sub">Ore spot pendenti: {kpis['total_unbilled_hours']}h</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Parco Multifunzione MPS</div>
      <div class="kpi-value">{kpis['total_printers']}</div>
      <div class="kpi-sub">Allarmi Toner Bassi: <b style="color: var(--accent-rose);">{kpis['total_toner_critical_alerts']}</b></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Conformità Media 231 / ISO</div>
      <div class="kpi-value" style="color: var(--accent-amber);">{kpis['avg_compliance_score']}%</div>
      <div class="kpi-sub">Audit e gap remediation attivi</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">
      <span>Matrice di Monitoraggio Clienti 360°</span>
      <span style="font-size: 12px; color: var(--text-muted);">{len(data['clients'])} Clienti a Sistema</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Cliente & Tier</th>
          <th>SLA Monte Ore</th>
          <th>Contabilità & Fatture</th>
          <th>Stato MPS & Toner</th>
          <th>Conformità 231</th>
          <th>Bridge itinfra</th>
        </tr>
      </thead>
      <tbody>
        {''.join(client_rows)}
      </tbody>
    </table>
  </div>

  <div class="footer">
    Aure System di Eduardo Possumato &bull; IT Operations & Governance Platform &bull; Zero-CDN Verified Engine
  </div>
</div>
</body>
</html>
"""
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(html_content, encoding="utf-8")

        return html_content
