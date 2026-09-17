---
okf_version: "0.2"
id: "spec-ops-pipeline-b-reports"
title: "Pipeline B — Rapportini di Assistenza, Time-Tracking & Firma"
type: "specification"
domain: "Business Operations & PSA"
tags: ["okf-v0.2", "pipeline-b", "reports", "time-tracking", "signature-pad", "spare-parts"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
lang: "it"

entities:
  - name: "Field Report Unique ID"
    type: "specification"
    description: "Codice progressivo deterministico RAP-YYYYMMDD-XXX per identificazione univoca intervento"
  - name: "Step Rounding Engine"
    type: "pattern"
    description: "Arrotondamento per eccesso a scatti predefiniti di 30 minuti del tempo netto"
  - name: "HTML5 Canvas Biometric Sign-off"
    type: "toolchain"
    description: "Pad interattivo web per cattura firma cliente su smartphone e tablet con resa print-ready"
  - name: "Spare Parts Consumption Tracking"
    type: "specification"
    description: "Registrazione materiali e componenti hardware utilizzati e immissione nel billing"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "implements"
    weight: 1.0
    description: "Componente di rendicontazione oraria del compendio operativo"
  - targetTitle: "Pipeline A — Contratti SLA, Monte Ore & Over-Budget"
    targetId: "spec-ops-pipeline-a-contracts"
    relationType: "depends_on"
    weight: 1.0
    description: "Scarica le ore lavorate dal monte ore del contratto attivo o segnala over-budget"
  - targetTitle: "Pipeline C — Fatturazione SDI v1.2 & Scadenzario Multi-Rata"
    targetId: "spec-ops-pipeline-c-billing"
    relationType: "depends_on"
    weight: 0.95
    description: "Trasmette interventi spot e ricambi fatturabili al batch contabile mensile"
---

# ⏱️ Pipeline B — Rapportini di Assistenza, Time-Tracking & Firma

## 1. Obiettivi e Ambito Operativo
La **Pipeline B** costituisce il cuore dell'operatività sul campo per i tecnici IT:
* Registrazione precisa dei timestamp di inizio (`clock_in`) e fine (`clock_out`) intervento.
* Arrotondamento deterministico secondo gli scatti contrattuali concordati (default: 30 min).
* Associazione degli apparati coinvolti (cross-check con seriali As-Built).
* Cattura immediata della firma del cliente su tablet o smartphone con emissione simultanea della scheda di lavoro in HTML/PDF.
* Scarico contestuale dal monte ore (Pipeline A) o flag per fatturazione separata (Pipeline C).

---

## 2. Diagramma di Flusso Esecutivo

```mermaid
flowchart TD
    IN["Inizio Intervento (clock_in)"]
    WORK["Esecuzione Lavori & Ricambi"]
    OUT["Fine Lavori (clock_out)"]
    CALC["Calcolo Netto Minuti & Arrotondamento (30 min)"]
    FORM{"Destinazione Amministrativa?"}
    CTR["debit_contract<br/>(Scarico da Monte Ore)"]
    SPOT["invoice_spot<br/>(Fatturazione Oraria Diretta)"]
    FLAT["included_flat<br/>(Incluso in Canone Forfait)"]
    PAD["Firma Cliente su Tablet<br/>(HTML5 Canvas Sign-off)"]
    GEN_HTML["Generazione Foglio di Lavoro<br/>(rap-YYYYMMDD-XXX.html)"]
    UPDATE_CTR["Update Fisico Contratto<br/>(consumed_hours += debited)"]

    IN --> WORK --> OUT --> CALC --> FORM
    FORM -->|A Contratto| CTR --> UPDATE_CTR --> PAD
    FORM -->|Spot a Tariffa| SPOT --> PAD
    FORM -->|Canone Flat| FLAT --> PAD
    PAD --> GEN_HTML
```

---

## 3. Regole Deterministiche di Calcolo

### 3.1 Arrotondamento Orario a Scatti di 30 Minuti
Dato $T_{in}$ (orario inizio), $T_{out}$ (orario fine) e pausa $P_{min}$:
$$\Delta_{min} = (T_{out} - T_{in}) - P_{min}$$
$$\text{Steps} = \left\lceil \frac{\Delta_{min}}{30} \right\rceil$$
$$H_{rounded} = \frac{\text{Steps} \times 30}{60} = \text{Steps} \times 0.5 \text{ ore}$$

*Esempio*: 
* Dalle 09:00 alle 10:10 ($\Delta = 70 \text{ min}$).
* $\text{Steps} = \lceil 70 / 30 \rceil = 3$.
* Ore addebitate: $3 \times 0.5 = 1.5 \text{ ore}$.

### 3.2 Distinzione Contabile (`ledger_action`)
* **`debit_contract`**: Consuma il saldo del contratto attivo; se esaurito, genera $extra\_hours$.
* **`invoice_spot`**: Genera una riga a tariffa standard (75 €/h) nel batch di fine mese.
* **`included_flat`**: Consuntiva le ore lavorate a scopo di controllo di gestione interno senza addebiti.

---

## 4. Schemi & Comandi CLI

* **Schema Formale**: `schemas/report.schema.yaml`
* **Percorso Storage**: `clients/<slug>/timesheets/rap-<YYYYMMDD>-<ID>.yaml` e `.html`

### Sintassi Comandi:
```powershell
# Creazione rapportino completo con ricambi e firma
.\it-ops.cmd report <slug> new `
  --tech "Mario Rossi" `
  --desc "Sostituzione switch di piano e ripristino VLAN" `
  --in "14:00" --out "15:45" `
  --action-type debit_contract `
  --assets "E4200891F7BC" `
  --parts "SW-24P:Switch 24P PoE:1:280.00" `
  --signed --signer "Marco Severino"

# Visualizzare il riepilogo delle ore dell'archivio rapportini
.\it-ops.cmd report <slug> balance
```
