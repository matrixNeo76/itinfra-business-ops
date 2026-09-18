---
okf_version: "0.2"
id: "spec-ops-pipeline-k-onboard"
title: "Pipeline K — Unified Client Onboarding Orchestrator (Zero-Drift Dual Storage)"
type: "specification"
domain: "Business Operations & Automation"
tags: ["okf-v0.2", "pipeline-k", "onboarding", "hub-and-spoke", "zero-drift", "automation"]
project_id: "itinfra-business-ops"
phase: 2
status: "approved"
version: "1.0"
created_at: "2026-09-18"
updated_at: "2026-09-18"
lang: "it"

entities:
  - name: "OnboardPipeline"
    type: "orchestrator"
    description: "Motore deterministico per onboarding unificato cross-repository tra business ops e infrastruttura tecnica"
  - name: "Shared Customer Slug"
    type: "identifier"
    description: "Chiave primaria comune che garantisce la corrispondenza 1:1 tra workspace commerciale e ingegneristico"
  - name: "Zero-Drift Certification"
    type: "governance"
    description: "Verifica automatica dell'integrita schemi e consistenza cross-repo al momento della creazione"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "partOf"
    weight: 1.0
  - targetTitle: "SPEC-20: Mission Control, Bounded Deterministic Swarm & Continuous Assurance"
    targetId: "spec-ops-20-mission-control-swarm-assurance"
    relationType: "satisfies"
    weight: 1.0
---

# Pipeline K — Unified Client Onboarding Orchestrator

> **Identificativo**: `Pipeline 11` / `Pipeline K`  
> **Comando CLI**: `.\it-ops.cmd onboard <slug> --client "Nome" --vat "IT..." [--subnet "192.168.X.0/24"] [--tier silver|gold|platinum]`  
> **Engine di Riferimento**: `scripts/pipelines/onboard.py` (`OnboardPipeline`).  
> **Brand & Titolarità**: **Aure System di Eduardo Possumato**  

---

## 1. Visione & Obiettivi

Prima dell'introduzione della Pipeline K, l'acquisizione di un nuovo cliente richiedeva due operazioni distinte:
1. Inizializzazione della parte commerciale in `itinfra-business-ops` (`it-ops init <slug>`).
2. Creazione manuale o guidata della cartella di progetto ingegneristico in `itinfra/projects/<slug>`.

Questa separazione manuale esponeva al rischio di drift (discrepanze di naming, subnet IP non allineate, P.IVA o referenti discordanti).  
La **Pipeline K** risolve alla radice il problema eseguendo una **creazione atomica e federata**, garantendo al contempo la rigorosa **Separation of Concerns (SoC)**.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│          PIPELINE K: UNIFIED CLIENT ONBOARDING (DUAL-STORAGE ZERO-DRIFT)      │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
        [1. Acquisizione Parametri & Selezione Profilo di Servizio]
                                        ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ • Slug: es. "cliente-rossi-srl"                               │
        │ • Ragione Sociale, P.IVA/CF, Codice SDI, PEC, Referente       │
        │ • Livello di Servizio: Silver (20h) | Gold (50h) | Plat (100h)│
        │ • Subnet Primaria: es. "192.168.10.0/24" (Gateway, IPAM Pool) │
        └───────────────────────────────┬───────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌────────────────────────────────────────┐ ┌────────────────────────────────────────┐
│  Workspace itinfra-business-ops        │ │  Workspace itinfra (Tecnico)           │
│  clients/<slug>/                       │ │  projects/<slug>/                      │
├────────────────────────────────────────┤ ├────────────────────────────────────────┤
│ • client-manifest.yaml                 │ │ • manifest.yaml (Sincronizzato)        │
│ • contracts/ctr-<slug>-2026.yaml (SLA) │ │ • 01-Executive-Summary.md              │
│ • quotes/quote-<slug>-01.yaml (Audit)  │ │ • 02-Physical-Site-Survey.md           │
│ • mps/mps-<slug>-01.yaml (Base)        │ │ • 03-Logical-Network-Architecture.md   │
│ • timesheets/, invoices/, furniture/   │ │ • 04-Network-IPAM.md (Subnet calcolata)│
│ • gap_analysis/ga-<slug>-01.yaml (231) │ │ • 05-Disaster-Recovery-Plan.md         │
│                                        │ │ • 06-As-Built.md (Baseline apparati)   │
└────────────────────────────────────────┘ └────────────────────────────────────────┘
             │                                                     │
             └──────────────────────────┬──────────────────────────┘
                                        │
                      [3. Cross-Check Bridge Immediato]
                                        ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ • ITInfraBridge.check_slug(slug)                              │
        │ • Validazione Schemi Formali YAML                             │
        │ • Certificazione Zero-Drift & Hash SHA-256                    │
        └───────────────────────────────────────────────────────────────┘
```

---

## 2. Profili di Servizio (Service Tiers)

Il parametro `--tier` configura deterministicamente le metriche contrattuali SLA di partenza:

| Parametro | Tier Silver | Tier Gold *(Default)* | Tier Platinum |
| :--- | :---: | :---: | :---: |
| **Monte Ore Annuale** | **20 ore** | **50 ore** | **100 ore** |
| **Tariffa Oraria Base** | € 75,00/h | € 70,00/h | € 65,00/h |
| **Canone SLA Periodico** | € 1.500/anno | € 3.500/anno | € 6.500/anno |
| **SLA Presa in Carico** | Entro 8 ore | Entro 4 ore | Entro 2 ore |
| **Reperibilità On-Site** | Next Business Day | Entro 4 ore lav. | Entro 2 ore (24/7 opt) |
| **Copie MPS Incluse/mese**| 1.000 BN / 200 Colore | 2.500 BN / 500 Colore | 5.000 BN / 1.500 Colore|

---

## 3. Generazione IPAM Deterministica in `itinfra`

Se specificata la subnet primaria (es. `192.168.20.0/24`), la Pipeline K calcola e popola automaticamente `04-Network-IPAM.md` e `06-As-Built.md`:
- **Default Gateway**: `192.168.20.1`
- **DNS Primario / Secondario**: `192.168.20.2` (DC01) / `1.1.1.1`
- **Range DHCP Client**: `192.168.20.100` - `192.168.20.250`
- **Pool Server & Apparati Critici**: `192.168.20.2` - `192.168.20.50`
- **Pool Stampanti di Rete MPS**: `192.168.20.51` - `192.168.20.70`

---

## 4. Sintassi CLI & Opzioni

```powershell
# Onboarding con profilo predefinito Gold
.\it-ops.cmd onboard acme-corp --client "ACME Corporation S.r.l." --vat "IT01234567890"

# Onboarding completo con parametri di rete e tier Platinum
.\it-ops.cmd onboard studio-legale-rossi `
  --client "Studio Legale Rossi & Associati" `
  --vat "IT98765432109" `
  --sdi "M5UXCR1" `
  --pec "studio.rossi@pec.it" `
  --subnet "192.168.50.0/24" `
  --tier platinum `
  --contact-name "Avv. Mario Rossi" `
  --contact-email "mario.rossi@studiorossi.it"
```
