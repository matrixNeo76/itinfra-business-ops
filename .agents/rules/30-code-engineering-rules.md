# Code Engineering & Execution Invariants
> **Ambito Operativo**: Regole su gestione stringhe Python, escaping PowerShell e script scratch
> *Compilato deterministicamente dal MemoryEngine OKF v0.2*

---

## 🔒 [ATTESTED] `LES-CODE-001` — Gestione Escaping Script Python e Operatori PowerShell
*Prevenzione errori di sintassi da f-string non escapate e operatori speciali in comandi inline*

# Regola Vincolante (Guardrail)
1. **Parentesi Graffe in Template e F-String Python**:
   - Se uno script Python utilizza f-string per generare codice CSS o JavaScript contenente `{` o `}`, le parentesi graffe non Python DEVONO essere sempre raddoppiate (`{{` e `}}`).
   - In alternativa, utilizzare template con segnaposto espliciti (es. `raw_html.replace("__VAR__", value)`) evitando interamente i conflitti di interpolazione.
2. **Esecuzione Comandi in PowerShell (Windows)**:
   - È **SEVERAMENTE VIETATO** eseguire snippet Python complessi inline con `python -c "..."` se contengono operatori PowerShell (`&`, `()`, `--foreground`, pipe complesse).
   - Scrivere SEMPRE lo script in un file temporaneo `scratch/<nome>.py` ed eseguirlo con `python scratch/<nome>.py`.
3. **Encoding dei File**:
   - Specificare sempre esplicitamente `encoding="utf-8"` in ogni operazione di lettura e scrittura file in Python.

---
