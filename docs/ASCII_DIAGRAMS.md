---
okf_version: "0.2"
id: "spec-ops-ascii-diagrams"
title: "Diagrammi Architetturali e Operativi ASCII — itinfra & itinfra-business-ops"
type: "specification"
domain: "Business Operations & System Architecture"
tags: ["okf-v0.2", "ascii-art", "diagrams", "architecture", "hub-and-spoke", "pipelines"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
lang: "it"

entities:
  - name: "ASCII Architectural Visualizations"
    type: "specification"
    description: "Rappresentazioni grafiche testuali ASCII/Unicode Box-Drawing universalmente leggibili in terminale, editor e web"
  - name: "Hub-and-Spoke Federation Topology"
    type: "pattern"
    description: "Topologia di collegamento deterministico tra ingegneria dei sistemi (itinfra) e operations/finance (itinfra-business-ops)"
  - name: "Pipeline Execution State Machines"
    type: "pattern"
    description: "Macchine a stati e flussi decisionali per le 7 pipeline di business e per il ciclo tecnico a 7 fasi di itinfra"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "documents"
    weight: 1.0
    description: "Compendio visuale ASCII di tutte le pipeline censite nell'indice master"
  - targetTitle: "Architettura di Repository Hub-and-Spoke"
    targetId: "spec-ops-architecture"
    relationType: "illustrates"
    weight: 1.0
    description: "Illustra l'interazione tra i due repository federati"
---

# 📐 Diagrammi ASCII Markdown: Architettura & Pipeline Operative

Questo documento raccoglie tutti i **diagrammi architetturali e di flusso in formato ASCII / Unicode Box-Drawing** per:
1. L'architettura federata **Hub-and-Spoke** tra `itinfra` e `itinfra-business-ops`.
2. La **Pipeline Tecnica Principale di `itinfra`** (Ciclo di Vita Ingegneristico a 7 Fasi).
3. Le **7 Pipeline di Business Operations** (da Pipeline A a Pipeline G).

I diagrammi sono ottimizzati per una resa impeccabile in qualsiasi editor testuale, terminale PowerShell/Bash e visualizzatore Markdown senza dipendere da renderer esterni o connessioni di rete.

---

## 🏛️ 1. Architettura Federata Hub-and-Spoke (`itinfra` ⟷ `itinfra-business-ops`)

```text
                  ╔═══════════════════════════════════════════════╗
                  ║           SHARED CUSTOMER SLUG                ║
                  ║       <slug> (es. "severino-srl")             ║
                  ╚═══════════════════════╦═══════════════════════╝
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼                                             ▼
  ┌─────────────────────────────────┐           ┌─────────────────────────────────┐
  │   REPOSITORIO TECNICO ITINFRA   │           │ REPOSITORIO ITINFRA-BUSINESS-OPS│
  │    (Technical Ground Truth)     │           │   (Commercial / PSA / Finance)  │
  ├─────────────────────────────────┤           ├─────────────────────────────────┤
  │ • manifest.yaml (Progetto IT)   │           │ • client-manifest.yaml (Client) │
  │ • 01-Assessment / 02-HLD        │           │ • contracts/ (SLA & Monte Ore)  │
  │ • 03-LLD / 04-Network-IPAM      │           │ • timesheets/ (Rapportini Tec.) │
  │ • 05-Runbook (Procedure Op.)    │           │ • invoices/ (Fatture SDI v1.2)  │
  │ • 06-As-Built.md (Apparati/SN)  │◄──Read-───│ • quotes/ (Offerte Cost-Plus)   │
  │ • 07-Test-Report / 09-Inventory │   Only    │ • mps/ (Noleggio Stampanti MPS) │
  │ • NIS2 & ISO 27001 Compliance   │   Bridge  │ • furniture/ (Commesse Arredo)  │
  └─────────────────────────────────┘           └─────────────────────────────────┘
                   │                                             │
                   ▼                                             ▼
          CLI Ingegneristica:                           CLI Operativa & PSA:
              `it <cmd>`                                   `it-ops <cmd>`
```

---

## ⚙️ 2. Pipeline Tecnica Principale di `itinfra` (Ciclo Ingegneristico a 7 Fasi)

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                      PIPELINE PRINCIPALE ITINFRA (7 FASI)                   │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 1: Valutazione & Strategia]      ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  01-Assessment.md (Stato Attuale)  ──►  02-HLD.md (High Level Architecture) │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 2: Ingegneria di Dettaglio]      ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  03-LLD.md (Low Level Design)      ──►  04-Network-IPAM.md (Subnet/VLAN/IP) │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 3: Piani di Implementazione]     ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  05-Runbook.md (Piani di Migrazione, Cut-Over e Procedure Operative)        │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 4: Collaudo & Validazione]       ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  06-As-Built.md (Config & Serials) ──►  07-Test-Report.md (FAT/SAT & Cert)  │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 5: Consegna & Operations]        ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  08-Handover-Operations.md         ──►  09-Handover-Inventory.md            │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │
  [FASE 6-7: Incident & Compliance]      ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  10-Incident-RCA.md (Post-Mortem)  ──►  Audit NIS2 & Matrice ISO 27001      │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📑 3. Pipeline A — Contratti di Assistenza IT, SLA & Monte Ore

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

## ⏱️ 4. Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi

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

## 💳 5. Pipeline C — Fatturazione SDI v1.2 & Scadenzario Multi-Rata

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

## 📅 6. Pipeline D — Task Jira & Schedulazione Agenda RFC 5545

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

## 📊 7. Pipeline E — Preventivazione Multiprodotto Cost-Plus

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

## 🖨️ 8. Pipeline F — Noleggio Multifunzione MPS & Telemetria SNMP

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

## 🪑 9. Pipeline G — Commesse Arredo Ufficio & Collaudo Finale

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
