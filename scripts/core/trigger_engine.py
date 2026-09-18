#!/usr/bin/env python3
"""
scripts/core/trigger_engine.py — Event-Driven Trigger System & Safe Action Gate (SPEC-22)
Gestione proattiva degli eventi operativi, bus di trigger, persistenza append-only
in .agents/events.jsonl e presidio di sicurezza Safe Action Gate (Human-in-the-Loop).
"""

import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.core.config import get_clients_dir, get_itinfra_dir
from scripts.core.bridge import ITInfraBridge


class TriggerEngine:
    """
    Motore a eventi proattivo per ITInfra Business Ops.
    Intercetta variazioni hardware As-Built, soglie consumabili MPS,
    consumo monte ore SLA e arrivo documenti, trasformandoli in azioni
    guidate con autorizzazione controllata.
    """

    def __init__(self, repo_root: Optional[Path] = None, clients_root: Optional[Path] = None):
        self.repo_root = repo_root or ROOT_DIR
        self.clients_root = clients_root or get_clients_dir()
        self.itinfra_root = self.repo_root.parent / "itinfra"
        self.agents_dir = self.repo_root / ".agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.events_log = self.agents_dir / "events.jsonl"
        self.pending_actions_file = self.agents_dir / "pending_actions.json"
        self.bridge = ITInfraBridge(itinfra_root=self.itinfra_root, clients_root=self.clients_root)

    def _append_event(self, event: Dict[str, Any]) -> None:
        """Accoda l'evento al log immutabile append-only."""
        with open(self.events_log, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _load_pending_actions(self) -> List[Dict[str, Any]]:
        """Carica l'elenco delle azioni in attesa di approvazione."""
        if not self.pending_actions_file.is_file():
            return []
        try:
            with open(self.pending_actions_file, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_pending_actions(self, actions: List[Dict[str, Any]]) -> None:
        """Salva l'elenco delle azioni in attesa."""
        with open(self.pending_actions_file, "w", encoding="utf-8") as fp:
            json.dump(actions, fp, indent=2, ensure_ascii=False)

    def emit_event(
        self,
        event_type: str,
        slug: str,
        source: str,
        payload: Dict[str, Any],
        auto_evaluate: bool = True,
    ) -> Dict[str, Any]:
        """
        Emette un nuovo evento nel sistema e, se richiesto, ne valuta
        immediatamente le regole operative.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        slug_clean = slug.replace("-", "").lower()
        evt_type_short = event_type.split(".")[-1].upper()[:8]
        evt_id = f"EVT-{ts}-{evt_type_short}-{slug_clean}"

        event_data: Dict[str, Any] = {
            "event_id": evt_id,
            "event_type": event_type,
            "slug": slug,
            "timestamp": now,
            "source": source,
            "payload": payload,
            "action_proposed": None,
            "status": "EMITTED",
            "resolved_at": None,
            "resolved_by": None,
        }

        if auto_evaluate:
            action = self.evaluate_rules(event_data)
            if action:
                event_data["action_proposed"] = action
                if action.get("requires_approval", True):
                    event_data["status"] = "PENDING_APPROVAL"
                    actions = self._load_pending_actions()
                    actions.append(action)
                    self._save_pending_actions(actions)
                else:
                    event_data["status"] = "EXECUTED"
                    event_data["resolved_at"] = now
                    event_data["resolved_by"] = "auto:trigger_engine"

        self._append_event(event_data)
        return event_data

    def evaluate_rules(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Valuta le regole di matching per l'evento e genera la proposta d'azione.
        """
        etype = event.get("event_type", "")
        slug = event.get("slug", "")
        payload = event.get("payload", {})
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")

        # Regola 1: Allarme Toner MPS
        if etype == "telemetry.mps.consumable_low":
            printer_model = payload.get("model", "Stampante Multifunzione")
            toner_info = payload.get("toner_info", "Toner <= 15%")
            action_id = f"ACT-{ts}-MPS-{slug}"
            return {
                "action_id": action_id,
                "event_id": event.get("event_id"),
                "slug": slug,
                "action_type": "mps_cartridge_reorder",
                "title": f"Riordino Consumabile per {printer_model}",
                "description": f"Rilevato {toner_info} per cliente {slug}. Predisporre cartuccia ricambio OEM e bolla di trasporto.",
                "requires_approval": True,
                "workflow_to_run": None,
                "target_params": {"slug": slug, "printer": printer_model, "toner": toner_info},
                "created_at": event.get("timestamp"),
            }

        # Regola 2: Saldo Ore SLA Critico
        if etype == "telemetry.sla.hours_low":
            rem_hours = payload.get("remaining_hours", 0.0)
            tot_hours = payload.get("total_hours", 0.0)
            pct = payload.get("hours_pct", 0)
            action_id = f"ACT-{ts}-SLA-{slug}"
            return {
                "action_id": action_id,
                "event_id": event.get("event_id"),
                "slug": slug,
                "action_type": "sla_contract_extension",
                "title": f"Proposta Rinnovo / Espansione SLA ({rem_hours:.1f}h residue)",
                "description": f"Il cliente {slug} ha consumato l'80%+ del monte ore ({rem_hours:.1f}h rimanenti su {tot_hours:.1f}h). Predisporre proposta commerciale di ricarica.",
                "requires_approval": True,
                "workflow_to_run": "contract-renewal",
                "target_params": {"slug": slug, "remaining_hours": rem_hours},
                "created_at": event.get("timestamp"),
            }

        # Regola 3: Modifica As-Built Hardware in itinfra
        if etype == "itinfra.asbuilt.changed":
            uncontracted = payload.get("uncontracted_devices", [])
            action_id = f"ACT-{ts}-ASB-{slug}"
            return {
                "action_id": action_id,
                "event_id": event.get("event_id"),
                "slug": slug,
                "action_type": "contract_sla_addendum",
                "title": f"Riconciliazione Nuovi Apparati As-Built ({len(uncontracted)} apparati)",
                "description": f"Rilevati apparati in 06-As-Built.md di {slug} privi di copertura contrattuale: {uncontracted}. Predisporre addendum SLA.",
                "requires_approval": True,
                "workflow_to_run": None,
                "target_params": {"slug": slug, "devices": uncontracted},
                "created_at": event.get("timestamp"),
            }

        # Regola 4: Drop Documento Ingestione
        if etype == "documents.incoming.dropped":
            file_path = payload.get("file_path", "")
            return {
                "action_id": f"ACT-{ts}-ING-{slug}",
                "event_id": event.get("event_id"),
                "slug": slug,
                "action_type": "auto_document_ingestion",
                "title": f"Ingestione Automatica Documento",
                "description": f"Avvio pipeline di ingestione visiva SOTA su {file_path}",
                "requires_approval": False,
                "workflow_to_run": None,
                "target_params": {"file_path": file_path, "slug": slug},
                "created_at": event.get("timestamp"),
            }

        # Regola 5: Pre-Flight Fine Mese
        if etype == "temporal.billing.preflight":
            period = payload.get("period", datetime.date.today().strftime("%Y-%m"))
            return {
                "action_id": f"ACT-{ts}-PREFLIGHT-BILLING",
                "event_id": event.get("event_id"),
                "slug": "all",
                "action_type": "monthly_closing_preflight",
                "title": f"Pre-Flight Chiusura Mensile {period}",
                "description": f"Simulazione chiusura contabile e calcolo conguagli fine mese per tutti i clienti.",
                "requires_approval": False,
                "workflow_to_run": "monthly-closing",
                "target_params": {"period": period, "dry_run": True},
                "created_at": event.get("timestamp"),
            }

        return None

    def list_events(self, slug: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Restituisce gli eventi recenti dal log immutabile."""
        if not self.events_log.is_file():
            return []
        events: List[Dict[str, Any]] = []
        try:
            with open(self.events_log, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if slug and slug != "all" and data.get("slug") != slug:
                                continue
                            events.append(data)
                        except Exception:
                            continue
        except Exception:
            return []

        events.reverse()
        return events[:limit]

    def list_pending_actions(self, slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Restituisce le azioni in attesa di approvazione umana."""
        actions = self._load_pending_actions()
        if slug and slug != "all":
            return [a for a in actions if a.get("slug") == slug]
        return actions

    def approve_action(self, action_id: str, approved_by: str = "human:possumato") -> Dict[str, Any]:
        """
        Approva ed esegue un'azione proposta dal Safe Action Gate.
        Se l'azione prevede un workflow collegato, lo invoca automaticamente.
        """
        actions = self._load_pending_actions()
        target_action = None
        remaining_actions = []

        for a in actions:
            if a.get("action_id") == action_id:
                target_action = a
            else:
                remaining_actions.append(a)

        if not target_action:
            raise ValueError(f"Azione {action_id} non trovata tra le azioni in attesa.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target_action["status"] = "APPROVED"
        target_action["resolved_at"] = now
        target_action["resolved_by"] = approved_by

        # Se prevede un workflow, lo innesca
        wf_name = target_action.get("workflow_to_run")
        wf_res = None
        if wf_name:
            from scripts.core.workflow_engine import WorkflowEngine
            from scripts.pipelines.workflow_definitions import WorkflowRegistry
            wf_engine = WorkflowEngine(repo_root=self.repo_root, clients_root=self.clients_root)
            reg_defs = WorkflowRegistry.get_definitions()
            if wf_name in reg_defs:
                wdef = reg_defs[wf_name]
                wf_instance = wf_engine.create_workflow(
                    workflow_type=wf_name,
                    slug=target_action.get("slug", "all"),
                    step_definitions=wdef.get("steps"),
                    metadata=target_action.get("target_params", {}),
                    initiated_by=approved_by,
                )
                runners = WorkflowRegistry.get_runners(clients_root=self.clients_root, itinfra_root=self.itinfra_root).get(wf_name, {})
                wf_res = wf_engine.run_workflow(wf_instance, runners, resume=False, dry_run=False)

        # Salva stato aggiornato delle azioni pendenti
        self._save_pending_actions(remaining_actions)

        # Registra evento di risoluzione
        self.emit_event(
            event_type="gate.action.approved",
            slug=target_action.get("slug", "all"),
            source="safe_action_gate",
            payload={"action_id": action_id, "workflow_executed": wf_name, "workflow_status": wf_res.get("status") if wf_res else None},
            auto_evaluate=False,
        )

        return {
            "status": "APPROVED",
            "action": target_action,
            "workflow_result": wf_res
        }

    def reject_action(self, action_id: str, reason: str = "", rejected_by: str = "human:possumato") -> Dict[str, Any]:
        """Rifiuta ed archivia un'azione proposta dal Safe Action Gate."""
        actions = self._load_pending_actions()
        target_action = None
        remaining_actions = []

        for a in actions:
            if a.get("action_id") == action_id:
                target_action = a
            else:
                remaining_actions.append(a)

        if not target_action:
            raise ValueError(f"Azione {action_id} non trovata tra le azioni in attesa.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target_action["status"] = "REJECTED"
        target_action["resolved_at"] = now
        target_action["resolved_by"] = rejected_by
        target_action["rejection_reason"] = reason

        self._save_pending_actions(remaining_actions)

        self.emit_event(
            event_type="gate.action.rejected",
            slug=target_action.get("slug", "all"),
            source="safe_action_gate",
            payload={"action_id": action_id, "reason": reason},
            auto_evaluate=False,
        )

        return {
            "status": "REJECTED",
            "action": target_action
        }

    def scan_sources(self, slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Esegue una scansione istantanea di tutte le sorgenti (MPS, SLA, Bridge)
        ed emette gli eventi corrispondenti per le condizioni rilevate.
        """
        emitted: List[Dict[str, Any]] = []
        targets = [slug] if slug and slug != "all" else [d.name for d in self.clients_root.iterdir() if d.is_dir() and not d.name.startswith(".")]

        for cl in targets:
            cdir = self.clients_root / cl

            # 1. Scansione MPS toner
            mps_dir = cdir / "mps"
            if mps_dir.is_dir():
                for mf in mps_dir.glob("*.yaml"):
                    try:
                        import yaml
                        with open(mf, "r", encoding="utf-8") as fp:
                            mdata = yaml.safe_load(fp) or {}
                        for p in mdata.get("printers", []):
                            cnts = p.get("current_counters", {})
                            tbk = cnts.get("toner_black_pct", 100)
                            if tbk <= 15:
                                evt = self.emit_event(
                                    event_type="telemetry.mps.consumable_low",
                                    slug=cl,
                                    source="scanner:mps",
                                    payload={"model": p.get("model", "Printer"), "toner_info": f"Toner Nero al {tbk}%", "printer_id": p.get("asset_id")},
                                )
                                emitted.append(evt)
                    except Exception:
                        pass

            # 2. Scansione monte ore SLA
            ctr_dir = cdir / "contracts"
            if ctr_dir.is_dir():
                from scripts.pipelines.contracts import ContractsPipeline
                cp = ContractsPipeline(clients_root=self.clients_root)
                try:
                    bal = cp.get_balance(cl)
                    rem = bal.get("remaining_hours", 0.0)
                    tot = bal.get("total_purchased_hours", 0.0)
                    if tot > 0:
                        pct = round((rem / tot) * 100, 1)
                        if rem <= 10.0 or pct <= 20.0:
                            evt = self.emit_event(
                                event_type="telemetry.sla.hours_low",
                                slug=cl,
                                source="scanner:sla",
                                payload={"remaining_hours": rem, "total_hours": tot, "hours_pct": pct},
                            )
                            emitted.append(evt)
                except Exception:
                    pass

            # 3. Scansione As-Built Bridge
            if self.bridge.project_exists(cl):
                cov = self.bridge.cross_check_sla_assets_coverage(cl)
                unc = cov.get("uncontracted_devices", [])
                if unc:
                    evt = self.emit_event(
                        event_type="itinfra.asbuilt.changed",
                        slug=cl,
                        source="scanner:bridge",
                        payload={"uncontracted_devices": unc},
                    )
                    emitted.append(evt)

        return emitted
