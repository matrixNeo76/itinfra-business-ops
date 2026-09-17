# 🏢 itinfra-business-ops

> **Hub Operativo, Finanziario, Contrattualistica PSA e Commesse**  
> Progettato secondo il paradigma **Hub-and-Spoke** basato su **Shared Customer Slug (`<slug>`)**, in perfetta sinergia con il repository tecnico [`itinfra`](https://github.com/matrixNeo76/itinfra).

---

## 🎯 Visione Architetturale: Hub-and-Spoke & SoC

L'architettura separa rigorosamente il **Ground Truth Tecnico** dal **Ground Truth Operativo & Finanziario** (Separation of Concerns):

```mermaid
flowchart TD
    subgraph Hub ["🔗 Shared Customer Slug"]
        SLUG["cliente-rossi-srl"]
    end

    subgraph TechRepo ["⚙️ itinfra — Ground Truth Tecnico"]
        direction TB
        T1["01-RSD-URS.md"]
        T2["03-LLD.md"]
        T3["06-As-Built.md — Serials & Topology"]
        T4["manifest.yaml — IPAM & Inventory"]
    end

    subgraph OpsRepo ["💼 itinfra-business-ops — Ground Truth Operativo"]
        direction TB
        O1["Pipeline A: Contratti SLA & Monte Ore"]
        O2["Pipeline B: Rapportini Intervento"]
        O3["Pipeline C: Fatturazione & Scadenzario"]
        O4["Pipeline D: Schedulazione Jira"]
        O5["Pipeline E: Preventivazione"]
        O6["Pipeline F: Noleggio Multifunzione MPS"]
        O7["Pipeline G: Commesse Arredo Ufficio"]
    end

    SLUG -->|"Identità Tecnica"| T4
    SLUG -->|"Identità Operativa"| O1
    O1 -.->|"Cross-Check Asset As-Built"| T3
    O2 -.->|"Verifica Seriali Intervento"| T3
    O6 -.->|"Verifica Seriale Stampante"| T3
```

---

## 🚀 Le 7 Pipeline Operative

| Pipeline | Ambito | Descrizione & Output |
| :---: | :--- | :--- |
| **A** | **Contratti Assistenza IT (SLA & Monte Ore)** | Gestione canoni fissi MSP, monte ore a scalare, scadenze, alert rinnovo (`ctr-*.yaml`). |
| **B** | **Rapportini di Assistenza** | Compilazione intervento tecnico, tracciamento ore, arrotondamenti, firma e scarico saldo (`rap-*.yaml`). |
| **C** | **Fatturazione & Scadenzario Attivo** | Calcolo batch fine mese, conguagli, generazione tracciato SDI v1.2 e scadenzario partite aperte (`billing_batch.json`). |
| **D** | **Task Giornalieri Jira & Agenda** | Allineamento ticket Jira, sincronizzazione slot appuntamenti e pre-compilazione rapportini (`jira_sync.yaml`). |
| **E** | **Preventivazione Multiprodotto** | Calcolo cost-plus con ricarichi differenziati per Hardware, VoIP, Licenze e Arredo (`quote-*.yaml`). |
| **F** | **Noleggio Multifunzione MPS (Costo Copia)** | Gestione canoni semestrali anticipati, telelettura contatori SNMP, alert consumabili toner (<15%) e conguaglio eccedenze. |
| **G** | **Fornitura Arredo Ufficio** | Gestione commessa chiavi in mano: rilievo metrico, layout 2D/3D, campionatura, posa e verbale di collaudo con handover. |

---

## 🛠️ Comandi Rapidi CLI (`it-ops`)

La suite include il wrapper Windows [`it-ops.cmd`](file:///c:/Users/auresystem/repos/itinfra-business-ops/it-ops.cmd) per esecuzione diretta da Prompt/PowerShell:

```powershell
# Inizializzare un nuovo cliente con la struttura completa
.\it-ops.cmd init <slug> --client "Nome Ragione Sociale"

# Verificare lo stato operativo 360° del cliente
.\it-ops.cmd status <slug>

# Cross-check deterministico con l'As-Built di itinfra
.\it-ops.cmd check <slug>

# Gestione Contratti SLA e Monte Ore
.\it-ops.cmd contract <slug> status
.\it-ops.cmd contract <slug> balance

# Rapportini di Assistenza e Time Tracking
.\it-ops.cmd report <slug> new
.\it-ops.cmd report <slug> list

# Calcolo Noleggio e Telelettura Stampanti MPS
.\it-ops.cmd mps <slug> calculate

# Calcolo Batch Fatturazione e Scadenzario
.\it-ops.cmd billing <slug> summary

# Commesse Arredo Ufficio
.\it-ops.cmd furniture <slug> status
```

---

## 📑 Documentazione Formale OKF v0.2 delle Pipeline Operative

Ciascuna pipeline è documentata con specifiche formali conformi allo standard **Open Knowledge Framework (OKF) v0.2**:

| Pipeline | Titolo Specifica OKF v0.2 | Documento |
| :---: | :--- | :--- |
| **📚 Master** | **Indice Master delle Pipeline Operative** | [`00-index-pipelines.md`](docs/pipelines/00-index-pipelines.md) |
| **A** | Contratti di Assistenza IT, SLA & Monte Ore | [`01-pipeline-a-contracts.md`](docs/pipelines/01-pipeline-a-contracts.md) |
| **B** | Rapportini Intervento, Firma Canvas & Ricambi | [`02-pipeline-b-reports.md`](docs/pipelines/02-pipeline-b-reports.md) |
| **C** | Fatturazione SDI v1.2 & Scadenzario Multi-Rata | [`03-pipeline-c-billing.md`](docs/pipelines/03-pipeline-c-billing.md) |
| **D** | Task Jira & Schedulazione Agenda RFC 5545 | [`04-pipeline-d-jira-calendar.md`](docs/pipelines/04-pipeline-d-jira-calendar.md) |
| **E** | Preventivazione Multiprodotto Cost-Plus | [`05-pipeline-e-quotes.md`](docs/pipelines/05-pipeline-e-quotes.md) |
| **F** | Noleggio Multifunzione MPS & Telemetria SNMP | [`06-pipeline-f-mps-rental.md`](docs/pipelines/06-pipeline-f-mps-rental.md) |
| **G** | Commesse Arredo Ufficio & Collaudo Finale | [`07-pipeline-g-furniture.md`](docs/pipelines/07-pipeline-g-furniture.md) |
| **📐 Visual** | **Compendio Diagrammi ASCII (Hub & Pipelines)** | [`docs/ASCII_DIAGRAMS.md`](docs/ASCII_DIAGRAMS.md) |

---

## 📁 Struttura del Repository

```text
itinfra-business-ops/
├── .gitignore
├── config.yaml                # Parametri globali, IVA, valuta e path itinfra
├── it-ops.cmd                 # Entrypoint batch per Windows
├── README.md                  # Questo documento
├── AGENTS.md                  # Istruzioni operative e comandi deterministici per AI
├── CLAUDE.md                  # Zero-search fast path per Claude Code
├── schemas/                   # Schemi formali YAML per validazione deterministica
│   ├── client-manifest.schema.yaml
│   ├── contract.schema.yaml
│   ├── report.schema.yaml
│   ├── billing.schema.yaml
│   ├── jira_sync.schema.yaml
│   ├── quote.schema.yaml
│   ├── mps.schema.yaml
│   └── furniture.schema.yaml
├── templates/                 # Modelli YAML pronti per scaffolding
├── scripts/                   # Motore Python CLI
│   ├── it_ops.py              # CLI Dispatcher
│   ├── core/                  # Config, Validator, Bridge verso itinfra
│   └── pipelines/             # Moduli dedicati alle pipeline A-G
├── docs/                      # Specifiche e guide operative di processo
└── clients/                   # Repository clienti partizionati per <slug>
```

---

## 🔒 Sicurezza & Riservatezza
* **Read-Only Bridge**: L'accesso ai dati di [`itinfra`](file:///c:/Users/auresystem/repos/itinfra) avviene rigorosamente in sola lettura, garantendo l'integrità dei documenti tecnici.
* **Separazione Dati Sensibili**: Fatture, canoni e coordinate bancarie risiedono esclusivamente in questo repository protetto da policy RBAC dedicate.
