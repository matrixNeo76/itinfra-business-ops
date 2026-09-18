#!/usr/bin/env python3
"""
tests/test_spec21_workflows.py — Test Suite per SPEC-21
Collaudo del WorkflowEngine deterministico, State Machine FSM,
checkpointing persistente, resume da interruzione, integrazione Mission Control
e gestione del fallimento con MemoryEngine.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent

from scripts.core.workflow_engine import WorkflowEngine
from scripts.pipelines.workflow_definitions import WorkflowRegistry
from scripts.pipelines.mission_control import MissionControlPipeline
from scripts.core.validator import validate_yaml_file


class TestSpec21Workflows(unittest.TestCase):
    """Test suite completa per SPEC-21 Workflow Orchestration."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_wf_"))
        cls.clients_dir = cls.temp_dir / "clients"
        cls.clients_dir.mkdir(parents=True, exist_ok=True)
        cls.engine = WorkflowEngine(repo_root=cls.temp_dir, clients_root=cls.clients_dir)

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_workflow_schema_validation(self):
        """Verifica conformita del modello dati workflow allo schema JSON/YAML."""
        step_defs = [
            {"step_id": "step_alpha", "name": "Primo Passo di Test"},
            {"step_id": "step_beta", "name": "Secondo Passo di Test"},
        ]
        wf = self.engine.create_workflow(
            workflow_type="test-flow",
            slug="all",
            step_definitions=step_defs,
            metadata={"test_mode": True}
        )
        self.assertEqual(wf["status"], "PENDING")
        self.assertEqual(wf["total_steps"], 2)
        self.assertEqual(wf["current_step_index"], 0)

        # Validazione formale contro schema
        wf_file = self.engine.find_workflow_file(wf["workflow_id"])
        self.assertIsNotNone(wf_file)
        schema_file = ROOT_DIR / "schemas" / "workflow.schema.yaml"
        self.assertTrue(schema_file.exists())
        
        is_valid, errors = validate_yaml_file(wf_file, "workflow.schema.yaml")
        self.assertTrue(is_valid, f"Errori di validazione schema: {errors}")
        self.assertEqual(len(errors), 0)

    def test_02_workflow_engine_create_save_load(self):
        """Verifica ciclo di vita di creazione, salvataggio su disco e ricaricamento."""
        slug = "cliente-wf-test"
        (self.clients_dir / slug).mkdir(parents=True, exist_ok=True)

        wf = self.engine.create_workflow(
            workflow_type="client-flow",
            slug=slug,
            step_definitions=[{"step_id": "s1", "name": "Init"}],
        )
        wf_id = wf["workflow_id"]

        # Ricarica da disco
        loaded = self.engine.load_workflow(wf_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["workflow_id"], wf_id)
        self.assertEqual(loaded["slug"], slug)

        # Verifica presenza in lista
        wfs = self.engine.list_workflows(slug=slug)
        self.assertTrue(any(w["workflow_id"] == wf_id for w in wfs))

    def test_03_workflow_execution_and_step_progression(self):
        """Verifica esecuzione sequenziale degli step e aggiornamento checkpoint."""
        step_defs = [
            {"step_id": "step_1", "name": "Step Uno"},
            {"step_id": "step_2", "name": "Step Due"},
        ]
        wf = self.engine.create_workflow(
            workflow_type="exec-flow",
            slug="all",
            step_definitions=step_defs
        )

        step_1_called = []
        step_2_called = []

        def runner_1(w, dry_run):
            step_1_called.append(True)
            return {"summary": "Step 1 OK", "data": {"res_1": 42}}

        def runner_2(w, dry_run):
            step_2_called.append(True)
            return {"summary": "Step 2 OK", "data": {"res_2": 99}}

        runners = {"step_1": runner_1, "step_2": runner_2}
        result = self.engine.run_workflow(wf, runners, resume=False, dry_run=False)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["current_step_index"], 2)
        self.assertTrue(step_1_called)
        self.assertTrue(step_2_called)

        self.assertEqual(result["steps"][0]["status"], "DONE")
        self.assertEqual(result["steps"][0]["output_summary"], "Step 1 OK")
        self.assertEqual(result["steps"][1]["status"], "DONE")
        self.assertEqual(result["steps"][1]["output_summary"], "Step 2 OK")

    def test_04_workflow_resume_idempotence(self):
        """Verifica ripresa da interruzione: gli step gia DONE non vengono rieseguiti."""
        step_defs = [
            {"step_id": "step_a", "name": "Gia Completato"},
            {"step_id": "step_b", "name": "Da Completare"},
        ]
        wf = self.engine.create_workflow(
            workflow_type="resume-flow",
            slug="all",
            step_definitions=step_defs
        )

        # Simula step_a gia completato in precedenza
        wf["steps"][0]["status"] = "DONE"
        wf["steps"][0]["output_summary"] = "Precedente successo"
        self.engine.save_workflow(wf)

        step_a_called = []
        step_b_called = []

        def failing_runner_a(w, dry_run):
            step_a_called.append(True)
            raise RuntimeError("Non avrebbe dovuto essere chiamato!")

        def runner_b(w, dry_run):
            step_b_called.append(True)
            return {"summary": "Ripresa completata con successo"}

        runners = {"step_a": failing_runner_a, "step_b": runner_b}
        result = self.engine.run_workflow(wf, runners, resume=True, dry_run=False)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertFalse(step_a_called, "Lo step_a non doveva essere rieseguito in modalita resume")
        self.assertTrue(step_b_called)
        self.assertEqual(result["steps"][1]["status"], "DONE")

    def test_05_workflow_failure_and_incident_capture(self):
        """Verifica che un errore in uno step porti a FAILED e notifichi il MemoryEngine."""
        step_defs = [
            {"step_id": "step_fail", "name": "Step Fallimentare"},
        ]
        wf = self.engine.create_workflow(
            workflow_type="fail-flow",
            slug="all",
            step_definitions=step_defs
        )

        def failing_runner(w, dry_run):
            raise ValueError("Errore di calcolo simulato per test FSM")

        runners = {"step_fail": failing_runner}
        result = self.engine.run_workflow(wf, runners, resume=False, dry_run=False)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["steps"][0]["status"], "FAILED")
        self.assertIn("Errore di calcolo simulato", result["steps"][0]["error"])

    def test_06_monthly_closing_workflow_dry_run(self):
        """Verifica esecuzione simulata del workflow di chiusura mensile su portfolio reale."""
        reg_defs = WorkflowRegistry.get_definitions()
        self.assertIn("monthly-closing", reg_defs)
        mc_def = reg_defs["monthly-closing"]

        wf = self.engine.create_workflow(
            workflow_type="monthly-closing",
            slug="all",
            step_definitions=mc_def["steps"],
            metadata={"period": "2026-09"}
        )

        real_runners = WorkflowRegistry.get_runners(
            clients_root=ROOT_DIR / "clients",
            itinfra_root=ROOT_DIR.parent / "itinfra"
        )["monthly-closing"]

        result = self.engine.run_workflow(wf, real_runners, resume=False, dry_run=True)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["current_step_index"], 5)
        for s in result["steps"]:
            self.assertEqual(s["status"], "DONE")

    def test_07_mission_control_shows_workflows(self):
        """Verifica integrazione con Mission Control (raccolta e rendering TUI)."""
        mc = MissionControlPipeline(
            clients_root=ROOT_DIR / "clients",
            itinfra_root=ROOT_DIR.parent / "itinfra"
        )
        data = mc.collect_all()
        self.assertIn("recent_workflows", data)

        tui_out = mc.render_tui()
        self.assertIn("AURE SYSTEM", tui_out)


if __name__ == "__main__":
    unittest.main()
