---
type: lesson
id: LES-CODE-001
title: Gestione Escaping Script Python e Operatori PowerShell
description: Prevenzione errori di sintassi da f-string non escapate e operatori speciali
  in comandi inline
domain: engineering
lifecycle: active
stale_after: '2027-09-01T00:00:00Z'
replaces: []
incident:
  context: Generazione file e script dinamici da terminale PowerShell
  observed_failure: 'SyntaxError: f-string expecting ''='' or ''!'' a causa di parentesi
    graffe JavaScript/CSS non raddoppiate in Python; fallimento di comandi inline
    powershell con operatori non quotati (&, (), --).'
  root_cause: PowerShell interpreta parentesi e ampersand come operatori di pipeline;
    Python f-string interpreta ogni singola parentesi graffa come espressione da valutare.
trust:
  tier: attested
  attested_by: human:possumato
  attestation_date: '2026-09-17T18:38:14.429253+00:00'
  attestation_method: live_interaction_review
  content_sha256: 00c64e86bb45b62b539b6dc979024bf936f17eb1451e3f55c71b4ad60473659c
eval:
  negative_check: grep 'python -c' command_history && grep -E '(&|[()]|--)' command_history
  positive_assertion: uses_scratch_files == true && fstring_braces_doubled == true
sources:
- conversation://fa358d31-fe29-48c8-af16-883e5d5b4d97
tags:
- python
- powershell
- escaping
- f-string
- guardrail
---

# Regola Vincolante (Guardrail)
1. **Parentesi Graffe in Template e F-String Python**:
   - Se uno script Python utilizza f-string per generare codice CSS o JavaScript contenente `{` o `}`, le parentesi graffe non Python DEVONO essere sempre raddoppiate (`{{` e `}}`).
   - In alternativa, utilizzare template con segnaposto espliciti (es. `raw_html.replace("__VAR__", value)`) evitando interamente i conflitti di interpolazione.
2. **Esecuzione Comandi in PowerShell (Windows)**:
   - È **SEVERAMENTE VIETATO** eseguire snippet Python complessi inline con `python -c "..."` se contengono operatori PowerShell (`&`, `()`, `--foreground`, pipe complesse).
   - Scrivere SEMPRE lo script in un file temporaneo `scratch/<nome>.py` ed eseguirlo con `python scratch/<nome>.py`.
3. **Encoding dei File**:
   - Specificare sempre esplicitamente `encoding="utf-8"` in ogni operazione di lettura e scrittura file in Python.
