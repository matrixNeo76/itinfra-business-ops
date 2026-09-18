# 🔄 Le 11 Pipeline Operative di itinfra-business-ops

Guida dettagliata al funzionamento deterministico delle pipeline da A a K con diagrammi di flusso ASCII.

> 📄 *Per il compendio architetturale completo, consulta [`docs/ASCII_DIAGRAMS.md`](ASCII_DIAGRAMS.md).*

---

### Pipeline A — Contratti di Assistenza IT (SLA & Monte Ore)
* **Scopo**: Trasformare i contratti cartacei in regole deterministiche per i tecnici.
* **Artefatti**: `clients/<slug>/contracts/ctr-*.yaml`
* **Workflow**:
  1. `Drafting & Quoting`: Definizione SLA, copertura apparati e monte ore/canone flat.
  2. `Activation`: Attivazione contratto e aggancio asset As-Built.
  3. `Monitoring`: Alert a 60/30/15 giorni dalla scadenza o al raggiungimento dell'80% del monte ore consumato.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│              PIPELINE A: CONTRATTI DI ASSISTENZA IT, SLA & MONTE ORE          │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌───────────────────────────────┐                     ┌─────────────────────────┐
│ Contratto Monte Ore           │                     │ Contratto Flat MSP      │
│ (hours_bank: 40.0 h)          │                     │ (msp_flat: canone fisso)│
└──────────────┬────────────────┘                     └────────────┬────────────┘
               │                                                   │
               ▼                                                   │
┌───────────────────────────────┐                                  │
│ Esecuzione Rapportino (Pip B) │                                  │
│ Netto Intervento: es. 3.5 h   │                                  │
└──────────────┬────────────────┘                                  │
               │                                                   │
               ▼                                                   ▼
┌───────────────────────────────┐                     ┌─────────────────────────┐
│ Verifica Capienza Residua     │                     │ Nessun Decremento Ore   │
│ Disponibili: 2.0 h | Usate: 3.5│                    │ Attività Coperte        │
└──────────────┬────────────────┘                     └─────────────────────────┘
               │
      ┌────────┴────────────────────────┐
      ▼                                 ▼
┌───────────────────────────┐     ┌─────────────────────────────────────────────┐
│ Entro Soglia (2.0 h)      │     │ Extra-Soglia / Over-Budget (1.5 h)          │
│ • Scalate dal Monte Ore   │     │ • Scorporo automatico nel rapportino        │
│ • Residuo = 0.0 h         │     │ • Tariffazione oraria maggiorata (es. 75€/h)│
│ • Alert 80% / Esaurimento │     │ • Instradamento automatico a Fatturazione C │
└───────────────────────────┘     └─────────────────────────────────────────────┘
```

---

### Pipeline B — Rapportini di Assistenza (Time-Tracking & Ledger Debit)
* **Scopo**: Rendicontazione degli interventi e scarico automatico del monte ore.
* **Artefatti**: `clients/<slug>/timesheets/rap-*.yaml`
* **Workflow**:
  1. `Check-in / Check-out`: Timestamp con calcolo netto ore e arrotondamento automatico a 15 minuti.
  2. `Technical Logging`: Descrizione attività e apparati impattati con verifica seriale As-Built.
  3. `Ledger Action`: Scarico dal contratto (`debit_contract`), fatturazione a parte (`invoice_spot`) o a forfait (`included_flat`).

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│          PIPELINE B: RAPPORTINI DI ASSISTENZA, FIRMA CANVAS & RICAMBI         │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Rilevazione Oraria]               ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Check-in: 09:10  ──►  Check-out: 11:18  (Lordo: 2h 08m)                     │
  │ Algoritmo di Arrotondamento ai 15 min: `ceil(128 / 15) * 0.25` = 2.25 ore   │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Cross-Check Asset & Ricambi]      ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Apparato Oggetto: SRV-DELL-R450 (S/N: 4F92KD3)                              │
  │ Verifica As-Built: [PASS] Apparato censito in itinfra (06-As-Built.md)      │
  │ Ricambio Installato: SSD NVMe 1.92TB Enterprise (S/N: MZ7LH1T9-9821)        │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Firma Grafometrica Tablet]        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Dispositivo Mobile / Tablet: HTML5 Canvas Pad touch-enabled                 │
  │ Conversione Vettoriale Tratto: `canvas.toDataURL("image/png")`               │
  │ Salvataggio Payload: Base64 in `clients/<slug>/timesheets/rap-*.yaml`       │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Ledger Routing]                   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ SCELTA: `ledger_action: debit_contract`  ──►  Scala da Pipeline A (Monte Ore)│
  │ SCELTA: `ledger_action: invoice_spot`    ──►  Invia a Pipeline C (Fattura)   │
  │ SCELTA: `ledger_action: included_flat`   ──►  Registrazione a Canone        │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline C — Fatturazione & Scadenziario Attivo
* **Scopo**: Incasso, conguagli e scadenziario finanziario.
* **Artefatti**: `clients/<slug>/invoices/`
* **Workflow**:
  1. `Aggregation`: Raggruppamento canoni ricorsivi contrattuali + rapportini spot + eccedenze copie MPS.
  2. `FatturaPA / SDI v1.2`: Generazione tracciato XML con codice destinatario e aliquote IVA.
  3. `Scadenzario`: Gestione scadenze a 30/60 gg d.f. f.m. con tracking incassi e solleciti.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│        PIPELINE C: BATCH FATTURAZIONE SDI v1.2 & SCADENZARIO MULTI-RATA       │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Aggregatore Fonti Mensile]        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  Canoni Contrattuali A  │  Rapportini Spot B  │  Eccedenze Copie MPS F      │
  │     (es. 850.00 €)      │    (es. 225.00 €)   │        (es. 85.00 €)        │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Calcolo Fiscale & IVA]            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Totale Imponibile Netto: 1.160,00 €                                         │
  │ Aliquota IVA (22%):        255,20 €                                         │
  │ Totale Documento Lordo:  1.415,20 €                                         │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Generatore SDI FPR12]             ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ File XML Tracciato FatturaPA: `IT09876543210_00042.xml`                      │
  │ Dati Trasmissione: Codice Destinatario SDI / PEC + Split Payment/Regime     │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Scadenzario Condizioni 30/60 gg FM (50% / 50%)]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • Rata 1 (50%): 707,60 €  ──►  Scadenza: 30 gg Fine Mese (es. 2026-10-31)  │
  │ • Rata 2 (50%): 707,60 €  ──►  Scadenza: 60 gg Fine Mese (es. 2026-11-30)  │
  │                                                                             │
  │ Tracking Stato: [EMESSA] ──► [PARZIALMENTE SALDATA] ──► [SALDATA CHIUSA]    │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline D — Task Jira & Schedulazione Appuntamenti
* **Scopo**: Allineamento bidirezionale tra agenda/calendario e consuntivo ore ticket.
* **Artefatti**: `clients/<slug>/jira_sync.yaml`
* **Workflow**:
  1. Ricezione task Jira -> Schedulazione slot intervento a calendario.
  2. Esecuzione intervento -> Generazione rapportino Pipeline B.
  3. Esportazione standard RFC 5545 `.ics` per Outlook e Google Calendar.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│          PIPELINE D: TASK JIRA & SCHEDULAZIONE AGENDA RFC 5545 (ICS)          │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Input Ticket Jira / Service Desk] ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Issue: JIRA-8492 | Cliente: severino-srl | Priorità: CRITICAL (SLA: 2h)     │
  │ Oggetto: "Guasto Cluster Hyper-V e Switch di Core"                          │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Parser & Normalizzatore Agenda]   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Finestra Intervento Schedulata: 2026-09-18 09:00:00 -> 12:30:00 (Europe/Rome)│
  │ Tecnico Incaricato: andrea.m@azienda.it                                     │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Generatore RFC 5545 iCalendar Engine]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Esportazione File `.ics`: `clients/<slug>/agenda-2026-09.ics`               │
  │ • `BEGIN:VCALENDAR` / `BEGIN:VEVENT`                                        │
  │ • `UID: JIRA-8492-20260918T090000Z@itinfra-business-ops`                   │
  │ • `SUMMARY: [severino-srl] Guasto Cluster Hyper-V (SLA CRITICAL)`           │
  │ • `ALARM: -15m (Reminder Notifica Push per Tecnico)`                        │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Integrazione Client di Posta]     ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Sincronizzazione con: Microsoft Outlook, Google Calendar, Apple Calendar   │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline E — Preventivazione Multiprodotto
* **Scopo**: Offerte multiprodotto (Hardware, Licenze, Cablaggio, Arredo, Manodopera, Canoni) con ricarichi cost-plus.
* **Artefatti**: `clients/<slug>/quotes/quote-*.yaml`
* **Workflow**:
  1. Raccolta capitolato e calcolo costi base di acquisto per categoria.
  2. Applicazione matrice ricarichi percentuali (`markup_percent`).
  3. Calcolo marginalità lorda, esclusione righe opzionali ed export proposta grafica HTML.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│            PIPELINE E: PREVENTIVAZIONE MULTIPRODOTTO COST-PLUS & EXPORT       │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Raggruppamento per Categoria]     ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ [1] Hardware  [2] Software/Licenze  [3] Cablaggio  [4] Arredo  [5] Manodopera│
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Calcolo Riga & Ricarico Cost-Plus]▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Articolo: Server R450 | Costo (C): 2.150,00 € | Ricarico (M): 28.0%         │
  │ Formula Prezzo di Vendita (P): P = C × (1 + M / 100) = 2.752,00 €           │
  │ Totale di Riga: P × Quantità                                                │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Gestione Righe Opzionali]         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ `is_optional: false`  ──► Somma nel Totale Imponibile Offerta Vincolante    │
  │ `is_optional: true`   ──► Evidenziata in Offerta ma ESCLUSA dai Totali      │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Analisi di Marginalità & Export]  ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Margine Lordo Commessa: Imponibile Totale - Costo Totale (€ e %)            │
  │ Generazione Documento Grafico: `clients/<slug>/quotes/quote-*.html`         │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline F — Noleggio Multifunzione MPS (Costo Copia Completo)
* **Scopo**: Gestione flotta stampanti, telelettura contatori, canoni semestrali anticipati e consumabili toner.
* **Artefatti**: `clients/<slug>/mps/mps-*.yaml`
* **Workflow**:
  1. `Stipula Noleggio`: Canone base semestrale anticipato + quote copie incluse (es. 6000 BN / 1500 Colore).
  2. `Telelettura SNMP`: Rilevazione contatori totali da Printer MIB via socket UDP 161 puro.
  3. `Alert Consumabili`: Allarme preventivo ordine toner se livello $\le 15\%$.
  4. `Conguaglio Semestrale`: Calcolo eccedenze copie (Copie Effettive - Incluse) * tariffa unitaria.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│        PIPELINE F: NOLEGGIO MULTIFUNZIONE MPS, COSTO COPIA & SNMP             │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Telemetria SNMP Porta UDP 161]    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Multifunzione di Rete (es. Canon iR-ADV C3830i @ 192.168.10.25)             │
  │ Client UDP `scripts/core/snmp.py` (SNMP v2c - Zero librerie esterne)        │
  │ OID Contatori Totali: `1.3.6.1.2.1.43.10.2.1.4.1.1`                         │
  │ OID Livelli Toner (K-C-M-Y): `1.3.6.1.2.1.43.11.1.1.9.1.x`                  │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
  [2. Controllo Consumabili]                           [3. Conguaglio Copie]
┌────────────────────────────────────────┐   ┌──────────────────────────────────┐
│ Toner <= 15% ?                         │   │ Delta = Lettura_Oggi - Iniziale  │
│ • [Sì]: ALERT CRITICO CONSUMABILE      │   │ Eccedenza = Delta - Franchigia   │
│   Ordine automatico toner di scorta    │   │ Costo Ecc = Eccedenza × Tariffa  │
│ • [No]: Stato Regolare                 │   │ Totale = Canone Base + Costi Ecc │
└────────────────────────────────────────┘   └─────────────────┬────────────────┘
                                                               │
  [4. Integrazione con As-Built e Fatturazione]                ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • Verifica S/N Hardware con `06-As-Built.md` di itinfra (Cross-Check PASS)  │
  │ • Trasferimento del conguaglio semestrale alla Pipeline C (Fatturazione)    │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline G — Fornitura Arredo da Ufficio
* **Scopo**: Commesse complesse chiavi in mano di arredo, allestimento e pareti divisorie.
* **Artefatti**: `clients/<slug>/furniture/arr-*.yaml`
* **Workflow**:
  1. `1_survey`: Rilievo metrico laser e mappatura torrette dati/elettriche.
  2. `2_design`: Layout 2D CAD DWG e render 3D fotorealistici.
  3. `3_sampling_approval`: Approvazione campionari finiture e tessuti.
  4. `4_procurement`: Emissione ordini alle fabbriche produttrici.
  5. `5_assembly`: Posa in opera e montaggio a regola d'arte.
  6. `6_handover_approved`: Verbale di collaudo (checklist 4 punti) e firma accettazione cliente.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│              PIPELINE G: COMMESSE ARREDO UFFICIO & COLLAUDO FINALE            │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [Macchina a Stati Sequenziale in 6 Fasi]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ [1_survey]               Rilievo metrico laser & torrette dati pavimento    │
  │     │                                                                       │
  │     ▼                                                                       │
  │ [2_design]               Layout 2D/3D CAD & computo metrico estimativo      │
  │     │                                                                       │
  │     ▼                                                                       │
  │ [3_sampling_approval]    Approvazione campionari finiture e tessuti cliente │
  │     │                                                                       │
  │     ▼                                                                       │
  │ [4_procurement]          Emissione ordini di produzione fabbriche arredo    │
  │     │                                                                       │
  │     ▼                                                                       │
  │ [5_assembly]             Posa in opera, montaggio a regola d'arte & pulizia │
  │     │                                                                       │
  │     ▼                                                                       │
  │ [6_handover_approved]    Collaudo con checklist & firma verbale accettazione│
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [Checklist di Collaudo a 4 Punti Vincolanti]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ [x] Stabilità Meccanica & Allineamento Giunzioni                            │
  │ [x] Funzionamento Torrette Elettriche & Passacavi Top Scrivania             │
  │ [x] Assenza Assoluta di Graffi o Difetti Superficiali                       │
  │ [x] Smaltimento Totale Imballaggi & Pulizia Finale Ambienti                 │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌────────────────────────────────────────┐   ┌──────────────────────────────────┐
│ Se TUTTI i 4 Check Superati:           │   │ Se ALMENO 1 Check Fallito:       │
│ • Firma Digitale del Cliente           │   │ • Riapertura ticket di montaggio │
│ • Generazione Verbale HTML Certificato │   │ • Blocco sblocco fattura saldo   │
│ • Sblocco Rata Finale Saldo (Pip C)    │   │ • Sostituzione pezzo / regolaz.  │
└────────────────────────────────────────┘   └──────────────────────────────────┘
```

---

### Pipeline H — Ingestione Documenti SOTA (Pixel-to-Markdown) & OKF v0.2
* **Scopo**: Acquisizione visiva nativa di documenti analogici/digitali (PDF, scansioni, preventivi, contratti cartacei) con ricostruzione deterministica delle tabelle, isolamento in pacchetti modulari OKF v0.2 e audit matematico/legale.
* **Artefatti**: `docs/<slug>/00-overview.okf.md`, `01-*.okf.md`, `02-*.okf.md`, `03-audit-*.okf.md`
* **Workflow**:
  1. `Pixel-Level Visual Ingestion`: Analisi visiva nativa (Deep Thinking) con decodifica layout multicolonna, note a margine, firme e tabelle contabili.
  2. `Modular Decomposition`: Suddivisione logica del documento in pacchetto modulare (Overview, Specifiche Tecniche, Computo Economico, Audit).
  3. `Deterministic Auditing`: Verifica formale tramite motori di audit 2026 (`ContractAuditEngine`, `QuoteAuditEngine`) per validare quadrature al centesimo, clausole ISTAT, arrotondamenti e conformità legale.
  4. `CLI Ingestion & Routing`: Popolamento deterministico degli artefatti gestionali del cliente (`clients/<slug>/`).

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│        PIPELINE H: INGESTIONE VISIVA SOTA (PIXEL-TO-MARKDOWN) & OKF v0.2      │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Acquisizione Ottica / PDF]        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ File Input: Cartaceo Scansionato / PDF Vettoriale Fornitore                 │
  │ Analisi Visiva Nativa (Deep Thinking): Ricostruzione celle, firme, colonne  │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Modularizzazione OKF v0.2]        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Creazione Pacchetto Modulare in `docs/<slug>/`:                             │
  │ • 00-overview.okf.md         (Identità, Frontmatter YAML, Punti Chiave)     │
  │ • 01-specifiche-*.okf.md     (Architettura, SLA, Hardware, Clausole)        │
  │ • 02-computo-economico.okf.md(Tabelle Prezzi, Sconti, Aliquote IVA, Totali) │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Motori di Audit Deterministici]   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • ContractAuditEngine: Verifica canone SLA, soglie ore, ISTAT, recesso      │
  │ • QuoteAuditEngine: Verifica quadratura somme, coerenza IVA, margini        │
  │ Generazione: 03-audit-<tipo>-2026.okf.md con esito PASS/FAIL e note legali  │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Ingestione Operativa nei Clienti] ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Comando CLI: `it-ops ingest docs/<slug>/00-overview.okf.md --apply`          │
  │ ➔ Popola `clients/<slug>/contracts/` o `clients/<slug>/quotes/`              │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline I — Memoria Auto-Correttiva Attestata & Cognitive Bridge
* **Scopo**: Prevenzione permanente delle regressioni agentiche (errori ripetuti di UI, compilazione documenti o fast-path), memorizzazione attestata SHA-256 e federazione bidirezionale con `itinfra`.
* **Artefatti**: `docs/concepts/LES-*.okf.md`, `.agents/rules/01-self-correcting-memory.md`, `../itinfra/projects/_global_scratchpad.md`
* **Workflow**:
  1. `Incident Capture`: Intercettazione di anomalie comportamentali (es. UI in iframe con scrollbar, mancato MSS clamping).
  2. `Attestation & Hashing`: Creazione nodo concettuale OKF v0.2 con classificazione Trust Tier (`attested`), revisione umana e calcolo hash crittografico SHA-256 anti-tampering.
  3. `Live Rule Compilation`: Compilazione deterministica istantanea nel file direttive `.agents/rules/01-self-correcting-memory.md` per renderlo attivo a 0 token all'avvio sessione.
  4. `Cognitive Bridge Federation`: Promozione guidata da L2 Staging Scratchpad (`_global_scratchpad.md`) a Guardrail Attestato con blocco atomico multipiattaforma e sanificazione multi-tenant.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│     PIPELINE I: MEMORIA AUTO-CORRETTIVA ATTESTATA & COGNITIVE BRIDGE          │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Cattura Anomalia / Lezione]       ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Regressione o Lezione Tecnica Rilevata (Chat, CLI, Collaudo o Incident)     │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Creazione Nodo OKF v0.2 & SHA-256]▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Generazione: `docs/concepts/LES-*.okf.md`                                   │
  │ Metadati: Trust Tier `attested`, verified: true, rule_category              │
  │ Anti-Tampering: Hash SHA-256 calcolato sui campi semantici vincolanti       │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Compilazione Automatica Regole]   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Comando: `it-ops learn sync`                                                │
  │ Output: `.agents/rules/01-self-correcting-memory.md`                        │
  │ Effetto: Regola caricata a 0 secondi all'avvio sessione per Antigravity/AI  │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. SPEC-17 Cognitive Bridge (Cross-Repo itinfra)]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • Lock Concorrente: `projects/_global_scratchpad.lock`                      │
  │ • Sanificazione: `MultiTenantSanitizer` (Zero IP, domini o credenziali)     │
  │ • Promozione: `it-ops learn promote <id> --code LES-NET-XXX`                │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline J — Gap Analysis, Compliance D.Lgs. 231/2001 & Vulnerability Assessment (CVSS v4.0)
* **Scopo**: Certificazione della conformità al D.Lgs. 231/2001 (Art. 24-bis reati informatici), ISO/IEC 27001:2022 e NIST CSF v2.0, calcolo deterministico del gap, penalità CVSS v4.0 FIRST, generazione del Remediation Plan prioritizzato e verifica Shadow IT con l'As-Built di `itinfra`.
* **Artefatti**: `clients/<slug>/gap_analysis/ga-*.yaml`, `01-verbale-kickoff.md`, `02-rapporto-gap-analysis-remediation.md` & `.pdf`, `03-rapporto-vulnerability-assessment.md` & `.pdf`, `04-executive-presentation-odv.html`.
* **Workflow**:
  1. `Documentary Review & Interviews`: Riesame di 7 documenti formali e svolgimento delle interviste sulle 5 aree canoniche.
  2. `Vulnerability Assessment & CVSS v4.0`: Scansione host e servizi con calcolo delle penalità tecniche.
  3. `Gap Calculation & Remediation Engine`: Calcolo ponderato (25% doc, 50% interviste, 25% VA), maturità CMMI (1.0-5.0) e generazione automatica roadmap correttiva (P1/P2/P3).
  4. `Deliverable Generation & Sigillo SHA-256`: Emissione dei verbali, report peritali in Markdown e PDF vettoriale ad alta risoluzione con logo ufficiale Aure System e dashboard HTML per OdV e CDA.
  5. `itinfra Hub-and-Spoke Cross-Check`: Riconciliazione tra gli IP target scansionati e gli asset IPAM/As-Built di `itinfra` con alert immediato in caso di Shadow IT.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│     PIPELINE J: GAP ANALYSIS & COMPLIANCE D.LGS. 231/01 (ART. 24-BIS)        │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [1. Acquisizione Evidenze]            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • Documenti Formali (7 minimi: MOG 231, Codice Etico, Policy ICT, BCP/DR)   │
  │ • Interviste 5 Aree: CISO, IT Ops, Risk/Compliance, Acquisti, Sicurezza     │
  │ • Vulnerability Assessment: Rilevazione debolezza con scoring CVSS v4.0     │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [2. Scoring Deterministico & CMMI]    ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Conformita' = 25% Doc + 50% Interviste + 25% VA (Penalita' CVSS v4.0 FIRST) │
  │ Maturita' CMMI = 1.0 + (Conformita' / 100) * 4.0 (Scala 1.0 - 5.0)         │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [3. Remediation Engine Prioritizzato] ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Generazione Azioni: P1_CRITICAL (15 gg) | P2_HIGH (45 gg) | P3_MEDIUM (90 gg│
  │ Correlazione automatica: Reati presupposto ex Art. 24-bis D.Lgs. 231/01     │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [4. Sigillo Forense & Deliverables]   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ • Sigillo Immutabile SHA-256 su payload canonico normalizzato               │
  │ • Deliverables: 01-Kickoff, 02-Rapporto Gap (MD+PDF), 03-VA (MD+PDF)        │
  │ • 04-Executive Dashboard HTML interattiva e print-ready per CDA e OdV       │
  └─────────────────────────────────────┬───────────────────────────────────────┘
                                        │
  [5. Bridge Federato itinfra (As-Built)]
                                        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Cross-check: IP Scansionati vs 04-Network-IPAM.md & 06-As-Built.md          │
  │ Esito: Copertura contrattuale certificata oppure ALLERTA SHADOW IT          │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

### Pipeline K — Unified Client Onboarding Orchestrator (Zero-Drift Dual Storage)
* **Scopo**: Creazione atomica e deterministica di nuovi clienti sia nel repository commerciale (`clients/<slug>/`) sia nel repository tecnico (`../itinfra/projects/<slug>/`), con certificazione istantanea di zero-drift, subnet IPAM e assegnazione profilo di servizio (Silver, Gold, Platinum).
* **Artefatti**: `clients/<slug>/client-manifest.yaml`, `contracts/ctr-*.yaml`, `quotes/quote-*.yaml`, `mps/mps-*.yaml`, `gap_analysis/ga-*.yaml`, e in `itinfra`: `manifest.yaml`, `01-Executive-Summary.md`, `04-Network-IPAM.md`, `06-As-Built.md`.
* **Workflow**:
  1. `Parameter Ingestion & Tier Selection`: Acquisizione ragione sociale, identificativi fiscali, subnet IP e livello di servizio.
  2. `Commercial Provisioning`: Generazione fascicolo commerciale completo con monte ore SLA associato.
  3. `Technical Workspace Provisioning`: Generazione documentazione ingegneristica con calcolo pool DHCP/IPAM e baseline apparati.
  4. `Zero-Drift Cross-Check`: Validazione istantanea con `ITInfraBridge.check_slug` e apposizione del sigillo SHA-256.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│       PIPELINE K: UNIFIED CLIENT ONBOARDING (DUAL-STORAGE ZERO-DRIFT)         │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌────────────────────────────────────────┐ ┌────────────────────────────────────────┐
│ Workspace itinfra-business-ops         │ │ Workspace itinfra (Tecnico)            │
│ clients/<slug>/                        │ │ projects/<slug>/                       │
├────────────────────────────────────────┤ ├────────────────────────────────────────┤
│ • client-manifest.yaml                 │ │ • manifest.yaml (Sincronizzato)        │
│ • contracts/ctr-<slug>-2026.yaml       │ │ • 01-Executive-Summary.md              │
│ • quotes/quote-<slug>-01.yaml          │ │ • 04-Network-IPAM.md (Subnet calcolata)│
│ • mps/mps-<slug>-01.yaml               │ │ • 06-As-Built.md (Baseline apparati)   │
│ • gap_analysis/ga-<slug>-01.yaml       │ │ • 02, 03, 05 (DR Plan, Survey, LLD)    │
└────────────────────────────────────────┘ └────────────────────────────────────────┘
             │                                                     │
             └──────────────────────────┬──────────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────────────────────────┐
        │ Validazione Bridge & Certificazione Zero-Drift Eseguita       │
        └───────────────────────────────────────────────────────────────┘
```
