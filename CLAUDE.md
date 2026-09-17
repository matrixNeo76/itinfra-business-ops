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

---

## 🔒 Principi di Integrazione Hub-and-Spoke
* **SoC**: Repository commerciale/operativo separato dal repository tecnico `itinfra`.
* **Shared Slug**: Identificativo cliente identico (`<slug>`).
* **Cross-Check**: Lettura in sola lettura di `../itinfra/projects/<slug>/` per coerenza con As-Built.
