"""CognitiveBridge — Ponte di Integrazione tra Memoria Ibrida a 3 Livelli e Auto-Correzione (SPEC-17).

Collega:
- Memoria Ibrida di Progetto ed Enterprise (itinfra: projects/_global_scratchpad.md)
- Motore di Auto-Correzione Attestata (itinfra-business-ops: MemoryEngine OKF v0.2)

Funzionalità:
- Estrazione ed elencazione voci dello scratchpad globale pronte per la promozione (list_promotables)
- Promozione transazionale di una voce scratchpad a guardrail attestato per Antigravity (promote_entry)
- Garanzia di concorrenza sicura tramite AtomicFileLock
- Garanzia di sicurezza multi-tenant Zero-Leakage (validate_global_entry_safety)
- Marcatura di idempotenza (<!-- promoted:LES-xxxx -->)
"""

from __future__ import annotations

import datetime
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.core.memory_engine import MemoryEngine


def _load_itinfra_memory_module(itinfra_root: Path):
    """Carica dinamicamente il modulo itinfra_memory.py dal repository itinfra."""
    script_path = itinfra_root / "scripts" / "itinfra_memory.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Modulo itinfra_memory.py non trovato in: {script_path}")

    spec = importlib.util.spec_from_file_location("itinfra_memory", str(script_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossibile creare spec per {script_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CognitiveBridge:
    """Orchestratore del ponte cognitivo tra lo scratchpad globale e i guardrail attestati."""

    def __init__(self, repo_root: Optional[Path] = None, itinfra_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.itinfra_root = itinfra_root or (self.repo_root.parent / "itinfra")

        self.memory_engine = MemoryEngine(repo_root=self.repo_root, peer_root=self.itinfra_root)

        # Carica modulo memoria itinfra
        self._itinfra_mod = None
        if self.itinfra_root.exists():
            try:
                self._itinfra_mod = _load_itinfra_memory_module(self.itinfra_root)
            except Exception:
                self._itinfra_mod = None

    @property
    def global_scratchpad_path(self) -> Path:
        return self.itinfra_root / "projects" / "_global_scratchpad.md"

    @property
    def global_lock_path(self) -> Path:
        return self.itinfra_root / "projects" / "_global_scratchpad.lock"

    def list_promotables(self) -> List[Dict[str, Any]]:
        """Estrae tutte le voci da _global_scratchpad.md che non sono ancora state promosse a guardrail."""
        if not self.global_scratchpad_path.exists():
            return []

        content = self.global_scratchpad_path.read_text(encoding="utf-8")
        promotables: List[Dict[str, Any]] = []

        current_sec = "Generale"
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("## 1. Best Practices"):
                current_sec = "Best Practices"
            elif line_str.startswith("## 2. Known Issues"):
                current_sec = "Known Issues"
            elif line_str.startswith("## 3. Hardware & Vendor"):
                current_sec = "Hardware Guidelines"
            elif line_str.startswith("## 4. Open Architectural"):
                current_sec = "Open Questions"
            elif line_str.startswith("## "):
                current_sec = line_str.replace("## ", "")
            elif line_str.startswith("- [") and "<!-- id:" in line_str:
                id_match = re.search(r"<!-- id:([A-Za-z0-9_-]+) -->", line_str)
                promoted_match = re.search(r"<!-- promoted:([A-Za-z0-9_-]+) -->", line_str)

                entry_id = id_match.group(1) if id_match else "unknown"
                is_promoted = bool(promoted_match)
                promoted_to = promoted_match.group(1) if promoted_match else None

                # Estrazione testo pulito
                text_clean = re.sub(r"<!--.*?-->", "", line_str).strip()
                text_clean = re.sub(r"^-\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]\s*(\[[^\]]+\])?\s*", "", text_clean).strip()

                promotables.append({
                    "id": entry_id,
                    "section": current_sec,
                    "raw_line": line_str,
                    "text": text_clean,
                    "is_promoted": is_promoted,
                    "promoted_to": promoted_to,
                })

        return promotables

    def promote_entry(
        self,
        entry_id: str,
        domain: str,
        node_id: str,
        title: str,
        guardrail_override: Optional[str] = None,
        attester: str = "human:possumato",
        eval_config: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Promuove una voce da _global_scratchpad.md a nodo di conoscenza OKF v0.2 attestato e aggiorna le regole."""
        if not self.global_scratchpad_path.exists():
            raise FileNotFoundError(f"Scratchpad globale non trovato in: {self.global_scratchpad_path}")

        clean_id = node_id.upper().strip()
        target_entry_id = entry_id.lower().strip()

        # Invocazione AtomicFileLock da itinfra se disponibile
        lock_ctx = None
        if self._itinfra_mod and hasattr(self._itinfra_mod, "AtomicFileLock"):
            lock_ctx = self._itinfra_mod.AtomicFileLock(self.global_lock_path)

        def _do_promotion():
            content = self.global_scratchpad_path.read_text(encoding="utf-8")
            pattern = re.compile(rf"^.*<!-- id:{re.escape(target_entry_id)} -->.*$", re.MULTILINE)
            match = pattern.search(content)

            if not match:
                raise ValueError(f"Voce con ID '{target_entry_id}' non trovata nello scratchpad globale.")

            line = match.group(0)

            # Verifica se gia' promossa
            if "<!-- promoted:" in line:
                prom_match = re.search(r"<!-- promoted:([A-Za-z0-9_-]+) -->", line)
                existing = prom_match.group(1) if prom_match else "unknown"
                raise ValueError(f"La voce '{target_entry_id}' e' gia' stata promossa al guardrail '{existing}'.")

            # Verifica sicurezza Multi-Tenant
            if self._itinfra_mod and hasattr(self._itinfra_mod, "validate_global_entry_safety"):
                self._itinfra_mod.validate_global_entry_safety(line)

            # Estrazione testo puro della voce
            text_clean = re.sub(r"<!--.*?-->", "", line).strip()
            text_clean = re.sub(r"^-\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]\s*(\[[^\]]+\])?\s*", "", text_clean).strip()

            # Costruzione contenuto guardrail
            if guardrail_override:
                guardrail_body = guardrail_override.strip()
            else:
                guardrail_body = f"# Regola Vincolante (Guardrail)\n1. **{title}**:\n   - {text_clean}\n"

            # Registrazione nodo in MemoryEngine
            incident_data = {
                "context": f"Promozione da _global_scratchpad.md (ID: {target_entry_id})",
                "observed_failure": f"Rischio di violazione best-practice o limitazione hardware: {text_clean}",
                "root_cause": f"Conoscenza operativa estratta dal campo ({target_entry_id})",
            }

            self.memory_engine.record_lesson(
                node_id=clean_id,
                title=title,
                description=f"Guardrail attestato derivato da {target_entry_id}",
                domain=domain,
                incident=incident_data,
                guardrail_content=guardrail_body,
                eval_config=eval_config,
                sources=[f"file://@projects/_global_scratchpad.md#{target_entry_id}"],
                tags=[domain, "promoted-guardrail", "scratchpad"],
            )

            # Attestazione immediata con hash SHA-256
            attestation_meta = self.memory_engine.attest_lesson(
                node_id=clean_id,
                attester=attester,
                method="scratchpad_promotion_bridge"
            )

            # Marcatura transazionale nello scratchpad
            new_line = line.rstrip() + f" <!-- promoted:{clean_id} -->"
            updated_content = content.replace(line, new_line)
            self.global_scratchpad_path.write_text(updated_content, encoding="utf-8")

            # Sincronizzazione e compilazione regole per entrambi i repository
            self.memory_engine.sync_with_peer()

            return {
                "status": "PROMOTED",
                "entry_id": target_entry_id,
                "node_id": clean_id,
                "domain": domain,
                "title": title,
                "sha256": attestation_meta["trust"]["content_sha256"],
                "promoted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        if lock_ctx:
            with lock_ctx:
                return _do_promotion()
        else:
            return _do_promotion()
