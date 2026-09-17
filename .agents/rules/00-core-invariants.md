# Core System Invariants & Zero-Search Fast-Path
> **Ambito Operativo**: Regole capitali e fast-path operativo a 0 secondi
> *Compilato deterministicamente dal MemoryEngine OKF v0.2*

---

## 🔒 [ATTESTED] `LES-FASTPATH-001` — Zero-Search Fast-Path e Risposta Deterministica a 0 Secondi
*Divieto di ricerche casuali (Glob, Grep, LS) per comandi operativi e saluti noti*

# Regola Vincolante (Guardrail)
1. **Risposta Immediata Deterministiche (0 Secondi)**:
   - Se l'utente saluta (`ciao`, `buongiorno`), chiede cosa fa l'applicativo, come visualizzare i comandi o quali comandi sono disponibili:
   - È **SEVERAMENTE VIETATO** invocare tool di ricerca file (`find_by_name`, `grep_search`, `list_dir`).
   - Rispondere ALL'ISTANTE presentando la **Scheda Operativa ITInfra Business Ops** con la matrice dei comandi rapidi (`init`, `stato`, `check`, `contratto`, `rapportino`, `mps`, `fatturazione`, `arredo`, `preventivo`, `ingest`, `learn`).
2. **Determinismo dei Comandi Operativi**:
   - I comandi rapidi (`anteprima <slug> <tipo>`, `stato <slug>`, `check <slug>`) devono essere eseguiti immediatamente indirizzando direttamente i percorsi noti degli schemi YAML e dei file generati.

---
