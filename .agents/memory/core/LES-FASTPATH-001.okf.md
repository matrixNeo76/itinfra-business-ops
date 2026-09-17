---
type: lesson
id: LES-FASTPATH-001
title: Zero-Search Fast-Path e Risposta Deterministica a 0 Secondi
description: Divieto di ricerche casuali (Glob, Grep, LS) per comandi operativi e
  saluti noti
domain: core
lifecycle: active
stale_after: '2027-09-01T00:00:00Z'
replaces: []
incident:
  context: Avvio sessione, saluti o richiesta comandi operativi da parte dell'utente
  observed_failure: Esecuzione non necessaria di tool di ricerca file per scoprire
    le capacità dell'applicativo, causando latenza ed erodendo il contesto.
  root_cause: Mancato riconoscimento immediato della natura deterministica e standardizzata
    dell'applicativo ITInfra Business Ops.
trust:
  tier: attested
  attested_by: human:possumato
  attestation_date: '2026-09-17T18:38:14.910910+00:00'
  attestation_method: live_interaction_review
  content_sha256: 9ed3f30e73dc3848d23079a4523428ab24d22149c2bf9bdff84e8bf0196133c9
eval:
  negative_check: user_intent in ['saluto', 'help', 'comandi'] && tool_call in ['find_by_name',
    'grep_search', 'list_dir']
  positive_assertion: direct_response_with_operational_card == true
sources:
- RULE[c:/Users/auresystem/repos/itinfra-business-ops/AGENTS.md]
- RULE[c:/Users/auresystem/repos/itinfra-business-ops/GEMINI.md]
tags:
- fast-path
- zero-search
- determinism
- guardrail
---

# Regola Vincolante (Guardrail)
1. **Risposta Immediata Deterministiche (0 Secondi)**:
   - Se l'utente saluta (`ciao`, `buongiorno`), chiede cosa fa l'applicativo, come visualizzare i comandi o quali comandi sono disponibili:
   - È **SEVERAMENTE VIETATO** invocare tool di ricerca file (`find_by_name`, `grep_search`, `list_dir`).
   - Rispondere ALL'ISTANTE presentando la **Scheda Operativa ITInfra Business Ops** con la matrice dei comandi rapidi (`init`, `stato`, `check`, `contratto`, `rapportino`, `mps`, `fatturazione`, `arredo`, `preventivo`, `ingest`, `learn`).
2. **Determinismo dei Comandi Operativi**:
   - I comandi rapidi (`anteprima <slug> <tipo>`, `stato <slug>`, `check <slug>`) devono essere eseguiti immediatamente indirizzando direttamente i percorsi noti degli schemi YAML e dei file generati.
