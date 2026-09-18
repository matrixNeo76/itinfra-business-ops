#!/usr/bin/env python3
"""
tests/test_spec22_triggers.py — Test Suite per SPEC-22
Collaudo del TriggerEngine, schema di validazione eventi,
regole deterministiche (MPS toner, SLA burn, As-Built), Safe Action Gate
(Approve/Reject) e integrazione con Mission Control.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent

from scripts.core.trigger_engine import TriggerEngine
from scripts.pipelines.mission_control import MissionControlPipeline
from scripts.core.validator import validate_yaml_file


class TestSpec22Triggers(unittest.TestCase):
    """Test suite completa per SPEC-22 Proactive Triggers & Action Gate."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_trig_"))
        cls.clients_dir = cls.temp_dir / "clients"
        cls.clients_dir.mkdir(parents=True, exist_ok=True)
        cls.engine = TriggerEngine(repo_root=cls.temp_dir, clients_root=cls.clients_dir)

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_trigger_event_schema_validation(self):
        """Verifica conformita del modello dati evento contro schemas/trigger_event.schema.yaml."""
        evt = self.engine.emit_event(
            event_type="test.event.ping",
            slug="test-slug",
            source="test_suite",
            payload={"test_param": 123},
            auto_evaluate=False
        )
        self.assertEqual(evt["status"], "EMITTED")
        self.assertEqual(evt["event_type"], "test.event.ping")

        # Serializza temporaneamente in YAML per validazione schema
        temp_yaml = self.temp_dir / "temp_event.yaml"
        with open(temp_yaml, "w", encoding="utf-8") as fp:
            yaml.safe_dump(evt, fp)

        schema_file = ROOT_DIR / "schemas" / "trigger_event.schema.yaml"
        self.assertTrue(schema_file.exists())
        is_valid, errors = validate_yaml_file(temp_yaml, "trigger_event.schema.yaml")
        self.assertTrue(is_valid, f"Errori validazione schema: {errors}")
        self.assertEqual(len(errors), 0)

    def test_02_emit_event_and_append_log(self):
        """Verifica scrittura append-only nel log immutabile .agents/events.jsonl."""
        evt = self.engine.emit_event(
            event_type="telemetry.heartbeat",
            slug="all",
            source="daemon:test",
            payload={"status": "healthy"},
            auto_evaluate=False
        )
        self.assertTrue(self.engine.events_log.is_file())
        events = self.engine.list_events(limit=10)
        self.assertTrue(any(e["event_id"] == evt["event_id"] for e in events))

    def test_03_rule_evaluation_mps_toner_low(self):
        """Verifica che allarme toner <= 15% generi proposta PENDING_APPROVAL."""
        evt = self.engine.emit_event(
            event_type="telemetry.mps.consumable_low",
            slug="cliente-mps-test",
            source="daemon:mps",
            payload={"model": "Kyocera TASKalfa 2554ci", "toner_info": "Toner Black al 12%"},
            auto_evaluate=True
        )
        self.assertEqual(evt["status"], "PENDING_APPROVAL")
        self.assertIsNotNone(evt["action_proposed"])
        prop = evt["action_proposed"]
        self.assertEqual(prop["action_type"], "mps_cartridge_reorder")
        self.assertTrue(prop["requires_approval"])

        # Verifica presenza nelle pending actions
        pending = self.engine.list_pending_actions(slug="cliente-mps-test")
        self.assertTrue(any(a["action_id"] == prop["action_id"] for a in pending))

    def test_04_rule_evaluation_sla_hours_low(self):
        """Verifica che saldo ore residuo <= 20% generi proposta rinnovo SLA."""
        evt = self.engine.emit_event(
            event_type="telemetry.sla.hours_low",
            slug="cliente-sla-test",
            source="daemon:sla",
            payload={"remaining_hours": 4.5, "total_hours": 50.0, "hours_pct": 9.0},
            auto_evaluate=True
        )
        self.assertEqual(evt["status"], "PENDING_APPROVAL")
        self.assertIsNotNone(evt["action_proposed"])
        prop = evt["action_proposed"]
        self.assertEqual(prop["action_type"], "sla_contract_extension")
        self.assertEqual(prop["workflow_to_run"], "contract-renewal")

    def test_05_rule_evaluation_asbuilt_change(self):
        """Verifica rilevamento apparati non contrattualizzati da As-Built."""
        evt = self.engine.emit_event(
            event_type="itinfra.asbuilt.changed",
            slug="cliente-asb-test",
            source="git_guard:asbuilt",
            payload={"uncontracted_devices": ["FortiGate-60F (SN: FG60F123456)"]},
            auto_evaluate=True
        )
        self.assertEqual(evt["status"], "PENDING_APPROVAL")
        self.assertIsNotNone(evt["action_proposed"])
        prop = evt["action_proposed"]
        self.assertEqual(prop["action_type"], "contract_sla_addendum")
        self.assertIn("FG60F123456", prop["description"])

    def test_06_safe_action_gate_approve_and_reject(self):
        """Verifica presidio Safe Action Gate: transizioni Approve e Reject."""
        # 1. Crea proposta
        evt = self.engine.emit_event(
            event_type="telemetry.mps.consumable_low",
            slug="cliente-gate-test",
            source="daemon:mps",
            payload={"model": "HP LaserJet", "toner_info": "Toner Magenta 8%"},
            auto_evaluate=True
        )
        aid = evt["action_proposed"]["action_id"]

        # 2. Verifica presenza in pending
        pending_before = self.engine.list_pending_actions(slug="cliente-gate-test")
        self.assertTrue(any(a["action_id"] == aid for a in pending_before))

        # 3. Test Approvazione
        res_appr = self.engine.approve_action(aid, approved_by="human:possumato")
        self.assertEqual(res_appr["status"], "APPROVED")
        self.assertEqual(res_appr["action"]["resolved_by"], "human:possumato")

        # 4. Verifica che non sia più in pending
        pending_after = self.engine.list_pending_actions(slug="cliente-gate-test")
        self.assertFalse(any(a["action_id"] == aid for a in pending_after))

        # 5. Test Rifiuto su seconda proposta
        evt2 = self.engine.emit_event(
            event_type="telemetry.mps.consumable_low",
            slug="cliente-gate-test-2",
            source="daemon:mps",
            payload={"model": "Brother MFC", "toner_info": "Toner Yellow 10%"},
            auto_evaluate=True
        )
        aid2 = evt2["action_proposed"]["action_id"]
        res_rej = self.engine.reject_action(aid2, reason="Cliente ha scorte in sede", rejected_by="human:possumato")
        self.assertEqual(res_rej["status"], "REJECTED")
        self.assertEqual(res_rej["action"]["rejection_reason"], "Cliente ha scorte in sede")

    def test_07_mission_control_shows_pending_actions(self):
        """Verifica che Mission Control rilevi le azioni pendenti del Safe Action Gate."""
        # Inserisce un'azione pendente fittizia
        self.engine.emit_event(
            event_type="telemetry.mps.consumable_low",
            slug="roberto-viola",
            source="daemon:mps",
            payload={"model": "Kyocera ECOSYS", "toner_info": "Toner Black 5%"},
            auto_evaluate=True
        )

        mc = MissionControlPipeline(
            clients_root=ROOT_DIR / "clients",
            itinfra_root=ROOT_DIR.parent / "itinfra"
        )
        data = mc.collect_all()
        self.assertIn("pending_actions", data)
        tui = mc.render_tui()
        self.assertIn("AURE SYSTEM", tui)


if __name__ == "__main__":
    unittest.main()
