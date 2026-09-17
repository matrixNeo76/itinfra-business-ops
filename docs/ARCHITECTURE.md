# 🏛️ Architettura di Repository: itinfra-business-ops & itinfra

## 1. Il Paradigma Hub-and-Spoke

L'architettura separa rigorosamente il repository ingegneristico (`itinfra`) dal repository gestionale/operativo (`itinfra-business-ops`).
L'anello di congiunzione deterministico è rappresentato dallo **Shared Customer Slug (`<slug>`)**.

```mermaid
flowchart TD
    subgraph S_SLUG ["Shared Customer Slug (<slug>)"]
        SLUG["cliente-rossi-srl / severino-srl"]
    end

    subgraph TECH ["Repo Tecnico: itinfra"]
        T_MAN["projects/<slug>/manifest.yaml"]
        T_LLD["projects/<slug>/03-LLD.md"]
        T_ASB["projects/<slug>/06-As-Built.md"]
        T_INV["projects/<slug>/09-Handover-Inventory.md"]
    end

    subgraph BIZ ["Repo Operativo: itinfra-business-ops"]
        B_MAN["clients/<slug>/client-manifest.yaml"]
        B_CTR["clients/<slug>/contracts/"]
        B_RAP["clients/<slug>/timesheets/"]
        B_INV["clients/<slug>/invoices/"]
        B_MPS["clients/<slug>/mps/"]
        B_ARR["clients/<slug>/furniture/"]
        B_QUO["clients/<slug>/quotes/"]
    end

    SLUG --> TECH
    SLUG --> BIZ
    BIZ -.->|ITInfraBridge (Read-Only)| TECH
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
