# Document Intelligence & Business Ops Invariants
> **Ambito Operativo**: Regole operative su template, computo economico, P.IVA e contratti SLA
> *Compilato deterministicamente dal MemoryEngine OKF v0.2*

---

## 🔒 [ATTESTED] `LES-DOC-001` — Quadratura Contabile e Conformità Forense Preventivi e Contratti
*Prevenzione incongruenze tra prezzi unitari e totali, obbligatorietà dati fiscali e clausole AI on-premise*

# Regola Vincolante (Guardrail)
1. **Quadratura Matematica Rigorosa**:
   - In ogni preventivo o computo metrico: se una voce espone un totale maggiore di zero (es. € 400,00), il prezzo unitario NON può essere contrassegnato come "Incluso", ma deve esporre la relativa tariffa unitaria (es. € 50,00/ora).
   - Se una voce è realmente a pacchetto/inclusa, il prezzo unitario e il totale riga DEVONO essere entrambi pari a € 0,00.
   - `subtotale_imponibile + iva_calcolata` deve coincidere al centesimo con `totale_lordo`.
2. **Presenza Dati Fiscali e Denominazione Sociale**:
   - È obbligatorio includere sempre la P.IVA fornitore (`IT07714231219`), PEC e recapito formale in testata.
   - La denominazione nel box firma deve coincidere esattamente con l'inquadramento societario registrato ("Aure System di Eduardo Possumato").
3. **Formule di Pagamento per Professionisti**:
   - Per forniture integrate di hardware e servizi, raccomandare sempre lo Stato Avanzamento Lavori (SAL): **40% all'ordine, 40% alla consegna hardware, 20% al collaudo finale**.
4. **Deontologia Forense & EU AI Act (Studi Legali)**:
   - Blindare l'architettura su base rigorosamente on-premise (Ollama locale su workstation protetta); vietare la trasmissione di fascicoli o dati confidenziali a LLM cloud pubblici senza DPA enterprise e clausola esplicita di no-training.

---
