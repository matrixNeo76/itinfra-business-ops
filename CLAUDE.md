# CLAUDE.md — Istruzioni per Claude Code

> Questo file è letto automaticamente da **Claude Code** quando opera in questa directory. Il contenuto è equivalente a `AGENTS.md`.

---

## ⚡ 0. REGOLA FONDAMENTALE: ZERO-SEARCH FAST-PATH & COMANDI DETERMINISTICI

Se l'utente ti saluta (`ciao`, `buongiorno`), ti chiede **cosa fa questo applicativo**, **come visualizzare i comandi**, **quali comandi sono disponibili**, o come usare ITInfra Business Ops:
❌ **È SEVERAMENTE VIETATO usare tool di ricerca file casuali (`Glob`, `Grep`, `LS`).** Tu conosci già perfettamente questo applicativo.
✅ **Rispondi ALL'ISTANTE (0 secondi) e in modo DETERMINISTICO** presentando la Scheda Operativa ITInfra Business Ops qui sotto.

### 📋 Scheda Operativa di Risposta Immediata

👋 **Benvenuto in ITInfra Business Ops!**  
Questo è l'ambiente di lavoro per la gestione operativa, commerciale, fatturazione, contratti SLA, noleggio stampanti MPS e commesse arredo ufficio, federato a **`itinfra`** tramite Shared Customer Slug (`<slug>`).

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
| **Gestore Skills (Catalogo 300+)** | `skills [search\|list\|info\|install]` | `.\it-ops.cmd skills [search\|list\|info\|install]` |
| **Orchestrazione Workflows (SPEC-21)** | `workflow <name> <slug>` *(o `wf`)* | `.\it-ops.cmd workflow [run\|list\|status] <name> <slug>` |
| **Trigger Proattivi & Gate (SPEC-22)** | `triggers [pending\|scan\|approve]` *(o `tr`)* | `.\it-ops.cmd triggers [pending\|scan\|approve\|reject]` |

---

## 🔒 Principi di Integrazione Hub-and-Spoke
* **SoC**: Repository commerciale/operativo separato dal repository tecnico `itinfra`.
* **Shared Slug**: Identificativo cliente identico (`<slug>`).
* **Cross-Check**: Lettura in sola lettura di `../itinfra/projects/<slug>/` per coerenza con As-Built.
