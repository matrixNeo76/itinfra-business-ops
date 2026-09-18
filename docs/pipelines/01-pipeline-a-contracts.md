---
okf_version: "0.2"
id: "spec-ops-pipeline-a-contracts"
title: "Pipeline A — Contratti di Assistenza IT, SLA & Monte Ore"
type: "specification"
domain: "Business Operations & PSA"
tags: ["okf-v0.2", "pipeline-a", "contracts", "sla", "hours-bank", "over-budget"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
lang: "it"

entities:
  - name: "SLA Tiers & Service Windows"
    type: "specification"
    description: "Finestre di copertura (es. 08:30-18:30 Lun-Ven) e tempi di prima risposta/risoluzione (Critical, High, Standard)"
  - name: "Hours Bank Ledger Engine"
    type: "pattern"
    description: "Motore di decremento deterministico delle ore consumate con allarme consumo 80%"
  - name: "Over-Budget Automatic Router"
    type: "pattern"
    description: "Algoritmo di scorporo automatico tra ore a canone e ore extra-soglia con tariffazione separata"
  - name: "As-Built Equipment Boundary"
    type: "concept"
    description: "Perimetro degli apparati hardware coperti da garanzia incrociato con 06-As-Built.md di itinfra"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "implements"
    weight: 1.0
    description: "Componente contrattuale del compendio operativo"
  - targetTitle: "Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi"
    targetId: "spec-ops-pipeline-b-reports"
    relationType: "depends_on"
    weight: 0.95
    description: "I rapportini consumano il monte ore del contratto attivo tramite ledger_action"
  - targetTitle: "Pipeline C — Fatturazione SDI v1.2 & Scadenzario Multi-Rata"
    targetId: "spec-ops-pipeline-c-billing"
    relationType: "depends_on"
    weight: 1.0
    description: "Invia canoni ricorsivi e ore extra-soglia al motore di fatturazione mensile"
---

# 📑 Pipeline A — Contratti di Assistenza IT, SLA & Monte Ore

## 1. Obiettivi e Ambito Operativo
La **Pipeline A** governa il ciclo di vita dei contratti di assistenza tecnica, traducendo gli accordi commerciali cartacei in vincoli operativi deterministici per tecnici, helpdesk e contabilità:
* Gestione di formule a **Monte Ore a scalare** (`hours_bank`), **Canone Flat MSP** (`msp_flat`) o **Ibride**.
* Garanzia dei livelli di servizio **SLA** differenziati per gravità del guasto.
* Protezione del perimetro apparati tramite cross-check con il repository tecnico [`itinfra`](https://github.com/matrixNeo76/itinfra).
* Prevenzione del mancato fatturato tramite gestione automatica dell'**over-budget**.

---

## 2. Diagramma di Flusso Esecutivo

```mermaid
flowchart TD
    DRAFT["1. Stipula & Drafting<br/>(ctr-draft.yaml)"]
    SIGN["2. Firma Digitale Cliente<br/>(Archiviazione PDF SHA-256)"]
    ACTIVE["3. Attivazione Contratto<br/>(status: active)"]
    MONITOR["4. Monitoraggio & Interventi<br/>(Consumo Monte Ore)"]
    CHECK_HOURS{"Saldo Residuo >= Ore Intervento?"}
    DEBIT_FULL["Scarico Totale a Canone<br/>(consumed_hours += h)"]
    SPLIT_OVER["Scorporo Over-Budget<br/>(Saldo = 0.0, Extra = h - res)"]
    INVOICE_EXTRA["Invio a Pipeline C<br/>(Fatturazione @ extra_hourly_rate)"]
    RENEWAL_ALERT{"Scadenza <= 60 gg o Monte Ore >= 80%?"}
    NOTIFY["Alert Notifica Rinnovo"]
    RENEW_CMD["5. Rinnovo Contratto<br/>(it-ops contract renew)"]

    DRAFT --> SIGN --> ACTIVE --> MONITOR --> CHECK_HOURS
    CHECK_HOURS -->|Sì| DEBIT_FULL
    CHECK_HOURS -->|No| SPLIT_OVER --> INVOICE_EXTRA
    DEBIT_FULL --> RENEWAL_ALERT
    SPLIT_OVER --> RENEWAL_ALERT
    RENEWAL_ALERT -->|Sì| NOTIFY --> RENEW_CMD
```

---

## 3. Regole Deterministiche di Business

### 3.1 Livelli di Servizio (SLA)
| Tier SLA | Prima Risposta (Presa in Carico) | Risoluzione Obiettivo | Finestra Oraria | Esempi di Guasto |
| :--- | :---: | :---: | :--- | :--- |
| **Critical** | $\le$ 2 ore | $\le$ 4 ore | H24 / Lun-Dom | Fermo totale host Hyper-V, blocco firewall perimetrale |
| **High** | $\le$ 4 ore | $\le$ 8 ore | 08:30-18:30 Lun-Ven | Degrado performance server, guasto switch secondario |
| **Standard** | $\le$ 8 ore | $\le$ 24 ore | 08:30-18:30 Lun-Ven | Configurazione nuova postazione, richiesta credenziali |

### 3.2 Algoritmo di Gestione Over-Budget
Dato un monte ore totale $H_{tot}$, ore già consumate $H_{cons}$, e un nuovo intervento di durata $h_{int}$:
1. Calcolo ore residue: $H_{res} = \max(0, H_{tot} - H_{cons})$.
2. Se $h_{int} \le H_{res}$:
   $$H_{cons}^{new} = H_{cons} + h_{int}, \quad h_{extra} = 0$$
3. Se $h_{int} > H_{res}$:
   $$H_{cons}^{new} = H_{tot}, \quad h_{extra} = h_{int} - H_{res}$$
   La quantità $h_{extra}$ viene memorizzata sia nel rapportino sia nel contratto e addebitata nella fattura mensile successiva al costo di $extra\_hourly\_rate$ (default: 80 €/h).

---

## 4. Schemi & Comandi CLI

* **Schema Formale**: `schemas/contract.schema.yaml`
* **Percorso Storage**: `clients/<slug>/contracts/ctr-<slug>-<anno>.yaml`

### Sintassi Comandi:
```powershell
# Verifica stato e saldo ore contratto attivo
.\it-ops.cmd contract <slug> status

# Cross-check con l'As-Built in itinfra
.\it-ops.cmd check <slug>

# Generare la bozza di rinnovo per l'anno successivo
.\it-ops.cmd contract <slug> renew --contract-id CTR-2026-SEVERINO
```


---

## 5. Sorveglianza Continua Scadenze & Rinnovi (SPEC-21, SPEC-24)

In aderenza alle specifiche **SPEC-21** e **SPEC-24**:
- **Demone di Sorveglianza Contrattuale (`CreditDaemon`)**: Monitora costantemente la data di scadenza (`end_date`) dei contratti attivi emettendo alert a **60 giorni** (avvio trattativa revisione tariffe) e a **30 giorni** (termine per eventuale disdetta a norma delle condizioni generali di contratto).
- **Workflow a Stati Finiti `contract-renewal`**: Avvia la procedura FSM guidata in 4 step per la revisione del canone, aggiornamento monte ore, redazione nuova appendice contrattuale e archiviazione del contratto precedente.
- **Trigger Proattivo `contract.renewal.*`**: Inoltra la proposta di rinnovo al **Safe Action Gate** (SPEC-22) richiedendo l'autorizzazione dell'amministrazione prima di apportare modifiche all'anagrafica cliente.
