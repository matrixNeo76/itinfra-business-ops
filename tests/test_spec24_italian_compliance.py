#!/usr/bin/env python3
"""
tests/test_spec24_italian_compliance.py
Suite di test unitari per SPEC-24:
- Convalida Partita IVA (Luhn modificato)
- Convalida Codice Fiscale (DM 23/12/1976 con omocodia ed enti giuridici a 11 cifre)
- Convalida Codice Destinatario SDI (B2B 7 char) e IPA (PA 6 char)
- Calcolo Interessi di Mora Commerciale ex D.Lgs. 231/2002 e indennizzo forfettario €40 (Art. 6)
- Generazione Solleciti a 3 Stadi (Cortesia, Mora 231, Diffida ex art. 1219 c.c.)
- Bozza Rapportino Emergenza Incident con maggiorazioni CCNL (Area 1)
- Demone Scadenzario e Recupero Crediti (CreditDaemon - Area 2)
- Workflows Tecnici a Stati Finiti itinfra (dr-drill, firmware-upgrade, raee - Area 3)
- Validazione Git Guard Hook di conformita italiana
"""

import datetime
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.core.italian_compliance import ItalianComplianceGuard
from scripts.pipelines.daemon import CreditDaemon
from scripts.pipelines.reports import ReportsPipeline
from scripts.core.workflow_engine import WorkflowEngine
from scripts.pipelines.workflow_definitions import WorkflowRegistry
from scripts.hooks.git_guard import run_pre_commit


class TestItalianCompliance(unittest.TestCase):

    def setUp(self):
        self.guard = ItalianComplianceGuard()

    # --- 1. PARTITA IVA TESTS ---
    def test_piva_valid(self):
        valid_pivas = [
            "09876543217",       # Severino Srl
            "12345678903",       # Viola SRL
            "IT09876543217",     # Con prefisso paese IT
            "it12345678903",     # Minuscolo
            " 09876543217 "      # Spazi da trimmare
        ]
        for piva in valid_pivas:
            res = self.guard.validate_partita_iva(piva)
            self.assertTrue(res["valid"], f"P.IVA {piva} dovrebbe essere valida ma ha fallito: {res.get('error')}")

    def test_piva_invalid(self):
        invalid_pivas = [
            "09876543210",       # Check digit errato (atteso 7, fornito 0)
            "1234567890",        # Troppo corta (10 cifre)
            "123456789012",      # Troppo lunga (12 cifre)
            "12345ABC890",       # Caratteri non numerici
            "",                  # Vuota
            None                 # None
        ]
        for piva in invalid_pivas:
            res = self.guard.validate_partita_iva(piva)
            self.assertFalse(res["valid"], f"P.IVA {piva} dovrebbe essere non valida!")

    # --- 2. CODICE FISCALE TESTS ---
    def test_cf_valid_persone_fisiche(self):
        valid_cfs = [
            "VLIRRT75A01F205A",  # Roberto Viola
            "RSSMRA85M01H501Q",  # Mario Rossi
            "VRDGPP70A01L219K",  # Giuseppe Verdi
            " 09876543217 "      # CF Ente numerico a 11 cifre
        ]
        for cf in valid_cfs:
            res = self.guard.validate_codice_fiscale(cf)
            self.assertTrue(res["valid"], f"CF {cf} dovrebbe essere valido ma ha fallito: {res.get('error')}")

    def test_cf_valid_omocodia(self):
        # Sostituzione di una cifra con lettera di omocodia ('L' per '0')
        res = self.guard.validate_codice_fiscale("RSSMRA85M01H50LU")
        self.assertTrue(res["valid"], f"CF con omocodia dovrebbe essere valido: {res.get('error')}")

    def test_cf_invalid(self):
        invalid_cfs = [
            "VLIRRT75A01F205B",  # Check digit errato
            "RSSMRA85M01",       # Troppo corto
            "RSSMRA85M01H501Z9", # Troppo lungo
            "RSSMRA85M01H501!",  # Carattere speciale
            "",
            None
        ]
        for cf in invalid_cfs:
            res = self.guard.validate_codice_fiscale(cf)
            self.assertFalse(res["valid"], f"CF {cf} dovrebbe essere non valido!")

    # --- 3. CODICE DESTINATARIO SDI & IPA TESTS ---
    def test_sdi_ipa_valid(self):
        valid_codes = [
            ("M5UXCR1", "", "B2B_SDI"),          # Codice canale SDI B2B (7 caratteri)
            ("0000000", "amm@pec.it", "PEC_FALLBACK"),  # Codice generico + PEC
            ("UF7H5D", "", "PA_IPA"),            # Codice IPA PA (6 caratteri)
            ("m5uxcr1", "", "B2B_SDI")           # Minuscolo da normalizzare
        ]
        for code, pec, expected_type in valid_codes:
            res = self.guard.validate_sdi_recipient(code, pec=pec)
            self.assertTrue(res["valid"], f"Codice {code} dovrebbe essere valido: {res.get('error')}")
            self.assertEqual(res["type"], expected_type)

    def test_sdi_ipa_invalid(self):
        invalid_codes = [
            ("12345", ""),       # 5 caratteri (non esiste)
            ("12345678", ""),    # 8 caratteri (troppo lungo)
            ("0000000", ""),     # 0000000 senza PEC
            ("AB-CD1", ""),      # Carattere speciale
            ("", ""),
            (None, "")
        ]
        for code, pec in invalid_codes:
            res = self.guard.validate_sdi_recipient(code, pec=pec)
            self.assertFalse(res["valid"], f"Codice {code} dovrebbe essere non valido!")

    # --- 4. CALCOLO INTERESSI D.LGS. 231/2002 & SPESE FORFETTARIE ---
    def test_dlgs231_calculation(self):
        today = datetime.date.today()
        due_date = (today - datetime.timedelta(days=30)).isoformat()
        calc = self.guard.calculate_dlgs231_interest(1000.0, due_date, ref_date=today.isoformat())

        self.assertEqual(calc["days_overdue"], 30)
        self.assertEqual(calc["total_mora_rate_pct"], 11.50)
        self.assertEqual(calc["lump_sum_fee"], 40.0)
        self.assertAlmostEqual(calc["interest_mora"], 9.45, places=2)
        self.assertAlmostEqual(calc["total_due_dlgs231"], 1049.45, places=2)

    def test_dlgs231_not_overdue(self):
        today = datetime.date.today()
        future_date = (today + datetime.timedelta(days=10)).isoformat()
        calc = self.guard.calculate_dlgs231_interest(1000.0, future_date, ref_date=today.isoformat())

        self.assertEqual(calc["days_overdue"], 0)
        self.assertEqual(calc["interest_mora"], 0.0)
        self.assertEqual(calc["lump_sum_fee"], 0.0)
        self.assertEqual(calc["total_due_dlgs231"], 1000.0)

    # --- 5. SOLLECITI A 3 STADI ---
    def test_reminder_letters_generation(self):
        inv_data = {
            "client_name": "Test Cliente S.r.l.",
            "invoice_number": "FATT-2026-TEST",
            "invoice_date": "2026-06-01",
            "due_date": "2026-07-01",
            "amount": 2000.0
        }

        # Stadio 1: Cortesia
        l1 = self.guard.generate_reminder_letter("test-slug", inv_data, stage=1)
        self.assertIn("AVVISO DI CORTESIA", l1)
        self.assertIn("FATT-2026-TEST", l1)
        self.assertNotIn("D.Lgs. 9 ottobre 2002 n. 231", l1)

        # Stadio 2: Mora D.Lgs. 231/2002 con indennizzo €40
        l2 = self.guard.generate_reminder_letter("test-slug", inv_data, stage=2)
        self.assertIn("SOLLECITO FORMALE CON ADDEBITO MORA EX D.LGS. 231/2002", l2)
        self.assertIn("40.00", l2)
        self.assertIn("11.50% annuo", l2)
        self.assertIn("Aure System di Eduardo Possumato", l2)

        # Stadio 3: Diffida ad adempiere ex art. 1219 c.c.
        l3 = self.guard.generate_reminder_letter("test-slug", inv_data, stage=3)
        self.assertIn("DIFFIDA AD ADEMPIERE", l3)
        self.assertIn("1219", l3)
        self.assertIn("5 (cinque) giorni", l3)


class TestHighReturnExtensions(unittest.TestCase):

    # --- AREA 1: INCIDENT TO REPORT BRIDGE WITH CCNL SURCHARGES ---
    def test_incident_report_draft_ccnl(self):
        pipeline = ReportsPipeline()
        incident_info = {
            "incident_id": "INC-TEST-001",
            "title": "Disruption Switch Core L2",
            "date": "2026-09-18",
            "clock_in": "21:00",
            "clock_out": "23:00",
            "tech": "Eduardo Possumato",
            "hours": 2.0,
            "root_cause": "Firmware crash looping",
            "resolution": "Rollback and config restore",
            "affected_assets": ["SW-CORE-01"],
            "ccnl_type": "night"
        }

        res = pipeline.create_incident_report_draft("severino-srl", incident_info)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["ccnl_multiplier"], 1.20)
        self.assertEqual(res["hours_billed"], 2.4)
        rep_p = Path(res["report_file"])
        self.assertTrue(rep_p.exists())
        # Clean up generated test report and restore contract
        if rep_p.exists():
            rep_p.unlink()
        html_p = rep_p.with_suffix(".html")
        if html_p.exists():
            html_p.unlink()
        patch_p = rep_p.parent / f"{rep_p.stem}.as-built-patch.md"
        if patch_p.exists():
            patch_p.unlink()

        # Restore contract consumed hours
        from scripts.pipelines.contracts import ContractsPipeline
        cp = ContractsPipeline(pipeline.clients_root)
        ctr_file = pipeline.clients_root / "severino-srl" / "contracts" / "ctr-severino-srl-2026.yaml"
        if ctr_file.exists():
            import yaml
            with open(ctr_file, "r", encoding="utf-8") as fp:
                cdata = yaml.safe_load(fp) or {}
            cdata.setdefault("financial", {})["consumed_hours"] = 11.5
            with open(ctr_file, "w", encoding="utf-8") as fp:
                yaml.safe_dump(cdata, fp, sort_keys=False, allow_unicode=True)

    # --- AREA 2: CREDIT DAEMON SCANS ---
    def test_credit_daemon_scan(self):
        daemon = CreditDaemon()
        res = daemon.check_all()
        self.assertIn("scanned_invoices", res)
        self.assertIn("scanned_contracts", res)
        self.assertIn("alerts", res)

    # --- AREA 3: TECHNICAL WORKFLOWS FSM ---
    def test_dr_drill_workflow(self):
        engine = WorkflowEngine()
        reg_defs = WorkflowRegistry.get_definitions()
        wdef = reg_defs["dr-drill"]
        wf = engine.create_workflow("dr-drill", slug="severino-srl", step_definitions=wdef.get("steps"))
        all_runners = WorkflowRegistry.get_runners(clients_root=engine.clients_root, itinfra_root=engine.repo_root.parent / "itinfra")
        res = engine.run_workflow(wf, all_runners.get("dr-drill", {}), dry_run=True)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(len(res.get("steps", [])), 5)
        self.assertTrue(all(s["status"] == "DONE" for s in res.get("steps", [])))

    def test_firmware_upgrade_workflow(self):
        engine = WorkflowEngine()
        reg_defs = WorkflowRegistry.get_definitions()
        wdef = reg_defs["firmware-upgrade"]
        wf = engine.create_workflow("firmware-upgrade", slug="severino-srl", step_definitions=wdef.get("steps"))
        all_runners = WorkflowRegistry.get_runners(clients_root=engine.clients_root, itinfra_root=engine.repo_root.parent / "itinfra")
        res = engine.run_workflow(wf, all_runners.get("firmware-upgrade", {}), dry_run=True)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(len(res.get("steps", [])), 5)
        self.assertTrue(all(s["status"] == "DONE" for s in res.get("steps", [])))

    def test_hardware_decommissioning_raee_workflow(self):
        engine = WorkflowEngine()
        reg_defs = WorkflowRegistry.get_definitions()
        wdef = reg_defs["hardware-decommissioning-raee"]
        wf = engine.create_workflow("hardware-decommissioning-raee", slug="severino-srl", step_definitions=wdef.get("steps"))
        all_runners = WorkflowRegistry.get_runners(clients_root=engine.clients_root, itinfra_root=engine.repo_root.parent / "itinfra")
        res = engine.run_workflow(wf, all_runners.get("hardware-decommissioning-raee", {}), dry_run=True)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(len(res.get("steps", [])), 4)
        self.assertTrue(all(s["status"] == "DONE" for s in res.get("steps", [])))

    # --- GIT GUARD HOOK ITALIAN COMPLIANCE ---
    def test_git_guard_italian_compliance_check(self):
        manifest_path = Path(__file__).resolve().parent.parent / "clients" / "severino-srl" / "client-manifest.yaml"
        exit_code = run_pre_commit(files=[manifest_path])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
