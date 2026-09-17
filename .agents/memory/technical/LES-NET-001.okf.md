---
type: lesson
id: LES-NET-001
title: Configurazione MTU 1400 e TCP MSS Clamping su Tunnel ZeroTier
description: Guardrail attestato derivato da mem-bp01zt
domain: technical
lifecycle: active
stale_after: '2027-09-17T18:48:35.279555+00:00'
replaces: []
incident:
  context: 'Promozione da _global_scratchpad.md (ID: mem-bp01zt)'
  observed_failure: 'Rischio di violazione best-practice o limitazione hardware: [ZeroTier/VPN]
    Su tutti i collegamenti overlay Layer 2/Layer 3 ZeroTier verso file server Windows
    (SMB/DFS), configurare sempre MTU 1400 e abilitare TCP MSS Clamping (change-tcp-mss=yes)
    sui router di confine per evitare frammentazione e timeout di sessione.'
  root_cause: Conoscenza operativa estratta dal campo (mem-bp01zt)
trust:
  tier: attested
  attested_by: human:possumato
  attestation_date: '2026-09-17T18:48:35.305091+00:00'
  attestation_method: scratchpad_promotion_bridge
  content_sha256: b6faab9a69487dc07d90fcb4a1637e6564d6923a28aae7371fc8bb6ea3b4baff
sources:
- file://@projects/_global_scratchpad.md#mem-bp01zt
tags:
- technical
- promoted-guardrail
- scratchpad
---

# Regola Vincolante (Guardrail)
1. **Configurazione MTU 1400 e TCP MSS Clamping su Tunnel ZeroTier**:
   - [ZeroTier/VPN] Su tutti i collegamenti overlay Layer 2/Layer 3 ZeroTier verso file server Windows (SMB/DFS), configurare sempre MTU 1400 e abilitare TCP MSS Clamping (change-tcp-mss=yes) sui router di confine per evitare frammentazione e timeout di sessione.
