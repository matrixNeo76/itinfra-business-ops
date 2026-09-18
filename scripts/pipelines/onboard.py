#!/usr/bin/env python3
"""
scripts/pipelines/onboard.py — Pipeline 11 (Pipeline K)
End-to-End Client Onboarding Orchestrator (SPEC-20)
Inizializzazione atomica e deterministica del workspace commerciale (itinfra-business-ops)
e del gemello tecnico (itinfra) con cross-validation zero-drift immediata.
"""

import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from scripts.core.config import get_clients_dir, get_itinfra_dir, get_templates_dir
from scripts.core.bridge import ITInfraBridge
from scripts.core.validator import validate_yaml_file


class OnboardPipeline:
    """
    Orchestratore unificato per l'onboarding atomico di nuovi clienti.
    Configura client-manifest, contratti SLA con monte ore scalato per tier,
    preventivi di assessment, cartelle contabili, template 231, e contestualmente
    genera in itinfra l'infrastruttura di documentazione (manifest, IPAM, As-Built).
    """

    TIER_CONFIG = {
        "silver": {
            "name": "Silver SLA",
            "hours": 20.0,
            "hourly_rate": 85.0,
            "annual_fee": 1700.0,
            "response_time_h": 8,
            "target_resolution_h": 24,
            "on_site_sla": "NBD",
        },
        "gold": {
            "name": "Gold SLA",
            "hours": 50.0,
            "hourly_rate": 75.0,
            "annual_fee": 3750.0,
            "response_time_h": 4,
            "target_resolution_h": 8,
            "on_site_sla": "4h",
        },
        "platinum": {
            "name": "Platinum SLA 24/7",
            "hours": 100.0,
            "hourly_rate": 65.0,
            "annual_fee": 6500.0,
            "response_time_h": 1,
            "target_resolution_h": 4,
            "on_site_sla": "2h",
        },
    }

    def __init__(self, clients_root: Optional[Path] = None, itinfra_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.itinfra_root = itinfra_root or get_itinfra_dir()
        self.bridge = ITInfraBridge(itinfra_root=self.itinfra_root, clients_root=self.clients_root)

    def onboard_client(
        self,
        slug: str,
        client_name: str,
        vat_id: Optional[str] = None,
        sdi_code: Optional[str] = None,
        primary_subnet: str = "192.168.10.0/24",
        tier: str = "gold",
        domain: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Esegue l'onboarding atomico completo.
        Restituisce un dizionario con i dettagli della transazione e la certificazione zero-drift.
        """
        slug = slug.strip().lower()
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug):
            raise ValueError(f"Slug non valido '{slug}': deve essere kebab-case minuscolo.")

        tier_key = tier.strip().lower()
        if tier_key not in self.TIER_CONFIG:
            tier_key = "gold"
        tier_cfg = self.TIER_CONFIG[tier_key]

        vat = vat_id or "IT99999999999"
        sdi = sdi_code or "0000000"
        domain_name = domain or f"{slug}.lan"
        today_iso = datetime.date.today().isoformat()
        year_str = str(datetime.date.today().year)

        # Determina IP gateway e apparati da subnet
        subnet_base = primary_subnet.split("/")[0]
        ip_parts = subnet_base.split(".")
        if len(ip_parts) == 4:
            ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        else:
            ip_prefix = "192.168.10"

        gateway_ip = f"{ip_prefix}.1"
        fw_serial = f"FW-{slug.upper()[:6]}-01"
        srv_serial = f"SRV-{slug.upper()[:6]}-01"

        client_dir = self.clients_root / slug
        itinfra_project_dir = self.itinfra_root / "projects" / slug

        if not dry_run:
            client_dir.mkdir(parents=True, exist_ok=True)
            for sub in ["contracts", "timesheets", "invoices", "quotes", "mps", "furniture", "gap_analysis"]:
                (client_dir / sub).mkdir(parents=True, exist_ok=True)

        # 1. client-manifest.yaml in itinfra-business-ops
        client_manifest = {
            "slug": slug,
            "client_name": client_name,
            "created_at": today_iso,
            "tier": tier_key,
            "contacts": [
                {
                    "name": "Referente Tecnico",
                    "role": "IT Manager",
                    "email": f"it@{slug}.local",
                    "phone": "+39 02 0000001",
                },
                {
                    "name": "Referente Amministrazione",
                    "role": "CFO / Accounting",
                    "email": f"amministrazione@{slug}.local",
                    "phone": "+39 02 0000002",
                },
            ],
            "billing_info": {
                "vat_id": vat,
                "fiscal_code": vat.replace("IT", ""),
                "sdi_code": sdi,
                "pec": f"amministrazione@pec.{slug}.local",
                "iban": "IT00X0000000000000000000000",
                "payment_terms": "30_60_DF_FM",
                "address": {
                    "street": "Sede Legale",
                    "zip": "00100",
                    "city": "Città",
                    "province": "RM",
                },
            },
            "modules": {
                "it_support": True,
                "mps_rental": True,
                "office_furniture": False,
                "gap_analysis_231": True,
            },
        }

        # 2. contracts/ctr-<slug>-<year>.yaml
        contract_id = f"CTR-{slug.upper()}-{year_str}"
        contract_data = {
            "contract_id": contract_id,
            "client_slug": slug,
            "contract_type": "sla_pack",
            "tier": tier_key,
            "status": "active",
            "valid_from": today_iso,
            "valid_until": f"{int(year_str) + 1}-12-31",
            "annual_fee": tier_cfg["annual_fee"],
            "sla": {
                "level": tier_key.capitalize(),
                "response_time_hours": tier_cfg["response_time_h"],
                "target_resolution_hours": tier_cfg["target_resolution_h"],
                "on_site": tier_cfg["on_site_sla"],
            },
            "hours_bank": {
                "total_purchased": tier_cfg["hours"],
                "consumed": 0.0,
                "hourly_rate": tier_cfg["hourly_rate"],
            },
            "covered_assets": [
                {
                    "serial_number": fw_serial,
                    "model": "Firewall Core UTM",
                    "role": "Firewall & Gateway",
                },
                {
                    "serial_number": srv_serial,
                    "model": "Virtualization Host Server",
                    "role": "Primary Host",
                },
            ],
            "terms": {
                "billing_frequency": "annual_advance",
                "rollover_unused_hours": True,
            },
        }

        # 3. quotes/quote-<slug>-01.yaml
        quote_id = f"QTE-{slug.upper()}-01"
        quote_data = {
            "quote_id": quote_id,
            "client_slug": slug,
            "title": f"Proposta Onboarding ICT & Assessment di Conformità — {client_name}",
            "created_at": today_iso,
            "valid_until": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            "status": "draft",
            "currency": "EUR",
            "author": "Aure System di Eduardo Possumato",
            "items": [
                {
                    "category": "professional_services",
                    "sku": "PS-ONBOARD-01",
                    "description": "Onboarding Iniziale, Rilevazione As-Built e Documentazione Tecnica",
                    "unit_cost": 400.0,
                    "unit_price": 600.0,
                    "quantity": 1.0,
                    "margin_percent": 33.3,
                },
                {
                    "category": "sla_subscription",
                    "sku": f"SLA-{tier_key.upper()}-01",
                    "description": f"Canone Annuale Assistenza Sistemica & Helpdesk ({tier_cfg['name']})",
                    "unit_cost": tier_cfg["annual_fee"] * 0.4,
                    "unit_price": tier_cfg["annual_fee"],
                    "quantity": 1.0,
                    "margin_percent": 60.0,
                },
            ],
            "financial_summary": {
                "total_cost": round(400.0 + (tier_cfg["annual_fee"] * 0.4), 2),
                "total_net_price": round(600.0 + tier_cfg["annual_fee"], 2),
                "gross_margin_amount": round((600.0 + tier_cfg["annual_fee"]) - (400.0 + (tier_cfg["annual_fee"] * 0.4)), 2),
                "vat_rate": 22.0,
            },
        }

        # 4. mps/mps-<slug>-01.yaml
        mps_id = f"MPS-{slug.upper()}-01"
        mps_data = {
            "contract_id": mps_id,
            "client_slug": slug,
            "status": "active",
            "start_date": today_iso,
            "end_date": f"{int(year_str) + 3}-12-31",
            "monthly_fee": 45.0,
            "printers": [
                {
                    "asset_id": f"PRN-{slug.upper()[:6]}-01",
                    "model": "Kyocera TASKalfa 2554ci",
                    "serial_number": f"KYOCERA-{slug.upper()[:6]}-01",
                    "ip_address": f"{ip_prefix}.50",
                    "location": "Ufficio Operativo",
                    "cost_per_page": {
                        "mono_included": 1000,
                        "color_included": 200,
                        "excess_mono": 0.009,
                        "excess_color": 0.065,
                    },
                    "current_counters": {
                        "mono_total": 0,
                        "color_total": 0,
                        "toner_black_pct": 100,
                        "toner_cyan_pct": 100,
                        "toner_magenta_pct": 100,
                        "toner_yellow_pct": 100,
                    },
                }
            ],
        }

        # 5. gap_analysis/ga-<slug>-01.yaml
        gap_id = f"GA-{slug.upper()}-01"
        gap_data = {
            "assessment_id": gap_id,
            "client_slug": slug,
            "title": f"Gap Analysis di Conformità D.Lgs. 231/2001 e Cybersecurity — {client_name}",
            "created_at": today_iso,
            "updated_at": today_iso,
            "lead_assessor": "Eduardo Possumato",
            "status": "in_progress",
            "frameworks": ["D.Lgs. 231/2001 Art. 24-bis", "ISO/IEC 27001:2022", "NIST CSF v2.0"],
            "interviews": {
                "ciso_security": {"conducted": False, "score": 0.0, "notes": "Da pianificare"},
                "it_operations": {"conducted": False, "score": 0.0, "notes": "Da pianificare"},
                "risk_compliance": {"conducted": False, "score": 0.0, "notes": "Da pianificare"},
                "procurement_contracts": {"conducted": False, "score": 0.0, "notes": "Da pianificare"},
                "facility_physical_security": {"conducted": False, "score": 0.0, "notes": "Da pianificare"},
            },
            "findings_va": [],
            "scoring": {
                "maturity_percent": 0.0,
                "risk_level": "PENDING",
            },
        }

        created_files: List[str] = []

        if not dry_run:
            p_manifest = client_dir / "client-manifest.yaml"
            p_contract = client_dir / "contracts" / f"ctr-{slug}-{year_str}.yaml"
            p_quote = client_dir / "quotes" / f"quote-{slug}-01.yaml"
            p_mps = client_dir / "mps" / f"mps-{slug}-01.yaml"
            p_gap = client_dir / "gap_analysis" / f"ga-{slug}-01.yaml"

            p_manifest.write_text(yaml.safe_dump(client_manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
            p_contract.write_text(yaml.safe_dump(contract_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            p_quote.write_text(yaml.safe_dump(quote_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            p_mps.write_text(yaml.safe_dump(mps_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            p_gap.write_text(yaml.safe_dump(gap_data, sort_keys=False, allow_unicode=True), encoding="utf-8")

            created_files.extend([str(p_manifest), str(p_contract), str(p_quote), str(p_mps), str(p_gap)])

        # 6. Generazione itinfra (se repository presente)
        itinfra_created = False
        if self.itinfra_root.exists():
            if not dry_run:
                itinfra_project_dir.mkdir(parents=True, exist_ok=True)

            tech_manifest = {
                "project_id": slug,
                "project_name": f"Infrastruttura ICT & Telecomunicazioni — {client_name}",
                "customer": client_name,
                "lead_architect": "Eduardo Possumato",
                "owner_team": "Aure System Infrastructure & Security Team",
                "status": "completed",
                "version": "1.0.0",
                "created_at": today_iso,
                "updated_at": today_iso,
                "sites": [
                    {
                        "code": f"HQ-{slug[:3].upper()}",
                        "name": f"Sede Operativa {client_name}",
                        "role": "Primary HQ",
                        "location": client_manifest["billing_info"]["address"]["city"],
                    }
                ],
                "network_baseline": {
                    "supernet_ipv4": primary_subnet,
                    "gateway_ip": gateway_ip,
                    "core_firewall_model": "Firewall Core UTM",
                    "domain_controller_ip": f"{ip_prefix}.10",
                    "active_directory_domain": domain_name,
                    "vault_secret_prefix": f"vault://it/projects/{slug}",
                },
                "hardware_baseline": {
                    "hypervisor_host": "Virtualization Host Server",
                    "core_firewall": "Firewall Core UTM",
                },
                "sla_baseline": {
                    "tier1_rto": f"{tier_cfg['target_resolution_h']} ore",
                    "tier1_rpo": "2 ore",
                    "change_window": "Sabato 14:00 - 20:00 CET",
                },
                "documents": {
                    "01-Executive-Summary": "approved",
                    "02-Physical-Site-Survey": "approved",
                    "03-Logical-Network-Architecture": "approved",
                    "04-Network-IPAM": "approved",
                    "05-Disaster-Recovery-Plan": "approved",
                    "06-As-Built": "approved",
                },
            }

            ipam_content = f"""---
okf_version: "0.2"
id: "architecture-{slug}-ipam-01"
title: "Network IPAM — Schema Indirizzamento e Allocazione IP {client_name}"
type: "specification"
domain: "Networking & IPAM"
tags: ["okf-v0.2", "ipam", "networking", "subnets", "{slug}"]
project_id: "{slug}"
phase: 3
status: "approved"
version: "1.0"
created_at: "{today_iso}"
updated_at: "{today_iso}"
lang: "it"

entities:
  - name: "Subnet LAN Primaria {client_name}"
    type: "specification"
    description: "Subnet {primary_subnet} per apparati core, server e client"
relations:
  - targetTitle: "As-Built {client_name}"
    targetId: "architecture-{slug}-asbuilt-01"
    relationType: "references"
    weight: 1.0
---

# Network IPAM — {client_name}

## 1. Subnet Censite
- **Subnet Primaria (CIDR)**: `{primary_subnet}` (Gateway: `{gateway_ip}`, Mask: `255.255.255.0`)

## 2. Tabella di Allocazione IP
| IP | Descrizione / Ruolo Apparato | VLAN | MAC / Note |
| :--- | :--- | :---: | :--- |
| `{gateway_ip}` | Firewall Core UTM (Gateway & Security) | VLAN 10 | 00:09:0F:00:01:01 |
| `{ip_prefix}.10` | Primary Domain Controller / DNS | VLAN 10 | 00:50:56:00:10:01 |
| `{ip_prefix}.50` | Kyocera TASKalfa Multifunzione | VLAN 20 | 00:17:C8:00:50:01 |
"""

            as_built_content = f"""---
okf_version: "0.2"
id: "architecture-{slug}-asbuilt-01"
title: "As-Built — Documentazione Tecnica Finale Apparati {client_name}"
type: "architecture"
domain: "IT Infrastructure & Documentation Delivery"
tags: ["okf-v0.2", "as-built", "inventory", "hardware", "{slug}"]
project_id: "{slug}"
phase: 5
status: "approved"
version: "1.0"
created_at: "{today_iso}"
updated_at: "{today_iso}"
lang: "it"

entities:
  - name: "Hardware Inventory {client_name}"
    type: "specification"
    description: "Inventario apparati hardware certificati installati"
relations:
  - targetTitle: "Network IPAM {client_name}"
    targetId: "architecture-{slug}-ipam-01"
    relationType: "references"
    weight: 1.0
---

# As-Built — {client_name}

## 1. Inventario Apparati Hardware e Virtual Appliance

| Apparato | Modello | Seriale / IP | Note di Configurazione |
| :--- | :--- | :--- | :--- |
| Firewall Core UTM | Firewall Core UTM | {fw_serial} / {gateway_ip} | Gateway di confine, VPN SSL, IPS/Antivirus attivo |
| Virtualization Host | Virtualization Host Server | {srv_serial} / {ip_prefix}.10 | Host hypervisor con macchine virtuali aziendali |
"""

            if not dry_run:
                p_tech_manifest = itinfra_project_dir / "manifest.yaml"
                p_tech_ipam = itinfra_project_dir / "04-Network-IPAM.md"
                p_tech_asbuilt = itinfra_project_dir / "06-As-Built.md"

                p_tech_manifest.write_text(yaml.safe_dump(tech_manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
                p_tech_ipam.write_text(ipam_content, encoding="utf-8")
                p_tech_asbuilt.write_text(as_built_content, encoding="utf-8")

                created_files.extend([str(p_tech_manifest), str(p_tech_ipam), str(p_tech_asbuilt)])
                itinfra_created = True

        # 7. Cross-Check immediato zero-drift
        cross_check_status = "NOT_CHECKED"
        if not dry_run and itinfra_created:
            coverage_result = self.bridge.cross_check_sla_assets_coverage(slug)
            cross_check_status = coverage_result.get("status", "UNKNOWN")

        # 8. Generazione SHA-256 seal
        cert_data = f"{slug}|{client_name}|{vat}|{today_iso}|{tier_key}|{cross_check_status}"
        seal = hashlib.sha256(cert_data.encode("utf-8")).hexdigest()

        return {
            "slug": slug,
            "client_name": client_name,
            "vat_id": vat,
            "tier": tier_key,
            "primary_subnet": primary_subnet,
            "gateway_ip": gateway_ip,
            "hours_allocated": tier_cfg["hours"],
            "sla_response_hours": tier_cfg["response_time_h"],
            "business_ops_path": str(client_dir),
            "itinfra_path": str(itinfra_project_dir) if itinfra_created else None,
            "itinfra_created": itinfra_created,
            "created_files": created_files,
            "cross_check_status": cross_check_status,
            "zero_drift_certified": (cross_check_status == "PASS"),
            "sha256_seal": seal,
            "timestamp": datetime.datetime.now().isoformat(),
        }
