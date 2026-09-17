"""MemoryEngine — Motore di Memoria Auto-Correttiva & Apprendimento Attestato (OKF v0.2).

Implementa lo standard Google Open Knowledge Format (OKF) v0.2 per:
- Registrazione e tracciamento incidenti e lezioni apprese (Trust Tiers: generated, verified, attested).
- Calcolo hash SHA-256 e sigillo di attestazione immutabile.
- Compilazione deterministica in regole attive per Antigravity (.agents/rules/*.md).
- Sincronizzazione atomica bidirezionale Hub-and-Spoke tra itinfra-business-ops e itinfra.
- Audit semantico, verifica scadenze (stale_after) ed eval harness.
"""

from __future__ import annotations

import datetime
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml


class MemoryEngine:
    """Gestore del grafo di conoscenza OKF v0.2 e compilatore regole Antigravity."""

    DOMAINS = ["core", "ui", "engineering", "documents", "technical", "business_ops"]
    VALID_TIERS = ["generated", "verified", "attested"]
    VALID_LIFECYCLES = ["active", "deprecated", "stale"]

    def __init__(self, repo_root: Optional[Path] = None, peer_root: Optional[Path] = None):
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root).resolve()

        if peer_root is None:
            # Default sibling in repos/
            sibling = self.repo_root.parent / ("itinfra" if self.repo_root.name == "itinfra-business-ops" else "itinfra-business-ops")
            self.peer_root = sibling if sibling.exists() else None
        else:
            self.peer_root = Path(peer_root).resolve() if Path(peer_root).exists() else None

        self.agents_dir = self.repo_root / ".agents"
        self.memory_dir = self.agents_dir / "memory"
        self.rules_dir = self.agents_dir / "rules"
        self.registry_file = self.memory_dir / "registry.yaml"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Assicura l'esistenza della gerarchia delle directory di memoria."""
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        for dom in self.DOMAINS:
            (self.memory_dir / dom).mkdir(parents=True, exist_ok=True)

        if not self.registry_file.exists():
            self._save_registry({
                "version": "0.2",
                "format": "google-okf-v0.2",
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "nodes": {}
            })

    def _load_registry(self) -> Dict[str, Any]:
        """Carica il registro di memoria globale."""
        if not self.registry_file.exists():
            return {"version": "0.2", "format": "google-okf-v0.2", "nodes": {}}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {"nodes": {}}
        except Exception:
            return {"nodes": {}}

    def _save_registry(self, registry_data: Dict[str, Any]) -> None:
        """Salva il registro di memoria con timestamp aggiornato."""
        registry_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(registry_data, f, sort_keys=False, allow_unicode=True)

    @staticmethod
    def parse_okf_file(filepath: Path) -> Tuple[Dict[str, Any], str]:
        """Estrae frontmatter YAML e corpo Markdown da un file OKF v0.2."""
        content = filepath.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"File {filepath.name} non conforme a OKF v0.2: frontmatter YAML assente.")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"File {filepath.name} malformato: delimitatori YAML '---' non chiusi.")

        raw_yaml = parts[1]
        body = parts[2].strip()
        metadata = yaml.safe_load(raw_yaml)
        if not isinstance(metadata, dict):
            metadata = {}

        return metadata, body

    @staticmethod
    def format_okf_file(metadata: Dict[str, Any], body: str) -> str:
        """Formatta un file conforme a OKF v0.2."""
        clean_yaml = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
        return f"---\n{clean_yaml}\n---\n\n{body}\n"

    def compute_node_hash(self, metadata: Dict[str, Any], body: str) -> str:
        """Calcola l'hash SHA-256 canonico del contenuto per l'attestazione."""
        canonical_meta = dict(metadata)
        if "trust" in canonical_meta and isinstance(canonical_meta["trust"], dict):
            trust_copy = dict(canonical_meta["trust"])
            trust_copy.pop("content_sha256", None)
            canonical_meta["trust"] = trust_copy

        dumped = yaml.safe_dump(canonical_meta, sort_keys=True) + "\n" + body.strip()
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def find_node_file(self, node_id: str) -> Optional[Path]:
        """Trova il percorso su disco di un nodo in base all'ID."""
        clean_id = node_id.upper().strip()
        for f in self.memory_dir.rglob("*.okf.md"):
            if f.name.upper().startswith(clean_id):
                return f
        for f in self.memory_dir.rglob("*.okf.md"):
            try:
                meta, _ = self.parse_okf_file(f)
                if meta.get("id", "").upper() == clean_id:
                    return f
            except Exception:
                continue
        return None

    def record_lesson(
        self,
        node_id: str,
        title: str,
        description: str,
        domain: str,
        incident: Dict[str, str],
        guardrail_content: str,
        eval_config: Optional[Dict[str, str]] = None,
        sources: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        replaces: Optional[List[str]] = None,
        stale_days: int = 365,
    ) -> Path:
        """Registra un nuovo nodo di apprendimento (Trust Tier: generated)."""
        clean_id = node_id.upper().strip()
        if domain not in self.DOMAINS:
            domain = "core"

        target_dir = self.memory_dir / domain
        target_file = target_dir / f"{clean_id}.okf.md"

        now = datetime.datetime.now(datetime.timezone.utc)
        stale_after = (now + datetime.timedelta(days=stale_days)).isoformat()

        metadata: Dict[str, Any] = {
            "type": "lesson",
            "id": clean_id,
            "title": title,
            "description": description,
            "domain": domain,
            "lifecycle": "active",
            "stale_after": stale_after,
            "replaces": replaces or [],
            "incident": {
                "context": incident.get("context", "Interazione operativa o sviluppo codice"),
                "observed_failure": incident.get("observed_failure", "Errore rilevato"),
                "root_cause": incident.get("root_cause", "Causa radice del disallineamento"),
            },
            "trust": {
                "tier": "generated",
                "attested_by": "machine:agent-proposal",
                "attestation_date": now.isoformat(),
                "attestation_method": "incident_capture",
                "content_sha256": "",
            },
            "sources": sources or [],
            "tags": tags or [domain, "anti-pattern", "guardrail"],
        }

        if eval_config:
            metadata["eval"] = eval_config

        content = self.format_okf_file(metadata, guardrail_content)
        target_file.write_text(content, encoding="utf-8")

        # Aggiorna registro
        reg = self._load_registry()
        reg["nodes"][clean_id] = {
            "file": str(target_file.relative_to(self.memory_dir)).replace("\\", "/"),
            "domain": domain,
            "tier": "generated",
            "title": title,
            "updated_at": now.isoformat(),
        }
        self._save_registry(reg)

        return target_file

    def attest_lesson(
        self,
        node_id: str,
        attester: str = "human:possumato",
        method: str = "live_interaction_review",
    ) -> Dict[str, Any]:
        """Sigilla un nodo con hash SHA-256 e lo promuove a trust.tier: attested."""
        filepath = self.find_node_file(node_id)
        if not filepath:
            raise FileNotFoundError(f"Nodo {node_id} non trovato in {self.memory_dir}")

        meta, body = self.parse_okf_file(filepath)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        meta["trust"] = {
            "tier": "attested",
            "attested_by": attester,
            "attestation_date": now,
            "attestation_method": method,
            "content_sha256": "",
        }
        meta["lifecycle"] = "active"

        # Calcolo hash canonico
        sha = self.compute_node_hash(meta, body)
        meta["trust"]["content_sha256"] = sha

        # Se rimpiazza altri nodi, segnali come deprecated
        for old_id in meta.get("replaces", []):
            old_file = self.find_node_file(old_id)
            if old_file:
                try:
                    old_meta, old_body = self.parse_okf_file(old_file)
                    old_meta["lifecycle"] = "deprecated"
                    old_file.write_text(self.format_okf_file(old_meta, old_body), encoding="utf-8")
                except Exception:
                    pass

        content = self.format_okf_file(meta, body)
        filepath.write_text(content, encoding="utf-8")

        # Aggiorna registro
        reg = self._load_registry()
        clean_id = meta.get("id", node_id).upper()
        reg["nodes"][clean_id] = {
            "file": str(filepath.relative_to(self.memory_dir)).replace("\\", "/"),
            "domain": meta.get("domain", "core"),
            "tier": "attested",
            "title": meta.get("title", ""),
            "attested_by": attester,
            "sha256": sha,
            "updated_at": now,
        }
        self._save_registry(reg)

        return meta

    def compile_rules(self) -> List[Path]:
        """Compila deterministicamente i nodi attivi e attestati nei file .agents/rules/*.md per Antigravity."""
        self._ensure_directories()
        nodes_by_domain: Dict[str, List[Tuple[Dict[str, Any], str]]] = {d: [] for d in self.DOMAINS}

        # Raccoglie tutti i nodi attivi
        for f in self.memory_dir.rglob("*.okf.md"):
            try:
                meta, body = self.parse_okf_file(f)
                if meta.get("lifecycle") == "active":
                    dom = meta.get("domain", "core")
                    if dom not in nodes_by_domain:
                        nodes_by_domain[dom] = []
                    nodes_by_domain[dom].append((meta, body))
            except Exception:
                continue

        compiled_files: List[Path] = []

        # 1. Core Invariants (Fondamentali)
        core_nodes = nodes_by_domain.get("core", [])
        if core_nodes:
            core_rule_file = self.rules_dir / "00-core-invariants.md"
            content = self._generate_rule_markdown(
                rule_name="Core System Invariants & Zero-Search Fast-Path",
                scope="Regole capitali e fast-path operativo a 0 secondi",
                nodes=core_nodes
            )
            core_rule_file.write_text(content, encoding="utf-8")
            compiled_files.append(core_rule_file)

        # 2. Regole UI Generative
        ui_nodes = nodes_by_domain.get("ui", [])
        if ui_nodes:
            ui_rule_file = self.rules_dir / "10-generative-ui-rules.md"
            content = self._generate_rule_markdown(
                rule_name="Generative UI & Visual Presentation Invariants",
                scope="Regole operative tassative per widget interattivi e anteprime documenti",
                nodes=ui_nodes
            )
            ui_rule_file.write_text(content, encoding="utf-8")
            compiled_files.append(ui_rule_file)

        # 3. Regole Document Engine & Contabilità
        doc_nodes = nodes_by_domain.get("documents", []) + nodes_by_domain.get("business_ops", [])
        if doc_nodes:
            doc_rule_file = self.rules_dir / "20-document-engine-rules.md"
            content = self._generate_rule_markdown(
                rule_name="Document Intelligence & Business Ops Invariants",
                scope="Regole operative su template, computo economico, P.IVA e contratti SLA",
                nodes=doc_nodes
            )
            doc_rule_file.write_text(content, encoding="utf-8")
            compiled_files.append(doc_rule_file)

        # 4. Regole Engineering & Scripting
        eng_nodes = nodes_by_domain.get("engineering", [])
        if eng_nodes:
            eng_rule_file = self.rules_dir / "30-code-engineering-rules.md"
            content = self._generate_rule_markdown(
                rule_name="Code Engineering & Execution Invariants",
                scope="Regole su gestione stringhe Python, escaping PowerShell e script scratch",
                nodes=eng_nodes
            )
            eng_rule_file.write_text(content, encoding="utf-8")
            compiled_files.append(eng_rule_file)

        return compiled_files

    def _generate_rule_markdown(self, rule_name: str, scope: str, nodes: List[Tuple[Dict[str, Any], str]]) -> str:
        """Genera il markdown compatto ad alta leggibilità per le regole di Antigravity."""
        lines = [
            f"# {rule_name}",
            f"> **Ambito Operativo**: {scope}",
            "> *Compilato deterministicamente dal MemoryEngine OKF v0.2*",
            "",
            "---",
            "",
        ]

        for meta, body in nodes:
            node_id = meta.get("id", "LES-UNKNOWN")
            title = meta.get("title", "Regola")
            tier = meta.get("trust", {}).get("tier", "unverified")
            tier_badge = "🔒 [ATTESTED]" if tier == "attested" else "⚠️ [GENERATED]"

            lines.append(f"## {tier_badge} `{node_id}` — {title}")
            desc = meta.get("description", "")
            if desc:
                lines.append(f"*{desc}*")
            lines.append("")

            # Estrae la sezione guardrail dal corpo
            guardrail_match = re.search(r"#+\s*(?:Regola Vincolante|Guardrail)[\s\S]*?(?=(?:#+|$))", body, re.IGNORECASE)
            if guardrail_match:
                lines.append(guardrail_match.group(0).strip())
            else:
                lines.append(body.strip())

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def audit_memory(self) -> Dict[str, Any]:
        """Scansiona l'intero grafo di memoria rilevando anomalie, scadenze e hash non conformi."""
        report: Dict[str, Any] = {
            "total_nodes": 0,
            "active_nodes": 0,
            "attested_nodes": 0,
            "generated_nodes": 0,
            "stale_nodes": [],
            "tampered_nodes": [],
            "schema_errors": [],
            "status": "PASS"
        }

        now = datetime.datetime.now(datetime.timezone.utc)

        for f in self.memory_dir.rglob("*.okf.md"):
            report["total_nodes"] += 1
            try:
                meta, body = self.parse_okf_file(f)
            except Exception as e:
                report["schema_errors"].append({"file": str(f.name), "error": str(e)})
                continue

            node_id = meta.get("id", f.stem)
            lifecycle = meta.get("lifecycle", "active")
            tier = meta.get("trust", {}).get("tier", "generated")

            if lifecycle == "active":
                report["active_nodes"] += 1
            if tier == "attested":
                report["attested_nodes"] += 1
            elif tier == "generated":
                report["generated_nodes"] += 1

            # Controllo Stale
            stale_str = meta.get("stale_after")
            if stale_str:
                try:
                    stale_dt = datetime.datetime.fromisoformat(stale_str.replace("Z", "+00:00"))
                    if stale_dt < now:
                        report["stale_nodes"].append({"id": node_id, "stale_since": stale_str})
                except Exception:
                    pass

            # Controllo Tamper / Hash Integrity per i nodi attestati
            if tier == "attested":
                expected_sha = meta.get("trust", {}).get("content_sha256")
                actual_sha = self.compute_node_hash(meta, body)
                if expected_sha and actual_sha != expected_sha:
                    report["tampered_nodes"].append({
                        "id": node_id,
                        "file": str(f.name),
                        "expected_sha": expected_sha,
                        "actual_sha": actual_sha
                    })

        if report["tampered_nodes"] or report["schema_errors"]:
            report["status"] = "FAIL"
        elif report["stale_nodes"]:
            report["status"] = "WARNING"

        return report

    def sync_with_peer(self) -> Dict[str, Any]:
        """Sincronizzazione atomica bidirezionale tra il repository locale e il repository gemello."""
        if not self.peer_root:
            return {"status": "SKIPPED", "reason": "Repository gemello non trovato o non configurato"}

        peer_agents_dir = self.peer_root / ".agents"
        peer_memory_dir = peer_agents_dir / "memory"
        peer_rules_dir = peer_agents_dir / "rules"

        peer_memory_dir.mkdir(parents=True, exist_ok=True)
        peer_rules_dir.mkdir(parents=True, exist_ok=True)

        copied_to_peer = 0
        copied_from_peer = 0

        # 1. Copia i nodi locali mancanti o più recenti sul peer
        for local_file in self.memory_dir.rglob("*.okf.md"):
            rel_path = local_file.relative_to(self.memory_dir)
            target_peer_file = peer_memory_dir / rel_path
            target_peer_file.parent.mkdir(parents=True, exist_ok=True)

            if not target_peer_file.exists() or local_file.stat().st_mtime > target_peer_file.stat().st_mtime:
                target_peer_file.write_text(local_file.read_text(encoding="utf-8"), encoding="utf-8")
                copied_to_peer += 1

        # 2. Copia i nodi del peer mancanti o più recenti sul locale
        for peer_file in peer_memory_dir.rglob("*.okf.md"):
            rel_path = peer_file.relative_to(peer_memory_dir)
            target_local_file = self.memory_dir / rel_path
            target_local_file.parent.mkdir(parents=True, exist_ok=True)

            if not target_local_file.exists() or peer_file.stat().st_mtime > target_local_file.stat().st_mtime:
                target_local_file.write_text(peer_file.read_text(encoding="utf-8"), encoding="utf-8")
                copied_from_peer += 1

        # 3. Compila le regole in entrambi i repository
        self.compile_rules()
        peer_engine = MemoryEngine(repo_root=self.peer_root, peer_root=self.repo_root)
        peer_engine.compile_rules()

        # 4. Sincronizza il registro
        if self.registry_file.exists():
            peer_reg = peer_memory_dir / "registry.yaml"
            peer_reg.write_text(self.registry_file.read_text(encoding="utf-8"), encoding="utf-8")

        return {
            "status": "OK",
            "peer_repo": str(self.peer_root.name),
            "copied_to_peer": copied_to_peer,
            "copied_from_peer": copied_from_peer,
            "synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
