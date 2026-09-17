---
type: "concept"
title: "Audit di Conformità, Rilevazione Incongruenze & Ottimizzazione Contrattuale 2026 — Severino Service SRL"
description: "Rapporto peritale di revisione del contratto Prot. 28/2026: rilevazione contraddizioni interne, sostenibilità economica monte ore, refusi tipografici e raccomandazioni di adeguamento agli standard normativi italiani ed europei aggiornati a Settembre 2026 (GDPR Art. 28, NIS 2, DORA, clausole di salvaguardia)."
generated.at: "2026-09-17T17:28:00+02:00"
sources:
  - "file://@PROPOSTA_CONTRATTO_SEVERINO_SERVICE_2026.pdf"
tags:
  - "document-intelligence"
  - "audit-contrattuale"
  - "compliance-2026"
  - "gdpr-art28"
  - "nis2-msp"
  - "part-3-audit"
---

# Punti Chiave

- [Criticità 1] **Contraddizione Oraria**: La Sez. 5.1 fissa il presidio feriale fino alle **17:00**, mentre la tabella di Sez. 8.1 lo estende fino alle **18:00**.
- [Criticità 2] **Discrepanza Recapiti Telefonici**: L'intestazione ufficiale riporta il numero `3337328065`, mentre la Sezione 5.1 per l'assistenza indica il numero `3928554426`.
- [Criticità 3] **Ambiguità nel Corpo del Testo (Sez. 6)**: Il testo recita testualmente *"un pacchetto pari a n° 24 oppure 12 giornate"*, lasciando un'opzione non sciolta nel corpo contrattuale, sebbene la tabella tariffaria di Sez. 8.1 riporti "24 giornate".
- [Criticità 4] **Anomalia Tariffaria e Sostenibilità Economica**: 24 giornate lavorative corrispondono a **192 ore/anno**. A fronte di un compenso annuo di € 3.600,00, la tariffa oraria implicita risulta di appena **€ 18,75 / ora** (con ore di viaggio incluse!), ampiamente al di sotto dei costi vivi di un sistemista senior. Rischio di equivoco: si intendevano forse *24 ore/anno* (2 ore/mese) o *12 giornate* a consumo?
- [Criticità 5] **Assenza Tariffa Extra Monte Ore**: Nessuna clausola definisce il costo orario applicabile in caso di esaurimento del pacchetto prima del termine dei 12 mesi.
- [Criticità 6] **Assenza Nomina Responsabile Trattamento Dati (GDPR Art. 28)**: Gravissima lacuna di compliance: il sistemista accede ad Active Directory, server, posta e backup aziendali ma manca l'accordo DPA obbligatorio per legge.
- [Criticità 7] **Assenza Clausole NIS 2 & Resilienza Operativa (Settembre 2026)**: Nessun riferimento agli standard di sicurezza informatica, tracciamento degli incidenti e gestione del rischio di filiera ICT imposti dalla Direttiva NIS 2 / D.Lgs. nazionale per i Managed Service Provider (MSP).
- [Criticità 8] **Assenza Clausola di Limitazione della Responsabilità (Liability Cap)**: Manca una manleva espressa per perdita dati o ransomware subordinata alla tenuta dei backup a carico del cliente.
- [Criticità 9] **Refuso Tipografico nel Box Firme (Pagina 8)**: La dicitura riporta l'errore materiale `"TIMRBO E FIRMA DEL FORNITORE"`.

---

# Matrice delle Incongruenze & Errori Rilevati

### Tabella 1: Sintesi Anomalie Interne del Documento
| ID Rilevazione | Sezione di Origine | Valore / Dicitura Attuale | Contraddizione / Anomalia | Rischio Operativo / Legale |
| :---: | :--- | :--- | :--- | :--- |
| **ERR-01** | Sez. 5.1 vs Sez. 8.1 | `10:00 - 17:00` vs `10:00 - 18:00` | Differenza di 1 ora giornaliera di presidio | Rischio contestazione SLA fuori orario |
| **ERR-02** | Intestazione vs Sez. 5.1 | `3337328065` vs `3928554426` | Due numeri mobili differenti non chiariti | Mancata o ritardata presa in carico chiamate |
| **ERR-03** | Sez. 6 | *"n° 24 oppure 12 giornate"* | Clausola con alternativa non definita | Incertezza sull'obbligazione della prestazione |
| **ERR-04** | Sez. 8.1 | 24 giornate = 192 ore a € 3.600 | Tariffa di € 18,75/h con trasferte incluse | Insostenibilità economica della commessa |
| **ERR-05** | Sez. 6 & 8.2 | Omesse condizioni di sforamento | Manca la tariffa oraria per ore eccedenti | Impossibilità di fatturare ore oltre il monte |
| **ERR-06** | Sez. 6 | Omesse regole di scadenza ore | Non si specifica se le ore residue decadono | Rischio accumulo pretese anni successivi |
| **ERR-07** | Sez. 8.2 | *"TIMRBO E FIRMA DEL FORNITORE"* | Refuso ortografico nel blocco formale firme | Danno d'immagine e forma non professionale |
| **ERR-08** | Sez. 3 | Doppio bullet list vuoto su parti ricambio | Errore di impaginazione grafica | Scarsa cura redazionale |

---

# Adeguamento agli Standard di Mercato & Normativi (Settembre 2026)

### 1. Compliance GDPR — Designazione a Responsabile del Trattamento (Art. 28 GDPR)
* **Contesto 2026**: Il Garante Privacy sanziona severamente l'accesso sistemistico ad infrastrutture aziendali senza formale nomina a Responsabile esterno.
* **Proposta di Integrazione**: Aggiungere l'**Art. 9 (Protezione Dati Personali)** con rimando all'Accordo DPA (Data Processing Agreement) che regoli:
  - Misure di sicurezza (MFA, cifratura credenziali, audit log accessi).
  - Divieto di trasferimento dati extra-UE non autorizzato.
  - Cancellazione o restituzione dei log alla chiusura del contratto.

### 2. Direttiva NIS 2 (D.Lgs. di recepimento) & Resilienza Informatica MSP
* **Contesto 2026**: Con l'entrata a pieno regime della Direttiva NIS 2 in Italia, i fornitori di servizi IT/sistemistici (MSP) che operano su clienti B2B in settori critici o catene di fornitura devono dimostrare conformità di sicurezza.
* **Proposta di Integrazione**: Inserire clausole che garantiscano:
  - Autenticazione a più fattori (MFA) per tutte le sessioni di teleassistenza remota.
  - Canale sicuro TLS 1.3 / VPN cifrata per la teleassistenza.
  - Notifica tempestiva al cliente in caso di incidente di sicurezza rilevato sulle sue macchine.

### 3. Clausola di Limitazione di Responsabilità & Regola del Backup (Liability Cap)
* **Contesto**: Il contratto attuale non contiene alcuna limitazione di responsabilità in caso di disastro, crash storage, attacco hacker o ransomware.
* **Proposta di Integrazione**: Inserire clausola standard secondo cui:
  - Aure System risponde esclusivamente per dolo o colpa grave comprovata.
  - La responsabilità risarcitoria massima è limitata al corrispettivo annuo del contratto (€ 3.600,00).
  - L'obbligo di verificare l'esistenza e la consistenza delle copie di backup non in linea (air-gapped / immutabili) rimane in capo al cliente, salvo incarico specifico.

### 4. Adeguamento ISTAT / Revisione Prezzi
* **Proposta di Integrazione**: In caso di rinnovo tacito, il canone annuo si intende automaticamente rivalutato secondo la variazione dell'indice FOI dell'ISTAT accertata nell'anno precedente.

---

# Testo Ottimizzato e Corretto delle Clausole Critiche (Draft Migliorativo)

#### Modifica Sezione 5.1 (Orari & Canali Univoci)
> *"Supporto telefonico, assistenza on-site e teleassistenza saranno disponibili dal lunedì al venerdì dalle ore 09:00 alle ore 18:00. Il canale telefonico dedicato per le emergenze è il numero mobile **333.7328065**, mentre le richieste ordinarie devono pervenire via ticket/email all'indirizzo **info@auresystem.it**."*

#### Modifica Sezione 6 & 8.1 (Chiarimento Monte Ore & Tariffa Eccedenza)
> *"Il contratto comprende un monte ore forfettario pari a **40 ore annuali** (ovvero n° 5 giornate lavorative), quantificate e portate in deduzione ad ogni intervento con scatto minimo di 30 minuti in teleassistenza e 60 minuti on-site. Gli interventi eccedenti il monte ore contrattuale saranno fatturati a consuntivo alla tariffa concordata di **€ 65,00 + IVA / ora**, oltre al contributo di trasferta per gli interventi on-site."*
