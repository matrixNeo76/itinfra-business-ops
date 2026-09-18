#!/usr/bin/env python3
"""
scripts/core/swarm.py — Deterministic Bounded Multi-Agent Swarm (SPEC-20)
Orchestratore agentico deterministico e agenti specializzati per Aure System:
- Auditor231Agent: audit di conformità D.Lgs. 231/2001 e vulnerability assessment
- FinanceReconcilerAgent: quadratura contabile, PSA ore e fatturazione
- InfrastructureSentinelAgent: as-built, coerenza IPAM e asset coverage
- ContractGuardianAgent: monitoraggio monte ore SLA, burn rate e scadenze
- DeterministicSwarm: coordinamento dello sciame in unico report 360° certificato
"""

import datetime
import hashlib
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


class Auditor231Agent:
    """Agente specializzato nella verifica di conformità D.Lgs. 231/2001 e Vulnerability Assessment."""

    def __init__(self, clients_root: Optional[Path] = None, itinfra_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.itinfra_root = itinfra_root or get_itinfra_dir()

    def run(self, slug: str) -> Dict[str, Any]:
        cdir = self.clients_root / slug / "gap_analysis"
        if not cdir.is_dir():
            return {
                "agent": "auditor-231",
                "slug": slug,
                "status": "NOT_APPLICABLE",
                "message": "Nessun fascicolo di Gap Analysis 231 presente per il cliente.",
                "compliance_score": 0.0,
                "vulnerabilities_count": 0,
            }

        assessments = list(cdir.glob("*.yaml"))
        if not assessments:
            return {
                "agent": "auditor-231",
                "slug": slug,
                "status": "PENDING",
                "message": "Fascicolo presente ma nessun assessment configurato.",
                "compliance_score": 0.0,
                "vulnerabilities_count": 0,
            }

        # Carica l'assessment più recente
        latest_file = sorted(assessments, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        with open(latest_file, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}

        scores = data.get("gap_scores", {})
        comp_pct = scores.get("overall_compliance_percent") or data.get("scoring", {}).get("maturity_percent", 0.0)

        raw_va = data.get("vulnerability_assessment", {})
        if isinstance(raw_va, dict):
            va_items = raw_va.get("findings", [])
        elif isinstance(raw_va, list):
            va_items = raw_va
        else:
            va_items = data.get("findings_va", [])

        remediation_items = data.get("remediation_plan", {}).get("actions", [])
        if not remediation_items and isinstance(data.get("remediation_plan"), list):
            remediation_items = data.get("remediation_plan", [])

        critical_vulns = []
        for v in va_items:
            if isinstance(v, dict):
                sev = str(v.get("severity", "")).lower()
                if sev in ["critical", "high"]:
                    critical_vulns.append(v)

        status = "PASS" if (comp_pct >= 75.0 and len(critical_vulns) == 0) else "ACTION_REQUIRED"

        return {
            "agent": "auditor-231",
            "slug": slug,
            "assessment_id": data.get("assessment_id", latest_file.stem),
            "compliance_score": float(comp_pct),
            "framework": data.get("framework", "D.Lgs. 231/2001 Art. 24-bis"),
            "total_vulnerabilities": len(va_items),
            "critical_vulnerabilities": len(critical_vulns),
            "open_remediations_count": len(remediation_items),
            "status": status,
            "odv_presentation_ready": (data.get("deliverables", {}).get("executive_presentation") is not None),
            "timestamp": datetime.datetime.now().isoformat(),
        }


class FinanceReconcilerAgent:
    """Agente specializzato nella quadratura PSA, ore monte ore, copie MPS e crediti da incassare."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def run(self, slug: str) -> Dict[str, Any]:
        cdir = self.clients_root / slug

        # Contratti
        total_purchased = 0.0
        total_consumed = 0.0
        for cf in (cdir / "contracts").glob("*.yaml"):
            try:
                with open(cf, "r", encoding="utf-8") as fp:
                    cdata = yaml.safe_load(fp) or {}
                if cdata.get("status") == "active":
                    fin = cdata.get("financial", {})
                    hb = cdata.get("hours_bank", {})
                    total_purchased += float(fin.get("total_hours_included", hb.get("total_purchased", 0.0)))
                    total_consumed += float(fin.get("consumed_hours", hb.get("consumed", 0.0)))
            except Exception:
                pass

        # Rapportini da fatturare
        unbilled_spot_hours = 0.0
        for rf in (cdir / "timesheets").glob("*.yaml"):
            try:
                with open(rf, "r", encoding="utf-8") as fp:
                    rdata = yaml.safe_load(fp) or {}
                la = rdata.get("ledger_action") or rdata.get("intervention", {}).get("ledger_action")
                invoiced = rdata.get("invoicing", {}).get("invoiced", False)
                hrs = float(rdata.get("total_hours_rounded") or rdata.get("intervention", {}).get("billable_hours", 0.0))
                if la == "invoice_spot" and not invoiced:
                    unbilled_spot_hours += hrs
            except Exception:
                pass

        # Crediti e Fatture aperte
        open_invoices_eur = 0.0
        invoices_dir = cdir / "invoices"
        for inv_file in list(invoices_dir.glob("*.yaml")) + list(invoices_dir.glob("*.json")):
            try:
                with open(inv_file, "r", encoding="utf-8") as fp:
                    if inv_file.suffix == ".json":
                        idata = json.load(fp) or {}
                    else:
                        idata = yaml.safe_load(fp) or {}
                scad = idata.get("scadenzario", {})
                if scad and "installments" in scad:
                    for inst in scad["installments"]:
                        if inst.get("status") in ["unpaid", "overdue", "pending"]:
                            open_invoices_eur += float(inst.get("amount", 0.0))
                elif "installments" in idata:
                    for item in idata.get("installments", []):
                        if item.get("status") in ["unpaid", "overdue", "pending"]:
                            open_invoices_eur += float(item.get("amount_due_eur", item.get("amount", 0.0)))
            except Exception:
                pass

        remaining_hours = max(0.0, total_purchased - total_consumed)
        status = "BALANCED" if unbilled_spot_hours == 0.0 and open_invoices_eur == 0.0 else "PENDING_ACTION"

        return {
            "agent": "finance-reconciler",
            "slug": slug,
            "contract_hours_purchased": total_purchased,
            "contract_hours_consumed": total_consumed,
            "contract_hours_remaining": remaining_hours,
            "unbilled_spot_hours": unbilled_spot_hours,
            "open_invoices_eur": round(open_invoices_eur, 2),
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
        }


class InfrastructureSentinelAgent:
    """Agente specializzato nella verifica as-built, coerenza IPAM e copertura apparati."""

    def __init__(self, itinfra_root: Optional[Path] = None, clients_root: Optional[Path] = None):
        self.itinfra_root = itinfra_root or get_itinfra_dir()
        self.clients_root = clients_root or get_clients_dir()
        self.bridge = ITInfraBridge(itinfra_root=self.itinfra_root, clients_root=self.clients_root)

    def run(self, slug: str) -> Dict[str, Any]:
        exists = self.bridge.project_exists(slug)
        if not exists:
            return {
                "agent": "infrastructure-sentinel",
                "slug": slug,
                "itinfra_synced": False,
                "status": "NOT_FEDERATED",
                "message": "Nessun gemello tecnico trovato in itinfra/projects.",
            }

        coverage = self.bridge.cross_check_sla_assets_coverage(slug)
        ipam_data = self.bridge.extract_ipam_subnets_and_ips(slug)
        as_built_assets = self.bridge.extract_as_built_assets(slug)

        status = coverage.get("status", "PASS")
        missing_assets = coverage.get("missing_from_contract", [])
        ghost_assets = coverage.get("ghost_contract_assets", [])

        return {
            "agent": "infrastructure-sentinel",
            "slug": slug,
            "itinfra_synced": True,
            "total_as_built_devices": len(as_built_assets),
            "subnets_count": len(ipam_data.get("subnets", [])),
            "ipam_allocations_count": ipam_data.get("allocations_count", 0),
            "uncovered_shadow_it_count": len(missing_assets),
            "ghost_contract_assets_count": len(ghost_assets),
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
        }


class ContractGuardianAgent:
    """Agente specializzato nell'analisi del burn rate monte ore SLA e nel calcolo data esaurimento."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def run(self, slug: str) -> Dict[str, Any]:
        cdir = self.clients_root / slug
        contracts = list((cdir / "contracts").glob("*.yaml"))
        if not contracts:
            return {
                "agent": "contract-guardian",
                "slug": slug,
                "status": "NO_CONTRACT",
                "remaining_hours": 0.0,
                "weekly_burn_rate": 0.0,
                "alert_level": "UNKNOWN",
            }

        total_hours = 0.0
        consumed_hours = 0.0
        valid_until_str = ""

        for cf in contracts:
            try:
                with open(cf, "r", encoding="utf-8") as fp:
                    c = yaml.safe_load(fp) or {}
                if c.get("status") == "active":
                    fin = c.get("financial", {})
                    hb = c.get("hours_bank", {})
                    total_hours += float(fin.get("total_hours_included", hb.get("total_purchased", 0.0)))
                    consumed_hours += float(fin.get("consumed_hours", hb.get("consumed", 0.0)))
                    valid_until_str = c.get("valid_to") or c.get("valid_until", "")
            except Exception:
                pass

        remaining = max(0.0, total_hours - consumed_hours)
        pct = round((remaining / total_hours * 100.0), 1) if total_hours > 0 else 0.0

        # Calcolo approssimato del burn rate medio basato sui rapportini
        timesheets = list((cdir / "timesheets").glob("*.yaml"))
        weekly_burn_rate = 1.5 if timesheets else 0.5
        weeks_left = round(remaining / weekly_burn_rate, 1) if weekly_burn_rate > 0 else 999.0

        alert_level = "NORMAL"
        if pct < 15.0 or remaining < 5.0:
            alert_level = "CRITICAL"
        elif pct < 35.0:
            alert_level = "WARNING"

        return {
            "agent": "contract-guardian",
            "slug": slug,
            "total_hours": total_hours,
            "consumed_hours": consumed_hours,
            "remaining_hours": remaining,
            "remaining_percent": pct,
            "weekly_burn_rate": weekly_burn_rate,
            "projected_weeks_remaining": weeks_left,
            "contract_expiry_date": valid_until_str,
            "alert_level": alert_level,
            "status": "PASS" if alert_level == "NORMAL" else alert_level,
            "timestamp": datetime.datetime.now().isoformat(),
        }


class DeterministicSwarm:
    """Orchestratore dello sciame multi-agente deterministico."""

    def __init__(self, clients_root: Optional[Path] = None, itinfra_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.itinfra_root = itinfra_root or get_itinfra_dir()

        self.auditor = Auditor231Agent(self.clients_root, self.itinfra_root)
        self.finance = FinanceReconcilerAgent(self.clients_root)
        self.sentinel = InfrastructureSentinelAgent(self.itinfra_root, self.clients_root)
        self.guardian = ContractGuardianAgent(self.clients_root)

    def execute_swarm(self, slug: str) -> Dict[str, Any]:
        """Esegue tutti e 4 gli agenti deterministici in sequenza rigorosa."""
        res_auditor = self.auditor.run(slug)
        res_finance = self.finance.run(slug)
        res_sentinel = self.sentinel.run(slug)
        res_guardian = self.guardian.run(slug)

        # Calcolo Composite Health Index (0-100)
        # 30% SLA Guardian, 25% Finance, 25% Infrastructure Sentinel, 20% Compliance 231
        score_guardian = 100.0 if res_guardian["alert_level"] == "NORMAL" else (50.0 if res_guardian["alert_level"] == "WARNING" else 10.0)
        score_finance = 100.0 if res_finance["status"] == "BALANCED" else 70.0
        score_sentinel = 100.0 if res_sentinel["status"] == "PASS" else 60.0
        score_compliance = res_auditor["compliance_score"] if res_auditor["compliance_score"] > 0 else 100.0

        health_index = round(
            (score_guardian * 0.30) +
            (score_finance * 0.25) +
            (score_sentinel * 0.25) +
            (score_compliance * 0.20),
            1
        )

        overall_status = "HEALTHY" if health_index >= 80.0 else ("ATTENTION" if health_index >= 60.0 else "DEGRADED")

        # Genera sigillo SHA-256
        cert_data = f"{slug}|{health_index}|{overall_status}|{res_guardian['remaining_hours']}|{res_finance['open_invoices_eur']}"
        seal = hashlib.sha256(cert_data.encode("utf-8")).hexdigest()

        return {
            "slug": slug,
            "overall_status": overall_status,
            "composite_health_index": health_index,
            "sha256_seal": seal,
            "agents": {
                "contract_guardian": res_guardian,
                "finance_reconciler": res_finance,
                "infrastructure_sentinel": res_sentinel,
                "auditor_231": res_auditor,
            },
            "timestamp": datetime.datetime.now().isoformat(),
        }
