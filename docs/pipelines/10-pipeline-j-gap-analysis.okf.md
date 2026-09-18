---
okf_version: "0.2"
id: "spec-ops-pipeline-j-gap-analysis"
title: "Pipeline J — Gap Analysis & Compliance D.Lgs. 231/2001 (Art. 24-bis), CVSS v4.0 & Remediation"
type: "specification"
domain: "Legal Cybersecurity & Compliance Governance"
tags: ["okf-v0.2", "pipeline-j", "gap-analysis", "dlgs-231", "cvss-v4", "remediation-plan", "odv", "shadow-it"]
project_id: "itinfra-business-ops"
phase: 1
status: "approved"
version: "1.0"
created_at: "2026-09-18"
updated_at: "2026-09-18"
lang: "it"

entities:
  - name: "GapAnalysisPipeline"
    type: "pipeline"
    description: "10a pipeline nativa di itinfra-business-ops per l'audit di conformita' legale D.Lgs. 231/01, ISO 27001 e NIST CSF"
  - name: "CVSS v4.0 Technical Scoring"
    type: "scoring_methodology"
    description: "Valutazione quantitativa delle vulnerabilita' di sicurezza secondo lo standard FIRST CVSS v4.0"
  - name: "Prioritized Remediation Engine"
    type: "engine"
    description: "Generatore automatico di roadmap operative correttive con deadline restrittive, owner, budget e correlazione ai reati informatici"
  - name: "As-Built Shadow IT Cross-Checker"
    type: "audit_bridge"
    description: "Bridge federato verso itinfra per la verifica incrociata tra gli IP scansionati e gli asset censiti nell'As-Built"

relations:
  - targetTitle: "Indice Master delle Pipeline Operative"
    targetId: "index-ops-pipelines-master"
    relationType: "part_of"
    weight: 1.0
  - targetTitle: "Pipeline A — Contratti SLA, Monte Ore & Over-Budget"
    targetId: "spec-ops-pipeline-a-contracts"
    relationType: "collaborates_with"
    weight: 0.9
  - targetTitle: "Pipeline E — Preventivazione Multiprodotto Cost-Plus"
    targetId: "spec-ops-pipeline-e-quotes"
    relationType: "collaborates_with"
    weight: 0.95
---

# Pipeline J — Gap Analysis & Compliance D.Lgs. 231/2001 (Art. 24-bis), CVSS v4.0 & Remediation

## 1. Perimetro Normativo ed Efficacia Esonerante 231

La **Pipeline J (`gap`)** governa la conduzione peritale e l'attestazione formale di conformita' al **D.Lgs. 8 giugno 2001, n. 231**, con specifico riferimento all'**Art. 24-bis (Delitti informatici e trattamento illecito di dati)** e alle normative collegate:
- **L. 90/2024**: Nuove disposizioni in materia di rafforzamento della cybersicurezza nazionale e reati informatici;
- **ISO/IEC 27001:2022**: Controlli organizzativi, fisici e tecnologici per la sicurezza delle informazioni;
- **ISO 22301:2019**: Business Continuity Management System;
- **NIST CSF v2.0**: Framework di riferimento per la gestione del rischio cyber (Govern, Identify, Protect, Detect, Respond, Recover);
- **Regolamento UE 2016/679 (GDPR)**: Misure tecniche e organizzative adeguate (Art. 32).

L'obiettivo peritale e' documentare l'adozione e l'efficace attuazione di un **Modello di Organizzazione, Gestione e Controllo (MOG 231)** idoneo a prevenire la commissione di illeciti, garantendo l'esonero da responsabilita' amministrativo-penale dell'ente.

---

## 2. Modello di Scoring Ponderato & CMMI

Il punteggio complessivo di conformita' e' calcolato con la seguente formula deterministica:
$$\text{Conformita' Globale \%} = 25\% \cdot \text{Audit Documentale} + 50\% \cdot \text{Interviste 5 Aree} + 25\% \cdot \text{Vulnerability Assessment}$$

### Livello di Maturita' CMMI Equivalente
$$\text{Maturita' CMMI} = 1.0 + \frac{\text{Conformita' \%}}{100} \cdot 4.0 \quad (1.0 \le \text{Score} \le 5.0)$$

### Penalita' Vulnerability Assessment (CVSS v4.0 FIRST)
$$\text{Penalita' VA} = (\text{Critiche} \cdot 25) + (\text{Alte} \cdot 10) + (\text{Medie} \cdot 4) + (\text{Basse} \cdot 1)$$
$$\text{Punteggio Tecnico VA} = \max(0, 100 - \text{Penalita' VA})$$

---

## 3. Le 5 Aree Canoniche di Intervista

1. `ciso_security`: CISO & Sicurezza delle Informazioni;
2. `it_operations`: IT Operations & Amministrazione Reti;
3. `risk_compliance`: Risk Management & OdV Compliance 231;
4. `procurement_contracts`: Ufficio Acquisti & Contratti Terzi (Supply Chain Security);
5. `facility_physical_security`: Sicurezza Fisica & Controllo Accessi.

---

## 4. Deliverables Ufficiali Brandizzati Aure System

L'esecuzione del comando `gap report` produce 4 deliverable integrati e sigillati con digest SHA-256 immutabile:
1. `01-verbale-kickoff.md`: Verbale istituzionale di apertura lavori e perimetro;
2. `02-rapporto-gap-analysis-remediation.md` & `.pdf`: Rapporto peritale completo con scorecard domini e piano di bonifica;
3. `03-rapporto-vulnerability-assessment.md` & `.pdf`: Rapporto tecnico con evidenze CVE (CVSS v4.0);
4. `04-executive-presentation-odv.html`: Dashboard esecutiva interattiva e print-ready per CDA e OdV.

---

## 5. Rilevamento Shadow IT tramite Federazione itinfra

La pipeline esegue un cross-check automatico in sola lettura con i file `04-Network-IPAM.md` e `06-As-Built.md` del repository federato `itinfra`:
- Se un IP scansionato nel VA non risulta censito nell'IPAM di `itinfra`, il sistema emette immediatamente un'allerta peritale di **Shadow IT**.
- Quando tutti gli IP scansionati corrispondono all'As-Built ufficiale, il sistema certifica la piena copertura contrattuale e l'assenza di apparati non monitorati.

---

## 6. Comandi CLI Disponibili

```bash
# Scheda di avanzamento e stato 360°
.\it-ops.cmd gap <slug> status

# Calcolo indici di conformita' e scorecard domini
.\it-ops.cmd gap <slug> calculate

# Generazione del Remediation Plan prioritizzato
.\it-ops.cmd gap <slug> remediation

# Ispezione rilievi Vulnerability Assessment (CVSS v4.0)
.\it-ops.cmd gap <slug> va

# Generazione dei 4 deliverable formali (MD + PDF + HTML)
.\it-ops.cmd gap <slug> report

# Cross-check con As-Built di itinfra e rilevamento Shadow IT
.\it-ops.cmd gap <slug> check
```
