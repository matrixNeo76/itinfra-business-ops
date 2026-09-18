---
okf_version: "0.2"
id: "CERT-DR-severino-srl-2026-09-18"
title: "Verbale Ufficiale Esercitazione Disaster Recovery — severino-srl"
type: "report"
domain: "Business Continuity & GDPR Art. 32"
generated.at: "2026-09-18T23:08:33.212206"
tags:
  - "disaster-recovery"
  - "gdpr-art32"
  - "dlgs-231"
  - "audit-odv"
---

# Verbale Ufficiale di Esercitazione Disaster Recovery
**Cliente:** `severino-srl`  
**Data Collaudo:** `2026-09-18`  
**Responsabile Tecnico:** Eduardo Possumato (Aure System)  
**Destinatari:** Organismo di Vigilanza D.Lgs. 231/2001, Data Protection Officer (DPO)

## 1. Esito delle Prove di Ripristino
- **Ambiente di Test:** Sandbox di staging isolata (zero impatto sui sistemi in produzione).
- **Integrità Dati:** Checksum crittografico SHA-256 conforme al 100%. Nessuna corruzione rilevata.
- **RTO Rilevato:** 42.5 minuti (Tempo massimo ammesso da SLA: 120 minuti) — **SUPERATO**.
- **RPO Rilevato:** 2.0 ore (Perdita massima ammessa da SLA: 4.0 ore) — **SUPERATO**.

## 2. Attestazione di Conformità
Si attesta che le procedure di salvataggio e continuità operativa del cliente severino-srl 
soddisfano i requisiti di cui all'Art. 32 del Regolamento UE 2016/679 (GDPR) e le prescrizioni 
del Modello Organizzativo ex D.Lgs. 231/2001 (Art. 24-bis reati informatici).
