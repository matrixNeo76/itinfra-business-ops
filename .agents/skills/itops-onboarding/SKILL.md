---
name: itops-onboarding
description: Orchestrate end-to-end client onboarding across itinfra-business-ops and itinfra with atomic zero-drift certification.
---

# itops-onboarding — Antigravity Skill

## Purpose
Use this skill when onboarding a new customer into the Aure System ecosystem. This skill automates the simultaneous creation of:
1. Business and commercial operations workspace in `itinfra-business-ops/clients/<slug>/`
2. Technical architecture and engineering workspace in `itinfra/projects/<slug>/`
3. Immediate cross-repo zero-drift validation via `ITInfraBridge`.

## Available Command
```powershell
.\it-ops.cmd onboard <slug> --client "Nome Cliente S.r.l." --vat "IT12345678901" --subnet "192.168.10.0/24" --tier gold
```

## Workflows
1. Validate slug (lowercase kebab-case).
2. Select SLA Tier (`silver`: 20h, `gold`: 50h, `platinum`: 100h).
3. Verify primary subnet allocation.
4. Run onboarding command.
5. Inspect zero-drift certification and SHA-256 seal.
