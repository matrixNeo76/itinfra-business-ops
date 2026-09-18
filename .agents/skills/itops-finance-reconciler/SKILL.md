---
name: itops-finance-reconciler
description: Reconcile PSA timesheet hours, SLA hours banks, MPS excess copy charges, and generate billing batches.
---

# itops-finance-reconciler — Antigravity Skill

## Purpose
Execute end-of-month and quarterly billing reconciliation, verifying contract hours bank debits, spot unbilled interventions, and excess copy counter charges.

## Available Commands
```powershell
# Verifica saldo monte ore
.\it-ops.cmd contract <slug> balance

# Riepilogo fatturazione e scadenziario
.\it-ops.cmd billing <slug> summary

# Generazione batch fattura
.\it-ops.cmd billing <slug> generate --period YYYY-MM

# Esecuzione agente Finance-Reconciler
.\it-ops.cmd agent finance-reconciler <slug>
```
