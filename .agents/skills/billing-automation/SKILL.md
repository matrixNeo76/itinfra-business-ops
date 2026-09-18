---
name: billing-automation
description: Automazione fatturazione elettronica SDI (FatturaPA XML v1.2), scadenzario attivo B2B (30/60 DF FM, MP05/MP12), conguagli PSA/MPS e recupero crediti a norma di legge ex D.Lgs. 231/2002.
---

# 💶 Billing Automation — Fatturazione Elettronica SDI & Governance Contabile B2B Italiana

> **Standard Normativo**: Agenzia delle Entrate (Specifiche Tecniche FatturaPA v1.2 / FPR12), D.Lgs. 231/2002 (Ritardi di pagamento nelle transazioni commerciali).  
> **Brand & Titolarità**: **Aure System di Eduardo Possumato**  
> **Engine di Riferimento**: `scripts/pipelines/billing.py` (`BillingPipeline` / `it-ops billing`).

---

## 1. Visione & Modello di Business B2B (Italia vs SaaS USA)

A differenza dei software SaaS americani basati su addebiti automatici ricorsivi su carta di credito (`stripe_charge`), il modello commerciale di **Aure System** (Managed Service Provider & System Integrator) si fonda su transazioni B2B con obbligo di legge di **Fatturazione Elettronica tramite il Sistema di Interscambio (SDI)** e pagamenti canalizzati su circuiti bancari interbancari (Bonifico SEPA / Ri.Ba.).

### 🏢 Modello Ibrido a 4 Componenti di Ricavo:
1. **Canoni Assistenza & Helpdesk SLA Ricorrenti** (`contracts/ctr-*.yaml`): canone periodico anticipato con gestione monte ore e rollover.
2. **Rapportini Tecnici Spot / Extra-Soglia** (`timesheets/rap-*.yaml`): tariffazione a consuntivo per interventi straordinari o ore extra-budget.
3. **Ricambi Hardware & Apparati**: vendita hardware censita con matricola e numero di serie certificato.
4. **Noleggio Operativo Multifunzione (MPS)** (`mps/mps-*.yaml`): canone fisso mensile/semestrale + conguaglio per telelettura copie eccedenti mono/colore.

---

## 2. Specifiche Tecniche Fattura Elettronica SDI (`FatturaPA` v1.2)

Ogni emissione contabile genera un file XML conforme allo schema XSD ministeriale `FPR12`:

### 📋 Struttura Dati Obbligatoria:
* **`DatiTrasmissione`**:
  * `IdTrasmittente`: Codice fiscale o P.IVA del trasmittente (`IT00000000000`).
  * `ProgressivoInvio`: Identificativo univoco alfanumerico (es. `B260901`).
  * `FormatoTrasmissione`: `FPR12` (Fattura tra privati B2B).
  * `CodiceDestinatario`: Codice SDI a 7 caratteri (es. `SUBM70N`) oppure `0000000` con valorizzazione di `PECDestinatario`.
* **`CedentePrestatore`**: Dati fiscali e societari di **Aure System di Eduardo Possumato** (P.IVA, Sede, Regime Fiscale `RF01` ordinario).
* **`CessionarioCommittente`**: Dati cliente estratti da `client-manifest.yaml` (`Denominazione`, `IdFiscaleIVA`, `CodiceFiscale`, `Sede`).
* **`DatiGeneraliDocumento`**:
  * `TipoDocumento`: `TD01` (Fattura ordinaria).
  * `Divisa`: `EUR`.
  * `Data`: Formato ISO `YYYY-MM-DD`.
  * `ImportoTotaleDocumento`: Totale lordo comprensivo di IVA.
* **`DatiBeniServizi`**:
  * `DettaglioLinee`: Voci dettagliate con descrizione chiara, quantità, prezzo unitario e aliquota IVA (tipicamente `22.0`%).
  * `DatiRiepilogo`: Imponibile e imposta riepilogati per ciascuna aliquota IVA.
* **`DatiPagamento`**:
  * `CondizioniPagamento`: `TP01` (pagamento a rate / scadenzario) o `TP02` (pagamento completo).
  * `ModalitaPagamento`:
    * `MP05`: Bonifico bancario (metodo principale).
    * `MP12`: Ri.Ba. (Ricevuta Bancaria con emissione distinta CBI).
    * `MP09`: RID / SDD (SEPA Direct Debit per canoni ricorrenti).
  * `IBAN`: Coordinate bancarie del conto corrente Aure System dedicato per l'incasso.

---

## 3. Scadenzario Attivo & Calcolo Rate (DFFM)

La determinazione delle date di scadenza è rigorosa e deterministica:
* **`30_60_DF_FM` (30/60 Giorni Data Fattura Fine Mese)**:
  * Rata 1: 50% dell'importo lordo con scadenza all'ultimo giorno del mese successivo alla data fattura (+30 gg FM).
  * Rata 2: 50% dell'importo lordo con scadenza all'ultimo giorno del secondo mese (+60 gg FM).
* **`30_DF_FM` / `60_DF_FM` / `90_DF_FM`**: 100% dell'importo all'ultimo giorno del rispettivo mese.
* **`rimessa_diretta`**: Pagamento a vista entro 5 giorni dall'emissione fattura.

---

## 4. Dunning & Recupero Crediti B2B a Norma di Legge (D.Lgs. 231/2002)

Niente bot di riaddebito carta Stripe: la tutela del credito B2B in Italia segue il **Decreto Legislativo 9 ottobre 2002, n. 231**:

1. **Interessi Moratori Automatici**:
   * Scattano di diritto dal giorno successivo alla scadenza pattuita, senza necessità di formale messa in mora.
   * Tasso legale: Tasso BCE semestrale + **8 punti percentuali di maggiorazione**.
2. **Indennizzo Forfettario Spese**:
   * Diritto fisso di **€40,00** a titolo di risarcimento del danno per il recupero (Art. 6 D.Lgs. 231/2002).
3. **Procedura di Sollecito Graduata Aure System**:
   * **Livello 1 (Scadenza + 5 giorni)**: Email di promemoria cortese con allegata fattura di cortesia PDF e IBAN.
   * **Livello 2 (Scadenza + 15 giorni)**: Sollecito formale via PEC con conteggio interessi moratori ex D.Lgs. 231/2002.
   * **Livello 3 (Scadenza + 30 giorni)**: Diffida formale PEC e **blocco cautelativo erogazione SLA** (sospensione presa in carico ticket Jira e interventi tecnici on-site).

---

## 5. Comandi Operativi CLI (`it-ops billing`)

Tutte le operazioni contabili sono orchestrate deterministicamente dalla CLI di ITInfra Business Ops:

```powershell
# 1. Riepilogo posizioni aperte, fatture emesse e scadenziario
.\it-ops.cmd billing <slug> summary

# 2. Generazione del batch contabile mensile (JSON + XML FatturaPA)
.\it-ops.cmd billing <slug> generate --period 2026-09

# 3. Visualizzazione anteprima / vista di cortesia fattura
.\it-ops.cmd billing <slug> view --batch-id BILL-202609-<slug>

# 4. Registrazione incasso rata con riconciliazione contabile CRO bancario
.\it-ops.cmd billing <slug> pay --batch-id BILL-202609-<slug> --inst 1 --tx "CRO1234567890"
```

---

## 6. Guardrail di Integrità Fiscale

* **Zero-Hallucination su Dati Bancari**: L'IBAN del fornitore non deve mai essere attribuito al cliente o viceversa.
* **Verifica Partita IVA**: Controllo formale a 11 cifre con checksum di Luhn per operatori italiani.
* **Quadratura Matematica dei Centesimi**: Somma delle rate esattamente coincidente al centesimo di euro con l'importo totale documento (gestione arrotondamento sull'ultima rata).
