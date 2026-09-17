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
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
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
    description: "Governa contratti di assistenza, monte ore a scalare e alert rinnovo"
  - targetTitle: "Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi"
    targetId: "spec-ops-pipeline-b-reports"
    relationType: "documents"
    weight: 1.0
    description: "Governa la rendicontazione oraria, la firma grafometrica e lo scarico dal contratto"
  - targetTitle: "Pipeline C — Fatturazione SDI v1.2 & Scadenzario Multi-Rata"
    targetId: "spec-ops-pipeline-c-billing"
    relationType: "documents"
    weight: 1.0
    description: "Aggrega canoni, copie ed extra nel tracciato XML FPR12 e calcola rate 30/60 FM"
  - targetTitle: "Pipeline D — Task Jira & Schedulazione Agenda RFC 5545"
    targetId: "spec-ops-pipeline-d-jira-calendar"
    relationType: "documents"
    weight: 0.9
    description: "Sincronizza ticket Jira con file di calendario iCalendar standard"
  - targetTitle: "Pipeline E — Preventivazione Multiprodotto Cost-Plus"
    targetId: "spec-ops-pipeline-e-quotes"
    relationType: "documents"
    weight: 0.95
    description: "Compone offerte multiprodotto con ricarichi cost-plus ed esporta proposte formali"
  - targetTitle: "Pipeline F — Noleggio Multifunzione MPS & Telemetria SNMP"
    targetId: "spec-ops-pipeline-f-mps-rental"
    relationType: "documents"
    weight: 1.0
    description: "Gestisce contratti costo copia, conguagli copie ed interroga stampanti via SNMP UDP 161"
  - targetTitle: "Pipeline G — Commesse Arredo Ufficio & Collaudo Finale"
    targetId: "spec-ops-pipeline-g-furniture"
    relationType: "documents"
    weight: 0.95
    description: "Governa il ciclo di commessa arredo in 6 fasi fino al verbale di handover"
---

# 📚 Indice Master delle Pipeline Operative

Benvenuto nel compendio formale **OKF v0.2** di **`itinfra-business-ops`**.  
Questo documento censisce, mappa e relaziona le 7 pipeline di gestione operativa, commerciale, contabile e logistica.

---

## 🗺️ Mappa delle Relazioni delle Pipeline

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

    SLUG --> PA
    SLUG --> PF
    SLUG --> PG
    SLUG --> PE

    PD -->|Innesco Intervento| PB
    PB -->|Scarico Ore / Over-Budget| PA
    PA -->|Canoni & Ore Extra| PC
    PB -->|Interventi Spot & Ricambi| PC
    PF -->|Canoni Base & Conguaglio Copie| PC
    PG -->|Milestone SAL & Collaudo| PC
    PE -->|Accettazione Offerta| PA
    PE -->|Accettazione Offerta| PG
```

---

## 📑 Registro Documentale OKF v0.2

| Documento Specifico | ID Univoco OKF | Dominio Operativo | Schemi Formale Associato |
| :--- | :--- | :--- | :--- |
| [`01-pipeline-a-contracts.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/01-pipeline-a-contracts.md) | `spec-ops-pipeline-a-contracts` | Contratti SLA & Monte Ore | `contract.schema.yaml` |
| [`02-pipeline-b-reports.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/02-pipeline-b-reports.md) | `spec-ops-pipeline-b-reports` | Time-Tracking & Rapportini | `report.schema.yaml` |
| [`03-pipeline-c-billing.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/03-pipeline-c-billing.md) | `spec-ops-pipeline-c-billing` | Fatturazione SDI v1.2 | `billing.schema.yaml` |
| [`04-pipeline-d-jira-calendar.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/04-pipeline-d-jira-calendar.md) | `spec-ops-pipeline-d-jira-calendar` | Jira & Calendario RFC 5545 | `jira_sync.schema.yaml` |
| [`05-pipeline-e-quotes.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/05-pipeline-e-quotes.md) | `spec-ops-pipeline-e-quotes` | Preventivazione Multiprodotto | `quote.schema.yaml` |
| [`06-pipeline-f-mps-rental.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/06-pipeline-f-mps-rental.md) | `spec-ops-pipeline-f-mps-rental` | MPS, Costo Copia & SNMP | `mps.schema.yaml` |
| [`07-pipeline-g-furniture.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/pipelines/07-pipeline-g-furniture.md) | `spec-ops-pipeline-g-furniture` | Commesse Arredo & Collaudo | `furniture.schema.yaml` |
| [`../ASCII_DIAGRAMS.md`](file:///c:/Users/auresystem/repos/itinfra-business-ops/docs/ASCII_DIAGRAMS.md) | `spec-ops-ascii-diagrams` | Compendio Diagrammi ASCII Hub & Pipelines | N/A |
