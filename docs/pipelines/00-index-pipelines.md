---
okf_version: "0.2"
id: "index-ops-pipelines-master"
title: "Indice Master delle Pipeline Operative — itinfra-business-ops"
type: "index"
domain: "Business Operations & PSA"
tags: ["okf-v0.2", "master-index", "pipelines", "hub-and-spoke", "business-ops"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.2"
created_at: "2026-09-17"
updated_at: "2026-09-18"
lang: "it"

entities:
  - name: "Shared Customer Slug"
    type: "specification"
    description: "Identificativo deterministico che connette i dati tecnici di itinfra ai dati commerciali di itinfra-business-ops"
  - name: "Hub-and-Spoke Operational Architecture"
    type: "pattern"
    description: "Architettura modulare che disaccoppia ingegneria dei sistemi, finance e logistica arredi"
  - name: "Unified Business CLI Engine"
    type: "toolchain"
    description: "Motore Python it-ops e wrapper it-ops.cmd per governance deterministica"

relations:
  - targetTitle: "Pipeline A — Contratti SLA, Monte Ore & Over-Budget"
    targetId: "spec-ops-pipeline-a-contracts"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi"
    targetId: "spec-ops-pipeline-b-reports"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline C — Fatturazione SDI v1.2 & Scadenzario Multi-Rata"
    targetId: "spec-ops-pipeline-c-billing"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline D — Task Jira & Schedulazione Agenda RFC 5545"
    targetId: "spec-ops-pipeline-d-jira-calendar"
    relationType: "documents"
    weight: 0.9
  - targetTitle: "Pipeline E — Preventivazione Multiprodotto Cost-Plus"
    targetId: "spec-ops-pipeline-e-quotes"
    relationType: "documents"
    weight: 0.95
  - targetTitle: "Pipeline F — Noleggio Multifunzione MPS & Telemetria SNMP"
    targetId: "spec-ops-pipeline-f-mps-rental"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline G — Commesse Arredo Ufficio & Collaudo Finale"
    targetId: "spec-ops-pipeline-g-furniture"
    relationType: "documents"
    weight: 0.95
  - targetTitle: "Pipeline H — Ingestione Documenti SOTA & Visual Parsing"
    targetId: "spec-ops-pipeline-h-document-ingestion"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline I — Memoria Auto-Correttiva Attestata & DAG Sync"
    targetId: "spec-ops-pipeline-i-memory-learning"
    relationType: "documents"
    weight: 1.0
  - targetTitle: "Pipeline J — Gap Analysis & Compliance D.Lgs. 231/2001"
    targetId: "spec-ops-pipeline-j-gap-analysis"
    relationType: "documents"
    weight: 1.0
---

# 📚 Indice Master delle Pipeline Operative

Benvenuto nel compendio formale **OKF v0.2** di **`itinfra-business-ops`**.  
Questo documento censisce, mappa e relaziona le **10 pipeline native** di gestione operativa, commerciale, contabile, logistica, documentale e di conformità legale.

---

## 🗺️ Mappa delle Relazioni delle 10 Pipeline

```mermaid
flowchart TD
    subgraph Hub ["🔗 Shared Customer Slug"]
        SLUG["Cliente (<slug>)"]
    end

    subgraph Service ["🛠️ Assistenza & Sistemi"]
        PA["01: Pipeline A (Contratti SLA)"]
        PB["02: Pipeline B (Rapportini)"]
        PD["04: Pipeline D (Jira & Agenda)"]
    end

    subgraph Office ["🖨️ Office & Facilities"]
        PF["06: Pipeline F (MPS Multifunzione)"]
        PG["07: Pipeline G (Arredo Ufficio)"]
    end

    subgraph Commercial ["💼 Commerciale & Finance"]
        PE["05: Pipeline E (Preventivi)"]
        PC["03: Pipeline C (Fatturazione SDI)"]
    end

    subgraph CognitiveSecurity ["🛡️ Document Intelligence & Compliance"]
        PH["08: Pipeline H (Ingestione SOTA & Audit)"]
        PI["09: Pipeline I (Memoria DAG Attestata)"]
        PJ["10: Pipeline J (Gap Analysis 231 & VA)"]
    end

    SLUG --> PA
    SLUG --> PF
    SLUG --> PG
    SLUG --> PE
    SLUG --> PJ

    PD -->|Innesco Intervento| PB
    PB -->|Scarico Ore / Over-Budget| PA
    PA -->|Canoni & Ore Extra| PC
    PB -->|Interventi Spot & Ricambi| PC
    PF -->|Canoni Base & Conguaglio Copie| PC
    PG -->|Milestone SAL & Collaudo| PC
    PE -->|Accettazione Offerta| PA
    PE -->|Accettazione Offerta| PG

    PH -->|Ingestione Offerte & XML SDI| PE
    PH -->|Ingestione Contratti| PA
    PI -->|Guardrail & Correzioni Live| Hub
    PJ -->|Roadmap Remediation & Preventivo| PE
    PJ -->|Cross-Check Asset As-Built| PA
```

---

## 📑 Registro Documentale OKF v0.2

| Documento Specifico | ID Univoco OKF | Dominio Operativo | Schemi Formale Associato |
| :--- | :--- | :--- | :--- |
| [`01-pipeline-a-contracts.md`](01-pipeline-a-contracts.md) | `spec-ops-pipeline-a-contracts` | Contratti SLA & Monte Ore | `contract.schema.yaml` |
| [`02-pipeline-b-reports.md`](02-pipeline-b-reports.md) | `spec-ops-pipeline-b-reports` | Time-Tracking & Rapportini | `report.schema.yaml` |
| [`03-pipeline-c-billing.md`](03-pipeline-c-billing.md) | `spec-ops-pipeline-c-billing` | Fatturazione SDI v1.2 (FPR12/FPA12) | `billing.schema.yaml` |
| [`04-pipeline-d-jira-calendar.md`](04-pipeline-d-jira-calendar.md) | `spec-ops-pipeline-d-jira-calendar` | Jira & Calendario RFC 5545 | `jira_sync.schema.yaml` |
| [`05-pipeline-e-quotes.md`](05-pipeline-e-quotes.md) | `spec-ops-pipeline-e-quotes` | Preventivazione Multiprodotto | `quote.schema.yaml` |
| [`06-pipeline-f-mps-rental.md`](06-pipeline-f-mps-rental.md) | `spec-ops-pipeline-f-mps-rental` | MPS, Costo Copia & SNMP v3 | `mps.schema.yaml` |
| [`07-pipeline-g-furniture.md`](07-pipeline-g-furniture.md) | `spec-ops-pipeline-g-furniture` | Commesse Arredo & Collaudo | `furniture.schema.yaml` |
| [`08-pipeline-h-document-ingestion.okf.md`](08-pipeline-h-document-ingestion.okf.md) | `spec-ops-pipeline-h-document-ingestion` | Ingestione SOTA & Audit Triangolare | N/A (Multi-Engine) |
| [`09-pipeline-i-memory-learning.okf.md`](09-pipeline-i-memory-learning.okf.md) | `spec-ops-pipeline-i-memory-learning` | Memoria DAG & Attestation | `registry.yaml` |
| [`10-pipeline-j-gap-analysis.okf.md`](10-pipeline-j-gap-analysis.okf.md) | `spec-ops-pipeline-j-gap-analysis` | Gap Analysis 231 & CVSS v4.0 | `gap_analysis.schema.yaml` |
| [`../ASCII_DIAGRAMS.md`](../ASCII_DIAGRAMS.md) | `spec-ops-ascii-diagrams` | Compendio Diagrammi ASCII Hub & Pipelines | N/A |
