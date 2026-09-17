---
type: "concept"
title: "Soluzione Studio Legale 4.0 — Avv. Roberto Viola (Specifiche Tecniche & Funzionali)"
description: "Dettaglio dell'architettura hardware HP Z6 G4, configurazione di rete LAN, virtualizzazione Hyper-V a 4 VM, stack software AI locale (Ollama, AnythingLLM, Paperless-NGX, n8n) e requisiti di privacy per studi legali."
generated.at: "2026-09-17T17:48:00+02:00"
sources:
  - "file://@preventivo-studio-legale-4.0.pdf#page=1-2"
tags:
  - "document-intelligence"
  - "estrazione-sota"
  - "quote-proposal"
  - "roberto-viola"
  - "part-1-specs"
---

# Punti Chiave

- [Pagina 1] **Stack Funzionale Studio Legale 4.0**:
  - Ricerca semantica AI su archivio completo studio (< 1 secondo).
  - Chat AI con documenti per individuazione precedenti simili e giurisprudenza interna.
  - Automazione email PEC e Gmail (estrazione allegati, OCR automatico, archiviazione).
  - Gestione scadenze con intelligenza artificiale che estrae date da atti e notifiche.
  - Dashboard operativa in tempo reale (scadenze, fascicoli, ore lavorate, email da evadere).
  - Time tracking automatico collegato a calendario ed email.
  - Generazione template atti giudiziari (citazioni, comparse, contratti, lettere).
  - OCR professionale su documenti cartacei scansionati.
  - Workflow automation personalizzabile basato su n8n.
  - Integrazione banche dati giuridiche esterne (DeJure, Italgiure).
  - Backup automatici cifrati locali.
  - Supporto tecnico incluso per 12 mesi.
- [Pagina 2] **Hardware Workstation Server (Pos. 1)**:
  - Modello: **HP Z6 G4 Workstation (AI Ready)**.
  - Processori: **2x Intel Xeon Silver 4108** (16 core / 32 thread totali, 1.80 GHz base).
  - Memoria: **128 GB RAM DDR4 ECC Registered**.
  - Sottosistema Disco: **2x NVMe 1TB + 2x SSD 1TB (4TB storage totale)**.
  - Acceleratore Grafico AI: **NVIDIA RTX 5060 Ti 16GB** (GPU AI per inferenza locale LLM).
  - Sistema Operativo Base: **Windows Server 2022 Datacenter**.
- [Pagina 2] **Infrastruttura Networking LAN (Pos. 2)**: Cablaggio strutturato, switch gestito, configurazione rete locale.
- [Pagina 2] **Virtualizzazione Hyper-V (Pos. 3)**:
  - Hypervisor: Microsoft Hyper-V su Windows Server 2022.
  - **4 Virtual Machines isolate**:
    1. *VM 1 — File Server & Storage Documentale*: Condivisioni SMB protette e profilazione accessi.
    2. *VM 2 — Paperless-NGX*: Gestione documentale DMS, indicizzazione full-text e motore OCR Tesseract.
    3. *VM 3 — UniFi Controller*: Gestione centralizzata apparati di rete e policy di sicurezza LAN.
    4. *VM 4 — Automation Hub*: Hosting n8n workflows e connettori PEC/Gmail.
  - Motore AI Locale: Ollama con modelli open-weight (es. Llama 3 / Mistral) interfacciato ad AnythingLLM con vector database locale per RAG (Retrieval-Augmented Generation).
- [Pagina 2] **Servizi Inclusi & Opzionali a Pagamento**:
  - *Inclusi*: Setup backup automatici, test e collaudo completo.
  - *Opzionali a pagamento*: Setup automazioni email n8n, configurazione dashboard operativa NocoDB, importazione archivio documentale pregresso dello studio.

# Contenuto Semantico

## 1. Descrizione della Soluzione
La soluzione "Studio Legale 4.0" proposta da Aure System risponde alla necessità dello studio legale moderno di coniugare l'efficienza degli strumenti di intelligenza artificiale generativa con il rigoroso rispetto del segreto professionale forense e del Regolamento UE 2016/679 (GDPR).

Tutti i documenti processati, gli atti difensivi, i contratti dei clienti e i fascicoli di causa risiedono esclusivamente all'interno del server fisico presente nei locali dello studio. L'inferenza dei modelli LLM avviene localmente tramite la GPU NVIDIA dedicata (16GB VRAM), garantendo che nessun dato riservato venga trasmesso a server cloud di terze parti o utilizzato per l'addestramento di modelli pubblici.

## 2. Architettura Logico-Funzionale

```
+-------------------------------------------------------------------------+
|                  HP Z6 G4 Workstation (Windows Server 2022)             |
|  2x Xeon Silver 4108 | 128GB ECC | 4TB NVMe/SSD | NVIDIA GPU 16GB VRAM  |
+-------------------------------------------------------------------------+
       |                                                    |
       v (Hypervisor Hyper-V)                               v (AI Local Runtime)
+------------------------------------+             +----------------------+
| VM 1: File Server & Storage SMB   |             | Ollama Engine        |
+------------------------------------+             | Modelli LLM Locali   |
| VM 2: Paperless-NGX (DMS & OCR)    | <---------> +----------------------+
+------------------------------------+             | AnythingLLM Frontend |
| VM 3: UniFi Network Controller     |             | Vector Store Embed.  |
+------------------------------------+             +----------------------+
| VM 4: Automation Hub (n8n & PEC)   |
+------------------------------------+
```

# Tabelle Estratte

### Tabella 1: Scheda Tecnica Hardware e Piattaforma di Virtualizzazione
| Componente / Sottosistema | Specifica Tecnica Fornita | Ruolo Operativo nello Studio |
| :--- | :--- | :--- |
| **Piattaforma Hardware** | HP Z6 G4 Workstation | Host fisico di elaborazione e virtualizzazione |
| **Processori (CPU)** | 2x Intel Xeon Silver 4108 (16C/32T) | Calcolo distribuito per le 4 macchine virtuali |
| **Memoria RAM** | 128 GB DDR4 ECC Registered | Allocazione dinamica tra host e VM guest |
| **Storage NVMe** | 2x NVMe 1TB (RAID 1 / Fast Tier) | Hosting OS, database vettoriale e VM runtime |
| **Storage SSD** | 2x SSD 1TB (Archivio Dati) | Volume documentale Paperless e backup interni |
| **GPU AI Dedicated** | NVIDIA RTX 5060 Ti 16GB VRAM | Accelerazione tensoriale per inferenza LLM locale |
| **Rete & Switching** | Switch gestito con cablaggio strutturato | Isolamento VLAN tra traffico dati e gestione |
| **Software Virtualizzazione** | Microsoft Hyper-V su Win 2022 | Segmentazione a 4 macchine virtuali dedicate |
| **Stack AI & DMS** | Ollama, AnythingLLM, Paperless-NGX | Ricerca semantica, RAG locale, OCR e workflow |
