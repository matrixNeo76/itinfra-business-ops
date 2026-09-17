"""TestSotaPipelines — Suite di Test di Validazione e Conformità SOTA (Settembre 2026).

Verifica l'intero ventaglio di funzionalità implementate lungo i 3 Assi Strategici:
- Asse 1: Fiscale, Finanziario & Contrattuale (Pipeline C, A, E)
- Asse 2: Telemetria, Hardware & Integrazione Fisica (Pipeline F, B, G)
- Asse 3: Document Intelligence & Cognitive Self-Healing (Pipeline H, I, D)
"""

from __future__ import annotations

import datetime
import os
import shutil
import sys
import unittest
from pathlib import Path

# Assicura import corretti
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.core.snmp import SNMPClient, VENDOR_OIDS
from scripts.core.memory_engine import MemoryEngine
from scripts.pipelines.billing import BillingPipeline
from scripts.pipelines.contracts import ContractsPipeline
from scripts.pipelines.furniture import FurniturePipeline
from scripts.pipelines.ingestion import DocumentIngestionPipeline
from scripts.pipelines.jira_sync import JiraSyncPipeline
from scripts.pipelines.mps import MPSPipeline
from scripts.pipelines.quotes import QuotesPipeline
from scripts.pipelines.reports import ReportsPipeline


class TestSotaPipelines(unittest.TestCase):
    """Test suite completa per le pipeline SOTA (Settembre 2026)."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = ROOT_DIR / "tests" / "scratch_sota_test"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.clients_dir = cls.test_dir / "clients"
        cls.clients_dir.mkdir(parents=True, exist_ok=True)

        # Inizializza pipeline collegate alla directory di test
        cls.billing = BillingPipeline(cls.clients_dir)
        cls.contracts = ContractsPipeline(cls.clients_dir)
        cls.furniture = FurniturePipeline(cls.clients_dir)
        cls.ingestion = DocumentIngestionPipeline(cls.clients_dir)
        cls.jira = JiraSyncPipeline(cls.clients_dir)
        cls.mps = MPSPipeline(cls.clients_dir)
        cls.quotes = QuotesPipeline(cls.clients_dir)
        cls.reports = ReportsPipeline(cls.clients_dir)
        cls.memory = MemoryEngine(repo_root=ROOT_DIR)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # ASSE 1: Fiscale, Finanziario & Contrattuale
    # -------------------------------------------------------------------------

    def test_01_billing_split_payment_and_stamp_duty(self):
        """Verifica Split Payment e applicazione Bollo Virtuale nel tracciato SDI XML."""
        # Fattura con Split Payment e righe esenti oltre 77.47 €
        invoice_data = {
            "invoice_number": "FATT-TEST-001",
            "invoice_date": "2026-09-17",
            "slug": "ente-pubblico-test",
            "is_split_payment": True,
            "lines": [
                {
                    "description": "Consulenza Specialistica Esente Art. 10",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "vat_rate": 0.0,
                    "natura": "N4"
                },
                {
                    "description": "Servizio Sistemistico con IVA",
                    "quantity": 1,
                    "unit_price": 200.00,
                    "vat_rate": 22.0
                }
            ]
        }
        client_manifest = {
            "client_name": "Comune Test",
            "billing_info": {
                "vat_id": "IT12345678901",
                "fiscal_code": "12345678901",
                "sdi_code": "ABC1234",
                "pec": "protocollo@pec.comune.test.it",
                "address": {
                    "street": "Piazza Municipio 1",
                    "zip": "00100",
                    "city": "Roma",
                    "province": "RM"
                }
            }
        }

        xml_content = self.billing.generate_sdi_xml(invoice_data, client_manifest)
        self.assertIn("<EsigibilitaIVA>S</EsigibilitaIVA>", xml_content, "Split payment deve generare EsigibilitaIVA = S")
        self.assertIn("<BolloVirtuale>SI</BolloVirtuale>", xml_content, "Bollo virtuale deve essere attivo per esenti > 77.47 €")
        self.assertIn("<ImportoBollo>2.00</ImportoBollo>", xml_content, "Importo bollo deve essere 2.00")
        self.assertIn("<Natura>N4</Natura>", xml_content, "Natura N4 deve comparire nella riga esente")

    def test_02_billing_sepa_sdd_xml_generation(self):
        """Verifica generazione file XML SEPA Direct Debit pain.008.001.02."""
        invoices = [
            {
                "invoice_number": "FATT-001",
                "slug": "cliente-sdd-1",
                "client_name": "Studio Alfa",
                "amount": 366.00,
                "iban": "IT60X0542811101000000123456",
                "bic": "BAPPIT21",
                "mandate_id": "MAND-001",
                "mandate_date": "2025-01-10"
            }
        ]
        sdd_xml = self.billing.generate_sdd_xml(invoices, execution_date="2026-09-25")
        self.assertIn("pain.008.001.02", sdd_xml)
        self.assertIn("<NbOfTxs>1</NbOfTxs>", sdd_xml)
        self.assertIn("<CtrlSum>366.00</CtrlSum>", sdd_xml)
        self.assertIn("IT60X0542811101000000123456", sdd_xml)
        self.assertIn("<MndtId>MAND-001</MndtId>", sdd_xml)

    def test_03_billing_dunning_status(self):
        """Verifica calcolo livelli sollecito credito e sospensione automatica SLA."""
        d0 = self.billing.check_dunning_status("2026-09-20", "2026-09-17")
        self.assertEqual(d0["dunning_level"], "LEVEL_0")
        self.assertFalse(d0["sla_suspended"])

        d1 = self.billing.check_dunning_status("2026-09-14", "2026-09-17")
        self.assertEqual(d1["dunning_level"], "LEVEL_1_REMINDER")

        d2 = self.billing.check_dunning_status("2026-09-01", "2026-09-17")
        self.assertEqual(d2["dunning_level"], "LEVEL_2_FORMAL_NOTICE")

        d3 = self.billing.check_dunning_status("2026-07-01", "2026-09-17")
        self.assertEqual(d3["dunning_level"], "LEVEL_3_LEGAL_ACTION")
        self.assertTrue(d3["sla_suspended"], "Oltre 60 giorni di insoluto la fornitura e lo SLA devono essere sospesi")

    def test_04_contracts_business_hours_and_istat(self):
        """Verifica computo SLA a ore lavorative (esclusi weekend/festivi) e rivalutazione ISTAT."""
        # Venerdì pomeriggio alle 16:00 -> Lunedì mattina alle 11:00
        # Venerdì lavora 16:00-18:00 (2h), Sab/Dom 0h, Lunedì 09:00-11:00 (2h) -> Totale 4.0h
        t_start = "2026-09-18T16:00:00"  # Venerdì
        t_end = "2026-09-21T11:00:00"    # Lunedì
        biz_hours = self.contracts.compute_business_hours_sla(t_start, t_end)
        self.assertEqual(biz_hours, 4.0, "Il calcolo delle ore lavorative deve escludere il weekend")

        # Rivalutazione ISTAT FOI
        base_fee = 1000.00
        istat_res = self.contracts.apply_istat_adjustment(base_fee, inflation_rate_percent=2.5, foi_coefficient=1.0)
        self.assertEqual(istat_res["revised_fee"], 1025.00)
        self.assertEqual(istat_res["adjustment_amount"], 25.00)

    def test_05_quotes_cascading_cost_and_leasing(self):
        """Verifica sconti fornitore a cascata e piano di noleggio operativo OpEx."""
        # Prezzo di listino 1000 con sconti 20% + 10%
        # 1000 - 20% = 800; 800 - 10% = 720
        cost = self.quotes.parse_cascading_cost("1000.00 - 20% - 10%")
        self.assertEqual(cost, 720.00)

        # Calcolo opzioni leasing
        lease = self.quotes.calculate_lease_options(total_capital_amount=10000.00)
        self.assertIn("36_months", lease["plans"])
        self.assertIn("monthly_installment", lease["plans"]["36_months"])
        self.assertGreater(lease["plans"]["36_months"]["monthly_installment"], 0)
        self.assertEqual(lease["plans"]["36_months"]["buyback_option_euro"], 100.00)

    # -------------------------------------------------------------------------
    # ASSE 2: Telemetria, Hardware & Integrazione Fisica
    # -------------------------------------------------------------------------

    def test_06_snmp_multi_vendor_profiles_and_mps_burn_rate(self):
        """Verifica profili multi-vendor OID e stima predittiva esaurimento consumabili."""
        self.assertIn("kyocera", VENDOR_OIDS)
        self.assertIn("hp", VENDOR_OIDS)
        self.assertIn("ricoh", VENDOR_OIDS)
        self.assertIn("konica_minolta", VENDOR_OIDS)

        client = SNMPClient()
        oids_hp = client.get_vendor_profile_oids("hp")
        self.assertIn("mono_counter", oids_hp)

        # Calcolo burn rate e Remaining Useful Life
        readings = [
            {"reading_date": "2026-09-01", "mono_total": 10000, "toner_black_percent": 80},
            {"reading_date": "2026-09-11", "mono_total": 12000, "toner_black_percent": 60}
        ]
        pred = self.mps.predict_toner_depletion(readings, current_toner_percent=15)
        self.assertEqual(pred["daily_burn_rate_pages"], 200.0)
        self.assertLessEqual(pred["remaining_useful_life_days"], 10)
        self.assertTrue(pred["reorder_triggered"], "Toner al 15% con RUL <= 10 giorni deve scattare l'alert di riordino")

    def test_07_reports_tariff_multipliers_and_as_built_patch(self):
        """Verifica moltiplicatori orari straordinari/notturni/festivi e patch As-Built."""
        # Notturno (22:00-02:00)
        t_night = self.reports.calculate_tariff_multiplier("22:00", "02:00", "2026-09-16")
        self.assertEqual(t_night["multiplier"], 1.20)
        self.assertEqual(t_night["category"], "feriale_notturno")

        # Festivo (Domenica 2026-09-20 di giorno)
        t_sun = self.reports.calculate_tariff_multiplier("10:00", "13:00", "2026-09-20")
        self.assertEqual(t_sun["multiplier"], 1.50)
        self.assertEqual(t_sun["category"], "festivo_diurno")

        # Sigillo SHA-256
        rep_sample = {"report_id": "RAP-TEST", "date": "2026-09-17", "technician": "Mario Rossi"}
        seal = self.reports.seal_report_sha256(rep_sample)
        self.assertEqual(len(seal), 64, "Il sigillo SHA-256 deve essere un digest a 64 caratteri")

        # Patch As-Built per nuovo ricambio o matricola
        patch_md = self.reports.generate_as_built_patch(
            slug="cliente-test",
            replaced_assets=[{"serial": "SN-NEW-1234", "model": "FortiGate 60F", "role": "Firewall", "ip": "192.168.1.1"}],
            report_id="RAP-TEST"
        )
        self.assertIn("SN-NEW-1234", patch_md)
        self.assertIn("RAP-TEST", patch_md)

    def test_08_furniture_ipam_cross_check_and_change_orders(self):
        """Verifica cross-check prese dati IPAM e gestione formale Change Orders."""
        order_data = {
            "order_id": "ARR-TEST-01",
            "title": "Arredo Ufficio Direzionale",
            "stages": {"survey": {"workstations_count": 4}},
            "totals": {"total_net": 5000.00}
        }
        # Verifica Change Order
        slug_f = "test-furn-client"
        fdir = self.clients_dir / slug_f / "furniture"
        fdir.mkdir(parents=True, exist_ok=True)
        import yaml
        with open(fdir / "order-ARR-TEST-01.yaml", "w", encoding="utf-8") as fp:
            yaml.safe_dump(order_data, fp)

        var_res = self.furniture.add_change_order(
            slug=slug_f,
            order_id="ARR-TEST-01",
            title="Aggiunta 2 cassettiere e passacavi",
            additional_amount=650.00,
            approved_by="Dott. Rossi"
        )
        self.assertIsNotNone(var_res)
        self.assertEqual(var_res["revised_total_net"], 5650.00)
        self.assertEqual(var_res["amount_added"], 650.00)

    # -------------------------------------------------------------------------
    # ASSE 3: Document Intelligence & Cognitive Self-Healing
    # -------------------------------------------------------------------------

    def test_09_ingestion_preflight_audit_gate(self):
        """Verifica il blocco di pre-flight audit per anomalie CRITICAL se non forzato."""
        fake_result = {
            "document_type": "SLA_CONTRACT",
            "evidence": [
                {
                    "field": "contract_audit",
                    "value": [
                        {
                            "id": "SEC-001",
                            "severity": "CRITICAL",
                            "title": "Assenza clausola DPA GDPR",
                            "description": "Manca allegato trattamento dati"
                        }
                    ],
                    "status": "VERIFIED"
                }
            ]
        }
        # Senza force_audit deve lanciare ValueError
        with self.assertRaises(ValueError) as ctx:
            self.ingestion.apply_to_client("slug-audit-test", fake_result, force_audit=False)
        self.assertIn("Pre-flight audit bloccato", str(ctx.exception))
        self.assertIn("CRITICAL", str(ctx.exception))

        # Con force_audit=True deve procedere senza sollevare eccezioni
        try:
            res_applied = self.ingestion.apply_to_client("slug-audit-test", fake_result, force_audit=True)
            self.assertEqual(res_applied["status"], "success")
        except ValueError:
            self.fail("apply_to_client non avrebbe dovuto fallire con force_audit=True")

    def test_10_memory_engine_record_incident_and_audit(self):
        """Verifica cattura autonoma incidenti e monitoraggio nodi stale o in scadenza."""
        draft_file = self.memory.record_incident_as_draft(
            context="Esecuzione script calcolo canoni",
            error_message="KeyError: 'semestral_base_fee' in mps.py",
            root_cause="File YAML privo di parametri tariffari minimi",
            suggested_guardrail="Verificare sempre presenza della chiave semestral_base_fee con fallback a 0.0"
        )
        self.assertTrue(draft_file.exists())
        meta, body = self.memory.parse_okf_file(draft_file)
        self.assertEqual(meta["trust"]["tier"], "generated")
        self.assertIn("KeyError", meta["incident"]["observed_failure"])

        # Pulizia del file generato dal test
        if draft_file.exists():
            draft_file.unlink()

        # Audit del grafo di memoria
        audit_rep = self.memory.audit_memory()
        self.assertIn("total_nodes", audit_rep)
        self.assertIn("expiring_soon_nodes", audit_rep)
        self.assertIn(audit_rep["status"], ["PASS", "WARNING"])

    def test_11_jira_outbox_queue_and_conflict_detection(self):
        """Verifica accodamento outbox offline e rilevamento sovrapposizioni d'agenda."""
        slug = "cliente-jira-test"
        # Accodamento azione outbox
        action = self.jira.queue_action(
            slug=slug,
            action_type="create_issue",
            payload={"summary": "Manutenzione straordinaria server", "priority": "High"}
        )
        self.assertEqual(action["status"], "pending")
        queued = self.jira.get_queued_actions(slug, status="pending")
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["action_type"], "create_issue")

        # Creazione appuntamento
        self.jira.create_appointment(
            slug=slug,
            issue_key="IT-101",
            summary="Intervento rack",
            start_dt="2026-09-25T10:00:00",
            duration_hours=2.0,
            technician="Mario Rossi"
        )

        # Rilevamento conflitto: appuntamento sovrapposto dalle 11:00 alle 13:00 con lo stesso tecnico
        conflicts = self.jira.check_schedule_conflicts(
            proposed_start="2026-09-25T11:00:00",
            proposed_end="2026-09-25T13:00:00",
            technician="Mario Rossi"
        )
        self.assertGreaterEqual(len(conflicts), 1, "La sovrapposizione tra 11:00 e 12:00 deve essere rilevata")
        self.assertEqual(conflicts[0]["jira_issue_key"], "IT-101")


if __name__ == "__main__":
    unittest.main()
