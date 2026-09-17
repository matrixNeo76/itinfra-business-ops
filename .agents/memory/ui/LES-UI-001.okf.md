---
type: lesson
id: LES-UI-001
title: Vincoli Dimensionali e Sandbox Iframe per Generative UI
description: Prevenzione finestre di scorrimento verticale compresse e link file:///
  inerti nei widget chat
domain: ui
lifecycle: active
stale_after: '2027-09-01T00:00:00Z'
replaces: []
incident:
  context: Visualizzazione interattiva preventivi, contratti e rapportini in chat
    Antigravity
  observed_failure: L'agente ha generato un widget inline <agent-embed> eccedente
    500px provocando scrollbar verticale forzata e inserito tag <a href='file://...'>
    che risultavano inerti per blocco sandbox del browser.
  root_cause: Altezza massima viewport iframe fissata a 500px da Antigravity; Chromium
    blocca navigazione file:// da iframes sandboxed.
trust:
  tier: attested
  attested_by: human:possumato
  attestation_date: '2026-09-17T18:38:14.196563+00:00'
  attestation_method: live_interaction_review
  content_sha256: fa37b891b4cadfee4fadf75cbe45f07431e9f7c32d089cb8a41ab6f3e6969570
eval:
  negative_check: grep '<agent-embed' chat_response && grep 'file:///' html_embed
  positive_assertion: inline_height <= 380 && uses_side_pane_for_documents == true
sources:
- file://@C:/Users/auresystem/.gemini/antigravity/builtin/skills/generative_ui/SKILL.md
- conversation://fa358d31-fe29-48c8-af16-883e5d5b4d97
tags:
- generative-ui
- iframe-sandbox
- side-pane
- zero-scroll
- guardrail
---

# Regola Vincolante (Guardrail)
1. **Documenti Complessi (Preventivi, Contratti SLA, Rapportini, Fatture)**:
   - È **SEVERAMENTE VIETATO** comprimere documenti A4 completi o tabelle estese all'interno di `<agent-embed>` inline nella chat.
   - Generarli SEMPRE come artefatti HTML a tutto schermo (`UserFacing: true` in `ArtifactMetadata`) per l'apertura a tutta altezza nel **Pannello Laterale (Side Pane)**.
2. **Dimensioni Massime per Widget Inline nella Chat**:
   - Qualsiasi componente incorporato con `<agent-embed>` deve avere un'altezza totale tassativamente **inferiore o uguale a 380px**.
   - Zero barre di scorrimento verticale interne o esterne (`overflow-y: hidden`).
3. **Azioni Consentite all'interno dell'Iframe**:
   - È **SEVERAMENTE VIETATO** inserire link `<a href="file://...">` o chiamate `window.open` a file locali dentro `<agent-embed>` (vengono bloccati silenziosamente dal browser).
   - Includere SOLO azioni locali: slider di calcolo, toggle di visualizzazione e pulsanti di copia negli appunti (`navigator.clipboard.writeText(...)`).
4. **Apertura File Locali**:
   - I link ai file fisici (`.pdf`, `.docx`, `.html`) devono essere posti nel messaggio Markdown nativo della chat oppure lanciati direttamente via shell con `Start-Process`.
