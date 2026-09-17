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

---

## 2. Il Connettore Deterministico: `ITInfraBridge`
Il modulo Python `scripts/core/bridge.py` fornisce accesso in sola lettura agli artefatti di `itinfra`:
* Verifica esistenza progetto tecnico in `../itinfra/projects/<slug>/`.
* Estrae in modo deterministico i numeri di serie hardware e gli hostname da `06-As-Built.md`.
* Fornisce a `it-ops check <slug>` la matrice di riscontro per verificare che ogni apparato coperto da contratto SLA o oggetto di rapportino esista effettivamente nella documentazione tecnica.
