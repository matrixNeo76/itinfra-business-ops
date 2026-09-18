---
type: "concept"
title: "SPEC-25: Generative UI, Mission Control Cockpit & Dual-Repo Interactive Architecture"
description: "Specifica architetturale e guida di sviluppo per l'interfaccia generativa unificata (Aure System Enterprise Cockpit 360°), allineamento completo con SPEC-18..SPEC-24, Safe Action Gate, FSM Workflows, Crediti 231, Zero-CDN e linee guida di evoluzione."
generated.at: "2026-09-18T23:10:00+02:00"
sources:
  - "file://scripts/pipelines/mission_control.py"
  - "file://scripts/itinfra_ui.py"
  - "file://docs/specs/20-spec-mission-control-and-autonomous-swarm.okf.md"
  - "file://docs/specs/21-spec-workflow-orchestration-and-lifecycle-assurance.okf.md"
  - "file://docs/specs/22-spec-event-driven-trigger-system-and-action-gate.okf.md"
  - "file://docs/specs/24-spec-italian-compliance-and-high-return-extensions.okf.md"
tags:
  - "generative-ui"
  - "mission-control"
  - "zero-cdn"
  - "safe-action-gate"
  - "fsm-workflows"
  - "italian-compliance"
  - "spec-25"
---

# SPEC-25: Generative UI, Mission Control Cockpit & Dual-Repo Interactive Architecture

**Identificativo Specifica:** `SPEC-25`  
**Stato:** `APPROVED & IMPLEMENTED`  
**Autore:** Aure System di Eduardo Possumato  
**Data di Rilascio:** 18 Settembre 2026  
**Repository Coinvolti:** `itinfra-business-ops` & `itinfra`  

---

## 1. Visione & Obiettivi Architetturali

Negli ultimi sviluppi dell'ecosistema unificato Aure System sono state implementate specifiche ad alta complessità che hanno trasformato la piattaforma da un insieme di script lineari a un **motore cognitivo deterministico a stati finiti (FSM), a eventi e con presidio normativo italiano**:
- **SPEC-20**: Continuous Assurance Pipeline, Swarm Agenti Deterministici e Demoni di Background;
- **SPEC-21**: Orchestratore FSM a Checkpoint e Resume Idempotente;
- **SPEC-22**: Event-Driven Trigger System e Safe Action Gate Human-in-the-Loop;
- **SPEC-23**: Tassonomia Integrata dei 10 Concetti Deterministici Hub-and-Spoke;
- **SPEC-24**: Presidio Italiano Fiscale (P.IVA, CF, SDI), Recupero Crediti D.Lgs. 231/2002 con Lettere Graduate, CCNL Incident-to-Report Bridge e Workflow Tecnici (`dr-drill`, `firmware-upgrade`, `hardware-decommissioning-raee`).

La precedente interfaccia utente generativa era tuttavia rimasta disallineata rispetto a questo volume di innovazioni. **SPEC-25 formalizza la completa riprogettazione della Generative UI**, definendo l'architettura dell'**Aure System Enterprise Cockpit 360°**, il modello di data injection disaccoppiato e la guida metodologica per mantenere sempre allineata la UI nei futuri cicli evolutivi.

---

## 2. Punti Chiave & Invarianti Architetturali

1. **Invariante Zero-CDN Strict (100% Offline-First)**:
   - Qualsiasi artefatto generato (`docs/mission-control.html` in Business Ops, `projects/enterprise_dashboard.html` in itinfra) deve funzionare integralmente **senza connessione internet**.
   - CSS e icone SVG sono interamente vettoriali e incorporati nel payload HTML. Nessun foglio di stile o font esterno può bloccare o degradare il rendering.
2. **Data Injection Model (Decoupled JSON Data Store)**:
   - La raccolta dati lato Python e la presentazione visiva sono rigorosamente disaccoppiate.
   - Il pipeline Python serializza il dizionario globale di stato in un blocco `<script id="dashboard-data" type="application/json">`.
   - Il client JavaScript esegue il parsing all'avvio (`DOMContentLoaded`) e alimenta dinamicamente tutti i tab, filtri, calcolatori live e modali senza necessità di ricaricare la pagina o effettuare chiamate server.
3. **Dual-Mode Antigravity Integration**:
   - L'interfaccia opera sia come **Standalone Executive Dashboard** nel browser (lanciata via `.\it-ops.cmd ui` o `.\it.cmd ui`), sia come **Interactive Generative UI Widget** incorporato nella chat di Google Antigravity tramite il tag:
     ```html
     <agent-embed src="file:///<artifact_dir>/mission-control.html"></agent-embed>
     ```
4. **Deterministic Click-to-Copy CLI Gateway**:
   - Ogni azione visiva (approvazione trigger, lancio workflow, ripresa checkpoint, diffida legale) espone un pulsante interattivo che copia negli appunti dell'operatore il comando esatto per PowerShell/CMD, garantendo il pieno controllo Human-in-the-Loop.

---

## 3. Gli 8 Moduli Operativi del Cockpit Unificato

L'interfaccia unificata organizza l'intero patrimonio operativo, contrattuale e sistemistico in **8 schede (tab) tematiche reattive**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AURE SYSTEM ENTERPRISE COCKPIT 360°                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [Top Ribbon] SLA Ore: 280.5h | Crediti 231: €1.0k | Parco MPS: 4 | 231%: 65.9% | Gate: 22│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [Tabs] 1. Panoramica | 2. Action Gate | 3. FSM Workflows | 4. Crediti 231 | 5. CCNL/IT│
│        6. Scheda Cliente 360° | 7. Swarm & Demoni | 8. Hub itinfra & RAEE              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Modulo 1: Panoramica 360° & Matrice Clienti
- **Filtri Istantanei**: pulsanti di filtro rapido per isolare clienti con `sla_alert`, `toner_alert`, `overdue` (insoluti) o `gap_231`.
- **Barra di Ricerca Live**: filtro testuale full-text per ragione sociale, slug o tier contrattuale.
- **Tabella di Monitoraggio**: stato monografico con badge a semaforo per SLA, contabilità, multifunzione, 231 e bridge `itinfra`.

### Modulo 2: Safe Action Gate (SPEC-22)
- **Coda Approvazioni Human-in-the-Loop**: mostra le azioni in attesa originate dai trigger proattivi (`ACT-SLA-REORDER`, `ACT-MPS-ORDER`, `ACT-DEBT-REMINDER`, `ACT-INCIDENT-REPORT`).
- **Ispezione Payload**: elemento `<details>` con rendering formattato dei parametri tecnici o contrattuali.
- **Pulsanti 1-Click**:
  - `Approva`: copia `.\it-ops.cmd triggers approve <id>`.
  - `Rifiuta`: copia `.\it-ops.cmd triggers reject <id> --reason "..."`.

### Modulo 3: Workflows FSM Studio (SPEC-21, SPEC-24)
- **Visual Stepper**: nodi a tappe con indicatore SVG di stato (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
- **Resilience & Resume**: per i workflow interrotti, visualizza il pulsante `Riprendi (Resume)` che genera `.\it-ops.cmd workflow resume <id>`.
- **Catalogo Workflow**: card descrittive per i 5 workflow di business e i 3 workflow tecnici con numero di tappe e comando di lancio.

### Modulo 4: Scadenzario Attivo & Recupero Crediti D.Lgs. 231/2002 (SPEC-24)
- **Matrice di Aging**: ripartizione crediti scaduti su 4 colonne (0-30 giorni, 31-60 giorni, 61-90 giorni, 90+ giorni).
- **Ticker Interessi di Mora**: calcolo automatico al tasso legale vigente del **11.50% annuo** (BCE 3.50% + spread legale 8.00%) pro-die ex Art. 5 D.Lgs. 231/2002.
- **Generatore Lettere di Sollecito**: modale grafico con anteprima del testo formale a 3 stadi (Stadio 1 Bonario, Stadio 2 Mora formale, Stadio 3 Intimazione legale ex Art. 1454 c.c. con addebito €40 forfettari ex Art. 6).

### Modulo 5: Presidio Normativo Italiano & CCNL Lavoro (SPEC-24)
- **Validatore Live Fisco Italiano**: collaudo in tempo reale di Partita IVA (algoritmo di Luhn e uffici 001-121), Codice Fiscale (omocodia DM 23/12/1976) e Codice SDI/IPA.
- **Simulatore CCNL Incident-to-Report**: selettore orario clock-in/out, calcolo automatico scatti di 30 minuti e applicazione dei moltiplicatori contrattuali (+20% notturno, +50% festivo, +75% notturno festivo) con conteggio delle ore scalate dallo SLA.

### Modulo 6: Scheda Monografica Cliente 360° (Deep Drill-Down)
- **Selettore a Pills Orizzontale**: switch dinamico istantaneo tra i clienti censiti.
- **4 Box Informativi**:
  1. *SLA Hours Bank*: barra di avanzamento del monte ore residuo con allarme rosso sotto il 20%.
  2. *Finanza & Insoluti*: dettaglio crediti aperti e mora maturata.
  3. *Parco MPS*: barre grafiche dei 4 toner (BK, C, M, Y) per ciascuna stampante del cliente.
  4. *Conformità 231 & As-Built*: score di maturità, vulnerabilità aperte e stato di allineamento con `06-As-Built.md`.

### Modulo 7: Swarm Agenti & Demoni Proattivi (SPEC-20)
- **Swarm Agenti**: stato e comando di lancio rapido per `audit-231`, `finance-reconciler`, `infrastructure-sentinel`, `contract-guardian`.
- **Demoni di Background**: frequenza e soglie di intervento per `MPSDaemon`, `SLADaemon` e `CreditDaemon`.

### Modulo 8: Hub Tecnico itinfra & Ciclo RAEE (SPEC-24)
- **Monitor Disaster Recovery**: esito dell'esercitazione `dr-drill` e conformità RTO/RPO ex Art. 32 GDPR.
- **Rollout Firmware Canary**: gestione delle modifiche sicure con auto-revert safe-mode.
- **Registro Smaltimento RAEE**: tracciabilità sanificazione dischi NIST SP 800-88 e formulario FIR RAEE.
- **Link Bidirezionale**: pulsante per aprire direttamente `enterprise_dashboard.html` di `itinfra`.

---

## 4. Allineamento del Cockpit Tecnico in `itinfra` (`scripts/itinfra_ui.py`)

Nel repository tecnico `itinfra`, il modulo `itinfra_ui.py` è stato allineato per riflettere le stesse convenzioni architetturali:
1. **Nuova Tab "Workflow Tecnici" (SPEC-24)**: permette all'amministratore di sistema di lanciare ed esaminare i comandi di `dr-drill`, `firmware-upgrade` e `hardware-decommissioning-raee`.
2. **Azioni Rapide Estese**: integrati pulsanti diretti per richiamare `it-ops ui` e `it-ops triggers pending`.
3. **Offline-First Styling**: stili CSS inline completi che garantiscono la visualizzazione anche qualora lo script remoto di Tailwind non sia raggiungibile.
4. **Publishing Atomico verso Antigravity**: sia `it.py ui` che `it_ops.py ui` copiano automaticamente l'artefatto nella cartella sessione `.gemini/antigravity/brain/<id>/` ed emettono il tag `<agent-embed>` per l'inclusione istantanea in chat.

---

## 5. Guida di Manutenzione & Linee Guida di Evoluzione Futura

Per garantire che la Generative UI rimanga costantemente allineata alle future evoluzioni dei due repository, gli sviluppatori e gli agenti AI devono attenersi alle seguenti direttive:

### Come Aggiungere una Nuova Metrica a un Cliente
1. Aprire `scripts/pipelines/mission_control.py`.
2. All'interno del metodo `collect_client_metrics(slug)`, aggiungere il codice di estrazione deterministica dal relativo file YAML del cliente (in `clients/<slug>/`).
3. Inserire la metrica nel dizionario restituito.
4. Nel template HTML/JS (`selectClient()`), inserire il rendering visivo leggendo la proprietà dal record `c.<nuova_metrica>`.

### Come Aggiungere un Nuovo Workflow al Catalogo
1. Definire il workflow in `scripts/pipelines/workflow_definitions.py` (`WorkflowRegistry.get_definitions()`).
2. Il metodo `collect_all()` di `mission_control.py` importerà e mapperà automaticamente il nuovo workflow nel catalogo della UI senza richiedere modifiche al codice HTML.

### Come Aggiungere una Nuova Tipologia di Trigger all'Action Gate
1. Registrare l'evento nel `TriggerEngine` (`scripts/core/trigger_engine.py`).
2. Quando l'azione viene emessa in `pending_actions.json`, la funzione JS `renderActionGate()` visualizzerà automaticamente la nuova card con payload e pulsanti di approvazione.

---

## 6. Verifica & Certificazione di Qualità

L'allineamento della Generative UI è stato certificato con esito **100% PASS**:
- **Test Suite `itinfra-business-ops`**: 77 unit test passati (`Ran 77 tests in 7.3s, OK`).
- **Test Suite `itinfra`**: 16 moduli enterprise passati (`16/16 Moduli Superati, 100.0%`).
- **Git Guard Hooks**: validazione pre-commit superata senza secret leak né errori di schema.
- **Generazione Artefatti**:
  - `itinfra-business-ops/docs/mission-control.html` generato regolarmente.
  - `itinfra/projects/enterprise_dashboard.html` generato regolarmente.
  - Copia sincronizzata nella directory Brain Artifact di Antigravity con supporto `<agent-embed>`.
