#!/usr/bin/env python3
"""
tests/test_spec20_mission_control_and_swarm.py — Unit Tests for SPEC-20
Verifica deterministica completa per:
- OnboardPipeline (Pipeline 11 dual-repo zero-drift)
- GitGuard (Secret leak & OKF linter)
- MissionControlPipeline (TUI & Zero-CDN HTML)
- DeterministicSwarm & 4 Specialised Agents
- MPSDaemon & SLADaemon
- QuoteSimulatorPipeline
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

from scripts.pipelines.onboard import OnboardPipeline
from scripts.hooks.git_guard import check_secrets_in_file, check_okf_frontmatter
from scripts.pipelines.mission_control import MissionControlPipeline
from scripts.core.swarm import Auditor231Agent, FinanceReconcilerAgent, InfrastructureSentinelAgent, ContractGuardianAgent, DeterministicSwarm
from scripts.pipelines.daemon import MPSDaemon, SLADaemon
from scripts.pipelines.quote_simulator import QuoteSimulatorPipeline


class TestSPEC20MissionControlAndSwarm(unittest.TestCase):

    def setUp(self):
        self.test_slug = "test-spec20-corp"
        self.bizops_path = ROOT_DIR / "clients" / self.test_slug
        self.itinfra_path = ROOT_DIR.parent / "itinfra" / "projects" / self.test_slug

    def tearDown(self):
        shutil.rmtree(self.bizops_path, ignore_errors=True)
        shutil.rmtree(self.itinfra_path, ignore_errors=True)

    def test_01_onboard_pipeline_dual_repo_zero_drift(self):
        pipeline = OnboardPipeline()
        res = pipeline.onboard_client(
            slug=self.test_slug,
            client_name="Test SPEC20 Corporation",
            vat_id="IT98765432109",
            tier="gold",
            primary_subnet="192.168.99.0/24"
        )

        self.assertEqual(res["slug"], self.test_slug)
        self.assertEqual(res["tier"], "gold")
        self.assertEqual(res["hours_allocated"], 50.0)
        self.assertTrue(res["itinfra_created"])
        self.assertTrue(self.bizops_path.is_dir())
        self.assertTrue(self.itinfra_path.is_dir())

        # Verifica file generati
        self.assertTrue((self.bizops_path / "client-manifest.yaml").is_file())
        self.assertTrue((self.bizops_path / "contracts" / f"ctr-{self.test_slug}-2026.yaml").is_file())
        self.assertTrue((self.bizops_path / "quotes" / f"quote-{self.test_slug}-01.yaml").is_file())
        self.assertTrue((self.bizops_path / "mps" / f"mps-{self.test_slug}-01.yaml").is_file())
        self.assertTrue((self.bizops_path / "gap_analysis" / f"ga-{self.test_slug}-01.yaml").is_file())
        self.assertTrue((self.itinfra_path / "manifest.yaml").is_file())
        self.assertTrue((self.itinfra_path / "04-Network-IPAM.md").is_file())
        self.assertTrue((self.itinfra_path / "06-As-Built.md").is_file())

        # Verifica Cross-Check e Zero-Drift Certification
        self.assertEqual(res["cross_check_status"], "PASS")
        self.assertTrue(res["zero_drift_certified"])
        self.assertTrue(len(res["sha256_seal"]) == 64)

    def test_02_git_guard_secret_detection_and_okf(self):
        # File pulito
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tf:
            tf.write("slug: test\nstatus: active\n")
            tf_name = tf.name

        try:
            hits = check_secrets_in_file(Path(tf_name))
            self.assertEqual(len(hits), 0)
        finally:
            os.remove(tf_name)

        # File con secret simulato (assemblato dinamicamente per isolare il test file dal linter)
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tf:
            key_name = "api_" + "secret"
            tf.write(f"{key_name}: 'secret_live_1234567890abcdef'\n")
            tf_name = tf.name

        try:
            hits = check_secrets_in_file(Path(tf_name))
            self.assertGreaterEqual(len(hits), 1)
        finally:
            os.remove(tf_name)

        # File OKF valido
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".okf.md", delete=False) as tf:
            tf.write("---\ntype: specification\ntitle: Test Spec\n---\n# Content\n")
            tf_name = tf.name

        try:
            errs = check_okf_frontmatter(Path(tf_name))
            self.assertEqual(len(errs), 0)
        finally:
            os.remove(tf_name)

        # File OKF senza type
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".okf.md", delete=False) as tf:
            tf.write("---\ntitle: Missing Type\n---\n# Content\n")
            tf_name = tf.name

        try:
            errs = check_okf_frontmatter(Path(tf_name))
            self.assertGreaterEqual(len(errs), 1)
        finally:
            os.remove(tf_name)

    def test_03_mission_control_metrics_and_html(self):
        mc = MissionControlPipeline()
        data = mc.collect_all()

        self.assertGreaterEqual(data["total_clients"], 4)
        kpis = data["global_kpis"]
        self.assertIn("total_sla_hours_available", kpis)
        self.assertIn("total_open_credit_eur", kpis)
        self.assertIn("total_printers", kpis)
        self.assertIn("avg_compliance_score", kpis)

        tui = mc.render_tui()
        self.assertIn("AURE SYSTEM — MISSION CONTROL", tui)
        self.assertIn("unisped-ag-sas", tui)

        html = mc.render_html()
        self.assertIn("Mission Control", html)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("AURE", html)

    def test_04_specialized_agents_and_swarm(self):
        # Auditor 231
        auditor = Auditor231Agent()
        res_aud = auditor.run("unisped-ag-sas")
        self.assertEqual(res_aud["agent"], "auditor-231")
        self.assertGreater(res_aud["compliance_score"], 0.0)
        self.assertIn(res_aud["status"], ["PASS", "ACTION_REQUIRED"])

        # Finance Reconciler
        fin = FinanceReconcilerAgent()
        res_fin = fin.run("severino-srl")
        self.assertEqual(res_fin["agent"], "finance-reconciler")
        self.assertGreaterEqual(res_fin["contract_hours_purchased"], 0.0)

        # Infrastructure Sentinel
        sentinel = InfrastructureSentinelAgent()
        res_sent = sentinel.run("severino-srl")
        self.assertEqual(res_sent["agent"], "infrastructure-sentinel")
        self.assertTrue(res_sent["itinfra_synced"])

        # Contract Guardian
        guardian = ContractGuardianAgent()
        res_guard = guardian.run("severino-srl")
        self.assertEqual(res_guard["agent"], "contract-guardian")
        self.assertGreater(res_guard["remaining_hours"], 0.0)

        # Swarm consolidato
        swarm = DeterministicSwarm()
        res_swarm = swarm.execute_swarm("unisped-ag-sas")
        self.assertEqual(res_swarm["slug"], "unisped-ag-sas")
        self.assertIn(res_swarm["overall_status"], ["HEALTHY", "ATTENTION", "DEGRADED"])
        self.assertGreater(res_swarm["composite_health_index"], 0.0)
        self.assertEqual(len(res_swarm["sha256_seal"]), 64)
        self.assertIn("auditor_231", res_swarm["agents"])
        self.assertIn("contract_guardian", res_swarm["agents"])

    def test_05_proactive_daemons(self):
        mps_daemon = MPSDaemon()
        mps_res = mps_daemon.check_all()
        self.assertGreaterEqual(mps_res["scanned_printers"], 4)
        self.assertIn("alerts_count", mps_res)

        sla_daemon = SLADaemon()
        sla_res = sla_daemon.check_all()
        self.assertGreaterEqual(sla_res["scanned_contracts"], 3)
        self.assertIn("alerts_count", sla_res)

    def test_06_quote_simulator_html(self):
        qsp = QuoteSimulatorPipeline()
        html = qsp.generate_interactive_simulator("severino-srl")
        self.assertIn("Generative UI Quote Simulator", html)
        self.assertIn("slider-hw", html)
        self.assertIn("recalculate()", html)


if __name__ == "__main__":
    unittest.main()
