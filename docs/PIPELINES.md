# 🔄 Le 7 Pipeline Operative di itinfra-business-ops

Guida dettagliata al funzionamento deterministico delle pipeline da A a G.

---

### Pipeline A — Contratti di Assistenza IT (SLA & Monte Ore)
* **Scopo**: Trasformare i contratti cartacei in regole deterministiche per i tecnici.
* **Artefatti**: `clients/<slug>/contracts/ctr-*.yaml`
* **Workflow**:
  1. `Drafting & Quoting`: Definizione SLA, copertura apparati e monte ore/canone flat.
  2. `Activation`: Attivazione contratto e aggancio asset As-Built.
  3. `Monitoring`: Alert a 60/30/15 giorni dalla scadenza o al raggiungimento dell'80% del monte ore consumato.

---

### Pipeline B — Rapportini di Assistenza (Time-Tracking & Ledger Debit)
* **Scopo**: Rendicontazione degli interventi e scarico automatico del monte ore.
* **Artefatti**: `clients/<slug>/timesheets/rap-*.yaml`
* **Workflow**:
  1. `Check-in / Check-out`: Timestamp con calcolo netto ore e arrotondamento automatico a 30 minuti.
  2. `Technical Logging`: Descrizione attività e apparati impattati.
  3. `Ledger Action`: Scarico dal contratto (`debit_contract`), fatturazione a parte (`invoice_spot`) o a forfait (`included_flat`).

---

### Pipeline C — Fatturazione & Scadenziario Attivo
* **Scopo**: Incasso, conguagli e scadenziario finanziario.
* **Artefatti**: `clients/<slug>/invoices/`
* **Workflow**:
  1. `Aggregation`: Raggruppamento canoni ricorsivi contrattuali + rapportini spot + eccedenze copie MPS.
  2. `FatturaPA / SDI v1.2`: Generazione tracciato XML con codice destinatario e aliquote IVA.
  3. `Scadenzario`: Gestione scadenze a 30/60 gg d.f. f.m. con tracking incassi e solleciti.

---

### Pipeline D — Task Jira & Schedulazione Appuntamenti
* **Scopo**: Allineamento bidirezionale tra agenda/calendario e consuntivo ore ticket.
* **Artefatti**: `clients/<slug>/jira_sync.yaml`
* **Workflow**:
  1. Ricezione task Jira -> Schedulazione slot intervento a calendario.
  2. Esecuzione intervento -> Generazione rapportino Pipeline B.
  3. Chiusura ticket Jira con consuntivo ore effettivo.

---

### Pipeline E — Preventivazione Multiprodotto
* **Scopo**: Offerte multiprodotto (Hardware, VoIP, Stampanti, Arredo, Licenze) con ricarichi cost-plus.
* **Artefatti**: `clients/<slug>/quotes/quote-*.yaml`
* **Workflow**:
  1. Raccolta capitolato e calcolo costi base di acquisto.
  2. Applicazione matrice ricarichi percentuali (`markup_percent`).
  3. Calcolo marginalità lorda e totale offerta.

---

### Pipeline F — Noleggio Multifunzione MPS (Costo Copia Completo)
* **Scopo**: Gestione flotta stampanti, telelettura contatori, canoni semestrali anticipati e consumabili toner.
* **Artefatti**: `clients/<slug>/mps/mps-*.yaml`
* **Workflow**:
  1. `Stipula Noleggio`: Canone base semestrale anticipato + quote copie incluse (es. 6000 BN / 1200 Colore).
  2. `Telelettura SNMP`: Rilevazione contatori totali da MIB standard.
  3. `Alert Consumabili`: Generazione ordine preventivo magazzino se toner < 15%.
  4. `Conguaglio Semestrale`: Calcolo eccedenze copie (Copie Effettive - Incluse) * tariffa unitaria.

---

### Pipeline G — Fornitura Arredo da Ufficio
* **Scopo**: Commesse complesse chiavi in mano di arredo e pareti divisorie.
* **Artefatti**: `clients/<slug>/furniture/arr-*.yaml`
* **Workflow**:
  1. `1_survey`: Rilievo metrico laser e mappatura punti luce/dati.
  2. `2_design`: Layout 2D CAD DWG e render 3D fotorealistici.
  3. `3_sampling_approval`: Approvazione finiture e colori con firma cliente.
  4. `4_procurement`: Emissione ordini alle fabbriche produttrici.
  5. `5_assembly`: Posa in opera, montaggio e posa canaline passacavi IT.
  6. `6_handover_approved`: Verbale di collaudo (planarità, chiusure, assenza graffi) e firma accettazione.
