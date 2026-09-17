---
type: "concept"
title: "Scheda Tecnica Configurazione — OpenStor JovianDSS Metro Cluster HA"
description: "Distinta tecnica e configurazione hardware per soluzione iperconvergente ad alta disponibilità basata su 2 nodi OpenStor JovianDSS 2U 24-Bay Full NVMe, Intel Xeon 6507P, 512GB RAM e ZFS Metro Cluster."
generated.at: "2026-09-17T16:35:00Z"
sources:
  - "file://@media_1789652609375.pdf"
tags:
  - "document-intelligence"
  - "estrazione-sota"
  - "spec-sheet"
  - "teatek-spa"
  - "openstor"
---

# Punti Chiave
- [Pagina 1] **Codice Configurazione Fornitore**: `JMC-14DI-224N`.
- [Pagina 1] **Produttore / Brand**: `OPENSTOR`.
- [Pagina 1] **Architettura**: Soluzione Intel in High Availability (HA) a 2 nodi rack 2U per Business Continuity Iperconvergente basata su ZFS Open-E JovianDSS Metro Cluster (Active/Passive o Active/Active).
- [Pagina 1] **Interconnessione Storage**: Lan a bassissima latenza con interconnect dedicato ad alta velocità a 25GbE / 100GbE QSFP28 per mirroring sincrono istantaneo senza soluzione di continuità.
- [Pagina 1] **Protezione Ransomware**: Sistema di continue snapshot ZFS (anche 1 ogni 30 secondi) per ripristino istantaneo ai 30 secondi precedenti l'attacco senza restore manuale.
- [Pagina 2] **Specifiche Chassis**: 2 chassis 2U (438x87.5x815 mm), 24 bay frontali hot-swap U.2/U.3 NVMe da 2,5" + 2 bay posteriori SATA da 2,5", alimentazione ridondata 2000W Titanium Level.
- [Pagina 2] **Calcolo & Memoria**: 4 processori Intel Xeon 6507P (8 Core / 16 Thread cad., fino a 4,30 GHz, 48MB Cache) e 16 moduli da 32GB DDR5-5600 ECC Registered (totale 512GB RAM).
- [Pagina 2] **Storage Pool & Cache Tiering**: 2x SSD NVMe Kioxia CM7-V Gen5 da 3,2TB (ZIL Write Log dedicato ad altissima resistenza 3 DWPD) e 20x SSD NVMe Samsung PM9A3 U.2 da 3,84TB (totale 76,8TB Raw NVMe).
- [Pagina 2] **Garanzia & Supporto**: Garanzia hardware standard 3 anni On Center, con opzione attivabile di estensione a 3 / 5 anni On-Site.
- [Pagina 1-2] **Zero-Hallucination Guardrail**: Nessun prezzo di vendita finale o canone SLA periodico è presente in questa scheda di configurazione fornitore (prezzo vincolante definito a € 66.000,00 + IVA come da istruzione commerciale del cliente).

# Contenuto Semantico

## 1. Descrizione Architetturale della Soluzione
Il sistema iperconvergente è progettato per garantire continuità operativa di livello Enterprise (RPO ≈ 0, RTO ≈ 0). È costituito da due server storage rack 2U OpenStor JovianDSS interconnessi tramite link sincrono a 100GbE QSFP28. 

Su entrambi i nodi fisici viene eseguito l'hypervisor **VMware ESXi** e una Virtual Storage Appliance (VSA) **Open-E JovianDSS**. Ogni scrittura effettuata sul nodo 1 viene replicata specularmente sul nodo 2 in modalità attiva/attiva. In caso di disservizio o guasto hardware su un nodo, il servizio di **Automatic Failover** preserva l'erogazione dei datastore iSCSI e NFS alle Virtual Machines senza interruzioni di servizio.

## 2. Piattaforma Hardware & Sottosistema di I/O
* **Chassis & Alimentazione**: 2x BAREBONE 2U OpenStor 24-Bay 2.5'' NVMe, alimentatori ridondanti estraibili a caldo da 2000W certificati Titanium Level (efficienza > 96%).
* **Processori**: 2x Socket LGA4710 per nodo (totale 4 CPU Intel Xeon 6507P) con 88 linee PCIe Gen5 ciascuno.
* **Memoria di Sistema**: 16 slot popolati con moduli DDR5-5600 ECC Registered ad elevata integrità di segnale.
* **Storage Tiering ZFS**:
  * **Write Log (ZIL / SLOG)**: 2 unità Kioxia CM7-V 3.2TB PCIe Gen5 (fino a 2.700.000 IOPS di picco) per sincronizzare scritture sincrone a latenza sub-millisecondo.
  * **Capacity Pool**: 20 dischi Samsung PM9A3 U.2 NVMe da 3,84TB in configurazione zpool ridondata (mirroring / RAID-Z2).

# Tabelle Estratte

### Tabella 1: Caratteristiche Principali del Sistema (Key Features)
| Parametro Architetturale | Specifica Tecnica Certificata |
| :--- | :--- |
| **Form Factor** | 2U Rackmount (438 x 87,5 x 815 mm) |
| **Drive Bays Frontali** | 24 x 2,5" U.2 / U.3 Full NVMe Hot Swap |
| **Drive Bays Posteriori** | 2 x 2,5" SATA rear (per OS/Boot) |
| **Alimentazione** | 2000W Ridondante Hot-Swap (Certificazione 80 PLUS Titanium) |
| **CPU Socket** | Dual Socket LGA4710 per nodo (supporto Xeon serie 6500 / 6700) |
| **Memoria Massima** | Fino a 32 slot DDR5 6400MHz ECC Reg (Max 6TB) |
| **Connettività Metrocluster** | 2 x 25GbE SFP28 / 2 x 100GbE QSFP28 a bassissima latenza |
| **Management Remoto** | IPMI 2.0 dedicato con funzionalità KVM-over-IP |
| **Garanzia Fornitore** | 3 anni On-Center (Estensione On-Site 3/5 anni opzionale) |

### Tabella 2: Distinta Componenti Hardware & Licenze (BOM Integrale)
| Cat / Sottocat | Prodotto & Descrizione Dettagliata | Quantità | Note / Licenza |
| :--- | :--- | :---: | :--- |
| **BAREBONE / Server** | 2U ZFS OpenStor JovianDSS Rack Storage (iSCSI/NFS/SMB/FC) 24 Bay 2.5" NVMe - DUAL INTEL XEON 6 - 2x100GbE QSFP28 for metrocluster - 2*1GbE - 2000W Redundant PSU Titanium Level | **2** | Licenza Jovian Metro Cluster inclusa |
| **CPU / SERVER** | Intel Xeon 6507P (8C/16T, base 3,50GHz - turbo 4,30GHz, 48MB Cache, LGA4710, TDP 150W, 88 PCIe lanes) | **4** | 2 CPU per nodo |
| **Memoria** | 32GB DDR5-5600 ECC Registered | **16** | 512GB RAM totali (256GB per nodo) |
| **HDD / 2,5" NVMe** | Kioxia CM7-V U.3 15mm 3.200 GB SIE 3 DWPD PCIe Gen5 1x4 (ZIL Write Log, fino a 2.700K IOPS) | **2** | 1 disco ZIL ad alta resistenza per nodo |
| **HDD / 2,5" NVMe** | Samsung PM9A3 3.8TB NVMe PCIe 4.0 x4 U.2 7mm 1 DWPD SED Opal (fino a 1.000K IOPS) | **20** | 10 dischi storage dati per nodo (76,8TB Raw) |
| **Servizi / Garanzia** | Estensione Garanzia a 3 Anni ON-SITE con supporto sistemistico certificato | **1** | [OPZIONE] Attivabile su richiesta cliente |
