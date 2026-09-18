---
okf_version: "0.2"
id: "spec-ops-pipeline-c-billing"
title: "Pipeline C — Fatturazione Elettronica SDI v1.2 & Scadenzario Multi-Rata"
type: "specification"
domain: "Business Operations & Finance"
tags: ["okf-v0.2", "pipeline-c", "billing", "sdi-v1.2", "fatturapa", "scadenzario", "multi-rata"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
lang: "it"

entities:
  - name: "Aggregation Billing Engine"
    type: "pattern"
    description: "Motore di consolidamento a fine mese di tutte le fonti di ricavo (canoni, spot, extra ore, ricambi, MPS)"
  - name: "FatturaPA SDI v1.2 XML Builder"
    type: "toolchain"
    description: "Generatore deterministico di tracciati formali FPR12 conformi alle specifiche dell'Agenzia delle Entrate"
  - name: "End-of-Month Multi-Installment Calculator"
    type: "pattern"
    description: "Algoritmo per ripartizione automatica importi e scadenze a 30/60 giorni fine mese"
  - name: "Accounts Receivable Ledger"
    type: "specification"
    description: "Scadenzario partite aperte con registrazione incassi e codici di riconciliazione bancaria"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "implements"
    weight: 1.0
    description: "Modulo di liquidazione finanziaria del compendio operativo"
  - targetTitle: "Pipeline A — Contratti SLA, Monte Ore & Over-Budget"
    targetId: "spec-ops-pipeline-a-contracts"
    relationType: "references"
    weight: 1.0
    description: "Riceve canoni periodici e addebiti extra-soglia"
  - targetTitle: "Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi"
    targetId: "spec-ops-pipeline-b-reports"
    relationType: "references"
    weight: 1.0
    description: "Riceve interventi spot da fatturare e ricambi consumati"
  - targetTitle: "Pipeline F — Noleggio Multifunzione MPS & Telemetria SNMP"
    targetId: "spec-ops-pipeline-f-mps-rental"
    relationType: "references"
    weight: 0.95
    description: "Riceve canoni semestrali base stampanti e conguagli costo copia"
---

# 💶 Pipeline C — Fatturazione Elettronica SDI v1.2 & Scadenzario

## 1. Obiettivi e Ambito Operativo
La **Pipeline C** governa il flusso di cassa e la liquidazione economica dell'azienda:
* Aggregazione automatica multi-fonte a fine mese per azzerare il mancato fatturato.
* Generazione del tracciato ministeriale **XML FatturaPA SDI v1.2** (formato FPR12 per transazioni B2B tra privati).
* Calcolo rigoroso dello scadenziario finanziario con ripartizione in rate percentuali e allineamento all'ultimo giorno del mese.
* Tracciamento dello stato di incasso (partita aperta, parziale, saldata) con associazione del CRO/ID transazione.

---

## 2. Diagramma di Flusso Esecutivo

```mermaid
flowchart TD
    subgraph Sources ["📥 Fonti di Ricavo Integrate"]
        S1["Canoni Assistenza IT (Pipeline A)"]
        S2["Ore Extra-Soglia Over-Budget (Pipeline A)"]
        S3["Interventi Tecnici Spot (Pipeline B)"]
        S4["Ricambi & Hardware Consumato (Pipeline B)"]
        S5["Canoni Base Multifunzione (Pipeline F)"]
        S6["Conguaglio Copie BN / Colore (Pipeline F)"]
        S7["Milestone SAL Commesse Arredo (Pipeline G)"]
    end

    ENGINE["⚙️ Aggregation Engine<br/>(it-ops billing generate)"]
    JSON_BATCH["Salvataggio Batch Dati<br/>(bill-YYYYMM-slug.json)"]
    XML_SDI["Generazione Tracciato FPR12<br/>(bill-YYYYMM-slug.xml)"]
    TERMS_CHECK{"Termini di Pagamento?"}
    SPLIT_3060["Split 50% / 50%<br/>Scadenza: 30 gg FM & 60 gg FM"]
    SINGLE_INST["Rata Singola 100%<br/>Scadenza: 30 gg FM o Rimessa"]
    LEDGER["Scadenzario Finanziario Attivo"]
    PAY_CMD["Registrazione Incasso Bancario<br/>(it-ops billing pay)"]

    Sources --> ENGINE
    ENGINE --> JSON_BATCH
    ENGINE --> XML_SDI
    ENGINE --> TERMS_CHECK
    TERMS_CHECK -->|30_60_DF_FM| SPLIT_3060 --> LEDGER
    TERMS_CHECK -->|Altro| SINGLE_INST --> LEDGER
    LEDGER --> PAY_CMD
```

---

## 3. Struttura del Tracciato SDI v1.2 & Calcolo Scadenze

### 3.1 Nodi Obbligatori FatturaPA (FPR12)
* `<FatturaElettronicaHeader>`:
  * `<DatiTrasmissione>`: ID Trasmittente, Progressivo Invio, Codice Destinatario (7 caratteri SDI o 7 zeri con PEC).
  * `<CedentePrestatore>`: Dati fiscali ITInfra (P.IVA, C.F., Regime Fiscale RF01 Ordinario, Sede legale).
  * `<CessionarioCommittente>`: Anagrafica cliente derivata da `client-manifest.yaml`.
* `<FatturaElettronicaBody>`:
  * `<DatiGeneraliDocumento>`: TipoDocumento `TD01`, Divisa `EUR`, Data e Importo Totale Lordo.
  * `<DatiBeniServizi>`: Dettaglio linee con quantità, prezzo unitario, aliquota IVA (22%) e totale riga.
  * `<DatiRiepilogo>`: Imponibile complessivo, imposta IVA calcolata ed esigibilità `I` (Immediata).
  * `<DatiPagamento>`: Condizioni `TP02` (Completo), Modalità `MP05` (Bonifico), Scadenze e IBAN di accredito.

### 3.2 Regola di Calcolo Rate a Fine Mese (`30_60_DF_FM`)
Dato l'importo totale $T_{gross}$ e la data fattura $D$:
1. **Rata 1**:
   $$A_1 = \text{round}(T_{gross} / 2, 2)$$
   $$\text{Scadenza}_1 = \text{EndOfMonth}(D + 30 \text{ giorni})$$
2. **Rata 2**:
   $$A_2 = T_{gross} - A_1$$
   $$\text{Scadenza}_2 = \text{EndOfMonth}(D + 60 \text{ giorni})$$

---

## 4. Schemi & Comandi CLI

* **Schema Formale**: `schemas/billing.schema.yaml`
* **Percorso Storage**: `clients/<slug>/invoices/bill-<YYYYMM>-<slug>.json` e `.xml`

### Sintassi Comandi:
```powershell
# Calcolare e salvare il batch contabile con XML SDI formale
.\it-ops.cmd billing <slug> generate --period 2026-09

# Registrare l'incasso bancario di una rata nello scadenzario
.\it-ops.cmd billing <slug> pay `
  --batch-id BILL-202609-severino-srl `
  --inst 1 `
  --tx "CRO-123456789012"
```


---

## 5. Gestione Crediti, Interessi di Mora & Recupero ex D.Lgs. 231/2002 (SPEC-24)

### 5.1 Calcolo Automatico Interessi Moratori Commerciali
Nelle transazioni B2B tra imprese, in caso di ritardo nel pagamento delle fatture attive:
- **Decorrenza Automatica**: Gli interessi di mora decorrono ipso iure dal giorno successivo alla scadenza pattuita, senza obbligo di preventiva costituzione in mora (Art. 4 D.Lgs. 231/2002).
- **Tasso Legale di Mora**: Tasso BCE sulle operazioni di rifinanziamento principale + maggiorazione legale **+8.00%** (es. BCE 3.50% $\rightarrow$ **11.50% annuo**).
- **Formula di Calcolo**:
  $$\text{Interessi} = \frac{\text{Capitale Insoluto} \times \text{Tasso Mora} \times \text{Giorni Ritardo}}{365}$$
- **Risarcimento Forfettario dei Costi di Recupero (Art. 6)**: Spetta al creditore, per ciascuna fattura scaduta e senza necessità di prova del danno, l'importo fisso di **€ 40,00**.

### 5.2 Strategia di Sollecito Graduata a 3 Stadi
Il modulo `ItalianComplianceGuard` e la CLI `it-ops credit remind` generano formalmente:
1. **Stadio 1 (Scaduta da 7 a 14 giorni)**: *Avviso di Cortesia / Promemoria* (invito bonario al saldo con coordinate IBAN).
2. **Stadio 2 (Scaduta da 15 a 30 giorni)**: *Sollecito Formale con Addebito Mora 231 & 40 €* (estratto conto analitico con sorte capitale, mora al centesimo e risarcimento spese).
3. **Stadio 3 (Scaduta da oltre 30 giorni)**: *Diffida ad Adempiere e Costituzione in Mora ex Art. 1219 C.C.* (termine perentorio di 5 giorni, preavviso immediato di sospensione supporto SLA e passaggio al legale per decreto ingiuntivo provvisoriamente esecutivo).

### 5.3 Presidio Fiscale Deterministico in Entrata
Tutti i dati fiscali associati al cliente sono convalidati all'origine da `ItalianComplianceGuard`:
- Partita IVA a 11 cifre con verifica algebrica Luhn modificato italiano.
- Codice Fiscale a 16 caratteri conforme al DM 23/12/1976 con gestione ufficiale omocodie (lettere L..V).
- Canale SDI conforme alle specifiche dell'Agenzia delle Entrate (7 car. B2B, 6 car. IPA per PA, 0000000 + PEC).
