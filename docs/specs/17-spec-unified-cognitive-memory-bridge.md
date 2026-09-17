# SPEC-17 — Unified Cognitive Memory Architecture & Cross-Repository Self-Correction Bridge (OKF v0.2)

```yaml
---
id: "SPEC-17"
title: "Architettura di Memoria Cognitiva Unificata & Bridge di Auto-Correzione Federato"
version: "1.0.0"
date: "2026-09-17"
status: "APPROVED"
authors:
  - "Eduardo Possumato (Titolare & Lead Solution Architect)"
  - "Antigravity AI Agent Core"
framework: "Google Open Knowledge Format (OKF) v0.2"
repositories:
  - "itinfra-business-ops"
  - "itinfra"
replaces: []
depends_on:
  - "SPEC-16"
  - "guide-memoria-ibrida-trust-signals-v02"
  - "guide-global-memory-system-test-01"
tags:
  - "okf-v0.2"
  - "hybrid-memory"
  - "cognitive-bridge"
  - "scratchpad-promotion"
  - "antigravity-rules"
  - "zero-leakage"
---
```

---

## 1. Visione & Obiettivi Architetturali

La presente specifica formalizza l'unificazione della **Memoria Ibrida a 3 Livelli** (introdotta in `itinfra` v0.8) con il **Motore di Auto-Correzione & Apprendimento Attestato** (introdotto in `itinfra-business-ops`), creando un unico ecosistema cognitivo condiviso tra i due repository federati.

### 1.1. Obiettivi Chiave
1. **Unificazione della Piramide Cognitiva**: Fusione logica dei 3 livelli di memoria (Breve, Medio e Lungo termine) su entrambi i perimetri.
2. **Scratchpad-to-Guardrail Promotion Pipeline**: Capacità di promuovere una scoperta tecnica o un bug hardware annotato nello scratchpad globale di `itinfra` direttamente in una regola vincolante attestata (`.agents/rules/`) per l'agente Antigravity.
3. **Immunità Operativa Bidirezionale**: Garantire che l'agente non commetta errori né sul piano tecnico (networking, server, Hyper-V) né sul piano commerciale/governance (computi, UI, contratti SLA).
4. **Sicurezza Multi-Tenant Zero-Leakage**: Preservare la segregazione assoluta tra dati riservati dei singoli clienti e la memoria globale condivisa.

---

## 2. La Piramide di Memoria Cognitiva Unificata

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               LIVELLO 1: BREVE TERMINE (Context Window & Invariant Rules)              │
│  - Contesto conversazionale attivo in Antigravity                                      │
│  - Invarianti immediate: AGENTS.md, GEMINI.md, .agents/rules/*.md (Compilate)          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
┌───────────────────────────────────────────────┐ ┌───────────────────────────────────────────────┐
│     LIVELLO 2: MEDIO TERMINE (Staging)        │ │     LIVELLO 2: MEDIO TERMINE (Staging)        │
│          Ambito Progetto / Tenant             │ │         Ambito Globale & Incidenti            │
│ ├── itinfra: projects/<slug>/_scratchpad.md   │ │ ├── itinfra: projects/_global_scratchpad.md   │
│ └── business-ops: clients/<slug>/             │ │ └── business-ops: .agents/memory/ [generated] │
│     (Note aperte, requisiti in sospeso)       │ │     (Best practice, bug noti, incidenti draft)│
└───────────────────────────────────────────────┘ └───────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│            LIVELLO 3: LUNGO TERMINE (Permanent Attested Knowledge & Guardrails)         │
│                                                                                        │
│  A. Conoscenza di Progetto Consolidata (Documenti OKF v0.2 di Tenant):                 │
│     - itinfra: 01-RSD ... 06-As-Built.md, 10-RCA.md (verified: true)                   │
│     - business-ops: contratti firmati, preventivi approvati, rapportini, As-Built match │
│                                                                                        │
│  B. Memoria Comportamentale dell'Agente (Attested Guardrails & Rules Engine):          │
│     - .agents/memory/*.okf.md [trust.tier: attested, SHA-256 seal]                     │
│     - Compilazione deterministica in .agents/rules/*.md (Progressive Disclosure)       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Specifiche del Bridge Operativo (`CognitiveBridge`)

Il modulo `scripts/core/cognitive_bridge.py` realizza il connettore ad alta affidabilità tra `MemoryEngine` e `MemoryManager`:

### 3.1. Pipeline di Promozione da Scratchpad a Guardrail Attestato
Quando un'osservazione o un incidente presente in `projects/_global_scratchpad.md` deve diventare una regola attiva:
1. **Acquisizione Atomica**: Il bridge acquisisce il lock atomico (`AtomicFileLock`) su `_global_scratchpad.lock`.
2. **Sanitizzazione Multi-Tenant**: Verifica che il testo non contenga riferimenti a `vault://` o password in chiaro tramite `validate_global_entry_safety`.
3. **Estrazione & Parsing**: Estrae la voce target (`<!-- id:mem-xxxx -->`).
4. **Generazione Nodo OKF v0.2**: Crea il file `.okf.md` in `.agents/memory/<domain>/LES-*.okf.md` con metadati estesi (`type: lesson`, `lifecycle: active`, `incident: ...`).
5. **Attestazione & Sealing**: Calcola l'hash canonico SHA-256 e promuove il nodo a `trust.tier: attested`.
6. **Compilazione Regole**: Invoca il compiler per rigenerare `.agents/rules/*.md` in entrambi i repository.
7. **Marcatura di Idempotenza**: Aggiorna la riga originale nello scratchpad con il tag `<!-- promoted:LES-xxxx -->` per evitare doppie promozioni.

### 3.2. Sincronizzazione Trasparente all'Avvio (Auto-Sync Hook)
Ad ogni invocazione di `it-ops` o `itinfra`:
- Se il timestamp o l'hash SHA-256 del `registry.yaml` differisce tra i due repository, viene eseguita la sincronizzazione atomica bidirezionale in background (<50ms).

---

## 4. Analisi delle Criticità & Misure Preventive

| Rischio / Criticità | Impatto Operativo | Contromisura Obbligatoria da Specifica |
| :--- | :--- | :--- |
| **Race Condition su Scritture Concorrenti** | Rischio di corruzione dello scratchpad globale se due processi scrivono simultaneamente. | Adozione universale di `AtomicFileLock` (timeout 10s, auto-prune lock obsoleti >120s). |
| **Data Leak Multi-Tenant nella Memoria Condivisa** | Rischio che secret o indirizzi IP di un cliente finiscano nelle regole visibili a tutti. | Esecuzione rigorosa del `MultiTenantSanitizer` prima di qualunque operazione di salvataggio. |
| **Promozione Duplicata / Drift** | La stessa voce viene promossa più volte generando nodi di memoria ridondanti. | Controllo rigoroso dell'ID voce (`mem-xxxx`) e apposizione del tag `promoted:LES-xxxx`. |
| **Conflitto di Regole nel Prompt dell'Agente** | Due regole compilate che danno istruzioni contrastanti. | Audit preventivo tramite `it-ops learn audit` e gestione delle clausole `replaces: [...]`. |

---

## 5. Riferimento Comandi CLI Unificati

```bash
# 1. Promozione da scratchpad globale a guardrail attivo Antigravity
.\it-ops.cmd learn promote --entry mem-a1b2c3d4 --domain technical --id LES-NET-002 --title "Regola MTU ZeroTier"

# 2. Sincronizzazione manuale forzata tra i repository
.\it-ops.cmd learn sync

# 3. Verifica dello stato di salute dell'intero ecosistema cognitivo
.\it-ops.cmd learn audit
.\it-ops.cmd learn test
```
