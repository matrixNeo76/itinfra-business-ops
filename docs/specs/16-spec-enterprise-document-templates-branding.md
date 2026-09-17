---
okf_version: "0.2"
id: "specification-enterprise-document-templates-branding-v01"
type: "specification"
title: "SPEC-16 — Enterprise Document Templating, Corporate Brand Identity & Zero-CDN Multi-Format Publishing"
description: "Specifica architetturale per la standardizzazione visiva, tipografica e contabile dei documenti prodotti da ITInfra Business Ops (DOCX, PDF, HTML) con asset ufficiali di brand identity e protezione offline."
version: "1.0.0"
status: "approved"
author: "System Architect"
created.at: "2026-09-17T18:10:00+02:00"
tags:
  - "document-rendering"
  - "brand-identity"
  - "zero-cdn"
  - "docx-templates"
  - "pdf-export"
---

# SPEC-16 — Enterprise Document Templating & Corporate Brand Identity

## 1. Obiettivi e Principi Guida

1. **Brand Identity Unificata**: ogni documento generato verso clienti, committenti e partner (preventivi commerciali, contratti di assistenza sistemistica SLA, nomine DPA, rapportini di lavoro, rendiconti MPS e copie di cortesia fatture) deve esporre l'identità visiva formale dell'azienda.
2. **Zero-CDN & Architettura 100% Offline**: tutti gli asset grafici (logo aziendale, icone, font) devono risiedere localmente nel repository o essere incorporati in formato Data URI Base64. È vietata qualsiasi dipendenza da CDN esterne, internet o server remoti per il rendering.
3. **Multi-Formato Deterministico (DOCX, PDF, HTML)**: la generazione deve produrre output speculari e coerenti tra:
   - **Microsoft Word (.docx)** per documenti editabili, revisionabili con "Revisioni / Track Changes" e personalizzabili.
   - **Adobe PDF (.pdf)** pronto stampa A4 per invio immediato, firma grafometrica o firma digitale CAdES/PAdES.
   - **HTML Stand-alone (.html)** per consultazione immediata da browser web, anteprima reattiva e archiviazione documentale leggera.
4. **Zero-Hallucination & Provenance**: i dati anagrafici, fiscali e contabili devono essere ereditati rigidamente dalle anagrafiche YAML validate (`client-manifest.yaml`, `quote.schema.yaml`, `contract.schema.yaml`), senza alterazione o invenzione di cifre.

---

## 2. Specifiche di Brand Identity (Aure System)

### 2.1. Anagrafica Fiscale e Istituzionale
- **Denominazione Formale**: Aure System di Eduardo Possumato
- **Sede Operativa / Legale**: Via Luigi Tansillo, 54 F - 80125 Napoli (NA)
- **Partita IVA**: IT07714231219
- **Codice Fiscale**: PSSDRD...
- **Recapito Telefonico**: +39 333 7328065 / +39 081 1234567
- **PEC / Email**: salvatorepossumato@pec.it / info@auresystem.it
- **Web**: www.auresystem.it

### 2.2. Palette Cromatica Ufficiale
| Ruolo Cromatico | Codice HEX | Valore RGB | Utilizzo Principale |
| :--- | :--- | :--- | :--- |
| **Aure Deep Navy** | `#1E3A8A` | `rgb(30, 58, 138)` | Titoli primari (H1), intestazioni di tabella, totali in risalto. |
| **Tech Accent Blue** | `#2563EB` | `rgb(37, 99, 235)` | Sottotitoli (H2), separatori orizzontali, badge di stato, bordi box. |
| **Slate Dark Text** | `#0F172A` | `rgb(15, 23, 42)` | Testo corpo primario, dati cliente, prezzi riga. |
| **Slate Medium Muted** | `#64748B` | `rgb(100, 116, 139)` | Metadati, etichette secondarie, date di validità, note legali. |
| **Slate Soft Surface** | `#F8FAFC` | `rgb(248, 250, 252)` | Sfondo box anagrafici, righe alternate tabelle (zebra). |
| **Neutral Border** | `#CBD5E1` | `rgb(203, 213, 225)` | Bordature tabelle, cornici box informativi. |
| **Amber Accent** | `#B45309` | `rgb(180, 83, 9)` | Evidenziazione voci opzionali, avvertenze operative. |

### 2.3. Asset Ufficiali di Brand
I file sorgente del logo aziendale sono collocati in modo immutabile in `templates/assets/brand/`:
- `logo.png`: immagine PNG in alta definizione (500×500 px, canale Alpha per trasparenza, 449 KB), estratta dalla documentazione ufficiale Word.
- `logo.base64.txt`: codifica Base64 UTF-8 per inclusione automatica inline nei documenti HTML e PDF.

---

## 3. Standard Impaginativi per i Formati di Output

### 3.1. Specifiche Microsoft Word (.docx)
1. **Margini Standard**: 2,0 cm (0,8 pollici) su tutti i lati (superiore, inferiore, sinistro, destro).
2. **Intestazione (Header)**:
   - Tabella a 2 colonne invisibile (senza bordi).
   - Colonna sinistra: Logo aziendale scalato a larghezza fissa (1,2 pollici / 3,0 cm) con rapporto di forma vincolato.
   - Colonna destra: Dati aziendali completi del fornitore (Ragione sociale, Indirizzo, P.IVA, PEC, Telefono) allineati a destra in grigio scuro (`#64748B`, Pt 8.5).
3. **Gabbia Contenuti**:
   - Titolo Documento centrato in grassetto (`#1E3A8A`, Pt 16).
   - Box Contraenti (Fornitore a sinistra, Committente a destra) con sfondo `#F8FAFC` e bordo sottile `#CBD5E1`.
   - Tabelle prodotti/servizi con riga header blu navy (`#1E3A8A`) e testo bianco in grassetto.
   - Righe alternate con sfondo tenue per massimizzare la leggibilità.
   - Colonne numeriche monetarie strettamente allineate a destra con formato valuta `€ X.XXX,XX`.
4. **Piè di Pagina (Footer)**:
   - Linea orizzontale di separazione (`#E2E8F0`).
   - Dicitura di riservatezza e conformità GDPR: *"Documento commerciale riservato ad uso esclusivo del destinatario ai sensi del Reg. UE 2016/679."*
   - Numerazione automatica pagine standard Word (campo nativo Page su Pages).

### 3.2. Specifiche Adobe PDF (.pdf) via ReportLab
1. **Formato Pagina**: Standard europeo A4 (210 × 297 mm) con orientamento Portrait.
2. **Flowable Header**: Inserimento del logo aziendale ad alta risoluzione tramite `reportlab.platypus.Image` affiancato al blocco testuale istituzionale.
3. **Tipografia**: Helvetica / Helvetica-Bold con interlinea corretta (`leading`), evitando collisioni tra righe.
4. **Box Totali & Firme**:
   - Box totali allineato a destra con imponibile netto, IVA 22% e totale complessivo evidenziato.
   - Sezione firme su 2 colonne con ampi spazi per firma autografa o apposizione di token di firma digitale.

### 3.3. Specifiche HTML Stand-alone Print-Ready
1. **CSS @page Standard**:
   ```css
   @page {
     size: A4 portrait;
     margin: 15mm 20mm 15mm 20mm;
   }
   @media print {
     body { margin: 0; background: #fff; }
     .no-print { display: none; }
     .page-break { page-break-before: always; }
   }
   ```
2. **Zero-CDN Embedding**: Il logo è incorporato via `src="data:image/png;base64,{logo_b64}"` garantendo apertura istantanea anche su macchine isolate dalla rete o ambienti air-gapped.

---

## 4. Tipologie Documentali Supportate

1. **Preventivo & Proposta Commerciale (`quotes`)**:
   - Computo metrico diviso per categorie merceologiche (Hardware, Servizi, Licenze).
   - Gestione delle righe opzionali `[OPZIONE]` escluse dal computo vincolante.
   - Condizioni di fornitura, tempi di consegna e validità dell'offerta.
2. **Contratto di Assistenza SLA & DPA (`contracts`)**:
   - Perimetro sistemistico, finestre orarie di reperibilità, tempi di presa in carico SLA.
   - Pacchetto monte ore/giornate, tariffa fuori pacchetto, clausola di riservatezza e nomina a Responsabile del Trattamento (Art. 28 GDPR).
3. **Rapportino di Intervento Tecnico (`reports`)**:
   - Data, tecnico operatore, apparati coinvolti, descrizione attività svolta, ore impiegate e firme di collaudo/accettazione.
4. **Copia di Cortesia Fattura Elettronica (`invoices`)**:
   - Trasformazione grafica da XML SDI FPR12 a PDF/HTML istituzionale.

---

## 5. Matrice di Conformità e Collaudo

| Modulo | Output Richiesto | Criterio di Accettazione |
| :--- | :--- | :--- |
| **Asset Manager** | `logo.png` & `logo.base64.txt` | File presenti in `templates/assets/brand/`, validi, risoluzione >= 500px. |
| **DOCX Renderer** | File `.docx` con logo e stili | Header con logo non deformato, tabelle con colori corporate, footer numerato. |
| **PDF Renderer** | File `.pdf` conforme | Layout A4 perfetto, tabella leggibile, logo nitido, 0 errori ReportLab. |
| **HTML Renderer** | File `.html` zero-CDN | Rendering corretto offline in browser, stampa A4 perfetta. |
| **CLI `it-ops`** | Comandi `export` integrati | Sintassi unificata `.\it-ops.cmd export <slug> <tipo> [<id>]`. |
