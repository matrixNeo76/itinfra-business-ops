---
name: visual-document-parser
description: Native visual document analysis (Pixel-to-Markdown) with OKF v0.2 Artifact generation and two-stage pipeline ingestion for ITInfra Business Ops.
metadata:
  model: inherit
---

# 📸 Visual Document Parser & OKF v0.2 Intelligence Skill

Questo skill definisce il protocollo di **Analisi Visiva Nativa (Pixel-to-Markdown)** per documenti allegati e la loro trasformazione in artefatti conformi allo standard **OKF v0.2 (Open Knowledge Framework)** per l'applicativo `itinfra-business-ops`.

---

## 🎯 Obiettivi Operativi

1. **Pixel-to-Markdown**: Analizzare i documenti a livello visivo per rispettare l'ordine topologico di lettura, preservare celle unite, note a margine, layout a più colonne e timbri.
2. **Cristallizzazione OKF v0.2**: Trasformare qualsiasi documento (fatture B2B, distinte tecniche hardware, contratti di fornitura, capitolati d'arredo) in un "gemello digitale" peritale Markdown prima di alimentare i database gestionali.
3. **Zero-Hallucination Guardrail**: Nessun campo o canone può essere dedotto o inventato.

---

## 📋 Struttura dell'Artefatto OKF v0.2

Ogni documento analizzato DEVE essere strutturato come segue:

```markdown
---
type: "concept"
title: "[Titolo effettivo e univoco del documento]"
description: "[Abstract sintetico del contenuto, tipo di atto o documento]"
generated.at: "[Data e ora ISO 8601, es. 2026-09-17T16:35:00Z]"
sources:
  - "file://@[nome_file_originale.ext]"
tags:
  - "document-intelligence"
  - "estrazione-sota"
  - "[categoria: invoice | spec-sheet | contract | furniture]"
---

# Punti Chiave
- [Pagina 1] Elemento essenziale o condizione contrattuale.
- [Pagina 1] Dati anagrafici e societari verificati.

# Contenuto Semantico
## [Sezione 1: Intestazione & Parti Coinvolte]
Descrizione ordinata delle parti, ruoli e riferimenti legali.

## [Sezione 2: Descrizione Tecnica / Oggetto della Fornitura]
Sintesi narrativa fedele della fornitura o dei servizi.

# Tabelle Estratte
### Tabella 1: [Titolo descrittivo tabella]
| Colonna 1 | Colonna 2 | Colonna 3 | ... |
|---|---|---|---|
| Cella 1 | Cella 2 | Cella 3 | ... |
```

---

## 🛠️ Regole per la Trascrizione delle Tabelle

1. **Completezza Cella per Cella**: È severamente vietato omettere righe o abbreviare con `...` tabelle di articoli o specifiche.
2. **Preservazione Numerica**: Prezzi unitari, sconti percentuali, quantità, codici articolo e aliquote IVA devono essere trascritti con esattezza decimale.
3. **Allineamento Colonne**:
   * Codici e ID: allineamento a sinistra o centrato.
   * Descrizioni: allineamento a sinistra.
   * Quantità: allineamento al centro.
   * Prezzi e Importi: allineamento a destra.

---

## 💻 Ingestione nell'Applicativo CLI

Una volta generato il file `.okf.md`, eseguire l'ingestione tramite:

```powershell
.\it-ops.cmd ingest percorso/documento.okf.md --slug <slug-cliente> --apply
```
