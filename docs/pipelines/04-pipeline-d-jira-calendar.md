---
okf_version: "0.2"
id: "spec-ops-pipeline-d-jira-calendar"
title: "Pipeline D — Task Jira, Agenda & Schedulazione RFC 5545"
type: "specification"
domain: "Business Operations & PSA"
tags: ["okf-v0.2", "pipeline-d", "jira", "icalendar", "rfc-5545", "scheduling"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-17"
updated_at: "2026-09-17"
lang: "it"

entities:
  - name: "Jira Issue Key Mapping"
    type: "specification"
    description: "Associazione deterministica tra la chiave ticket Jira (es. IT-142) e lo slug cliente"
  - name: "iCalendar RFC 5545 Sync Object"
    type: "pattern"
    description: "Generazione file .ics standard con UID, date ISO UTC e slot geografico per client di posta"
  - name: "Worklog Reconciliation Trigger"
    type: "pattern"
    description: "Allineamento tra la durata stimata dell'appuntamento e le ore effettive del rapportino"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "implements"
    weight: 1.0
    description: "Modulo di pianificazione e ticketing del compendio operativo"
  - targetTitle: "Pipeline B — Rapportini Intervento, Firma Canvas & Ricambi"
    targetId: "spec-ops-pipeline-b-reports"
    relationType: "depends_on"
    weight: 0.95
    description: "L'appuntamento pianificato innesca la compilazione del rapportino sul campo"
---

# 📅 Pipeline D — Task Jira, Agenda & Schedulazione RFC 5545

## 1. Obiettivi e Ambito Operativo
La **Pipeline D** unifica il ticketing di assistenza con la gestione dei calendari e degli interventi sul campo:
* Mappatura bidirezionale tra ticket di supporto Jira (`Incident`, `Task`, `Maintenance`) e il cliente di riferimento.
* Riserva automatica di slot temporali nel calendario del tecnico e del cliente.
* Emissione di file standard **iCalendar (`.ics`)** compatibili nativamente con Outlook, Google Calendar, Apple Calendar e Thunderbird.
* Predisposizione del contesto operativo per pre-compilare il rapportino di lavoro (Pipeline B).

---

## 2. Diagramma di Flusso Esecutivo

```mermaid
flowchart TD
    TICKET["Richiesta di Assistenza<br/>(Creazione Issue Jira)"]
    SCHED["Schedulazione Data/Ora & Tecnico<br/>(it-ops jira schedule)"]
    YAML_SYNC["Salvataggio Record Locale<br/>(jira_sync.yaml)"]
    ICS_GEN["Generazione File RFC 5545<br/>(appointment-KEY.ics)"]
    CAL_IMPORT["Import Calendario Tecnico & Cliente<br/>(Outlook / Google Calendar)"]
    FIELD_WORK["Esecuzione Intervento"]
    TRIGGER_REP["Innesco Automatico Rapportino<br/>(Pipeline B)"]
    CLOSE_JIRA["Consuntivo & Chiusura Ticket Jira<br/>(Log Work Effettivo)"]

    TICKET --> SCHED --> YAML_SYNC --> ICS_GEN --> CAL_IMPORT
    CAL_IMPORT --> FIELD_WORK --> TRIGGER_REP --> CLOSE_JIRA
```

---

## 3. Specifiche del File iCalendar (`.ics`)

Il file generato rispetta lo standard **RFC 5545**:
```text
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ITInfra Business Ops//Intervento Tecnico//IT
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:IT-142@itinfra.local
DTSTAMP:20260917T131617Z
DTSTART:20260920T090000
DTEND:20260920T110000
SUMMARY:[IT-142] Manutenzione e verifica perimetrale
DESCRIPTION:Intervento tecnico programmato per il cliente severino-srl\nAssegnatario: Mario Rossi
LOCATION:Presso sede cliente severino-srl
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
```

---

## 4. Schemi & Comandi CLI

* **Schema Formale**: `schemas/jira_sync.schema.yaml`
* **Percorso Storage**: `clients/<slug>/jira_sync.yaml` e `appointment-<issue>.ics`

### Sintassi Comandi:
```powershell
# Schedulare un appuntamento e generare il file .ics
.\it-ops.cmd jira <slug> schedule `
  --issue "IT-205" `
  --summary "Sostituzione tamburo e tuning VPN" `
  --start "2026-09-22T09:30:00" `
  --duration 2.5 `
  --tech "Mario Rossi"
```
