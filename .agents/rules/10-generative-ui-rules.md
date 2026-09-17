# Generative UI & Visual Presentation Invariants
> **Ambito Operativo**: Regole operative tassative per widget interattivi e anteprime documenti
> *Compilato deterministicamente dal MemoryEngine OKF v0.2*

---

## 🔒 [ATTESTED] `LES-UI-001` — Vincoli Dimensionali e Sandbox Iframe per Generative UI
*Prevenzione finestre di scorrimento verticale compresse e link file:/// inerti nei widget chat*

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

---
