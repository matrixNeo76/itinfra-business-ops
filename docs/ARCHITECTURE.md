# 🏛️ Architettura di Repository: itinfra-business-ops & itinfra

## 1. Il Paradigma Hub-and-Spoke

L'architettura separa rigorosamente il repository ingegneristico (`itinfra`) dal repository gestionale/operativo (`itinfra-business-ops`).
L'anello di congiunzione deterministico è rappresentato dallo **Shared Customer Slug (`<slug>`)**.

```mermaid
flowchart TD
    subgraph S_SLUG ["Shared Customer Slug"]
        SLUG["cliente-rossi-srl / severino-srl"]
    end

    subgraph TECH ["Repo Tecnico: itinfra"]
        T_MAN["projects/&lt;slug&gt;/manifest.yaml"]
        T_LLD["projects/&lt;slug&gt;/03-LLD.md"]
        T_ASB["projects/&lt;slug&gt;/06-As-Built.md"]
        T_INV["projects/&lt;slug&gt;/09-Handover-Inventory.md"]
    end

    subgraph BIZ ["Repo Operativo: itinfra-business-ops"]
        B_MAN["clients/&lt;slug&gt;/client-manifest.yaml"]
        B_CTR["clients/&lt;slug&gt;/contracts/"]
        B_RAP["clients/&lt;slug&gt;/timesheets/"]
        B_INV["clients/&lt;slug&gt;/invoices/"]
        B_MPS["clients/&lt;slug&gt;/mps/"]
        B_ARR["clients/&lt;slug&gt;/furniture/"]
        B_QUO["clients/&lt;slug&gt;/quotes/"]
    end

    SLUG -->|"Identità Tecnica"| T_MAN
    SLUG -->|"Identità Commerciale"| B_MAN
    B_CTR -.->|"Cross-Check Asset As-Built"| T_ASB
    B_RAP -.->|"Verifica Seriali Intervento"| T_ASB
    B_MPS -.->|"Verifica Seriale Hardware"| T_ASB
```

### Perché Non nel Repo Tecnico (SoC & Compliance)
1. **Separation of Concerns (SoC)**: Il repo tecnico gestisce topologie di rete, configurazioni firewall, backup e conformità NIS2/ISO 27001. Il repo gestionale governa contratti, fatture elettroniche, canoni anticipati, SLA e logistica arredi.
2. **Access Control (RBAC)**: I tecnici di rete sul campo non devono accedere ai dati economici e ai margini commerciali. Gli addetti contabili o commerciali non devono modificare configurazioni di rete.
3. **Integrità dei Linter**: Gli audit tecnici (`it validate`) rimangono focalizzati sulla correttezza architetturale senza essere appesantiti da regole di fatturazione o codici SDI.

### 📐 Topologia ASCII Hub-and-Spoke

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

### ⚙️ Pipeline Principale di itinfra (7 Fasi Ingegneristiche)

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

> 📄 *Per il compendio completo di tutti i diagrammi ASCII, consulta [`docs/ASCII_DIAGRAMS.md`](ASCII_DIAGRAMS.md).*

---

## 2. Il Connettore Deterministico: `ITInfraBridge`
Il modulo Python `scripts/core/bridge.py` fornisce accesso in sola lettura agli artefatti di `itinfra`:
* Verifica esistenza progetto tecnico in `../itinfra/projects/<slug>/`.
* Estrae in modo deterministico i numeri di serie hardware e gli hostname da `06-As-Built.md`.
* Fornisce a `it-ops check <slug>` la matrice di riscontro per verificare che ogni apparato coperto da contratto SLA o oggetto di rapportino esista effettivamente nella documentazione tecnica.
