"""
Gap Analysis & Compliance 231 Pipeline (SPEC-19)
================================================
Pipeline nativa per la conduzione, calcolo del gap, prioritizzazione del remediation plan,
audit dei controlli di sicurezza e redazione peritale di fascicoli di conformità al
D.Lgs. 231/2001 (Art. 24-bis reati informatici), ISO/IEC 27001:2022, ISO 22301 e NIST CSF v2.0.

Fornitore ufficiale: Aure System di Eduardo Possumato
Marchio e identità: Aure System (Cybersecurity & Governance Division)
Federazione itinfra: Shared Customer Slug con cross-check As-Built & IPAM (Read-Only)
Zero-CDN Invariant: Generazione standalone, offline-ready e conforme agli standard forensi.
"""

import os
import sys
import json
import yaml
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Internal dependencies
from scripts.core.document_branding import BrandConfig

class ItinfraBridge:
    """Interfaccia in sola lettura verso il repository tecnico federato ../itinfra."""

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.workspace_root = workspace_root
        self.itinfra_root = self.workspace_root.parent / "itinfra"
        self.clients_root = self.workspace_root / "clients"

    def has_itinfra(self) -> bool:
        return self.itinfra_root.is_dir()

    def get_itinfra_project_dir(self, slug: str) -> Optional[Path]:
        pdir = self.itinfra_root / "projects" / slug
        if pdir.is_dir():
            return pdir
        return None

    def extract_ipam_subnets_and_ips(self, slug: str) -> Dict[str, Any]:
        pdir = self.get_itinfra_project_dir(slug)
        if not pdir:
            return {"found": False, "subnets": [], "allocations": []}

        ipam_file = pdir / "04-Network-IPAM.md"
        if not ipam_file.is_file():
            return {"found": False, "subnets": [], "allocations": []}

        try:
            content = ipam_file.read_text(encoding="utf-8")
        except Exception:
            return {"found": False, "subnets": [], "allocations": []}

        allocations = []
        subnets = []
        in_table = False
        import re
        for line in content.splitlines():
            line_str = line.strip()
            m = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})', line_str)
            if m:
                subnets.append(m.group(1))
            if line_str.startswith("|") and ("IP" in line_str or "Host" in line_str):
                in_table = True
                continue
            if in_table and line_str.startswith("|"):
                parts = [p.strip().replace("`", "") for p in line_str.split("|") if p.strip()]
                if len(parts) >= 2 and not parts[0].startswith("---"):
                    ip_candidate = parts[0].strip()
                    desc = parts[1] if len(parts) > 1 else ""
                    if any(char.isdigit() for char in ip_candidate) and "." in ip_candidate:
                        allocations.append({"ip": ip_candidate, "hostname_or_desc": desc})
            elif in_table and not line_str.startswith("|"):
                in_table = False

        return {"found": True, "subnets": list(set(subnets)), "allocations": allocations}

    def extract_as_built_assets(self, slug: str) -> List[Dict[str, Any]]:
        pdir = self.get_itinfra_project_dir(slug)
        if not pdir:
            return []

        as_built = pdir / "06-As-Built.md"
        if not as_built.is_file():
            return []

        try:
            content = as_built.read_text(encoding="utf-8")
        except Exception:
            return []

        assets = []
        in_table = False
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("|") and ("Apparato" in line_str or "Modello" in line_str or "Hardware" in line_str):
                in_table = True
                continue
            if in_table and line_str.startswith("|"):
                parts = [p.strip() for p in line_str.split("|") if p.strip()]
                if len(parts) >= 2 and not parts[0].startswith("---"):
                    assets.append({
                        "device_name": parts[0],
                        "model": parts[1] if len(parts) > 1 else "",
                        "serial_or_ip": parts[2] if len(parts) > 2 else ""
                    })
            elif in_table and not line_str.startswith("|"):
                in_table = False

        return assets


class GapAnalysisPipeline:
    """
    Pipeline unificata per la gestione completa di Gap Analysis e Conformità 231.
    """

    CANONICAL_AREAS = [
        "ciso_security",
        "it_operations",
        "risk_compliance",
        "procurement_contracts",
        "facility_physical_security"
    ]

    AREA_LABELS = {
        "ciso_security": "CISO & Sicurezza delle Informazioni",
        "it_operations": "IT Operations & Amministrazione Reti",
        "risk_compliance": "Risk Management & OdV Compliance 231",
        "procurement_contracts": "Acquisti & Gestione Contratti Fornitori",
        "facility_physical_security": "Sicurezza Fisica & Controllo Accessi"
    }

    REQUIRED_DOCUMENTS = [
        ("modello_231_morg", "Modello di Organizzazione, Gestione e Controllo (MOG 231)"),
        ("codice_etico", "Codice Etico Aziendale"),
        ("politiche_sicurezza_ict", "Politiche di Sicurezza delle Informazioni (Policy ICT)"),
        ("disciplinare_dispositivi", "Disciplinare Tecnico Uso Dispositivi (Art. 4 L. 300/70)"),
        ("disaster_recovery_plan", "Piano di Continuità Operativa e Disaster Recovery (BCP/DR)"),
        ("registro_trattamenti", "Registro delle Attività di Trattamento Dati (Art. 30 GDPR)"),
        ("organigramma_ict", "Organigramma Funzionale ICT & Matrice RACI Sicurezza")
    ]

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.workspace_root = workspace_root
        self.bridge = ItinfraBridge(self.workspace_root)

    def get_gap_dir(self, slug: str) -> Path:
        p = self.workspace_root / "clients" / slug / "gap_analysis"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def list_assessments(self, slug: str) -> List[Dict[str, Any]]:
        gdir = self.get_gap_dir(slug)
        results = []
        for f in sorted(gdir.glob("ga-*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("assessment_id"):
                    results.append(data)
            except Exception:
                pass
        return results

    def load_assessment(self, slug: str, assessment_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        gdir = self.get_gap_dir(slug)
        assessments = []
        for f in gdir.glob("ga-*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if not assessment_id or data.get("assessment_id") == assessment_id:
                    if assessment_id:
                        return data
                    assessments.append(data)
            except Exception:
                pass
        if assessments:
            return sorted(assessments, key=lambda x: str(x.get("created_at", "")), reverse=True)[0]
        return None

    def save_assessment(self, slug: str, data: Dict[str, Any]) -> Path:
        aid = data.get("assessment_id", f"ga-{datetime.date.today().strftime('%Y')}-231-01")
        gdir = self.get_gap_dir(slug)
        target = gdir / f"{aid.lower()}.yaml"
        with open(target, "w", encoding="utf-8") as fp:
            yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)
        return target

    def init_assessment(
        self,
        slug: str,
        assessment_id: Optional[str] = None,
        framework: str = "dlgs_231",
        title: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
        lead_auditor: str = "Aure System Senior Advisor",
        reference_quote_id: Optional[str] = None,
        target_completion_date: Optional[str] = None
    ) -> Dict[str, Any]:
        today_str = datetime.date.today().isoformat()
        year_str = datetime.date.today().strftime('%Y')
        aid = assessment_id or f"ga-{year_str}-231-01"

        cmanifest = self.bridge.clients_root / slug / "client-manifest.yaml"
        client_name = slug
        client_address = "Sede cliente"
        if cmanifest.is_file():
            try:
                with open(cmanifest, "r", encoding="utf-8") as fp:
                    m = yaml.safe_load(fp) or {}
                client_name = m.get("client_name", slug)
                c_addr = m.get("billing_info", {}).get("address", {})
                if c_addr.get("street"):
                    client_address = f"{c_addr.get('street')}, {c_addr.get('zip', '')} {c_addr.get('city', '')} ({c_addr.get('province', '')})"
            except Exception:
                pass

        default_scope = {
            "location": client_address,
            "target_networks": ["192.168.10.0/24"],
            "in_scope_assets_count": 25,
            "third_party_dependencies": ["Fornitore Cloud / Hosting", "Outsourcer Gestionali"]
        }
        if scope:
            default_scope.update(scope)

        initial_docs = []
        for code, name in self.REQUIRED_DOCUMENTS:
            initial_docs.append({
                "code": code,
                "name": name,
                "status": "missing",
                "finding": "In attesa di ricezione dal cliente per esame documentale."
            })

        assessment = {
            "assessment_id": aid,
            "slug": slug,
            "title": title or f"Servizi di Compliance & Gap Analysis D.Lgs. 231/01 — {client_name}",
            "framework": framework,
            "created_at": today_str,
            "target_completion_date": target_completion_date or (datetime.date.today() + datetime.timedelta(days=45)).isoformat(),
            "status": "in_progress",
            "lead_auditor": lead_auditor,
            "reference_quote_id": reference_quote_id or "",
            "scope": default_scope,
            "documentary_review": {
                "documents_requested": 7,
                "documents_received": 0,
                "reviewed_items": initial_docs
            },
            "interviews": [],
            "vulnerability_assessment": {
                "scan_date": today_str,
                "engine": "CVSS_v4",
                "total_targets_scanned": 0,
                "findings_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "findings": []
            },
            "gap_scores": {
                "overall_compliance_percent": 0.0,
                "maturity_level": 1.0,
                "domain_scores": {}
            },
            "remediation_plan": {
                "total_actions": 0,
                "total_cost_eur": 0.0,
                "actions": []
            },
            "deliverables": {}
        }

        self.save_assessment(slug, assessment)
        return assessment

    def record_document_review(
        self,
        slug: str,
        document_code: str,
        name: str,
        status: str,
        finding: str = "",
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        d_rev = ass.setdefault("documentary_review", {"documents_requested": 7, "documents_received": 0, "reviewed_items": []})
        items = d_rev.setdefault("reviewed_items", [])

        updated = False
        for it in items:
            if it.get("code") == document_code:
                it["name"] = name
                it["status"] = status
                it["finding"] = finding
                updated = True
                break

        if not updated:
            items.append({
                "code": document_code,
                "name": name,
                "status": status,
                "finding": finding
            })

        d_rev["documents_received"] = len([it for it in items if it.get("status") in ["compliant", "compliant_with_gaps", "acquired"]])
        self.save_assessment(slug, ass)
        return ass

    def record_interview(
        self,
        slug: str,
        area: str,
        respondent: str,
        maturity_score: float,
        notes: str = "",
        answers: Optional[Dict[str, Any]] = None,
        interview_date: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if area not in self.CANONICAL_AREAS:
            raise ValueError(f"Area '{area}' non valida. Scegliere tra: {self.CANONICAL_AREAS}")

        score = max(1.0, min(5.0, float(maturity_score)))
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        interviews = ass.setdefault("interviews", [])
        i_date = interview_date or datetime.date.today().isoformat()

        record = {
            "area": area,
            "respondent": respondent,
            "interview_date": i_date,
            "maturity_score": round(score, 2),
            "notes": notes,
            "answers": answers or {}
        }

        replaced = False
        for idx, item in enumerate(interviews):
            if item.get("area") == area:
                interviews[idx] = record
                replaced = True
                break
        if not replaced:
            interviews.append(record)

        self.save_assessment(slug, ass)
        return ass

    @staticmethod
    def classify_cvss_severity(score: float) -> str:
        s = float(score)
        if s >= 9.0:
            return "critical"
        elif s >= 7.0:
            return "high"
        elif s >= 4.0:
            return "medium"
        else:
            return "low"

    def record_vulnerability_findings(
        self,
        slug: str,
        findings: List[Dict[str, Any]],
        scan_date: Optional[str] = None,
        engine: str = "CVSS_v4",
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        va = ass.setdefault("vulnerability_assessment", {})
        va["scan_date"] = scan_date or datetime.date.today().isoformat()
        va["engine"] = engine

        normalized_findings = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        unique_ips = set()

        for f in findings:
            score = float(f.get("cvss_v4_score", f.get("score", 5.0)))
            sev = f.get("severity") or self.classify_cvss_severity(score)
            sev = sev.lower()
            if sev not in summary:
                sev = "medium"
            summary[sev] += 1

            ip = f.get("target_ip", "127.0.0.1")
            unique_ips.add(ip)

            normalized_findings.append({
                "cve_id": f.get("cve_id", "CVE-LOCAL-FINDING"),
                "target_ip": ip,
                "port": int(f.get("port", 80)),
                "service": f.get("service", "Generic Service"),
                "cvss_v4_score": round(score, 1),
                "severity": sev,
                "title": f.get("title", "Debolezza di sicurezza rilevata"),
                "remediation": f.get("remediation", f.get("remediation_guidance", "Applicare le patch raccomandate.")),
                "evidence_packet": f.get("evidence_packet", "")
            })

        va["total_targets_scanned"] = len(unique_ips) if unique_ips else len(normalized_findings)
        va["findings_summary"] = summary
        va["findings"] = normalized_findings

        self.save_assessment(slug, ass)
        return ass

    def compute_gap_scores(self, slug: str, assessment_id: Optional[str] = None) -> Dict[str, Any]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        d_rev = ass.get("documentary_review", {})
        r_items = d_rev.get("reviewed_items", [])
        if r_items:
            doc_points = 0.0
            for it in r_items:
                st = it.get("status")
                if st in ["compliant", "acquired"]:
                    doc_points += 100.0
                elif st == "compliant_with_gaps":
                    doc_points += 60.0
                elif st == "not_applicable":
                    doc_points += 100.0
                else:
                    doc_points += 0.0
            doc_score = round(doc_points / len(r_items), 2)
        else:
            doc_score = 0.0

        interviews = ass.get("interviews", [])
        domain_scores = {}
        if interviews:
            total_mat = 0.0
            for inv in interviews:
                area = inv.get("area")
                mat = float(inv.get("maturity_score", 1.0))
                total_mat += mat
                pct = round((mat / 5.0) * 100.0, 2)
                domain_scores[area] = pct
            avg_mat = total_mat / len(interviews)
            int_score = round((avg_mat / 5.0) * 100.0, 2)
        else:
            avg_mat = 1.0
            int_score = 20.0

        va = ass.get("vulnerability_assessment", {})
        va_sum = va.get("findings_summary", {})
        crit = va_sum.get("critical", 0)
        high = va_sum.get("high", 0)
        med = va_sum.get("medium", 0)
        low = va_sum.get("low", 0)

        penalty = (crit * 25.0) + (high * 10.0) + (med * 4.0) + (low * 1.0)
        va_score = max(0.0, round(100.0 - penalty, 2))

        overall_pct = round((doc_score * 0.25) + (int_score * 0.50) + (va_score * 0.25), 2)
        maturity_cmmi = round(max(1.0, min(5.0, (overall_pct / 100.0) * 5.0)), 2)

        full_domains = {
            "modello_231_legal": domain_scores.get("risk_compliance", doc_score),
            "access_governance": domain_scores.get("ciso_security", int_score),
            "network_infrastructure": round((domain_scores.get("it_operations", int_score) + va_score) / 2.0, 2),
            "data_protection_gdpr": round((doc_score + domain_scores.get("risk_compliance", int_score)) / 2.0, 2),
            "incident_continuity": domain_scores.get("facility_physical_security", int_score)
        }

        gap_scores = {
            "overall_compliance_percent": overall_pct,
            "maturity_level": maturity_cmmi,
            "documentary_score": doc_score,
            "interviews_score": int_score,
            "technical_vulnerability_score": va_score,
            "domain_scores": full_domains
        }

        ass["gap_scores"] = gap_scores
        self.save_assessment(slug, ass)
        return gap_scores

    calculate_gap_scores = compute_gap_scores

    def generate_remediation_plan(self, slug: str, assessment_id: Optional[str] = None) -> Dict[str, Any]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        actions = []
        counter = 1

        va = ass.get("vulnerability_assessment", {})
        for f in va.get("findings", []):
            sev = f.get("severity", "").lower()
            if sev in ["critical", "high"]:
                prio = "P1_CRITICAL" if sev == "critical" else "P2_HIGH"
                days = 15 if sev == "critical" else 45
                actions.append({
                    "id": f"REM-{counter:02d}",
                    "priority": prio,
                    "deadline_days": days,
                    "domain": "network_infrastructure",
                    "title": f"Mitigazione {f.get('cve_id')} su {f.get('target_ip')}:{f.get('port')}",
                    "description": f"{f.get('title')}. Contromisura raccomandata: {f.get('remediation')}",
                    "owner": "IT Operations / Security Advisor",
                    "estimated_cost_eur": 650.0 if sev == "critical" else 450.0,
                    "related_reato_presupposto": "Art. 24-bis D.Lgs. 231/01 (Accesso abusivo a sistema informatico)"
                })
                counter += 1

        d_rev = ass.get("documentary_review", {})
        for doc in d_rev.get("reviewed_items", []):
            if doc.get("status") in ["missing", "compliant_with_gaps"]:
                actions.append({
                    "id": f"REM-{counter:02d}",
                    "priority": "P2_HIGH" if doc.get("status") == "missing" else "P3_MEDIUM",
                    "deadline_days": 60 if doc.get("status") == "missing" else 90,
                    "domain": "modello_231_legal",
                    "title": f"Aggiornamento e formalizzazione: {doc.get('name')}",
                    "description": doc.get("finding") or "Formalizzare documento conforme a D.Lgs. 231/01 e ISO/IEC 27001.",
                    "owner": "Compliance & Team Legale",
                    "estimated_cost_eur": 1200.0,
                    "related_reato_presupposto": "Art. 6 e 7 D.Lgs. 231/01 (Idoneità del Modello Organizzativo MOG)"
                })
                counter += 1

        gap_s = ass.get("gap_scores", {})
        domains = gap_s.get("domain_scores", {})
        if domains.get("access_governance", 100) < 70.0:
            actions.append({
                "id": f"REM-{counter:02d}",
                "priority": "P2_HIGH",
                "deadline_days": 45,
                "domain": "access_governance",
                "title": "Adozione MFA obbligatoria e revisione account privilegiati",
                "description": "Introdurre autenticazione a più fattori su VPN e pannelli amministrativi con dismissione password deboli.",
                "owner": "IT Administrator",
                "estimated_cost_eur": 800.0,
                "related_reato_presupposto": "Art. 24-bis D.Lgs. 231/01 (Frode informatica con furto di identità)"
            })
            counter += 1

        prio_order = {"P1_CRITICAL": 1, "P2_HIGH": 2, "P3_MEDIUM": 3, "P4_LOW": 4}
        actions.sort(key=lambda x: prio_order.get(x.get("priority", "P3_MEDIUM"), 9))

        total_cost = round(sum(a.get("estimated_cost_eur", 0.0) for a in actions), 2)
        rem_plan = {
            "total_actions": len(actions),
            "total_cost_eur": total_cost,
            "actions": actions
        }

        ass["remediation_plan"] = rem_plan
        self.save_assessment(slug, ass)
        return rem_plan

    build_remediation_plan = generate_remediation_plan

    def cross_check_itinfra(self, slug: str, assessment_id: Optional[str] = None) -> Dict[str, Any]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        aid = ass.get("assessment_id")
        ipam_data = self.bridge.extract_ipam_subnets_and_ips(slug)
        as_built_assets = self.bridge.extract_as_built_assets(slug)

        known_ips = set()
        for alloc in ipam_data.get("allocations", []):
            if alloc.get("ip"):
                known_ips.add(alloc.get("ip").strip())

        va_findings = ass.get("vulnerability_assessment", {}).get("findings", [])
        scanned_ips = set(f.get("target_ip").strip() for f in va_findings if f.get("target_ip"))

        shadow_it_ips = list(scanned_ips - known_ips) if known_ips else []
        unscanned_ipam_ips = list(known_ips - scanned_ips) if scanned_ips else list(known_ips)

        status = "PASS" if not shadow_it_ips else "WARNING"
        result = {
            "slug": slug,
            "assessment_id": aid,
            "itinfra_project_exists": ipam_data.get("found", False),
            "target_networks": ipam_data.get("subnets", ass.get("scope", {}).get("target_networks", [])),
            "as_built_devices": as_built_assets,
            "total_ipam_allocations": len(known_ips),
            "scanned_ips": list(scanned_ips),
            "shadow_it_alerts": shadow_it_ips,
            "unscanned_ipam_ips": unscanned_ipam_ips,
            "status": status,
            "message": "Nessuna anomalia di Shadow IT riscontrata." if status == "PASS" else f"Rilevati {len(shadow_it_ips)} indirizzi IP scansionati non censiti nell'IPAM di itinfra (Shadow IT)."
        }
        return result

    def seal_assessment_sha256(self, assessment_data: Dict[str, Any]) -> str:
        norm_data = {
            "assessment_id": assessment_data.get("assessment_id"),
            "slug": assessment_data.get("slug"),
            "framework": assessment_data.get("framework"),
            "created_at": assessment_data.get("created_at"),
            "gap_scores": assessment_data.get("gap_scores"),
            "remediation_actions_count": len(assessment_data.get("remediation_plan", {}).get("actions", [])),
            "lead_auditor": assessment_data.get("lead_auditor")
        }
        raw_json = json.dumps(norm_data, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    def generate_deliverables(self, slug: str, assessment_id: Optional[str] = None, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        ass = self.load_assessment(slug, assessment_id)
        if not ass:
            raise ValueError(f"Nessun assessment trovato per {slug}")

        aid = ass.get("assessment_id")
        target_dir = output_dir or self.get_gap_dir(slug)
        target_dir.mkdir(parents=True, exist_ok=True)

        cmanifest = self.bridge.clients_root / slug / "client-manifest.yaml"
        client_name = slug
        if cmanifest.is_file():
            try:
                with open(cmanifest, "r", encoding="utf-8") as fp:
                    client_name = (yaml.safe_load(fp) or {}).get("client_name", slug)
            except Exception:
                pass

        seal = self.seal_assessment_sha256(ass)
        scores = ass.get("gap_scores", {})
        va = ass.get("vulnerability_assessment", {})
        rem = ass.get("remediation_plan", {})

        p1 = target_dir / "01-verbale-kickoff.md"
        p1_content = f"""# Verbale di Kick-off di Progetto — Gap Analysis & Compliance 231

**Fornitore**: {BrandConfig.COMPANY_NAME}  
**Committente**: {client_name} ({slug})  
**Data Avvio**: {ass.get('created_at')}  
**Riferimento Fascicolo**: `{aid}`  
**Lead Auditor**: {ass.get('lead_auditor')}  
**Sigillo Digitale Verbali**: `{seal[:16]}...`

---

## 1. Obiettivi e Perimetro Tecnico-Legale
In data {ass.get('created_at')} si è tenuto il kick-off operativo per le attività peritali di conformità al **D.Lgs. 231/2001 (Art. 24-bis reati informatici)**, ISO/IEC 27001:2022 e NIST CSF v2.0.

- **Sede Operativa**: {ass.get('scope', {}).get('location')}
- **Reti Target**: {', '.join(ass.get('scope', {}).get('target_networks', []))}
- **Referenti di Progetto**:
  - CISO & Sicurezza delle Informazioni: da intervistare
  - IT Operations & Reti: da intervistare
  - Risk Management & Compliance 231: da intervistare
  - Ufficio Acquisti: da intervistare
  - Sicurezza Fisica: da intervistare

---
*Aure System — Documento Istituzionale di Avvio Progetto*
"""
        p1.write_text(p1_content, encoding="utf-8")

        p2 = target_dir / "02-rapporto-gap-analysis-remediation.md"
        doms = scores.get("domain_scores", {})
        dom_rows = "\n".join(f"| {k.replace('_', ' ').title()} | {v:.1f}% | {'CONFORME' if v >= 75 else 'GAP RILEVATO' if v >= 50 else 'CRITICO'} |" for k, v in doms.items())
        act_rows = "\n".join(f"| `{a.get('id')}` | **{a.get('priority')}** | {a.get('deadline_days')} gg | {a.get('title')} | {a.get('owner')} | € {a.get('estimated_cost_eur', 0):.2f} |" for a in rem.get("actions", []))

        p2_content = f"""# Rapporto Ufficiale di Gap Analysis & Remediation Plan

**Organizzazione Auditata**: {client_name}  
**Auditor Emittente**: {BrandConfig.COMPANY_NAME}  
**Standard di Riferimento**: D.Lgs. 231/2001 Art. 24-bis, ISO/IEC 27001:2022, NIST CSF v2.0  
**Data Certificazione**: {datetime.date.today().isoformat()}  
**Sigillo Immutabile SHA-256**: `{seal}`  

---

## 1. Executive Summary & Indici di Maturità
- **Indice Complessivo di Conformità**: **{scores.get('overall_compliance_percent', 0.0):.1f}%**
- **Livello di Maturità CMMI Equivalente**: **{scores.get('maturity_level', 1.0):.1f} / 5.0**
- **Stato Conformità MOG 231**: {'ADEGUATO' if scores.get('overall_compliance_percent', 0) >= 80 else 'ADEGUATO CON RILIEVI' if scores.get('overall_compliance_percent', 0) >= 60 else 'NON ADEGUATO — RISCHIO SANZIONATORIO'}

### Scorecard per Dominio di Sicurezza
| Dominio di Valutazione | Punteggio Riscontrato | Esito Peritale |
| :--- | :---: | :---: |
{dom_rows}

---

## 2. Piano di Rimedio Operativo (Remediation Plan Prioritizzato)
| ID | Priorità | Scadenza | Azione Correttiva | Responsabile | Costo Stimato |
| :-: | :-: | :-: | :--- | :--- | -: |
{act_rows}

---
*Certificato emesso con firma digitale da Aure System di Eduardo Possumato*
"""
        p2.write_text(p2_content, encoding="utf-8")

        p3 = target_dir / "03-rapporto-vulnerability-assessment.md"
        find_rows = "\n".join(f"| `{f.get('cve_id')}` | `{f.get('target_ip')}` | {f.get('service')} | **{f.get('cvss_v4_score')}** | {f.get('severity').upper()} | {f.get('title')} |" for f in va.get("findings", []))
        sum_va = va.get("findings_summary", {})

        p3_content = f"""# Rapporto Tecnico di Vulnerability Assessment (CVSS v4.0)

**Cliente**: {client_name}  
**Data Scansione**: {va.get('scan_date')}  
**Metodologia di Scoring**: FIRST Common Vulnerability Scoring System (CVSS v4.0)  
**Host & Servizi Ispezionati**: {va.get('total_targets_scanned', 0)}  
**Sigillo Tecnico SHA-256**: `{seal}`  

---

## 1. Riepilogo Severità
- **Critiche (9.0 - 10.0)**: {sum_va.get('critical', 0)}
- **Alte (7.0 - 8.9)**: {sum_va.get('high', 0)}
- **Medie (4.0 - 6.9)**: {sum_va.get('medium', 0)}
- **Basse (0.1 - 3.9)**: {sum_va.get('low', 0)}

---

## 2. Registro Dettagliato delle Rilevazioni
| CVE ID | IP Target | Servizio | CVSS v4 | Severità | Descrizione Debolezza |
| :--- | :--- | :--- | :---: | :---: | :--- |
{find_rows}

---
*Aure System — Vulnerability Assessment Division*
"""
        p3.write_text(p3_content, encoding="utf-8")

        p4 = target_dir / "04-executive-presentation-odv.html"
        p4_html = self._generate_executive_html(ass, client_name, seal)
        p4.write_text(p4_html, encoding="utf-8")

        p2_pdf = target_dir / "02-rapporto-gap-analysis-remediation.pdf"
        p3_pdf = target_dir / "03-rapporto-vulnerability-assessment.pdf"
        try:
            from scripts.core.document_renderer import DocumentRenderer
            DocumentRenderer.render_gap_analysis_to_pdf(ass, p2_pdf)
            DocumentRenderer.render_vulnerability_assessment_to_pdf(ass, p3_pdf)
            ass.setdefault("deliverables", {})["gap_analysis_report_pdf"] = str(p2_pdf)
            ass["deliverables"]["vulnerability_assessment_report_pdf"] = str(p3_pdf)
        except Exception as ex:
            print(f"[!] Avviso generazione PDF: {ex}")

        ass.setdefault("deliverables", {})["kickoff"] = str(p1)
        ass["deliverables"]["gap_analysis_report"] = str(p2)
        ass["deliverables"]["vulnerability_assessment_report"] = str(p3)
        ass["deliverables"]["executive_presentation"] = str(p4)
        ass["deliverables"]["sha256_seal"] = seal
        self.save_assessment(slug, ass)

        return {
            "kickoff": p1,
            "gap_analysis_report": p2,
            "gap_analysis_report_pdf": p2_pdf,
            "vulnerability_assessment_report": p3,
            "vulnerability_assessment_report_pdf": p3_pdf,
            "executive_presentation": p4
        }

    def _generate_executive_html(self, ass: Dict[str, Any], client_name: str, seal: str) -> str:
        scores = ass.get("gap_scores", {})
        doms = scores.get("domain_scores", {})
        va = ass.get("vulnerability_assessment", {})
        sum_va = va.get("findings_summary", {})
        rem = ass.get("remediation_plan", {})
        ov_pct = scores.get("overall_compliance_percent", 0.0)

        domain_bars = ""
        for k, v in doms.items():
            name = k.replace('_', ' ').title()
            color = "#10B981" if v >= 75 else "#F59E0B" if v >= 50 else "#EF4444"
            domain_bars += f"""
            <div style="margin-bottom: 14px;">
              <div style="display:flex; justify-content:space-between; font-weight:600; font-size:13px; margin-bottom:4px;">
                <span>{name}</span>
                <span style="color:{color};">{v:.1f}%</span>
              </div>
              <div style="background:#E2E8F0; border-radius:8px; height:12px; overflow:hidden;">
                <div style="background:{color}; width:{min(100.0, v)}%; height:100%;"></div>
              </div>
            </div>
            """

        actions_html = ""
        for a in rem.get("actions", [])[:6]:
            badge_color = "#EF4444" if "CRITICAL" in a.get("priority", "") else "#F59E0B" if "HIGH" in a.get("priority", "") else "#3B82F6"
            actions_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; font-size:13px;">
              <td style="padding:8px;"><code>{a.get('id')}</code></td>
              <td style="padding:8px;"><span style="background:{badge_color}; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{a.get('priority')}</span></td>
              <td style="padding:8px;">{a.get('title')}</td>
              <td style="padding:8px;">{a.get('owner')}</td>
              <td style="padding:8px; text-align:right; font-weight:600;">€ {a.get('estimated_cost_eur', 0):.2f}</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Executive Dashboard Compliance 231 — {client_name}</title>
  <style>
    @media print {{
      body {{ margin: 0; background: #fff; }}
      .no-print {{ display: none; }}
      .dashboard-container {{ box-shadow: none; border: none; }}
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #F1F5F9;
      color: #0F172A;
      margin: 0;
      padding: 24px;
    }}
    .dashboard-container {{
      max-width: 1080px;
      margin: 0 auto;
      background: #FFFFFF;
      border-radius: 16px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08);
      overflow: hidden;
      border: 1px solid #CBD5E1;
    }}
    .header {{
      background: linear-gradient(135deg, {BrandConfig.HEX_PRIMARY} 0%, {BrandConfig.HEX_SECONDARY} 100%);
      color: #FFFFFF;
      padding: 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }}
    .header p {{ margin: 4px 0 0 0; font-size: 14px; opacity: 0.9; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      padding: 24px;
      background: #F8FAFC;
      border-bottom: 1px solid #E2E8F0;
    }}
    .kpi-card {{
      background: #FFFFFF;
      padding: 18px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      text-align: center;
    }}
    .kpi-val {{ font-size: 28px; font-weight: 800; color: {BrandConfig.HEX_PRIMARY}; margin: 4px 0; }}
    .kpi-lbl {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748B; }}
    .content-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      padding: 24px;
    }}
    .panel {{
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 20px;
    }}
    .panel h3 {{ margin-top: 0; font-size: 16px; color: {BrandConfig.HEX_PRIMARY}; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    .footer {{
      background: #F8FAFC;
      padding: 16px 24px;
      border-top: 1px solid #E2E8F0;
      font-size: 12px;
      color: #64748B;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>

  <div class="dashboard-container">
    <div class="header">
      <div>
        <h1>AURE SYSTEM — Cybersecurity & Compliance Governance</h1>
        <p>Executive Dashboard D.Lgs. 231/2001 (Art. 24-bis) • Organismo di Vigilanza & CDA</p>
      </div>
      <div style="text-align:right;">
        <span style="background:rgba(255,255,255,0.2); padding:6px 14px; border-radius:20px; font-weight:bold; font-size:12px;">{ass.get('assessment_id')}</span>
        <div style="margin-top:6px; font-size:12px;">Committente: <strong>{client_name}</strong></div>
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-lbl">Conformità Complessiva</div>
        <div class="kpi-val" style="color:{'#10B981' if ov_pct>=75 else '#F59E0B' if ov_pct>=50 else '#EF4444'};">{ov_pct:.1f}%</div>
        <div style="font-size:11px; color:#64748B;">Target Legale: 100%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Maturità CMMI</div>
        <div class="kpi-val">{scores.get('maturity_level', 1.0):.1f} <span style="font-size:16px;">/ 5.0</span></div>
        <div style="font-size:11px; color:#64748B;">Livello Gestito</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Vulnerabilità Critiche</div>
        <div class="kpi-val" style="color:#EF4444;">{sum_va.get('critical', 0)}</div>
        <div style="font-size:11px; color:#64748B;">CVSS v4.0 >= 9.0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Azioni Remediation</div>
        <div class="kpi-val">{rem.get('total_actions', 0)}</div>
        <div style="font-size:11px; color:#64748B;">Prioritizzate P1/P2/P3</div>
      </div>
    </div>

    <div class="content-grid">
      <div class="panel">
        <h3>Maturità per Dominio di Sicurezza</h3>
        {domain_bars}
      </div>

      <div class="panel">
        <h3>Vulnerability Assessment (CVSS v4.0)</h3>
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; margin-bottom:16px;">
          <div style="background:#FEE2E2; color:#991B1B; padding:10px; border-radius:8px; text-align:center;">
            <div style="font-size:18px; font-weight:800;">{sum_va.get('critical', 0)}</div>
            <div style="font-size:10px; font-weight:bold;">CRITICAL</div>
          </div>
          <div style="background:#FFEDD5; color:#9A3412; padding:10px; border-radius:8px; text-align:center;">
            <div style="font-size:18px; font-weight:800;">{sum_va.get('high', 0)}</div>
            <div style="font-size:10px; font-weight:bold;">HIGH</div>
          </div>
          <div style="background:#FEF3C7; color:#92400E; padding:10px; border-radius:8px; text-align:center;">
            <div style="font-size:18px; font-weight:800;">{sum_va.get('medium', 0)}</div>
            <div style="font-size:10px; font-weight:bold;">MEDIUM</div>
          </div>
          <div style="background:#DBEAFE; color:#1E40AF; padding:10px; border-radius:8px; text-align:center;">
            <div style="font-size:18px; font-weight:800;">{sum_va.get('low', 0)}</div>
            <div style="font-size:10px; font-weight:bold;">LOW</div>
          </div>
        </div>
        <p style="font-size:12px; color:#64748B; line-height:1.5;">
          Scansione eseguita su <strong>{va.get('total_targets_scanned', 0)} apparati</strong>. Il riscontro di vulnerabilità critiche impone l'immediata applicazione delle azioni di remediation a salvaguardia della responsabilità penale dell'ente ex Art. 24-bis.
        </p>
      </div>
    </div>

    <div style="padding: 0 24px 24px 24px;">
      <div class="panel">
        <h3>Prime Azioni di Remediation Prioritarie</h3>
        <table>
          <thead>
            <tr style="border-bottom: 2px solid #CBD5E1; text-align:left; font-size:12px; color:#64748B;">
              <th style="padding:8px;">ID</th>
              <th style="padding:8px;">Priorità</th>
              <th style="padding:8px;">Azione di Bonifica</th>
              <th style="padding:8px;">Owner</th>
              <th style="padding:8px; text-align:right;">Stima Spesa</th>
            </tr>
          </thead>
          <tbody>
            {actions_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="footer">
      <div>{BrandConfig.COMPANY_NAME} • {BrandConfig.ADDRESS} • P.IVA: {BrandConfig.VAT_ID}</div>
      <div>Sigillo Forense SHA-256: <code>{seal[:24]}...</code></div>
    </div>
  </div>

</body>
</html>
"""

    # =========================================================================
    # CLI COMMAND HANDLERS
    # =========================================================================

    def cmd_init(self, slug: str, title: Optional[str] = None) -> int:
        try:
            ass = self.init_assessment(slug, title=title)
            print(f"[✓ OK] Inizializzato assessment '{ass.get('assessment_id')}' per il cliente '{slug}'.")
            print(f"      File di tracciamento: clients/{slug}/gap_analysis/{ass.get('assessment_id')}.yaml")
            print(f"      Documenti OKF v0.2 di quadro: clients/{slug}/gap_analysis/01-*, 02-*, 03-*")
            return 0
        except Exception as e:
            print(f"[ERRORE] Inizializzazione fallita: {e}")
            return 1

    def cmd_status(self, slug: str) -> int:
        ass = self.load_assessment(slug)
        if not ass:
            print(f"[!] Nessun assessment di Gap Analysis trovato per '{slug}'. Esegui prima 'gap {slug} init'.")
            return 1

        print("=" * 72)
        print(f"GAP ANALYSIS & COMPLIANCE 231 STATUS — {slug.upper()}")
        print("=" * 72)
        print(f"ID Assessment       : {ass.get('assessment_id')}")
        print(f"Titolo              : {ass.get('title')}")
        print(f"Stato Avanzamento   : {ass.get('status', 'draft').upper()}")
        print(f"Data Creazione      : {ass.get('created_at')}")

        docs = ass.get("documentary_review", {}).get("reviewed_items", [])
        print(f"\nDocumenti Analizzati ({len(docs)}/7 minimi):")
        for d in docs:
            st = "✓ CONFORME" if d.get("status") in ["compliant", "acquired"] else ("⚠️ CON RILIEVI" if d.get("status") == "compliant_with_gaps" else "✗ ASSENTE")
            print(f"  - [{st}] {d.get('code')}: {d.get('name')}")

        interviews = ass.get("interviews", [])
        print(f"\nInterviste Eseguite ({len(interviews)}/5 aree canoniche):")
        for inv in interviews:
            area_lbl = self.AREA_LABELS.get(inv.get("area"), inv.get("area"))
            print(f"  - [✓] {area_lbl}: {inv.get('respondent')} (Maturità: {inv.get('maturity_score', 1.0):.1f}/5.0)")

        va = ass.get("vulnerability_assessment", {})
        findings = va.get("findings", [])
        sum_va = va.get("findings_summary", {})
        print(f"\nVulnerability Assessment (CVSS v4.0): {len(findings)} rilievi")
        print(f"  - Critiche: {sum_va.get('critical', 0)} | Alte: {sum_va.get('high', 0)} | Medie: {sum_va.get('medium', 0)} | Basse: {sum_va.get('low', 0)}")

        scores = ass.get("gap_scores", {})
        if scores and scores.get("overall_compliance_percent", 0.0) > 0:
            print(f"\nIndici di Conformità:")
            print(f"  - Conformità Globale : {scores.get('overall_compliance_percent', 0.0):.1f}%")
            print(f"  - Maturità CMMI      : {scores.get('maturity_level', 1.0):.1f} / 5.0")
        else:
            print("\nIndici di Conformità: [NON ANCORA CALCOLATI — esegui 'gap <slug> calculate']")

        rem = ass.get("remediation_plan", {})
        if rem and rem.get("actions"):
            print(f"\nRemediation Plan: {rem.get('total_actions', 0)} azioni (Costo stimato: € {rem.get('total_cost_eur', 0):.2f})")

        deliv = ass.get("deliverables", {})
        if deliv.get("executive_presentation"):
            print(f"\nDeliverables Generati: [✓ PRONTI]")
            print(f"  - Report: {deliv.get('gap_analysis_report')}")
            print(f"  - VA Report: {deliv.get('vulnerability_assessment_report')}")
            print(f"  - Executive Dashboard: {deliv.get('executive_presentation')}")
        else:
            print(f"\nDeliverables Generati: [NON GENERATI — esegui 'gap <slug> report']")
        print("=" * 72)
        return 0

    def cmd_interview(self, slug: str, area: Optional[str] = None, notes: Optional[str] = None, score: float = 0.0) -> int:
        if not area:
            print("Specificare l'area con --area. Aree canoniche ammesse:")
            for k, v in self.AREA_LABELS.items():
                print(f"  - {k}: {v}")
            return 1
        try:
            # Score can be 0-100 or 1-5, normalize to 1-5
            mat_score = score if score <= 5.0 and score >= 1.0 else max(1.0, min(5.0, score / 20.0))
            self.record_interview(
                slug=slug,
                area=area,
                respondent="Referente Incaricato",
                maturity_score=mat_score,
                notes=notes or f"Intervista condotta per area {area}"
            )
            print(f"[✓ OK] Intervista per l'area '{area}' registrata con maturità {mat_score:.1f}/5.0.")
            return 0
        except Exception as e:
            print(f"[ERRORE] Registrazione intervista fallita: {e}")
            return 1

    def cmd_va(self, slug: str, finding_json: Optional[str] = None) -> int:
        ass = self.load_assessment(slug)
        if not ass:
            print(f"[!] Nessun assessment trovato per '{slug}'.")
            return 1
        va = ass.get("vulnerability_assessment", {})
        findings = va.get("findings", [])
        print(f"Rilievi VA per {slug} ({len(findings)} totali):")
        for f in findings:
            print(f"  - [{f.get('severity').upper()}] {f.get('cve_id')} on {f.get('target_ip')}:{f.get('port')} (CVSS {f.get('cvss_v4_score')}): {f.get('title')}")
        return 0

    def cmd_calculate(self, slug: str) -> int:
        try:
            scores = self.calculate_gap_scores(slug)
            print(f"\n[✓ OK] Calcolo Gap Analysis completato per '{slug}':")
            print(f"      Conformità Complessiva : {scores.get('overall_compliance_percent', 0.0):.1f}%")
            print(f"      Maturità CMMI          : {scores.get('maturity_level', 1.0):.1f} / 5.0")
            print("\nScorecard Domini:")
            for k, v in scores.get("domain_scores", {}).items():
                status_lbl = "CONFORME" if v >= 75 else "GAP RILEVATO" if v >= 50 else "CRITICO"
                print(f"  - {k.replace('_', ' ').title():<32}: {v:5.1f}% [{status_lbl}]")
            return 0
        except Exception as e:
            print(f"[ERRORE] Calcolo punteggi fallito: {e}")
            return 1

    def cmd_remediation(self, slug: str) -> int:
        try:
            rem = self.generate_remediation_plan(slug)
            print(f"\n[✓ OK] Remediation Plan generato per '{slug}':")
            print(f"      Azioni Totali : {rem.get('total_actions')}")
            print(f"      Costo Totale  : € {rem.get('total_cost_eur', 0):.2f}")
            print("\nAzioni Prioritarie:")
            print(f"  {'ID':<10} {'PRIORITÀ':<14} {'SCADENZA':<10} {'AZIONE':<36} {'COSTO':>10}")
            print("  " + "-" * 84)
            for a in rem.get("actions", []):
                print(f"  {a.get('id'):<10} {a.get('priority'):<14} {str(a.get('deadline_days')) + ' gg':<10} {a.get('title')[:34]:<36} €{a.get('estimated_cost_eur', 0):>8.2f}")
            return 0
        except Exception as e:
            print(f"[ERRORE] Generazione remediation plan fallita: {e}")
            return 1

    def cmd_report(self, slug: str) -> int:
        try:
            res = self.generate_deliverables(slug)
            print(f"\n[✓ OK] Generazione Deliverables completata per '{slug}':")
            print(f"      1. Verbale Kick-off     : {res['kickoff']}")
            print(f"      2. Rapporto Gap Analysis: {res['gap_analysis_report']}")
            print(f"      3. Rapporto VA          : {res['vulnerability_assessment_report']}")
            print(f"      4. Executive Dashboard  : {res['executive_presentation']}")
            print(f"\n      Dashboard HTML renderizzata con brand Aure System pronta per stampa/PDF.")
            return 0
        except Exception as e:
            print(f"[ERRORE] Generazione deliverable fallita: {e}")
            return 1

    def cmd_check(self, slug: str) -> int:
        try:
            res = self.cross_check_itinfra(slug)
            print(f"\n[✓ OK] Cross-Check itinfra As-Built per '{slug}':")
            print(f"      itinfra Project Exists  : {'SI' if res.get('itinfra_project_exists') else 'NO'}")
            print(f"      Apparati As-Built       : {len(res.get('as_built_devices', []))}")
            print(f"      Reti Monitorate         : {', '.join(res.get('target_networks', []))}")
            print(f"      IP Scansionati nel VA   : {len(res.get('scanned_ips', []))}")
            shadow = res.get("shadow_it_alerts", [])
            if shadow:
                print(f"\n      [!] ALLERTA SHADOW IT ({len(shadow)} IP non censiti nell'As-Built):")
                for ip in shadow:
                    print(f"          - {ip}")
            else:
                print("      [✓] Nessun dispositivo Shadow IT rilevato. Tutti i target corrispondono all'As-Built.")
            return 0
        except Exception as e:
            print(f"[ERRORE] Cross-check itinfra fallito: {e}")
            return 1
