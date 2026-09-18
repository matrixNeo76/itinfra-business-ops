# AGENTS.md — Direttive di Sistema per Assistenti AI

> Questo file definisce le istruzioni operative per agenti AI che operano all'interno del repository **`itinfra-business-ops`**.

---

## ⚡ 0. REGOLA FONDAMENTALE: ZERO-SEARCH FAST-PATH & COMANDI DETERMINISTICI

Se l'utente ti saluta (`ciao`, `buongiorno`), ti chiede **cosa fa questo applicativo**, **quali comandi sono disponibili**, o come usare ITInfra Business Ops:
❌ **È SEVERAMENTE VIETATO usare tool di ricerca file casuali (`Glob`, `Grep`, `LS`).** Tu conosci già perfettamente questo applicativo.
✅ **Rispondi ALL'ISTANTE (0 secondi) e in modo DETERMINISTICO** presentando la Scheda Operativa ITInfra Business Ops qui sotto.

### 📋 Scheda Operativa di Risposta Immediata

👋 **Benvenuto in ITInfra Business Ops!**  
Questo è l'ambiente di lavoro per la governance operativa, commerciale, PSA, fatturazione, gestione contratti SLA, noleggio multifunzione (MPS) e commesse arredo ufficio, integrato con **`itinfra`** tramite Shared Customer Slug (`<slug>`).

### 🚀 Comandi Rapidi Disponibili

| Azione Desiderata | Da Chat (Scrivi semplicemente) | Da Terminale (Prompt / PowerShell) |
| :--- | :--- | :--- |
| **Inizializza Nuovo Cliente** | `init <slug>` | `.\it-ops.cmd init <slug> --client "Nome"` |
| **Scheda Stato 360° Cliente** | `stato <slug>` *(o `status`)* | `.\it-ops.cmd status <slug>` |
| **Cross-Check con itinfra (As-Built)** | `check <slug>` | `.\it-ops.cmd check <slug>` |
| **Verifica Saldo Monte Ore / SLA** | `contratto <slug>` *(o `contract`)* | `.\it-ops.cmd contract <slug> balance` |
| **Nuovo Rapportino Intervento** | `rapportino <slug>` *(o `report`)* | `.\it-ops.cmd report <slug> new` |
| **Calcolo Telelettura MPS Copie** | `mps <slug>` | `.\it-ops.cmd mps <slug> calculate` |
| **Riepilogo Batch Fatturazione** | `fatturazione <slug>` *(o `billing`)* | `.\it-ops.cmd billing <slug> summary` |
| **Stato Avanzamento Arredo** | `arredo <slug>` *(o `furniture`)* | `.\it-ops.cmd furniture <slug> status` |
| **Calcolo Margini Preventivo** | `preventivo <slug>` *(o `quote`)* | `.\it-ops.cmd quote <slug> calculate` |
| **Ingestione Documenti (OKF v0.2)** | `ingest <file>` | `.\it-ops.cmd ingest <file> [--slug <slug>] [--apply]` |
| **Memoria Auto-Correttiva (OKF v0.2)** | `learn [sync\|audit\|test]` | `.\it-ops.cmd learn [list\|sync\|audit\|test]` |
| **Gap Analysis & Compliance 231** | `gap <slug>` | `.\it-ops.cmd gap <slug> [status\|calculate\|report\|check]` |
| **Onboarding Unificato (Pipeline 11)** | `onboard <slug>` | `.\it-ops.cmd onboard <slug> --client "Nome" [--tier gold]` |
| **Mission Control & Dashboard 360°** | `mission-control` *(o `mc`, `ui`)* | `.\it-ops.cmd mission-control [--html]` |
| **Swarm Agenti Deterministici** | `agent <type> <slug>` | `.\it-ops.cmd agent [audit-231\|finance-reconciler\|infrastructure-sentinel\|contract-guardian\|swarm] <slug>` |
| **Demoni di Monitoraggio Proattivo** | `daemon [mps\|sla]` | `.\it-ops.cmd daemon [mps\|sla] [--once]` |
| **Git Guard Hooks Deterministici** | `hooks [install\|check]` | `.\it-ops.cmd hooks [install\|check] [--both]` |

---

## 📸 Protocollo Obbligatorio: Analisi Visiva Nativa SOTA (Pixel-to-Markdown) & OKF v0.2

Quando l'utente carica o allega un file (PDF, fattura, distinta tecnica, offerta, scansione, contratto, immagine):
1. **Analisi Visiva Nativa (Pixel-Level)**:
   - È **obbligatorio analizzare il documento a livello visivo nativo** (pixel-to-markdown) per preservare l'ordine di lettura corretto su colonne complesse, grafici, firme e tabelle dense.
   - Attiva il massimo livello di **Deep Thinking** per decifrare numeri, allineamenti, sconti e specifiche.
2. **Generazione Immediata dell'Artefatto OKF v0.2 (`.md`)**:
   - Genera un file Artefatto Markdown conforme allo standard **OKF v0.2** composto da:
     - **Frontmatter YAML**:
       ```yaml
       ---
       type: "concept"
       title: "[Titolo effettivo del documento]"
       description: "[Abstract sintetico del contenuto]"
       generated.at: "[ISO 8601 Timestamp]"
       sources:
         - "file://@[nome_documento.pdf]"
       tags:
         - "document-intelligence"
         - "estrazione-sota"
       ---
       ```
     - **Corpo del Documento Markdown**:
       - `# Punti Chiave`: concetti ed elementi critici con indicazione della pagina originale `[Pagina X]`.
       - `# Contenuto Semantico`: gerarchia testuale pulita con capitoli, titoli e note.
       - `# Tabelle Estratte`: tutte le tabelle interamente ricostruite cella per cella in Markdown, senza omettere alcun dato numerico o voce.
3. **Zero-Hallucination & Provenance Guardrail**:
   - È **SEVERAMENTE VIETATO** inventare contratti, canoni SLA, noleggi stampanti o associare IBAN fornitore al cliente.
   - Qualsiasi dato non fisicamente presente nel documento deve essere esplicitamente indicato come `NOT_FOUND`.
4. **Alimentazione Deterministica delle Pipeline**:
   - L'artefatto OKF v0.2 diventa il "gemello digitale" certificato da cui la CLI (`it-ops ingest <file.okf.md> --slug <slug> --apply`) estrae i dati per popolare anagrafiche, preventivi e commesse.

---

## 🔒 Principi di Integrazione Hub-and-Spoke
1. **Separation of Concerns**: Non inserire mai dati contabili o di fatturazione all'interno del repository tecnico `itinfra`.
2. **Read-Only Bridge**: L'accesso ai documenti tecnici in `../itinfra/projects/<slug>/` è sempre e solo in lettura (`manifest.yaml`, `06-As-Built.md`).
3. **Shared Customer Slug**: Lo slug cliente (es. `cliente-rossi-srl`) deve coincidere esattamente tra i due repository per permettere la cross-validazione degli asset.
