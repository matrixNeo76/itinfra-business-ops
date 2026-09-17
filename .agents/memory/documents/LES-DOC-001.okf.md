---
type: lesson
id: LES-DOC-001
title: Quadratura Contabile e Conformità Forense Preventivi e Contratti
description: Prevenzione incongruenze tra prezzi unitari e totali, obbligatorietà
  dati fiscali e clausole AI on-premise
domain: documents
lifecycle: active
stale_after: '2027-09-01T00:00:00Z'
replaces: []
incident:
  context: Audit qualitativo e contabile su preventivo per studio legale e contratto
    SLA
  observed_failure: Voce formazione con prezzo unitario indicato come 'Incluso' ma
    sommato a 400€ nel subtotale; omissione P.IVA fornitore; formula pagamento 100%
    all'ordine rischiosa per il committente; rischio privacy su LLM cloud.
  root_cause: Mancanza di cross-check deterministico tra subtotali e descrizioni;
    mancato presidio conformità EU AI Act e Codice Deontologico Forense (Art. 28 CDF).
trust:
  tier: attested
  attested_by: human:possumato
  attestation_date: '2026-09-17T18:38:14.675158+00:00'
  attestation_method: live_interaction_review
  content_sha256: 54dfcf86e0aff497ca0465f0fe4071f2c274631843bc2ef4918730fbf84f7943
eval:
  negative_check: unit_price == 'Incluso' && total_price > 0
  positive_assertion: abs((net_total + vat_amount) - gross_total) <= 0.01 && supplier_piva
    != ''
sources:
- conversation://fa358d31-fe29-48c8-af16-883e5d5b4d97
- docs/viola-preventivo/03-audit-preventivo-2026.okf.md
tags:
- accounting
- quote
- sla-contract
- tax-compliance
- eu-ai-act
- guardrail
---

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
