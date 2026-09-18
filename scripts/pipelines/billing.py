import datetime
import json
import re
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir, load_config
from scripts.pipelines.contracts import ContractsPipeline
from scripts.pipelines.reports import ReportsPipeline
from scripts.pipelines.mps import MPSPipeline

class BillingPipeline:
    """Pipeline C: Fatturazione Elettronica SDI (v1.2) & Scadenzario Attivo."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()

    def get_invoices_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "invoices"

    def get_client_manifest(self, slug: str) -> Dict[str, Any]:
        mfile = self.clients_root / slug / "client-manifest.yaml"
        if mfile.is_file():
            with open(mfile, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @staticmethod
    def _get_end_of_month(d: datetime.date) -> datetime.date:
        """Calcola l'ultimo giorno del mese per la data fornita."""
        next_month = d.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def compute_installments(self, total_gross: float, terms: str, base_date: datetime.date) -> List[Dict[str, Any]]:
        """Calcola deterministamente le rate e le scadenze (es. 30/60 gg fine mese)."""
        installments = []
        if terms == "30_60_DF_FM":
            inst1_due = self._get_end_of_month(base_date + datetime.timedelta(days=30)).isoformat()
            inst2_due = self._get_end_of_month(base_date + datetime.timedelta(days=60)).isoformat()
            amt1 = round(total_gross / 2.0, 2)
            amt2 = round(total_gross - amt1, 2)
            installments.append({
                "number": 1,
                "due_date": inst1_due,
                "amount": amt1,
                "status": "unpaid",
                "paid_date": "",
                "bank_transaction_id": ""
            })
            installments.append({
                "number": 2,
                "due_date": inst2_due,
                "amount": amt2,
                "status": "unpaid",
                "paid_date": "",
                "bank_transaction_id": ""
            })
        elif terms in ("30_DF_FM", "30_FM"):
            inst_due = self._get_end_of_month(base_date + datetime.timedelta(days=30)).isoformat()
            installments.append({
                "number": 1,
                "due_date": inst_due,
                "amount": total_gross,
                "status": "unpaid",
                "paid_date": "",
                "bank_transaction_id": ""
            })
        elif terms in ("60_DF_FM", "60_FM"):
            inst_due = self._get_end_of_month(base_date + datetime.timedelta(days=60)).isoformat()
            installments.append({
                "number": 1,
                "due_date": inst_due,
                "amount": total_gross,
                "status": "unpaid",
                "paid_date": "",
                "bank_transaction_id": ""
            })
        else:
            inst_due = (base_date + datetime.timedelta(days=30)).isoformat()
            installments.append({
                "number": 1,
                "due_date": inst_due,
                "amount": total_gross,
                "status": "unpaid",
                "paid_date": "",
                "bank_transaction_id": ""
            })
        return installments

    def aggregate_monthly_batch(self, slug: str, period: Optional[str] = None) -> Dict[str, Any]:
        """Aggrega canoni ricorrenti, ore spot, ore extra-soglia, ricambi, canoni e conguagli MPS."""
        if not period:
            period = datetime.date.today().strftime("%Y-%m")

        contracts_pipe = ContractsPipeline(self.clients_root)
        reports_pipe = ReportsPipeline(self.clients_root)
        mps_pipe = MPSPipeline(self.clients_root)

        contracts = contracts_pipe.list_contracts(slug)
        reports = reports_pipe.list_reports(slug)
        reports_summary = reports_pipe.get_ledger_summary(slug)
        mps_contracts = mps_pipe.list_mps_contracts(slug)
        cmanifest = self.get_client_manifest(slug)
        terms = cmanifest.get("billing_info", {}).get("payment_terms", "30_60_DF_FM")

        vat_rate = float(self.config.get("company", {}).get("default_vat_rate", 22.0))
        lines: List[Dict[str, Any]] = []

        # 1. Canoni Contrattuali Ricorrenti
        for c in contracts:
            if c.get("status") == "active":
                fee = float(c.get("financial", {}).get("recurring_fee", 0.0))
                cid = c.get("contract_id", "CTR")
                if fee > 0:
                    lines.append({
                        "description": f"Canone Assistenza IT {cid} - Periodo {period}",
                        "quantity": 1,
                        "unit_price": fee,
                        "vat_rate": vat_rate,
                        "total_line": fee,
                        "source_type": "recurring_contract",
                        "source_ref": cid
                    })

        # 2. Rapportini Spot da Fatturare
        for rep in reports_summary["unbilled_spot_reports"]:
            h = rep["hours"]
            hourly_rate = 75.0
            tot = round(h * hourly_rate, 2)
            lines.append({
                "description": f"Intervento tecnico {rep['report_id']} ({rep['date']}) - {rep['description']}",
                "quantity": h,
                "unit_price": hourly_rate,
                "vat_rate": vat_rate,
                "total_line": tot,
                "source_type": "rapportino_hours",
                "source_ref": rep["report_id"]
            })

        # 3. Ore Extra-Soglia da Contratti (Over-Budget da Rapportini)
        for r in reports:
            extra_h = float(r.get("extra_hours", 0.0))
            if extra_h > 0 and r.get("date", "").startswith(period):
                # Trova tariffa extra da contratto
                cid = r.get("contract_id", "")
                extra_rate = 80.0
                for c in contracts:
                    if c.get("contract_id") == cid:
                        extra_rate = float(c.get("financial", {}).get("extra_hourly_rate", 80.0))
                        break
                tot_extra = round(extra_h * extra_rate, 2)
                lines.append({
                    "description": f"Ore Extra-Soglia a contratto {cid} ({r.get('report_id')})",
                    "quantity": extra_h,
                    "unit_price": extra_rate,
                    "vat_rate": vat_rate,
                    "total_line": tot_extra,
                    "source_type": "rapportino_hours",
                    "source_ref": r.get("report_id")
                })

        # 4. Ricambi & Materiali fatturabili da Rapportini
        for r in reports:
            if r.get("date", "").startswith(period):
                for part in r.get("spare_parts", []):
                    qty = float(part.get("quantity", 1))
                    price = float(part.get("unit_price", 0.0))
                    if price > 0:
                        line_tot = round(qty * price, 2)
                        lines.append({
                            "description": f"Ricambio: {part.get('description')} [{part.get('code')}] ({r.get('report_id')})",
                            "quantity": qty,
                            "unit_price": price,
                            "vat_rate": vat_rate,
                            "total_line": line_tot,
                            "source_type": "hardware_sale",
                            "source_ref": r.get("report_id")
                        })

        # 5. Canoni & Conguagli Copie MPS Stampanti
        for m in mps_contracts:
            if m.get("status") == "active":
                st = mps_pipe.calculate_settlement(m)
                mid = m.get("mps_contract_id", "MPS")
                model = m.get("device_info", {}).get("model", "Stampante")
                rental_type = m.get("contract_terms", {}).get("rental_type", "direct_internal")

                # Se non è finanziaria terza, include il canone base hardware
                if "financial_lease" not in rental_type and st["base_fee"] > 0:
                    lines.append({
                        "description": f"Canone Noleggio {model} ({mid}) - Periodo {period}",
                        "quantity": 1,
                        "unit_price": st["base_fee"],
                        "vat_rate": vat_rate,
                        "total_line": st["base_fee"],
                        "source_type": "mps_base_fee",
                        "source_ref": mid
                    })
                if st["mono_overage_cost"] > 0:
                    lines.append({
                        "description": f"Eccedenza Copie BN ({st['mono_excess']} pag) {mid}",
                        "quantity": st["mono_excess"],
                        "unit_price": float(m.get("contract_terms", {}).get("overage_cost_per_page", {}).get("mono", 0.009)),
                        "vat_rate": vat_rate,
                        "total_line": st["mono_overage_cost"],
                        "source_type": "mps_excess_bw",
                        "source_ref": mid
                    })
                if st["color_overage_cost"] > 0:
                    lines.append({
                        "description": f"Eccedenza Copie Colore ({st['color_excess']} pag) {mid}",
                        "quantity": st["color_excess"],
                        "unit_price": float(m.get("contract_terms", {}).get("overage_cost_per_page", {}).get("color", 0.065)),
                        "vat_rate": vat_rate,
                        "total_line": st["color_overage_cost"],
                        "source_type": "mps_excess_color",
                        "source_ref": mid
                    })

        subtotal = round(sum(l["total_line"] for l in lines), 2)
        vat_amount = round(subtotal * (vat_rate / 100.0), 2)
        total_gross = round(subtotal + vat_amount, 2)

        batch_id = f"BILL-{period.replace('-', '')}-{slug}"
        today = datetime.date.today()
        installments = self.compute_installments(total_gross, terms, today)

        batch = {
            "batch_id": batch_id,
            "slug": slug,
            "period": period,
            "status": "draft",
            "invoice_draft": {
                "invoice_number": f"DRAFT-{batch_id}",
                "invoice_date": today.isoformat(),
                "payment_method": "MP05",
                "payment_terms": terms,
                "lines": lines,
                "totals": {
                    "subtotal_net": subtotal,
                    "vat_amount": vat_amount,
                    "total_gross": total_gross
                }
            },
            "scadenzario": {
                "overall_status": "open",
                "payment_terms": terms,
                "installments": installments
            }
        }
        return batch

    def generate_sdi_xml(self, batch: Dict[str, Any], client_manifest: Optional[Dict[str, Any]] = None) -> str:
        """Genera il tracciato formale FatturaPA/SDI v1.2 (FPR12 B2B) completo di Cedente e Cessionario."""
        slug = batch.get("slug", "")
        cmanifest = client_manifest or self.get_client_manifest(slug)
        cbilling = cmanifest.get("billing_info", {})
        caddr = cbilling.get("address", {})
        comp = self.config.get("company", {})

        draft = batch.get("invoice_draft") or batch
        client_obj = batch.get("client") or draft.get("client") or {}

        is_pa = bool(
            cmanifest.get("is_public_administration") or
            cbilling.get("is_pa") or
            batch.get("is_public_administration") or
            batch.get("is_pa") or
            client_obj.get("is_public_administration") or
            client_obj.get("is_pa") or
            (len(str(client_obj.get("sdi_code", "")).strip()) == 6)
        )

        versione = "FPA12" if is_pa else "FPR12"
        root = ET.Element("p:FatturaElettronica", {
            "versione": versione,
            "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#"
        })

        # --- HEADER ---
        header = ET.SubElement(root, "FatturaElettronicaHeader")
        
        # Dati Trasmissione
        dati_trasm = ET.SubElement(header, "DatiTrasmissione")
        id_trasm = ET.SubElement(dati_trasm, "IdTrasmittente")
        ET.SubElement(id_trasm, "IdPaese").text = "IT"
        ET.SubElement(id_trasm, "IdCodice").text = comp.get("fiscal_code", "01234567890")
        ET.SubElement(dati_trasm, "ProgressivoInvio").text = batch.get("batch_id", "00001")[-10:]

        sdi_code = client_obj.get("sdi_code") or cbilling.get("sdi_code") or cbilling.get("ipa_code") or ("000000" if is_pa else "0000000")
        if is_pa:
            ET.SubElement(dati_trasm, "FormatoTrasmissione").text = "FPA12"
            ET.SubElement(dati_trasm, "CodiceDestinatario").text = str(sdi_code).strip().upper()[:6]
        else:
            ET.SubElement(dati_trasm, "FormatoTrasmissione").text = "FPR12"
            ET.SubElement(dati_trasm, "CodiceDestinatario").text = str(sdi_code).strip().upper()[:7]

        if cbilling.get("pec") or client_obj.get("pec"):
            ET.SubElement(dati_trasm, "PECDestinatario").text = cbilling.get("pec") or client_obj.get("pec")

        # Cedente / Prestatore (Fornitore)
        cedente = ET.SubElement(header, "CedentePrestatore")
        dati_anag_ced = ET.SubElement(cedente, "DatiAnagrafici")
        id_fisc_ced = ET.SubElement(dati_anag_ced, "IdFiscaleIVA")
        ET.SubElement(id_fisc_ced, "IdPaese").text = "IT"
        ET.SubElement(id_fisc_ced, "IdCodice").text = comp.get("fiscal_code", "01234567890")
        anag_ced = ET.SubElement(dati_anag_ced, "Anagrafica")
        ET.SubElement(anag_ced, "Denominazione").text = comp.get("name", "ITInfra Business Ops")
        ET.SubElement(dati_anag_ced, "RegimeFiscale").text = "RF01"
        sede_ced = ET.SubElement(cedente, "Sede")
        ET.SubElement(sede_ced, "Indirizzo").text = "Via dell'Infrastruttura, 10"
        ET.SubElement(sede_ced, "CAP").text = "20100"
        ET.SubElement(sede_ced, "Comune").text = "Milano"
        ET.SubElement(sede_ced, "Provincia").text = "MI"
        ET.SubElement(sede_ced, "Nazione").text = "IT"

        # Cessionario / Committente (Cliente)
        cessionario = ET.SubElement(header, "CessionarioCommittente")
        dati_anag_cess = ET.SubElement(cessionario, "DatiAnagrafici")
        vat_raw = str(client_obj.get("vat_id") or cbilling.get("vat_id", "00000000000")).replace("IT", "")
        id_fisc_cess = ET.SubElement(dati_anag_cess, "IdFiscaleIVA")
        ET.SubElement(id_fisc_cess, "IdPaese").text = "IT"
        ET.SubElement(id_fisc_cess, "IdCodice").text = vat_raw
        fisc_code = client_obj.get("fiscal_code") or cbilling.get("fiscal_code")
        if fisc_code:
            ET.SubElement(dati_anag_cess, "CodiceFiscale").text = str(fisc_code)
        anag_cess = ET.SubElement(dati_anag_cess, "Anagrafica")
        ET.SubElement(anag_cess, "Denominazione").text = client_obj.get("name") or cmanifest.get("client_name", slug)
        sede_cess = ET.SubElement(cessionario, "Sede")
        ET.SubElement(sede_cess, "Indirizzo").text = client_obj.get("address") or caddr.get("street", "Via Cliente, 1")
        ET.SubElement(sede_cess, "CAP").text = client_obj.get("zip") or caddr.get("zip", "00100")
        ET.SubElement(sede_cess, "Comune").text = client_obj.get("city") or caddr.get("city", "Roma")
        ET.SubElement(sede_cess, "Provincia").text = client_obj.get("province") or caddr.get("province", "RM")
        ET.SubElement(sede_cess, "Nazione").text = client_obj.get("country") or caddr.get("country", "IT")

        # Supporto sia batch completo che dizionario fattura diretto
        raw_lines = draft.get("lines", [])

        # --- BODY ---
        body = ET.SubElement(root, "FatturaElettronicaBody")
        dati_gen = ET.SubElement(body, "DatiGenerali")
        dati_doc = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
        ET.SubElement(dati_doc, "TipoDocumento").text = "TD01"
        ET.SubElement(dati_doc, "Divisa").text = comp.get("currency", "EUR")
        ET.SubElement(dati_doc, "Data").text = draft.get("invoice_date", "")
        ET.SubElement(dati_doc, "Numero").text = draft.get("invoice_number", "DRAFT-01")

        # Ritenuta d'Acconto (se presente)
        withholding = draft.get("withholding_tax") or cbilling.get("withholding_tax")
        if withholding and isinstance(withholding, dict):
            w_tax = ET.SubElement(dati_doc, "DatiRitenuta")
            ET.SubElement(w_tax, "TipoRitenuta").text = withholding.get("type", "RT02")
            ET.SubElement(w_tax, "ImportoRitenuta").text = f"{float(withholding.get('amount', 0.0)):.2f}"
            rate = withholding.get("rate_percent") if withholding.get("rate_percent") is not None else withholding.get("percentage", 20.0)
            ET.SubElement(w_tax, "AliquotaRitenuta").text = f"{float(rate):.2f}"
            ET.SubElement(w_tax, "CausalePagamento").text = withholding.get("causale") or withholding.get("reason", "A")

        # Cassa Previdenziale (se presente)
        pension = draft.get("pension_fund") or cbilling.get("pension_fund")
        if pension and isinstance(pension, dict):
            p_fund = ET.SubElement(dati_doc, "DatiCassaPrevidenziale")
            ET.SubElement(p_fund, "TipoCassa").text = pension.get("type", "TC22")
            rate = pension.get("rate_percent") if pension.get("rate_percent") is not None else pension.get("percentage", 4.0)
            ET.SubElement(p_fund, "AlCassa").text = f"{float(rate):.2f}"
            ET.SubElement(p_fund, "ImportoContributoCassa").text = f"{float(pension.get('amount', 0.0)):.2f}"
            ET.SubElement(p_fund, "ImponibileCassa").text = f"{float(pension.get('taxable_base', 0.0)):.2f}"
            ET.SubElement(p_fund, "AliquotaIVA").text = f"{float(pension.get('vat_rate', 22.0)):.2f}"
            ET.SubElement(p_fund, "Ritenuta").text = "SI" if pension.get("withholding") else "NO"

        # Dati Ordine / CIG & CUP (Obbligatori per PA)
        po = draft.get("purchase_order") or batch.get("purchase_order") or {}
        cig = draft.get("cig") or cbilling.get("cig") or batch.get("cig") or po.get("cig")
        cup = draft.get("cup") or cbilling.get("cup") or batch.get("cup") or po.get("cup")
        order_ref = draft.get("order_reference") or cbilling.get("order_reference") or batch.get("order_reference") or po.get("po_number")
        if is_pa or cig or cup or order_ref:
            dati_ord = ET.SubElement(dati_gen, "DatiOrdineAcquisto")
            ET.SubElement(dati_ord, "RiferimentoNumeroLinea").text = "1"
            ET.SubElement(dati_ord, "IdDocumento").text = str(order_ref or f"ORD-{draft.get('invoice_number', '01')}")
            if cig:
                ET.SubElement(dati_ord, "CodiceCIG").text = str(cig).strip().upper()
            if cup:
                ET.SubElement(dati_ord, "CodiceCUP").text = str(cup).strip().upper()

        # Calcolo totali e bollo
        tot_gross = draft.get("totals", {}).get("total_gross")
        if tot_gross is None:
            tot_gross = sum(float(l.get("total_line", float(l.get("quantity", 1)) * float(l.get("unit_price", 0.0)))) for l in raw_lines)
        ET.SubElement(dati_doc, "ImportoTotaleDocumento").text = f"{tot_gross:.2f}"

        # Verifica Marca da Bollo Virtuale (obbligatoria per esenti > 77.47 €)
        exempt_total = sum(
            float(l.get("total_line", float(l.get("quantity", 1)) * float(l.get("unit_price", 0.0))))
            for l in raw_lines
            if float(l.get("vat_rate", 22.0)) == 0.0
        )
        if exempt_total > 77.47:
            dati_bollo = ET.SubElement(dati_doc, "DatiBollo")
            ET.SubElement(dati_bollo, "BolloVirtuale").text = "SI"
            ET.SubElement(dati_bollo, "ImportoBollo").text = "2.00"

        # Righe Dettaglio
        dati_beni = ET.SubElement(body, "DatiBeniServizi")
        vat_rate = float(comp.get("default_vat_rate", 22.0))
        has_exempt = False
        exempt_nature = "N4"

        for i, line in enumerate(raw_lines, start=1):
            dett = ET.SubElement(dati_beni, "DettaglioLinee")
            ET.SubElement(dett, "NumeroLinea").text = str(i)
            ET.SubElement(dett, "Descrizione").text = line.get("description", "")
            q_val = float(line.get('quantity', 1))
            p_val = float(line.get('unit_price', 0.0))
            tot_l = float(line.get('total_line', q_val * p_val))
            ET.SubElement(dett, "Quantita").text = f"{q_val:.2f}"
            ET.SubElement(dett, "PrezzoUnitario").text = f"{p_val:.2f}"
            ET.SubElement(dett, "PrezzoTotale").text = f"{tot_l:.2f}"
            l_vat = float(line.get('vat_rate', vat_rate))
            ET.SubElement(dett, "AliquotaIVA").text = f"{l_vat:.2f}"
            if l_vat == 0.0:
                has_exempt = True
                natura_code = line.get("natura") or line.get("vat_nature", "N4")
                exempt_nature = natura_code
                ET.SubElement(dett, "Natura").text = natura_code

        # Dati Riepilogo IVA (Standard & Split Payment)
        is_split = bool(cbilling.get("split_payment") or cmanifest.get("is_public_administration") or batch.get("is_split_payment"))
        
        # Riepilogo imponibile standard
        riepilogo = ET.SubElement(dati_beni, "DatiRiepilogo")
        ET.SubElement(riepilogo, "AliquotaIVA").text = f"{vat_rate:.2f}"
        subtot = draft.get("totals", {}).get("subtotal_net", sum(float(l.get("total_line", float(l.get("quantity", 1)) * float(l.get("unit_price", 0.0)))) for l in raw_lines if float(l.get("vat_rate", vat_rate)) > 0))
        vat_amt = draft.get("totals", {}).get("vat_amount", round(subtot * (vat_rate / 100.0), 2))
        ET.SubElement(riepilogo, "ImponibileImporto").text = f"{subtot:.2f}"
        ET.SubElement(riepilogo, "Imposta").text = f"{vat_amt:.2f}"
        ET.SubElement(riepilogo, "EsigibilitaIVA").text = "S" if is_split else "I" # S = Split Payment, I = Immediata

        # Se presenti esenti, aggiunge nodo di riepilogo esente
        if has_exempt:
            riep_esente = ET.SubElement(dati_beni, "DatiRiepilogo")
            ET.SubElement(riep_esente, "AliquotaIVA").text = "0.00"
            ET.SubElement(riep_esente, "Natura").text = exempt_nature
            ET.SubElement(riep_esente, "ImponibileImporto").text = f"{exempt_total:.2f}"
            ET.SubElement(riep_esente, "Imposta").text = "0.00"
            ET.SubElement(riep_esente, "RiferimentoNormativo").text = "Operazione Esente IVA D.P.R. 633/72"

        # Dati Pagamento
        dati_pag = ET.SubElement(body, "DatiPagamento")
        ET.SubElement(dati_pag, "CondizioniPagamento").text = "TP02" # Completo
        dett_pag = ET.SubElement(dati_pag, "DettaglioPagamento")
        ET.SubElement(dett_pag, "ModalitaPagamento").text = draft.get("payment_method", "MP05")
        inst = batch.get("scadenzario", {}).get("installments", [{}])[0]
        if inst.get("due_date"):
            ET.SubElement(dett_pag, "DataScadenzaPagamento").text = inst.get("due_date")
        ET.SubElement(dett_pag, "ImportoPagamento").text = f"{tot_gross:.2f}"
        if cbilling.get("iban"):
            ET.SubElement(dett_pag, "IBAN").text = cbilling.get("iban")

        # Pretty-print indentation
        self._indent(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def save_batch(self, slug: str, batch: Dict[str, Any]) -> Dict[str, Path]:
        """Salva fisicamente il batch JSON, l'XML SDI e genera automaticamente le viste HTML e PDF."""
        from scripts.core.document_renderer import DocumentRenderer

        idir = self.get_invoices_dir(slug)
        idir.mkdir(parents=True, exist_ok=True)
        batch_id = batch["batch_id"]

        json_path = idir / f"{batch_id.lower()}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)

        xml_content = self.generate_sdi_xml(batch)
        xml_path = idir / f"{batch_id.lower()}.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        # Genera viste di cortesia HTML e PDF
        html_path = DocumentRenderer.render_xml_invoice_to_html(xml_path)
        pdf_path = DocumentRenderer.render_xml_invoice_to_pdf(xml_path)

        return {
            "json": json_path,
            "xml": xml_path,
            "html": html_path,
            "pdf": pdf_path
        }

    def render_invoice(self, slug: str, invoice_or_batch_id: str) -> Dict[str, Path]:
        """Rigenera le viste grafiche HTML e PDF di cortesia da un file XML esistente."""
        from scripts.core.document_renderer import DocumentRenderer

        idir = self.get_invoices_dir(slug)
        target_xml = None

        search_id = invoice_or_batch_id.lower()
        for xf in idir.glob("*.xml"):
            if search_id in xf.name.lower():
                target_xml = xf
                break

        if not target_xml:
            # Prova con nome file diretto
            direct = idir / f"{search_id}.xml"
            if direct.is_file():
                target_xml = direct

        if not target_xml or not target_xml.is_file():
            return {}

        html_path = DocumentRenderer.render_xml_invoice_to_html(target_xml)
        pdf_path = DocumentRenderer.render_xml_invoice_to_pdf(target_xml)
        return {"xml": target_xml, "html": html_path, "pdf": pdf_path}

    def mark_installment_paid(self, slug: str, batch_id: str, installment_num: int = 1, tx_id: str = "") -> bool:
        """Registra l'avvenuto incasso di una rata nello scadenzario."""
        idir = self.get_invoices_dir(slug)
        json_path = idir / f"{batch_id.lower()}.json"
        if not json_path.is_file():
            return False

        with open(json_path, "r", encoding="utf-8") as f:
            batch = json.load(f)

        updated = False
        all_paid = True
        for inst in batch.get("scadenzario", {}).get("installments", []):
            if inst.get("number") == installment_num:
                inst["status"] = "paid"
                inst["paid_date"] = datetime.date.today().isoformat()
                inst["bank_transaction_id"] = tx_id or f"TX-{datetime.date.today().strftime('%Y%m%d')}-01"
                updated = True
            if inst.get("status") != "paid":
                all_paid = False

        if updated:
            if all_paid:
                batch["scadenzario"]["overall_status"] = "paid"
                batch["status"] = "paid"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(batch, f, indent=2, ensure_ascii=False)
            return True
        return False

    def generate_sdd_xml(
        self,
        target_or_slug: Any,
        batch: Optional[Dict[str, Any]] = None,
        debtor_iban: str = "",
        mandate_id: str = "",
        debtor_bic: str = "",
        execution_date: str = ""
    ) -> str:
        """
        Genera il tracciato SEPA Direct Debit (SDD) in standard ISO 20022 XML (pain.008.001.02)
        per l'incasso telematico bancario dei canoni ricorrenti (B2B/CORE).
        Supporta sia una lista di transazioni/fatture massive che un singolo batch cliente.
        """
        comp = self.config.get("company", {})
        comp_name = comp.get("name", "ITInfra Business Ops")
        creditor_iban = comp.get("iban", "IT00X0000000000000000000000")
        creditor_id = comp.get("creditor_id", f"IT00ZZZ{comp.get('fiscal_code', '01234567890')}")

        root = ET.Element("Document", {
            "xmlns": "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
        })
        cstmr_dir_deb = ET.SubElement(root, "CstmrDrctDbtInitn")

        # Modalità lista transazioni massive
        if isinstance(target_or_slug, list):
            tx_list = target_or_slug
            msg_id = f"SDD-BATCH-{int(datetime.datetime.now().timestamp())}"
            coll_date = execution_date or (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
            tot_sum = sum(float(tx.get("amount", 0.0)) for tx in tx_list)

            # Group Header
            grpHdr = ET.SubElement(cstmr_dir_deb, "GrpHdr")
            ET.SubElement(grpHdr, "MsgId").text = msg_id
            ET.SubElement(grpHdr, "CreDtTm").text = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            ET.SubElement(grpHdr, "NbOfTxs").text = str(len(tx_list))
            ET.SubElement(grpHdr, "CtrlSum").text = f"{tot_sum:.2f}"
            initgPty = ET.SubElement(grpHdr, "InitgPty")
            ET.SubElement(initgPty, "Nm").text = comp_name

            # Payment Information
            pmtInf = ET.SubElement(cstmr_dir_deb, "PmtInf")
            ET.SubElement(pmtInf, "PmtInfId").text = f"PMT-{msg_id}"
            ET.SubElement(pmtInf, "PmtMtd").text = "DD"
            ET.SubElement(pmtInf, "NbOfTxs").text = str(len(tx_list))
            ET.SubElement(pmtInf, "CtrlSum").text = f"{tot_sum:.2f}"

            pmtTpInf = ET.SubElement(pmtInf, "PmtTpInf")
            svcLvl = ET.SubElement(pmtTpInf, "SvcLvl")
            ET.SubElement(svcLvl, "Cd").text = "SEPA"
            lclInstrm = ET.SubElement(pmtTpInf, "LclInstrm")
            ET.SubElement(lclInstrm, "Cd").text = "B2B"
            ET.SubElement(pmtTpInf, "SeqTp").text = "RCUR"

            ET.SubElement(pmtInf, "ReqdColltnDt").text = coll_date

            # Creditor
            cdtr = ET.SubElement(pmtInf, "Cdtr")
            ET.SubElement(cdtr, "Nm").text = comp_name
            cdtrAcct = ET.SubElement(pmtInf, "CdtrAcct")
            cdtrId = ET.SubElement(cdtrAcct, "Id")
            ET.SubElement(cdtrId, "IBAN").text = creditor_iban.replace(" ", "")

            cdtrAgt = ET.SubElement(pmtInf, "CdtrAgt")
            cdtrFinInst = ET.SubElement(cdtrAgt, "FinInstnId")
            if comp.get("bic"):
                ET.SubElement(cdtrFinInst, "BIC").text = comp.get("bic")
            else:
                othr_c = ET.SubElement(cdtrFinInst, "Othr")
                ET.SubElement(othr_c, "Id").text = "NOTPROVIDED"

            cdtrSchmeId = ET.SubElement(pmtInf, "CdtrSchmeId")
            schmeId = ET.SubElement(cdtrSchmeId, "Id")
            prvtId = ET.SubElement(schmeId, "PrvtId")
            othr = ET.SubElement(prvtId, "Othr")
            ET.SubElement(othr, "Id").text = creditor_id
            schmeNm = ET.SubElement(othr, "SchmeNm")
            ET.SubElement(schmeNm, "Prtry").text = "SEPA"

            for idx, tx in enumerate(tx_list, start=1):
                drctDbtTxInf = ET.SubElement(pmtInf, "DrctDbtTxInf")
                pmtId = ET.SubElement(drctDbtTxInf, "PmtId")
                ET.SubElement(pmtId, "EndToEndId").text = f"E2E-{tx.get('invoice_number', idx)}"

                instdAmt = ET.SubElement(drctDbtTxInf, "InstdAmt", {"Ccy": "EUR"})
                instdAmt.text = f"{float(tx.get('amount', 0.0)):.2f}"

                drctDbtTx = ET.SubElement(drctDbtTxInf, "DrctDbtTx")
                mndtRltdInf = ET.SubElement(drctDbtTx, "MndtRltdInf")
                ET.SubElement(mndtRltdInf, "MndtId").text = tx.get("mandate_id", f"MND-{idx}")
                ET.SubElement(mndtRltdInf, "DtOfSgntr").text = tx.get("mandate_date", "2025-01-01")

                # Debtor
                dbtr = ET.SubElement(drctDbtTxInf, "Dbtr")
                ET.SubElement(dbtr, "Nm").text = tx.get("client_name", tx.get("slug", "Cliente"))
                dbtrAcct = ET.SubElement(drctDbtTxInf, "DbtrAcct")
                dbtrId = ET.SubElement(dbtrAcct, "Id")
                ET.SubElement(dbtrId, "IBAN").text = str(tx.get("iban", "")).replace(" ", "")

                dbtrAgt = ET.SubElement(drctDbtTxInf, "DbtrAgt")
                dbtrFinInst = ET.SubElement(dbtrAgt, "FinInstnId")
                if tx.get("bic"):
                    ET.SubElement(dbtrFinInst, "BIC").text = tx["bic"]
                else:
                    othr_dbtr = ET.SubElement(dbtrFinInst, "Othr")
                    ET.SubElement(othr_dbtr, "Id").text = "NOTPROVIDED"

                rmtInf = ET.SubElement(drctDbtTxInf, "RmtInf")
                ET.SubElement(rmtInf, "Ustrd").text = f"Incasso Fattura {tx.get('invoice_number', '')} - {tx.get('slug', '')}"

            self._indent(root)
            return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

        # Modalità singolo cliente / batch
        slug = str(target_or_slug)
        batch = batch or {}
        cmanifest = self.get_client_manifest(slug)

        # Group Header
        grpHdr = ET.SubElement(cstmr_dir_deb, "GrpHdr")
        msg_id = f"SDD-{batch.get('batch_id', '001')}"
        ET.SubElement(grpHdr, "MsgId").text = msg_id
        ET.SubElement(grpHdr, "CreDtTm").text = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ET.SubElement(grpHdr, "NbOfTxs").text = "1"
        tot_gross = float(batch.get("invoice_draft", {}).get("totals", {}).get("total_gross", 0.0))
        ET.SubElement(grpHdr, "CtrlSum").text = f"{tot_gross:.2f}"
        initgPty = ET.SubElement(grpHdr, "InitgPty")
        ET.SubElement(initgPty, "Nm").text = comp_name

        # Payment Information
        pmtInf = ET.SubElement(cstmr_dir_deb, "PmtInf")
        ET.SubElement(pmtInf, "PmtInfId").text = f"PMT-{msg_id}"
        ET.SubElement(pmtInf, "PmtMtd").text = "DD"
        ET.SubElement(pmtInf, "NbOfTxs").text = "1"
        ET.SubElement(pmtInf, "CtrlSum").text = f"{tot_gross:.2f}"

        pmtTpInf = ET.SubElement(pmtInf, "PmtTpInf")
        svcLvl = ET.SubElement(pmtTpInf, "SvcLvl")
        ET.SubElement(svcLvl, "Cd").text = "SEPA"
        lclInstrm = ET.SubElement(pmtTpInf, "LclInstrm")
        ET.SubElement(lclInstrm, "Cd").text = "B2B"
        ET.SubElement(pmtTpInf, "SeqTp").text = "RCUR"

        reqdColltnDt = execution_date or batch.get("invoice_draft", {}).get("invoice_date", datetime.date.today().isoformat())
        ET.SubElement(pmtInf, "ReqdColltnDt").text = reqdColltnDt

        # Creditor
        cdtr = ET.SubElement(pmtInf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = comp_name
        cdtrAcct = ET.SubElement(pmtInf, "CdtrAcct")
        cdtrId = ET.SubElement(cdtrAcct, "Id")
        ET.SubElement(cdtrId, "IBAN").text = creditor_iban.replace(" ", "")

        cdtrAgt = ET.SubElement(pmtInf, "CdtrAgt")
        cdtrFinInst = ET.SubElement(cdtrAgt, "FinInstnId")
        if comp.get("bic"):
            ET.SubElement(cdtrFinInst, "BIC").text = comp.get("bic")
        else:
            othr_c = ET.SubElement(cdtrFinInst, "Othr")
            ET.SubElement(othr_c, "Id").text = "NOTPROVIDED"

        cdtrSchmeId = ET.SubElement(pmtInf, "CdtrSchmeId")
        schmeId = ET.SubElement(cdtrSchmeId, "Id")
        prvtId = ET.SubElement(schmeId, "PrvtId")
        othr = ET.SubElement(prvtId, "Othr")
        ET.SubElement(othr, "Id").text = creditor_id
        schmeNm = ET.SubElement(othr, "SchmeNm")
        ET.SubElement(schmeNm, "Prtry").text = "SEPA"

        # Direct Debit Transaction Information
        drctDbtTxInf = ET.SubElement(pmtInf, "DrctDbtTxInf")
        pmtId = ET.SubElement(drctDbtTxInf, "PmtId")
        ET.SubElement(pmtId, "EndToEndId").text = f"E2E-{msg_id}"

        instdAmt = ET.SubElement(drctDbtTxInf, "InstdAmt", {"Ccy": "EUR"})
        instdAmt.text = f"{tot_gross:.2f}"

        drctDbtTx = ET.SubElement(drctDbtTxInf, "DrctDbtTx")
        mndtRltdInf = ET.SubElement(drctDbtTx, "MndtRltdInf")
        m_id = mandate_id or f"MND-{slug.upper()}-01"
        ET.SubElement(mndtRltdInf, "MndtId").text = m_id
        ET.SubElement(mndtRltdInf, "DtOfSgntr").text = batch.get("invoice_draft", {}).get("invoice_date", "2026-01-01")

        # Debtor
        dbtr = ET.SubElement(drctDbtTxInf, "Dbtr")
        ET.SubElement(dbtr, "Nm").text = cmanifest.get("client_name", slug)
        dbtrAcct = ET.SubElement(drctDbtTxInf, "DbtrAcct")
        dbtrId = ET.SubElement(dbtrAcct, "Id")
        ET.SubElement(dbtrId, "IBAN").text = debtor_iban.replace(" ", "")

        dbtrAgt = ET.SubElement(drctDbtTxInf, "DbtrAgt")
        dbtrFinInst = ET.SubElement(dbtrAgt, "FinInstnId")
        if debtor_bic:
            ET.SubElement(dbtrFinInst, "BIC").text = debtor_bic
        else:
            othr_dbtr = ET.SubElement(dbtrFinInst, "Othr")
            ET.SubElement(othr_dbtr, "Id").text = "NOTPROVIDED"

        rmtInf = ET.SubElement(drctDbtTxInf, "RmtInf")
        ET.SubElement(rmtInf, "Ustrd").text = f"Incasso Canone IT {batch.get('batch_id')} - {slug}"

        self._indent(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def check_dunning_status(self, target: str, reference_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Analizza lo scadenzario di tutte le fatture del cliente (se target è uno slug)
        oppure calcola direttamente il livello di sollecito per una data scadenza (se target è una data YYYY-MM-DD).
        Livelli:
        - LEVEL_0 / LEVEL_0_CURRENT: Pagamento regolare / Non scaduto.
        - LEVEL_1_REMINDER: Scaduta da 1 a 7 giorni (Promemoria cortese).
        - LEVEL_2_FORMAL_NOTICE / LEVEL_2_WARNING: Insoluto da 8 a 30 giorni (Sollecito formale).
        - LEVEL_3_LEGAL_ACTION / LEVEL_3_SUSPENSION: Insoluto > 30 giorni (Diffida con sospensione SLA).
        """
        ref_dt = datetime.date.fromisoformat(reference_date) if reference_date else datetime.date.today()

        # Se target è una data (formato YYYY-MM-DD)
        if len(target) == 10 and target[4] == "-" and target[7] == "-":
            due_date = datetime.date.fromisoformat(target)
            delta_days = (ref_dt - due_date).days
            if delta_days > 60:
                level = "LEVEL_3_LEGAL_ACTION"
                suspended = True
                action = "Inoltro pratica legale per recupero forzoso del credito. Fornitura e SLA sospesi."
            elif delta_days > 30:
                level = "LEVEL_3_LEGAL_ACTION"
                suspended = True
                action = "Diffida legale inviata. Erogazione SLA sospesa per morosita oltre 30 gg."
            elif delta_days >= 8:
                level = "LEVEL_2_FORMAL_NOTICE"
                suspended = False
                action = "Sollecito formale inviato. Avviso di possibile sospensione SLA."
            elif delta_days > 0:
                level = "LEVEL_1_REMINDER"
                suspended = False
                action = "Promemoria cortese scadenza inviato."
            else:
                level = "LEVEL_0"
                suspended = False
                action = "Fattura non ancora scaduta o regolare."

            return {
                "due_date": target,
                "reference_date": ref_dt.isoformat(),
                "days_overdue": max(0, delta_days),
                "dunning_level": level,
                "sla_suspended": suspended,
                "recommended_action": action
            }

        # Altrimenti target è uno slug cliente
        slug = target
        idir = self.get_invoices_dir(slug)
        if not idir.is_dir():
            return {"slug": slug, "dunning_level": "LEVEL_0", "sla_suspended": False, "overdue_installments": []}

        today = ref_dt
        overdue_installments = []
        max_overdue_days = 0

        for jf in idir.glob("*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    batch = json.load(f)
                scad = batch.get("scadenzario", {})
                for inst in scad.get("installments", []):
                    if inst.get("status") != "paid":
                        due_date_str = inst.get("due_date")
                        if due_date_str:
                            due_date = datetime.date.fromisoformat(due_date_str)
                            delta_days = (today - due_date).days
                            if delta_days > 0:
                                overdue_installments.append({
                                    "batch_id": batch.get("batch_id"),
                                    "installment_number": inst.get("number"),
                                    "due_date": due_date_str,
                                    "amount": inst.get("amount"),
                                    "days_overdue": delta_days
                                })
                                if delta_days > max_overdue_days:
                                    max_overdue_days = delta_days
            except Exception:
                pass

        if max_overdue_days > 60:
            level = "LEVEL_3_LEGAL_ACTION"
            suspended = True
            action = "Inoltro pratica legale per recupero forzoso del credito. Fornitura e SLA sospesi."
        elif max_overdue_days > 30:
            level = "LEVEL_3_LEGAL_ACTION"
            suspended = True
            action = "Diffida legale inviata. Erogazione SLA sospesa per morosita oltre 30 gg."
        elif max_overdue_days >= 8:
            level = "LEVEL_2_FORMAL_NOTICE"
            suspended = False
            action = "Sollecito formale inviato. Avviso di possibile sospensione SLA."
        elif max_overdue_days > 0:
            level = "LEVEL_1_REMINDER"
            suspended = False
            action = "Promemoria cortese scadenza inviato."
        else:
            level = "LEVEL_0"
            suspended = False
            action = "Posizione contabile regolare."

        return {
            "slug": slug,
            "dunning_level": level,
            "sla_suspended": suspended,
            "max_overdue_days": max_overdue_days,
            "recommended_action": action,
            "overdue_count": len(overdue_installments),
            "overdue_installments": overdue_installments
        }

    def create_invoice(
        self,
        slug: str,
        items: List[Dict[str, Any]],
        payment_terms: str = "bonifico_30gg",
        sdi_code: str = "0000000",
        invoice_number: Optional[str] = None
    ) -> Path:
        """Crea e salva un file fattura YAML per il cliente."""
        idir = self.clients_root / slug / "invoices"
        idir.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today()
        if not invoice_number:
            existing = list(idir.glob("fat-*.yaml"))
            seq = len(existing) + 1
            invoice_number = f"FAT-{today.year}-{seq:04d}"

        subtotal = sum(float(it.get("total", it.get("quantity", 1) * it.get("unit_price", 0.0))) for it in items)
        vat_rate = 22.0
        vat_amount = round(subtotal * (vat_rate / 100.0), 2)
        total_gross = round(subtotal + vat_amount, 2)

        inv_data = {
            "invoice_number": invoice_number,
            "invoice_date": today.isoformat(),
            "slug": slug,
            "status": "unpaid",
            "payment_terms": payment_terms,
            "sdi_code": sdi_code,
            "lines": items,
            "totals": {
                "subtotal_net": subtotal,
                "vat_amount": vat_amount,
                "total_gross": total_gross
            }
        }
        inv_file = idir / f"{invoice_number.lower()}.yaml"
        with open(inv_file, "w", encoding="utf-8") as fp:
            yaml.safe_dump(inv_data, fp, sort_keys=False, allow_unicode=True)
        return inv_file

    def reconcile_bank_statement(self, camt_xml_content_or_path: Any, auto_mark_paid: bool = True) -> Dict[str, Any]:
        """
        Riconcilia automaticamente i movimenti bancari da tracciato standard ISO 20022 CAMT.053.
        Interpreta gli accrediti (CRDT), estrae la causale libera (<RmtInf><Ustrd>) ed esegue il matching
        con le fatture aperte, aggiornando deterministicamente lo scadenzario con data incasso e ID transazione.
        """
        if isinstance(camt_xml_content_or_path, Path) or (isinstance(camt_xml_content_or_path, str) and ("\n" not in camt_xml_content_or_path and Path(camt_xml_content_or_path).is_file())):
            raw_xml = Path(camt_xml_content_or_path).read_text(encoding="utf-8")
        else:
            raw_xml = str(camt_xml_content_or_path)

        # Rimuove namespace per parsing agnostico e resiliente
        clean_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', raw_xml)
        root = ET.fromstring(clean_xml)

        matched = []
        unmatched = []
        total_reconciled = 0.0

        # Trova tutte le voci movimento Ntry
        for ntry in root.findall(".//Ntry"):
            amt_elem = ntry.find("Amt")
            amt = float(amt_elem.text) if amt_elem is not None and amt_elem.text else 0.0
            cdt_dbt = ntry.findtext("CdtDbtInd", "CRDT").strip().upper()

            # Riconciliamo solo entrate (CRDT)
            if cdt_dbt != "CRDT":
                continue

            dt_elem = ntry.find(".//BookgDt/Dt")
            if dt_elem is None:
                dt_elem = ntry.find(".//ValDt/Dt")
            tx_date = dt_elem.text.strip() if dt_elem is not None and dt_elem.text else datetime.date.today().isoformat()

            ustrd_elem = ntry.find(".//RmtInf/Ustrd")
            remittance = ustrd_elem.text.strip() if ustrd_elem is not None and ustrd_elem.text else ""

            dbtr_elem = ntry.find(".//Dbtr/Nm")
            debtor_name = dbtr_elem.text.strip() if dbtr_elem is not None and dbtr_elem.text else ""

            tx_id_elem = ntry.find(".//AcctSvcrRef")
            if tx_id_elem is None:
                tx_id_elem = ntry.find(".//EndToEndId")
            tx_id = tx_id_elem.text.strip() if tx_id_elem is not None and tx_id_elem.text else f"TX-CAMT-{int(datetime.datetime.now().timestamp())}"

            # Ricerca fattura/batch associato
            found_match = False
            for client_dir in self.clients_root.iterdir():
                if not client_dir.is_dir():
                    continue
                c_slug = client_dir.name
                idir = client_dir / "invoices"
                if not idir.is_dir():
                    continue

                # 1. Controlla file JSON batch fatturazione
                for jf in idir.glob("*.json"):
                    try:
                        with open(jf, "r", encoding="utf-8") as fp:
                            batch = json.load(fp)
                        bid = batch.get("batch_id", "")
                        inv_num = batch.get("invoice_draft", {}).get("invoice_number", "")
                        
                        # Match per numero fattura, batch_id o slug presente nella causale
                        matches_ref = (inv_num and inv_num.lower() in remittance.lower()) or \
                                      (bid and bid.lower() in remittance.lower()) or \
                                      (c_slug in remittance.lower())

                        if matches_ref:
                            # Controlla importo rata
                            scad = batch.get("scadenzario", {})
                            for inst in scad.get("installments", []):
                                if inst.get("status") != "paid":
                                    inst_amt = float(inst.get("amount", 0.0))
                                    # Tolleranza centesimi
                                    if abs(inst_amt - amt) < 0.05 or abs(float(batch.get("invoice_draft", {}).get("totals", {}).get("total_gross", 0.0)) - amt) < 0.05:
                                        if auto_mark_paid:
                                            self.mark_installment_paid(
                                                slug=c_slug,
                                                batch_id=bid,
                                                installment_num=inst.get("number", 1),
                                                tx_id=tx_id
                                            )
                                        matched.append({
                                            "slug": c_slug,
                                            "batch_id": bid,
                                            "invoice_number": inv_num,
                                            "installment_number": inst.get("number", 1),
                                            "amount": amt,
                                            "tx_id": tx_id,
                                            "date": tx_date,
                                            "debtor_name": debtor_name,
                                            "remittance": remittance
                                        })
                                        total_reconciled += amt
                                        found_match = True
                                        break
                        if found_match:
                            break
                    except Exception:
                        pass
                if found_match:
                    break

                # 2. Controlla file YAML singole fatture
                for yf in idir.glob("*.yaml"):
                    try:
                        with open(yf, "r", encoding="utf-8") as fp:
                            inv_data = yaml.safe_load(fp) or {}
                        inv_num = inv_data.get("invoice_number", "")
                        if inv_num and inv_num.lower() in remittance.lower():
                            if inv_data.get("status") != "paid":
                                if auto_mark_paid:
                                    inv_data["status"] = "paid"
                                    inv_data["payment_date"] = tx_date
                                    inv_data["payment_reference"] = f"CAMT053-RECONCILED-{tx_id}"
                                    with open(yf, "w", encoding="utf-8") as fp:
                                        yaml.safe_dump(inv_data, fp, sort_keys=False, allow_unicode=True)
                                matched.append({
                                    "slug": c_slug,
                                    "invoice_number": inv_num,
                                    "amount": amt,
                                    "tx_id": tx_id,
                                    "date": tx_date,
                                    "debtor_name": debtor_name,
                                    "remittance": remittance
                                })
                                total_reconciled += amt
                                found_match = True
                                break
                    except Exception:
                        pass
                if found_match:
                    break

            if not found_match:
                unmatched.append({
                    "amount": amt,
                    "date": tx_date,
                    "debtor_name": debtor_name,
                    "remittance": remittance,
                    "tx_id": tx_id
                })

        return {
            "status": "success",
            "total_entries": len(matched) + len(unmatched),
            "matched_entries_count": len(matched),
            "unmatched_entries_count": len(unmatched),
            "reconciled_count": len(matched),
            "reconciled_invoices": matched,
            "total_reconciled_amount": round(total_reconciled, 2),
            "matched": matched,
            "unmatched": unmatched
        }

    @staticmethod
    def _indent(elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                BillingPipeline._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
