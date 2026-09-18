---
okf_version: "0.2"
id: "spec-ops-pipeline-h-document-ingestion"
title: "Pipeline H — Ingestione Documenti SOTA, Analisi Visiva & Audit Anti-Allucinazione"
type: "specification"
domain: "Document Intelligence & SOTA Parsing"
tags: ["okf-v0.2", "pipeline-h", "document-ingestion", "pdf-extractor", "sdi-xml", "audit-triangolare"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-18"
updated_at: "2026-09-18"
lang: "it"

entities:
  - name: "Document Ingestion Pipeline"
    type: "pipeline"
    description: "Pipeline per l'acquisizione, estrazione e strutturazione deterministica di documenti eterogenei (PDF, XML SDI, preventivi, distinte tecniche)"
  - name: "SdiXmlExtractor"
    type: "extractor"
    description: "Parser ad alta fedelta' per tracciati XML di fatturazione elettronica FPR12 e FPA12"
  - name: "Triangular Reconciliation Engine"
    type: "audit_engine"
    description: "Motore di verifica incrociata a 3 vie tra evidenze documentali, preventivi calcolati e anagrafiche contrattuali"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "part_of"
    weight: 1.0
  - targetTitle: "Pipeline C — Fatturazione SDI v1.2"
    targetId: "spec-ops-pipeline-c-billing"
    relationType: "collaborates_with"
    weight: 0.95
  - targetTitle: "Pipeline E — Preventivazione Multiprodotto Cost-Plus"
    targetId: "spec-ops-pipeline-e-quotes"
    relationType: "collaborates_with"
    weight: 0.95
---

# Pipeline H — Ingestione Documenti SOTA, Analisi Visiva & Audit Anti-Allucinazione

## 1. Obiettivi e Principi Guida

La **Pipeline H (`ingest`)** governa l'acquisizione, digitalizzazione e validazione di documenti non strutturati o semi-strutturati (offerte commerciali fornitore, preventivi PDF, fatture XML SDI, computi metrici e schede tecniche).

I principi cardine della pipeline sono:
1. **Analisi Visiva Nativa (Pixel-to-Markdown)**: Nessuna degradazione della struttura geometrica; tabelle complesse a più livelli e note a piè di pagina vengono preservate.
2. **Zero-Hallucination Guardrail**: Nessun dato puo' essere inventato. Se un'informazione (es. IBAN, clausole SLA, canoni noleggio) non e' fisicamente presente nel documento, viene marcata esplicitamente come `NOT_FOUND`.
3. **Audit Triangolare (3-Way Matching)**: Riconciliazione deterministica tra:
   - Evidenze estratte dal documento sorgente;
   - Preventivo calcolato nel sistema (`quotes/`);
   - Anagrafica cliente e condizioni contrattuali (`client-manifest.yaml`).

---

## 2. Architettura dei Moduli Estrattivi

### `PdfExtractor`
- Estrazione testuale e tabellare ad alta risoluzione con preservazione degli allineamenti contabili.
- Ripristino dell'ordine di lettura naturale su layout multi-colonna e intestazioni dense.

### `SdiXmlExtractor` (FPR12 & FPA12)
- Parsing conforme allo schema XSD di FatturaPA / SDI v1.2.2.
- Supporto nativo per tracciati B2B privati (`FPR12`) e Pubblica Amministrazione (`FPA12`).
- Riconoscimento automatico di:
  - Dati anagrafici cedente/prestatore e cessionario/committente;
  - Linee di dettaglio con codici articolo, aliquote IVA, sconti/maggiorazioni;
  - Ritenute d'acconto (`RT01`/`RT02`) e contributi cassa previdenziale (`TC22`);
  - Dati di pagamento con IBAN, coordinate bancarie e scadenze rate.

---

## 3. Comandi CLI Disponibili

```bash
# Ingestione con verifica evidenze e audit di qualita'
.\it-ops.cmd ingest percorso/al/documento.pdf --slug <slug>

# Applicazione deterministica all'anagrafica cliente o preventivo
.\it-ops.cmd ingest percorso/al/documento.pdf --slug <slug> --apply

# Ingestione con prezzo di vendita target (per distinte tecniche)
.\it-ops.cmd ingest distinta.pdf --slug <slug> --target-price 8500.00 --apply
```
