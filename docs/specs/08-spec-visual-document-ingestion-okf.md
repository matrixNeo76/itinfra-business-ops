# 08-SPEC: Analisi Visiva Nativa SOTA (Pixel-to-Markdown) & OKF v0.2 Ingestion

## 1. Visione d'Insieme
Questo documento formalizza lo standard architetturale per la lettura, decodifica e integrazione di documenti complessi (fatture commerciali, distinte tecniche hardware, contratti di fornitura e ordini arredo) all'interno dell'ecosistema **ITInfra Business Ops**.

---

## 2. Architettura a Due Stadi (Two-Stage Architecture)

### Stadio 1: Analisi Visiva Nativa & Generazione Artefatto OKF v0.2
* **Input**: File binario (PDF, JPG, PNG) caricato in chat.
* **Motore**: Visione Multimodale Nativa Antigravity + Deep Thinking.
* **Output**: Artefatto Markdown conforme a **OKF v0.2 (`.okf.md`)**.
* **Principio Guida**: Preservazione dell'ordine topologico reale di lettura, celle unite, riquadri a colonna, e trascrizione integrale delle tabelle senza omissioni numeriche.

### Stadio 2: Ingestione Deterministica nei Moduli Gestionali
* **Input**: File `.okf.md` generato nello Stadio 1.
* **Motore**: `scripts/pipelines/ingestion.py` (`OKFDocumentParser`).
* **Output**: Aggiornamento convalidato da schema di:
  * `client-manifest.yaml` (Anagrafica, P.IVA, Sede, Termini di Pagamento).
  * `quotes/quote-<id>.yaml` (Distinte B2B, preventivazione cost-plus, esportazione HTML/PDF/DOCX).
  * `furniture/arr-<id>.yaml` (Commesse fornitura arredo ufficio).

---

## 3. Specifiche Schema Frontmatter OKF v0.2

```yaml
---
type: "concept"
title: "[Nome/Titolo Univoco Documento]"
description: "[Abstract sintetico del contenuto]"
generated.at: "[ISO 8601 Timestamp]"
sources:
  - "file://@[nome_file.pdf]"
tags:
  - "document-intelligence"
  - "estrazione-sota"
  - "[invoice | spec-sheet | contract | furniture]"
---
```

---

## 4. Sezioni Strutturali del Documento

1. `# Punti Chiave`
   - Sintesi delle clausole ed elementi critici con annotazione obbligatoria `[Pagina X]`.
2. `# Contenuto Semantico`
   - Testo per esteso organizzato secondo la gerarchia visiva originale (titoli, sezioni, note legali).
3. `# Tabelle Estratte`
   - Ogni tabella è fedelmente ricostruita in sintassi GFM (GitHub Flavored Markdown), riportando ogni riga, codice, descrizione, quantità, prezzo e aliquota IVA.

---

## 5. Regole Anti-Allucinazione e Provenance
* **Nessun Dato Immaginato**: I campi non presenti sul documento originale NON devono mai essere dedotti o inseriti artificialmente.
* **Isolamento dei Ruoli**: Su fatture passive, l'IBAN per l'accredito appartiene all'emittente fornitore e non deve mai essere assegnato all'anagrafica del cliente committente.
