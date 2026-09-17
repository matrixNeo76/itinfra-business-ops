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

---

## 🔒 Principi di Integrazione Hub-and-Spoke
1. **Separation of Concerns**: Non inserire mai dati contabili o di fatturazione all'interno del repository tecnico `itinfra`.
2. **Read-Only Bridge**: L'accesso ai documenti tecnici in `../itinfra/projects/<slug>/` è sempre e solo in lettura (`manifest.yaml`, `06-As-Built.md`).
3. **Shared Customer Slug**: Lo slug cliente (es. `cliente-rossi-srl`) deve coincidere esattamente tra i due repository per permettere la cross-validazione degli asset.
