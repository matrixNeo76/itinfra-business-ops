---
okf_version: "0.2"
id: "spec-ops-pipeline-i-memory-learning"
title: "Pipeline I — Memoria Auto-Correttiva Attestata, DAG Cycles DFS & Peer Sync"
type: "specification"
domain: "Cognitive Memory & Continual Learning"
tags: ["okf-v0.2", "pipeline-i", "memory-learning", "dag-cycle-detection", "attestation", "peer-sync"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-18"
updated_at: "2026-09-18"
lang: "it"

entities:
  - name: "Attested Memory Engine"
    type: "engine"
    description: "Motore di accumulo, verifica e attestazione formale di regole operative, vincoli e lezioni apprese"
  - name: "DAG Cycle Detector"
    type: "graph_validator"
    description: "Algoritmo Depth-First Search (DFS) con marcatura ternaria (WHITE/GRAY/BLACK) per prevenire deadlock semantici"
  - name: "Cross-Repo Peer Synchronizer"
    type: "synchronizer"
    description: "Modulo di propagazione mtime-based e hash-checked del registro di memoria tra repository federati"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "part_of"
    weight: 1.0
  - targetTitle: "Specifica Unificata Memoria Ibrida (itinfra)"
    targetId: "spec-unified-cognitive-memory-bridge"
    relationType: "federated_with"
    weight: 1.0
---

# Pipeline I — Memoria Auto-Correttiva Attestata, DAG Cycles DFS & Peer Sync

## 1. Visione Operativa

La **Pipeline I (`learn`)** abilita l'ecosistema a migliorare costantemente nel tempo, persistendo correzioni umane, guardrail operativi e pattern di successo all'interno di un grafo di conoscenza immutabile e verificabile.

Ogni apprendimento segue il ciclo di vita rigoroso:
$$\text{Scratchpad Volatile} \xrightarrow{\text{Audit}} \text{Proposta} \xrightarrow{\text{Attestazione Umana}} \text{Nodo DAG Immutabile}$$

---

## 2. Funzionalita' SOTA Level-2

### Rilevamento Cicli DAG con Algoritmo DFS
Il grafo delle dipendenze tra regole e nodi di memoria e' validato prima di ogni compilazione tramite DFS ricorsiva con tre stati di colorazione:
- `WHITE`: Nodo non visitato;
- `GRAY`: Nodo nello stack di ricorsione corrente (se re-incontrato, segnala ciclo critico `ERR_DAG_CYCLE`);
- `BLACK`: Ramo completamente visitato ed esente da cicli.

### Decadimento Temporale della Confidenza (Confidence Decay)
La confidenza di una regola non verificata decade nel tempo seguendo un modello logaritmico, prevenendo l'accumulo di informazioni obsolete o contrastanti con normative recenti.

### Attestazione Formale Umana
Nessuna regola puo' influenzare le decisioni operative critiche senza l'attestazione esplicita con firma di audit (es. `human:possumato`).

### Peer Synchronization Bidirezionale
Il registro `.agents/memory/registry.yaml` e' mantenuto automaticamente sincronizzato tra `itinfra-business-ops` e `itinfra`: se un repository presenta una modifica piu' recente con hash valido, la sincronizzazione allinea entrambi gli ambienti all'istante (0 secondi).

---

## 3. Comandi CLI Disponibili

```bash
# Elenco nodi di memoria attivi
.\it-ops.cmd learn list [--domain technical|business_ops|core]

# Promozione voce dallo scratchpad a regola formale
.\it-ops.cmd learn promote --entry mem-bp01zt --title "Regola Margini" --domain business_ops

# Attestazione formale di conformita'
.\it-ops.cmd learn attest --id LES-UI-001 --by human:possumato

# Sincronizzazione con il peer federato
.\it-ops.cmd learn sync

# Audit di integrita' e test automatico del DAG
.\it-ops.cmd learn audit
.\it-ops.cmd learn test
```
