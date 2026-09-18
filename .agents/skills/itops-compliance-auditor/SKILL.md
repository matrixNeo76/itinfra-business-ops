---
name: itops-compliance-auditor
description: Audit regulatory compliance (D.Lgs. 231/2001, ISO 27001, NIST CSF), calculate gap scores, and generate OdV executive reports.
---

# itops-compliance-auditor — Antigravity Skill

## Purpose
Automate compliance assessments, Vulnerability Assessments (CVSS v4.0), and Organismo di Vigilanza (OdV) / CdA briefings according to Italian Law D.Lgs. 231/2001 (Art. 24-bis) and ISO/IEC 27001:2022.

## Available Commands
```powershell
# Stato assessment
.\it-ops.cmd gap <slug> status

# Calcolo score e gap analysis
.\it-ops.cmd gap <slug> calculate

# Generazione deliverable formali (Markdown, PDF, OdV HTML)
.\it-ops.cmd gap <slug> report

# Esecuzione agente specializzato Auditor-231
.\it-ops.cmd agent audit-231 <slug>
```

## Key Output Artifacts
- `01-verbale-kickoff.md`
- `02-rapporto-gap-analysis-remediation.pdf`
- `03-rapporto-vulnerability-assessment.pdf`
- `04-executive-presentation-odv.html`
