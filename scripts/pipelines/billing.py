import datetime
import json
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir, load_config
from scripts.pipelines.contracts import ContractsPipeline
from scripts.pipelines.reports import ReportsPipeline

class BillingPipeline:
    """Pipeline C: Fatturazione Elettronica SDI & Scadenzario Attivo."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()

    def get_invoices_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "invoices"

    def aggregate_monthly_batch(self, slug: str, period: Optional[str] = None) -> Dict[str, Any]:
        """Aggrega canoni, rapportini spot ed eventuali voci MPS per la fatturazione."""
        if not period:
            period = datetime.date.today().strftime("%Y-%m")

        contracts_pipe = ContractsPipeline(self.clients_root)
        reports_pipe = ReportsPipeline(self.clients_root)

        contracts = contracts_pipe.list_contracts(slug)
        reports_summary = reports_pipe.get_ledger_summary(slug)

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
            hourly_rate = 75.0 # Default o preso da contratto
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

        subtotal = round(sum(l["total_line"] for l in lines), 2)
        vat_amount = round(subtotal * (vat_rate / 100.0), 2)
        total_gross = round(subtotal + vat_amount, 2)

        batch_id = f"BILL-{period.replace('-', '')}-{slug}"
        batch = {
            "batch_id": batch_id,
            "slug": slug,
            "period": period,
            "status": "draft",
            "invoice_draft": {
                "invoice_number": f"DRAFT-{batch_id}",
                "invoice_date": datetime.date.today().isoformat(),
                "payment_method": "MP05", # Bonifico Bancario
                "lines": lines,
                "totals": {
                    "subtotal_net": subtotal,
                    "vat_amount": vat_amount,
                    "total_gross": total_gross
                }
            },
            "scadenzario": {
                "overall_status": "open",
                "installments": [
                    {
                        "number": 1,
                        "due_date": (datetime.date.today() + datetime.timedelta(days=60)).isoformat(),
                        "amount": total_gross,
                        "status": "unpaid"
                    }
                ]
            }
        }
        return batch

    def generate_sdi_xml_preview(self, batch: Dict[str, Any]) -> str:
        """Genera anteprima tracciato XML FatturaPA/SDI (v1.2)."""
        root = ET.Element("p:FatturaElettronica", {
            "versione": "FPR12",
            "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
        })

        header = ET.SubElement(root, "FatturaElettronicaHeader")
        dati_trasm = ET.SubElement(header, "DatiTrasmissione")
        id_trasm = ET.SubElement(dati_trasm, "IdTrasmittente")
        ET.SubElement(id_trasm, "IdPaese").text = "IT"
        ET.SubElement(id_trasm, "IdCodice").text = self.config.get("company", {}).get("fiscal_code", "01234567890")
        ET.SubElement(dati_trasm, "FormatoTrasmissione").text = "FPR12"
        ET.SubElement(dati_trasm, "CodiceDestinatario").text = self.config.get("company", {}).get("sdi_code", "0000000")

        body = ET.SubElement(root, "FatturaElettronicaBody")
        dati_gen = ET.SubElement(body, "DatiGenerali")
        dati_doc = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
        ET.SubElement(dati_doc, "TipoDocumento").text = "TD01"
        ET.SubElement(dati_doc, "Divisa").text = self.config.get("company", {}).get("currency", "EUR")
        ET.SubElement(dati_doc, "Data").text = batch.get("invoice_draft", {}).get("invoice_date", "")
        ET.SubElement(dati_doc, "ImportoTotaleDocumento").text = f"{batch.get('invoice_draft', {}).get('totals', {}).get('total_gross', 0.0):.2f}"

        dati_beni = ET.SubElement(body, "DatiBeniServizi")
        for i, line in enumerate(batch.get("invoice_draft", {}).get("lines", []), start=1):
            dett = ET.SubElement(dati_beni, "DettaglioLinee")
            ET.SubElement(dett, "NumeroLinea").text = str(i)
            ET.SubElement(dett, "Descrizione").text = line.get("description", "")
            ET.SubElement(dett, "Quantita").text = f"{line.get('quantity', 1):.2f}"
            ET.SubElement(dett, "PrezzoUnitario").text = f"{line.get('unit_price', 0.0):.2f}"
            ET.SubElement(dett, "PrezzoTotale").text = f"{line.get('total_line', 0.0):.2f}"
            ET.SubElement(dett, "AliquotaIVA").text = f"{line.get('vat_rate', 22.0):.2f}"

        return ET.tostring(root, encoding="utf-8").decode("utf-8")
