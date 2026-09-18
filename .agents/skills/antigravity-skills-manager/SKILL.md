---
name: antigravity-skills-manager
description: Global skills manager for Google Antigravity. Explore, search, install, and manage 300+ agent skills from the rmyndharis/antigravity-skills catalog using pure stdlib CLI tools.
---

# 📦 Antigravity Skills Manager (`rmyndharis/antigravity-skills`)

Questo strumento consente all'agente e all'operatore di esplorare, cercare ed installare oltre **300+ skill per agenti** dal catalogo open-source [`rmyndharis/antigravity-skills`](https://github.com/rmyndharis/antigravity-skills).

## Comandi Rapidi Disponibili (via it-ops CLI)

```powershell
# 1. Cerca skill nel catalogo per parola chiave
.\it-ops.cmd skills search "c4 architecture"
.\it-ops.cmd skills search "incident response"
.\it-ops.cmd skills search "security"

# 2. Visualizza dettagli di una skill specifica
.\it-ops.cmd skills info c4-architecture-c4-architecture

# 3. Installa una skill nel workspace locale
.\it-ops.cmd skills install c4-architecture-c4-architecture

# 4. Elenca tutte le skill attualmente installate
.\it-ops.cmd skills list

# 5. Elenca i bundle curati disponibili (core-dev, security-core, ops-core, k8s-core)
.\it-ops.cmd skills bundles
```

## Regola di Governance: Installazione Selettiva ("Install Strategically")
Antigravity carica automaticamente all'avvio i metadati (nome e descrizione) di ogni skill presente nel workspace o a livello globale. Installare centinaia di skill contemporaneamente appesantisce il contesto. Si raccomanda di installare selettivamente solo le skill rilevanti per il compito corrente.
