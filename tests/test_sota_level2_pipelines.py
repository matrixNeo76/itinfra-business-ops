import datetime
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

from scripts.pipelines.billing import BillingPipeline
from scripts.pipelines.contracts import ContractsPipeline
from scripts.pipelines.quotes import QuotesPipeline
from scripts.core.snmp import SNMPPoller
from scripts.pipelines.mps import MPSPipeline
from scripts.pipelines.reports import ReportsPipeline
from scripts.pipelines.furniture import FurniturePipeline
from scripts.pipelines.ingestion import (
    SdiXmlExtractor,
    TableContinuityStitcher,
    TriangularAuditEngine,
    DocumentIngestionPipeline
)
from scripts.core.memory_engine import MemoryEngine
from scripts.pipelines.jira_sync import JiraSyncPipeline
from scripts.core.bridge import ITInfraBridge


class TestSOTALevel2Pipelines(unittest.TestCase):
    """Test suite completo per le pipeline SOTA Level-2 (Evoluzione Settembre 2026)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.clients_root = self.root_path / "clients"
        self.clients_root.mkdir(parents=True, exist_ok=True)
        self.test_slug = "cliente-test-sota"
        self.client_dir = self.clients_root / self.test_slug
        self.client_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        from scripts.core.config import get_itinfra_dir
        itinfra_p = get_itinfra_dir() / "projects" / self.test_slug
        if itinfra_p.exists():
            shutil.rmtree(itinfra_p, ignore_errors=True)
        self.temp_dir.cleanup()

    # =========================================================================
    # ASSE 1: FISCALE & CONTRATTUALE
    # =========================================================================

    def test_asse1_pa_cig_cup_and_withholding_xml(self):
        """Verifica generazione XML SDI FPA12 per PA con CIG, CUP e Ritenuta d'acconto."""
        bp = BillingPipeline(self.clients_root)
        invoice_data = {
            "invoice_number": "FAT-2026-PA01",
            "invoice_date": "2026-09-18",
            "slug": self.test_slug,
            "client": {
                "name": "Comune di Napoli",
                "vat_id": "IT01234567890",
                "fiscal_code": "01234567890",
                "address": "Piazza Municipio 1",
                "city": "Napoli",
                "zip": "80100",
                "country": "IT",
                "sdi_code": "ABCDEF", # 6 caratteri PA
                "is_public_administration": True
            },
            "totals": {
                "total_net": 1000.0,
                "total_vat": 220.0,
                "total_gross": 1220.0,
                "withholding_tax_amount": 40.0,
                "pension_fund_contribution": 40.0
            },
            "withholding_tax": {
                "type": "RT02",
                "percentage": 4.0,
                "amount": 40.0,
                "reason": "A"
            },
            "pension_fund": {
                "type": "TC22",
                "percentage": 4.0,
                "amount": 40.0,
                "vat_rate": 22.0
            },
            "purchase_order": {
                "po_number": "ORD-2026-PA",
                "cig": "9876543210",
                "cup": "B12C34567890"
            },
            "lines": [
                {
                    "description": "Consulenza Specialistica IT per PA",
                    "quantity": 10.0,
                    "unit_price": 100.0,
                    "total": 1000.0,
                    "vat_rate": 22.0
                }
            ]
        }

        xml_str = bp.generate_sdi_xml(invoice_data)
        self.assertIn("FPA12", xml_str)
        self.assertIn("<CodiceCIG>9876543210</CodiceCIG>", xml_str)
        self.assertIn("<CodiceCUP>B12C34567890</CodiceCUP>", xml_str)
        self.assertIn("<DatiRitenuta>", xml_str)
        self.assertIn("<TipoRitenuta>RT02</TipoRitenuta>", xml_str)
        self.assertIn("<DatiCassaPrevidenziale>", xml_str)
        self.assertIn("<TipoCassa>TC22</TipoCassa>", xml_str)

    def test_asse1_camt053_bank_reconciliation(self):
        """Verifica riconciliazione automatica estratti conto bancari ISO 20022 CAMT.053."""
        bp = BillingPipeline(self.clients_root)
        # Prepara una fattura non saldata
        inv_file = bp.create_invoice(
            slug=self.test_slug,
            items=[{"description": "Server setup", "quantity": 1, "unit_price": 2440.0, "total": 2440.0, "vat_rate": 22.0}],
            payment_terms="bonifico_30gg",
            sdi_code="0000000"
        )
        with open(inv_file, "r", encoding="utf-8") as fp:
            inv_data = yaml.safe_load(fp)
        inv_num = inv_data["invoice_number"]

        camt_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <Stmt>
      <Id>STMT-2026-09</Id>
      <Ntry>
        <Amt Ccy="EUR">2976.80</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <BookgDt><Dt>2026-09-18</Dt></BookgDt>
        <NtryDtls>
          <TxDtls>
            <RmtInf>
              <Ustrd>Saldo fattura {inv_num} fornitura IT</Ustrd>
            </RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""
        res = bp.reconcile_bank_statement(camt_xml, auto_mark_paid=True)
        self.assertGreaterEqual(res["reconciled_count"], 1)
        self.assertEqual(res["reconciled_invoices"][0]["invoice_number"], inv_num)

        # Ricarica fattura e verifica che sia contrassegnata come pagata
        with open(inv_file, "r", encoding="utf-8") as fp:
            reloaded = yaml.safe_load(fp)
        self.assertEqual(reloaded.get("status"), "paid")
        self.assertIn("CAMT053", reloaded.get("payment_reference", ""))

    def test_asse1_gauss_easter_pasquetta_and_patron(self):
        """Verifica calcolo astronomico di Pasqua, Pasquetta e patrono locale."""
        # Nel 2026: Pasqua è il 5 aprile, Pasquetta è il 6 aprile
        easter_2026 = ContractsPipeline.compute_easter_date(2026)
        self.assertEqual(easter_2026, datetime.date(2026, 4, 5))
        easter_monday_2026 = ContractsPipeline.get_easter_monday(2026)
        self.assertEqual(easter_monday_2026, datetime.date(2026, 4, 6))

        # Pasquetta deve essere considerata festivo
        self.assertTrue(ContractsPipeline.is_italian_holiday_or_weekend(easter_monday_2026))

        # Patrono locale (es. Sant'Ambrogio a Milano: 7 Dicembre)
        sant_ambrogio = datetime.date(2026, 12, 7) # 7 Dicembre 2026 è lunedì
        self.assertFalse(ContractsPipeline.is_italian_holiday_or_weekend(sant_ambrogio))
        self.assertTrue(ContractsPipeline.is_italian_holiday_or_weekend(sant_ambrogio, patron_date=(12, 7)))

        # Calcolo ore lavorative a cavallo di Pasquetta (venerdì 3 aprile ore 17:00 a martedì 7 aprile ore 10:00)
        # Ven 17-18 = 1h; Sab/Dom = 0h; Lun Pasquetta = 0h; Mar 09-10 = 1h. Totale = 2 ore.
        h = ContractsPipeline.compute_business_hours_sla(
            start_dt="2026-04-03T17:00:00",
            end_dt="2026-04-07T10:00:00"
        )
        self.assertEqual(h, 2.0)

    def test_asse1_sla_penalties_tracking(self):
        """Verifica calcolo e accumulo penali contrattuali per sforamento tempi SLA."""
        cp = ContractsPipeline(self.clients_root)
        cdir = self.client_dir / "contracts"
        cdir.mkdir(parents=True, exist_ok=True)
        cfile = cdir / "ctr-test-2026.yaml"
        contract_data = {
            "contract_id": "CTR-2026-TEST",
            "slug": self.test_slug,
            "status": "active",
            "financial": {"annual_fee": 12000.0, "consumed_hours": 0.0, "total_hours_included": 50.0},
            "sla": {
                "severities": {
                    "sev1": {"name": "Critical Outage", "resolution_hours": 4.0}
                }
            }
        }
        with open(cfile, "w", encoding="utf-8") as fp:
            yaml.safe_dump(contract_data, fp)

        # Risoluzione ticket Sev1 in 7 ore (consentite 4 ore -> 3 ore di ritardo @ € 50/h = € 150)
        pen = cp.compute_sla_penalties(
            slug=self.test_slug,
            ticket_id="TCK-999",
            report_id="RAP-999",
            severity="sev1",
            start_time="2026-09-18T09:00:00",
            end_time="2026-09-18T16:00:00", # 7 ore lavorative
            hourly_penalty_rate=50.0,
            contract_id="CTR-2026-TEST"
        )

        self.assertTrue(pen["is_breached"])
        self.assertEqual(pen["delay_hours"], 3.0)
        self.assertEqual(pen["penalty_amount"], 150.0)

        # Verifica scrittura su YAML
        with open(cfile, "r", encoding="utf-8") as fp:
            updated_c = yaml.safe_load(fp)
        self.assertEqual(updated_c["financial"]["sla_penalties_total"], 150.0)
        self.assertEqual(len(updated_c["sla_penalties"]), 1)

    def test_asse1_quotes_margin_floor_and_currency_buffer(self):
        """Verifica margin safety floor (min 20%) e rischio cambio USD -> EUR con buffer 2.5%."""
        qp = QuotesPipeline(self.clients_root)

        # Test conversione USD con buffer 2.5%
        # $ 1080 @ 1.08 = € 1000 spot -> con buffer +2.5% = € 1025 hedged
        fx = qp.convert_currency_with_buffer(amount=1080.0, fx_rate=1.08, buffer_percent=2.5, from_currency="USD", to_currency="EUR")
        self.assertEqual(fx["spot_amount"], 1000.0)
        self.assertEqual(fx["hedged_amount"], 1025.0)

        # Test calcolo preventivo con violazione soglia minima di margine (10% < 20%)
        q_data = {
            "quote_id": "PREV-TEST-MARGIN",
            "categories": [
                {
                    "name": "hardware",
                    "items": [
                        {
                            "unit_cost": 900.0,
                            "quantity": 1,
                            "unit_price": 1000.0 # Margine 10% (costo 900, vendita 1000)
                        }
                    ]
                }
            ]
        }
        calc = qp.calculate_quote(q_data, min_gross_margin_percent=20.0)
        self.assertTrue(calc["totals"]["margin_safety_violation"])
        self.assertEqual(calc["totals"]["gross_margin_percent"], 10.0)
        self.assertGreater(calc["totals"]["target_floor_net"], 1000.0)

    def test_asse1_quotes_revisions_and_diff(self):
        """Verifica versionamento immutabile preventivi e diff analitico."""
        qp = QuotesPipeline(self.clients_root)
        qdir = self.client_dir / "quotes"
        qdir.mkdir(parents=True, exist_ok=True)
        qfile = qdir / "prev-rev-test.yaml"

        base_quote = {
            "quote_id": "PREV-REV-TEST",
            "revision": 1,
            "categories": [
                {
                    "name": "hardware",
                    "items": [{"unit_cost": 500.0, "unit_price": 700.0, "quantity": 1}]
                }
            ]
        }
        recalc = qp.calculate_quote(base_quote)
        with open(qfile, "w", encoding="utf-8") as fp:
            yaml.safe_dump(recalc, fp)

        # Salva snapshot revisione 1
        snap_path = qp.save_quote_revision(self.test_slug, "PREV-REV-TEST", note="Prima versione cliente")
        self.assertIsNotNone(snap_path)
        self.assertTrue(snap_path.is_file())

        # Modifica la revisione corrente
        qp.add_item_to_quote(
            slug=self.test_slug,
            quote_id="PREV-REV-TEST",
            category="hardware",
            part_number="RAM-EXTRA",
            description="Upgrade RAM 32GB",
            quantity=1,
            unit_cost=100.0,
            markup_percent=50.0
        )

        # Diff tra revisione 1 e revisione 2 (corrente)
        diff = qp.compare_quote_revisions(self.test_slug, "PREV-REV-TEST", rev_a=1, rev_b=2)
        self.assertIn("deltas", diff)
        self.assertGreater(diff["deltas"]["total_net"], 0)

    # =========================================================================
    # ASSE 2: TELEMETRIA & FISICO
    # =========================================================================

    def test_asse2_snmp_v3_and_long_life_wear(self):
        """Verifica polling SNMP v3 con OID per parti di ricambio a lunga durata."""
        poller = SNMPPoller()
        res_v3 = poller.poll_v3(
            ip_address="192.168.1.200",
            username="secadmin",
            auth_protocol="SHA256",
            priv_protocol="AES128",
            security_level="authPriv",
            vendor="kyocera"
        )
        self.assertEqual(res_v3["snmp_version"], "v3")
        self.assertEqual(res_v3["security_level"], "authPriv")
        self.assertIn("drum_life_percent", res_v3["telemetry"])
        self.assertIn("fuser_life_percent", res_v3["telemetry"])
        self.assertIn("transfer_belt_percent", res_v3["telemetry"])

    def test_asse2_mps_hardware_depletion_and_billing_lines(self):
        """Verifica stima esaurimento hardware drum/fusore e generazione righe fattura MPS."""
        mps = MPSPipeline(self.clients_root)
        readings = [
            {"reading_date": "2026-01-01", "mono_total": 10000, "color_total": 2000, "drum_life_percent": 90, "fuser_life_percent": 95},
            {"reading_date": "2026-04-01", "mono_total": 25000, "color_total": 5000, "drum_life_percent": 75, "fuser_life_percent": 85}
        ]

        pred = mps.predict_hardware_depletion(
            slug=self.test_slug,
            printer_serial_or_ip="KYOCERA-SN123",
            historical_readings=readings
        )
        self.assertIn("drum", pred["hardware_components"])
        self.assertIn("rul_days", pred["hardware_components"]["drum"])
        self.assertGreater(pred["daily_burn_rate_pages"], 0)

        # Generazione righe fattura MPS
        mdir = self.client_dir / "mps"
        mdir.mkdir(parents=True, exist_ok=True)
        mfile = mdir / "mps-test.yaml"
        mps_contract = {
            "mps_contract_id": "MPS-2026-TEST",
            "slug": self.test_slug,
            "device_info": {"model": "TASKalfa 3253ci", "serial_number": "SN12345"},
            "contract_terms": {
                "semestral_base_fee": 600.0,
                "included_copies_semestral": {"mono": 5000, "color": 1000},
                "overage_cost_per_page": {"mono": 0.010, "color": 0.060}
            },
            "readings": [
                {"reading_date": "2026-01-01", "mono_total": 10000, "color_total": 2000},
                {"reading_date": "2026-06-30", "mono_total": 17000, "color_total": 3500} # Eccedenza: 2000 mono, 500 color
            ]
        }
        with open(mfile, "w", encoding="utf-8") as fp:
            yaml.safe_dump(mps_contract, fp)

        lines = mps.generate_mps_billing_lines(self.test_slug, "MPS-2026-TEST")
        self.assertEqual(len(lines), 3) # Canone, Eccedenza mono, Eccedenza colore
        self.assertEqual(lines[0]["unit_price"], 600.0) # Canone base
        self.assertEqual(lines[1]["quantity"], 2000.0) # 2000 copie mono eccedenti
        self.assertEqual(lines[2]["quantity"], 500.0)  # 500 copie color eccedenti

    def test_asse2_reports_travel_allowance_and_atomic_as_built(self):
        """Verifica calcolo rimborso chilometrico trasferta e patch atomica ad As-Built."""
        rp = ReportsPipeline(self.clients_root)

        # 1. Test indennità trasferta
        allowance = rp.calculate_travel_allowance(distance_km=80.0, rate_per_km=0.50, tolls_eur=12.50, parking_eur=5.0)
        self.assertEqual(allowance["km_reimbursement"], 40.0)
        self.assertEqual(allowance["total_travel_allowance"], 57.50)

        # 2. Creazione rapportino con trasferta e ricambio hardware
        rep = rp.create_report(
            slug=self.test_slug,
            technician="Mario Rossi",
            description="Sostituzione switch di piano difettoso",
            clock_in="09:00",
            clock_out="11:00",
            distance_km=50.0,
            tolls_eur=5.0,
            spare_parts=[{"description": "Switch Cisco Catalyst 24P", "part_number": "C9200L-24P", "serial_number": "FCW2345ABC", "quantity": 1, "unit_price": 600.0}]
        )
        self.assertEqual(rep["travel_allowance"]["total_travel_allowance"], 30.0) # 50km * 0.5 + 5

        # 3. Patch atomica su As-Built in cartella federata
        bridge = ITInfraBridge()
        tech_proj_dir = bridge.itinfra_root / "projects" / self.test_slug
        tech_proj_dir.mkdir(parents=True, exist_ok=True)
        as_built_file = tech_proj_dir / "06-As-Built.md"
        as_built_file.write_text("# As-Built Documentazione\n\n## Componenti Attuali\n| Componente | Seriale |\n|---|---|\n| Router | `RTR001` |\n", encoding="utf-8")

        patch_res = rp.apply_as_built_patch_to_project(self.test_slug, rep["report_id"])
        self.assertTrue(patch_res["applied"])

        # Controllo idempotenza: seconda applicazione deve essere saltata
        patch_res2 = rp.apply_as_built_patch_to_project(self.test_slug, rep["report_id"])
        self.assertFalse(patch_res2["applied"])
        self.assertEqual(patch_res2["status"], "already_applied")

    def test_asse2_furniture_punch_list_and_electrical_check(self):
        """Verifica gestione Punch List (snagging), ritenuta 5% e cross-check carico elettrico."""
        fp = FurniturePipeline(self.clients_root)
        fdir = self.client_dir / "furniture"
        fdir.mkdir(parents=True, exist_ok=True)
        ffile = fdir / "arr-test.yaml"

        order_data = {
            "order_id": "ARR-2026-TEST",
            "slug": self.test_slug,
            "title": "Arredo Uffici Nuova Sede",
            "status": "5_assembly",
            "totals": {"total_net": 10000.0},
            "items": [
                {"description": "Scrivania direzionale sit-stand motorizzata", "quantity": 4},
                {"description": "Cabina acustica meeting pod 4 posti", "quantity": 1},
                {"description": "Postazione operativa bench 4 posti", "quantity": 2}
            ],
            "stages": {
                "handover": {
                    "warranty_retention_percent": 5.0,
                    "checklist": {"desk_planarity_ok": True}
                }
            }
        }
        with open(ffile, "w", encoding="utf-8") as fp_out:
            yaml.safe_dump(order_data, fp_out)

        # Aggiunta snagging item (graffio finitura)
        st = fp.add_punch_list_item(self.test_slug, "ARR-2026-TEST", "Graffio su piano scrivania 02", severity="minor")
        self.assertEqual(st["current_stage"], "6_handover_conditional_snagging")
        self.assertEqual(st["warranty_retention_amount"], 500.0) # 5% su 10000
        self.assertFalse(st["warranty_retention_released"])

        # Risoluzione difetto
        st_resolved = fp.resolve_punch_list_item(self.test_slug, "ARR-2026-TEST", item_id=1, resolution_note="Sostituito top scrivania")
        self.assertEqual(st_resolved["current_stage"], "6_handover_approved")
        self.assertTrue(st_resolved["warranty_retention_released"])

        # Cross-check carico elettrico
        elec = fp.cross_check_electrical_load(self.test_slug, "ARR-2026-TEST")
        self.assertGreater(elec["total_power_kw_peak"], 0.0)
        self.assertIn("recommended_circuits_count", elec)

    # =========================================================================
    # ASSE 3: COGNITIVE & INTELLIGENCE
    # =========================================================================

    def test_asse3_sdi_xml_ingestion_and_table_stitcher(self):
        """Verifica estrazione XML SDI Fattura Elettronica e stitcher tabelle multi-pagina."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdCodice>09876543210</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>IT Vendor Distribution SRL</Denominazione></Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdCodice>12345678901</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>Studio Legale Alpha</Denominazione></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2026-09-18</Data>
        <Numero>FATT-987</Numero>
        <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
      <DatiOrdineAcquisto>
        <IdDocumento>PO-2026-001</IdDocumento>
      </DatiOrdineAcquisto>
      <DatiDDT>
        <NumeroDDT>DDT-5432</NumeroDDT>
      </DatiDDT>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Notebook Lenovo ThinkPad T14</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>1000.00</PrezzoUnitario>
        <PrezzoTotale>1000.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
    </DatiBeniServizi>
    <DatiPagamento>
      <DettaglioPagamento>
        <IBAN>IT60X0542811101000000123456</IBAN>
      </DettaglioPagamento>
    </DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        parsed = SdiXmlExtractor.extract(xml_content)
        self.assertEqual(parsed["document_type"], "INVOICE_SDI_XML")
        p_inv = parsed["parsed_invoice"]
        self.assertEqual(p_inv["invoice_number"], "FATT-987")
        self.assertEqual(p_inv["client_name"], "Studio Legale Alpha")
        self.assertEqual(p_inv["po_number"], "PO-2026-001")
        self.assertEqual(p_inv["ddt_numbers"], ["DDT-5432"])
        self.assertEqual(len(p_inv["lines"]), 1)

        # Test Table Continuity Stitcher
        tables = [
            {"headers": ["Codice", "Descrizione", "Qta"], "rows": [["01", "Server", "1"]]},
            {"headers": ["Codice", "Descrizione", "Qta"], "rows": [["02", "Switch", "2"]]}
        ]
        stitched = TableContinuityStitcher.stitch_markdown_tables(tables)
        self.assertEqual(len(stitched), 1)
        self.assertEqual(len(stitched[0]["rows"]), 2)

    def test_asse3_triangular_audit_engine(self):
        """Verifica riconciliazione triangolare 3-Way Match (PO vs DDT vs Fattura)."""
        po_data = {
            "items": [
                {"part_number": "SRV-01", "description": "Server Dell R660", "quantity": 1, "unit_price": 4000.0},
                {"part_number": "SW-01", "description": "Switch 24P PoE", "quantity": 2, "unit_price": 500.0}
            ]
        }
        ddt_data = {
            "items": [
                {"part_number": "SRV-01", "description": "Server Dell R660", "quantity": 1},
                {"part_number": "SW-01", "description": "Switch 24P PoE", "quantity": 2}
            ]
        }
        # Caso 1: Match perfetto
        inv_data_perfect = {
            "items": [
                {"part_number": "SRV-01", "description": "Server Dell R660", "quantity": 1, "unit_price": 4000.0},
                {"part_number": "SW-01", "description": "Switch 24P PoE", "quantity": 2, "unit_price": 500.0}
            ]
        }
        res_perfect = TriangularAuditEngine.audit_triangular(po_data, ddt_data, inv_data_perfect)
        self.assertTrue(res_perfect["is_conforming"])
        self.assertEqual(res_perfect["overall_status"], "MATCH")

        # Caso 2: Discrepanza prezzo e quantità extra senza DDT
        inv_data_discrepant = {
            "items": [
                {"part_number": "SRV-01", "description": "Server Dell R660", "quantity": 1, "unit_price": 4500.0}, # +500 prezzo
                {"part_number": "SW-01", "description": "Switch 24P PoE", "quantity": 3, "unit_price": 500.0}       # +1 qta rispetto a DDT
            ]
        }
        res_disc = TriangularAuditEngine.audit_triangular(po_data, ddt_data, inv_data_discrepant)
        self.assertFalse(res_disc["is_conforming"])
        self.assertGreater(res_disc["discrepancies_count"], 0)

    def test_asse3_memory_dag_cycle_detection_and_decay(self):
        """Verifica rilevamento cicli DAG, nodi orfani e decadimento confidenza in MemoryEngine."""
        mem = MemoryEngine(repo_root=self.root_path)

        # Crea 3 nodi con un ciclo A -> B -> C -> A
        dom_dir = mem.memory_dir / "core"
        dom_dir.mkdir(parents=True, exist_ok=True)

        node_a = {"id": "CYC-A", "lifecycle": "active", "confidence": 1.0, "prerequisites": ["CYC-B"]}
        node_b = {"id": "CYC-B", "lifecycle": "active", "confidence": 0.9, "prerequisites": ["CYC-C"]}
        node_c = {"id": "CYC-C", "lifecycle": "active", "confidence": 0.8, "prerequisites": ["CYC-A"]}

        (dom_dir / "cyc_a.okf.md").write_text(mem.format_okf_file(node_a, "Corpo A"), encoding="utf-8")
        (dom_dir / "cyc_b.okf.md").write_text(mem.format_okf_file(node_b, "Corpo B"), encoding="utf-8")
        (dom_dir / "cyc_c.okf.md").write_text(mem.format_okf_file(node_c, "Corpo C"), encoding="utf-8")

        audit_res = mem.audit_memory()
        self.assertEqual(audit_res["status"], "FAIL")
        self.assertGreater(len(audit_res["dag_cycles"]), 0)

        # Test rinforzo confidenza
        reinf = mem.reinforce_confidence("CYC-B", delta=0.05)
        self.assertEqual(reinf["status"], "success")
        self.assertEqual(reinf["new_confidence"], 0.95)

        # Test decadimento
        decay = mem.decay_confidence_scores(half_life_days=30.0)
        self.assertEqual(decay["total_nodes_evaluated"], 3)

    def test_asse3_jira_travel_buffer_and_outbox_backoff(self):
        """Verifica buffer di viaggio 45 min per clienti diversi e dispatcher outbox."""
        jp = JiraSyncPipeline(self.clients_root)

        # Crea un appuntamento esistente per Cliente A (10:00 - 12:00)
        jp.create_appointment(
            slug="cliente-alfa",
            issue_key="TCK-100",
            summary="Intervento Alfa",
            start_dt="2026-09-18T10:00:00",
            duration_hours=2.0,
            technician="Mario Rossi"
        )

        # Proposta per Cliente B alle 12:15 (gap di soli 15 min < 45 min)
        conflicts = jp.check_schedule_conflicts(
            proposed_start="2026-09-18T12:15:00",
            proposed_end="2026-09-18T14:15:00",
            technician="Mario Rossi",
            target_slug="cliente-beta",
            travel_buffer_minutes=45
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["conflict_type"], "INSUFFICIENT_TRAVEL_BUFFER")

        # Proposta per Cliente B alle 13:00 (gap di 60 min >= 45 min) -> nessun conflitto
        no_conflicts = jp.check_schedule_conflicts(
            proposed_start="2026-09-18T13:00:00",
            proposed_end="2026-09-18T15:00:00",
            technician="Mario Rossi",
            target_slug="cliente-beta",
            travel_buffer_minutes=45
        )
        self.assertEqual(len(no_conflicts), 0)

        # Test Outbox Dispatcher
        jp.queue_action("cliente-alfa", "log_work", {"timeSpent": "2h", "comment": "Risolto"})
        dispatch_res = jp.dispatch_outbox_queue("cliente-alfa")
        self.assertEqual(dispatch_res["total_succeeded"], 1)
        self.assertEqual(len(jp.get_queued_actions("cliente-alfa", status="sent")), 1)

    # =========================================================================
    # CORE BRIDGE: IPAM & SLA ASSET COVERAGE
    # =========================================================================

    def test_core_bridge_ipam_and_sla_coverage(self):
        """Verifica estrazione IPAM e cross-check copertura asset As-Built vs Contratti SLA."""
        bridge = ITInfraBridge(clients_root=self.clients_root)
        tech_proj_dir = bridge.itinfra_root / "projects" / self.test_slug
        tech_proj_dir.mkdir(parents=True, exist_ok=True)

        # Scrive 04-Network-IPAM.md
        ipam_file = tech_proj_dir / "04-Network-IPAM.md"
        ipam_file.write_text("""# Network & IPAM
Subnet di gestione: 192.168.10.0/24

| IP | Hostname | Descrizione |
|---|---|---|
| `192.168.10.1` | GW-FIREWALL | Gateway primario |
| `192.168.10.10` | SRV-ESXI01 | Hypervisor principale |
""", encoding="utf-8")

        # Scrive 06-As-Built.md
        as_built_file = tech_proj_dir / "06-As-Built.md"
        as_built_file.write_text("""# As-Built
### 4.1 Server Principale
| Proprietà | Valore |
|---|---|
| **Modello** | PowerEdge R660 |
| **Numero di Serie** | `SRV-ASBUILT-01` |
| **Hostname** | srv-prod |

### 4.2 Switch Accesso
| Proprietà | Valore |
|---|---|
| **Modello** | Catalyst 9200 |
| **Numero di Serie** | `SW-ASBUILT-02` |
""", encoding="utf-8")

        # Crea contratto SLA che copre solo SRV-ASBUILT-01 (SW-ASBUILT-02 rimane scoperto / Shadow IT)
        cdir = self.client_dir / "contracts"
        cdir.mkdir(parents=True, exist_ok=True)
        cfile = cdir / "ctr-test-cov.yaml"
        with open(cfile, "w", encoding="utf-8") as fp:
            yaml.safe_dump({
                "contract_id": "CTR-TEST-COV",
                "status": "active",
                "covered_assets": [{"serial_number": "SRV-ASBUILT-01", "role": "server"}]
            }, fp)

        # 1. Estrazione IPAM
        ipam_res = bridge.extract_ipam_subnets_and_ips(self.test_slug)
        self.assertTrue(ipam_res["found"])
        self.assertEqual(len(ipam_res["subnets"]), 1)
        self.assertEqual(ipam_res["allocations_count"], 2)

        # 2. Cross-check SLA Coverage
        cov = bridge.cross_check_sla_assets_coverage(self.test_slug)
        self.assertEqual(cov["total_as_built_assets"], 2)
        self.assertEqual(cov["total_covered_in_contract"], 1)
        self.assertEqual(len(cov["missing_from_contract"]), 1)
        self.assertEqual(cov["missing_from_contract"][0]["serial_number"], "SW-ASBUILT-02")
        self.assertEqual(cov["coverage_ratio_percent"], 50.0)
        self.assertEqual(cov["status"], "WARNING")


if __name__ == "__main__":
    unittest.main()
