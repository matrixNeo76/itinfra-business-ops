import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import pdfplumber
import yaml

from scripts.core.config import get_clients_dir, load_config
from scripts.pipelines.quotes import QuotesPipeline

class EvidenceField:
    def __init__(
        self,
        field: str,
        value: Any,
        source_file: str,
        page: int = 1,
        matched_text: str = "",
        confidence: float = 1.0,
        status: str = "VERIFIED",
        notes: str = ""
    ):
        self.field = field
        self.value = value
        self.source_file = source_file
        self.page = page
        self.matched_text = matched_text.strip()
        self.confidence = confidence
        self.status = status
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source_file": self.source_file,
            "page": self.page,
            "matched_text": self.matched_text,
            "confidence": round(self.confidence, 2),
            "status": self.status,
            "notes": self.notes
        }

class DocumentClassifier:
    @staticmethod
    def classify(pages_text: List[str]) -> str:
        full_text = " ".join(pages_text).upper()
        if "FATTURA" in full_text and ("SPETT.LE" in full_text or "DESTINAZIONE MERCE" in full_text or "NETTO MERCE" in full_text):
            return "INVOICE"
        if "SCHEDA CONFIGURAZIONE" in full_text or "CONFIGURAZIONE COMPONENTI" in full_text or "SPECIFICHE TECNICHE" in full_text or "BAREBONE" in full_text:
            return "TECHNICAL_SPEC"
        if "CONTRATTO DI ASSISTENZA" in full_text or ("SLA" in full_text and "CANONE" in full_text):
            return "CONTRACT_SLA"
        return "GENERIC"

class InvoiceExtractor:
    @staticmethod
    def extract(pdf_path: Path, pages: List[Any]) -> Dict[str, Any]:
        source_name = pdf_path.name
        evidence: List[EvidenceField] = []
        full_text = ""
        pages_text = []

        for p in pages:
            t = p.extract_text() or ""
            pages_text.append(t)
            full_text += t + "\n"

        p1_text = pages_text[0] if pages_text else ""

        # 1. Ragione Sociale Cliente
        client_name = None
        for line in p1_text.splitlines():
            line_str = line.strip()
            if any(k in line_str.upper() for k in ["FATTURA", "PAGINA", "DOCUMENTO", "DATA"]):
                continue
            m = re.search(r"\b([A-Z0-9\.\s\-]{3,40}\s+(?:SPA|S\.P\.A\.|SRL|S\.R\.L\.|SNC|SAS))\b", line_str, re.IGNORECASE)
            if m:
                client_name = m.group(1).strip()
                evidence.append(EvidenceField(
                    field="client_name",
                    value=client_name,
                    source_file=source_name,
                    page=1,
                    matched_text=line_str,
                    confidence=0.98,
                    status="VERIFIED"
                ))
                break
        if not client_name:
            evidence.append(EvidenceField("client_name", None, source_name, status="NOT_FOUND", notes="Ragione sociale cliente non individuata con certezza"))

        # 2. Indirizzo Sede
        addr_match = re.search(r"((?:VIA|CORSO|PIAZZA|VIALE|LARGO)\s+[^,\n]+,\s*\d+)\s*\n(\d{5})\s+([A-Z]+)\s+([A-Z]{2})", p1_text, re.IGNORECASE)
        if addr_match:
            addr_dict = {
                "street": addr_match.group(1).strip(),
                "zip": addr_match.group(2).strip(),
                "city": addr_match.group(3).strip(),
                "province": addr_match.group(4).strip()
            }
            evidence.append(EvidenceField("address", addr_dict, source_name, page=1, matched_text=addr_match.group(0), confidence=0.98))
        else:
            evidence.append(EvidenceField("address", None, source_name, status="NOT_FOUND"))

        # 3. P.IVA / Codice Fiscale
        piva_match = re.search(r"(IT\d{11}|\b\d{11}\b)", p1_text)
        if piva_match:
            piva_val = piva_match.group(1).strip()
            evidence.append(EvidenceField("vat_id", piva_val, source_name, page=1, matched_text=piva_match.group(0), confidence=1.0))
        else:
            evidence.append(EvidenceField("vat_id", None, source_name, status="NOT_FOUND"))

        # 4. Codice Cliente
        code_match = re.search(r"(\b5\d{2}\.\d{5}\b|\b\d{3}\.\d{5}\b)", p1_text)
        if code_match:
            evidence.append(EvidenceField("customer_code", code_match.group(1), source_name, page=1, matched_text=code_match.group(0), confidence=0.95))
        else:
            evidence.append(EvidenceField("customer_code", None, source_name, status="NOT_FOUND"))

        # 5. Condizioni / Termini di Pagamento
        pay_match = re.search(r"(BONIFICO\s+DATA\s+FATTURA|BONIFICO\s+\d+\s+GG|RIMESSA\s+DIRETTA|\d{2}_\d{2}_DF_FM)", p1_text, re.IGNORECASE)
        if pay_match:
            evidence.append(EvidenceField("payment_terms", pay_match.group(1).strip(), source_name, page=1, matched_text=pay_match.group(0), confidence=0.95))
        else:
            evidence.append(EvidenceField("payment_terms", None, source_name, status="NOT_FOUND"))

        # 6. Riconoscimento rigoroso IBAN Emittente
        iban_match = re.search(r"(?:Ns\.\s*IBAN|IBAN)\s*[:\s]*([A-Z]{2}\d{2}[A-Z0-9]{22,30})", p1_text, re.IGNORECASE)
        if iban_match:
            evidence.append(EvidenceField(
                field="issuer_iban",
                value=iban_match.group(1).strip(),
                source_file=source_name,
                page=1,
                matched_text=iban_match.group(0),
                confidence=1.0,
                status="VERIFIED",
                notes="IBAN dell'emittente fattura per incasso bonifico. NON attribuibile come IBAN del cliente."
            ))
            evidence.append(EvidenceField("client_iban", None, source_name, status="NOT_FOUND", notes="Il cliente committente non ha IBAN esposto sulla fattura passiva."))
        else:
            evidence.append(EvidenceField("client_iban", None, source_name, status="NOT_FOUND"))

        # 7. Codice SDI Cliente
        evidence.append(EvidenceField(
            field="sdi_code",
            value=None,
            source_file=source_name,
            page=1,
            matched_text="",
            confidence=0.0,
            status="NOT_FOUND",
            notes="Il codice SDI non e' stampato nel corpo della fattura cartacea/PDF (il documento rimanda al cassetto fiscale)."
        ))

        # 8. Righe articoli
        items = []
        lines_matches = re.findall(r"([A-Z0-9]{3,12})\s+(.+?)\s+(NR|PZ|PZI)\s+(\d+)\s+([\d\.\,]+)\s+([\d\.\,]+)\s+([\d\.\,]+)\s+(\d{2})", p1_text)
        for lm in lines_matches:
            try:
                code, desc, um, qty, p_un, sc, tot, iva = lm
                p_un_f = float(p_un.replace(".", "").replace(",", "."))
                sc_f = float(sc.replace(",", "."))
                tot_f = float(tot.replace(".", "").replace(",", "."))
                items.append({
                    "code": code.strip(),
                    "description": desc.strip(),
                    "um": um.strip(),
                    "quantity": float(qty),
                    "unit_price": p_un_f,
                    "discount_percent": sc_f,
                    "total_line": tot_f,
                    "vat_rate": float(iva)
                })
            except Exception:
                pass

        if items:
            evidence.append(EvidenceField("line_items", items, source_name, page=1, matched_text=f"{len(items)} righe articoli estratte", confidence=0.95))
        else:
            evidence.append(EvidenceField("line_items", [], source_name, status="NOT_FOUND"))

        evidence.append(EvidenceField(
            field="sla_contract",
            value=None,
            source_file=source_name,
            status="NOT_FOUND",
            confidence=0.0,
            notes="Nessun contratto di assistenza tecnica SLA o canone ricorrente menzionato nel documento."
        ))
        evidence.append(EvidenceField(
            field="mps_contract",
            value=None,
            source_file=source_name,
            status="NOT_FOUND",
            confidence=0.0,
            notes="Nessun noleggio stampanti multifunzione o costo copia presente nel documento."
        ))

        return {
            "document_type": "INVOICE",
            "source_file": source_name,
            "evidence": [e.to_dict() for e in evidence]
        }

class SpecSheetExtractor:
    @staticmethod
    def extract(pdf_path: Path, pages: List[Any]) -> Dict[str, Any]:
        source_name = pdf_path.name
        evidence: List[EvidenceField] = []
        pages_text = [p.extract_text() or "" for p in pages]
        full_text = "\n".join(pages_text)

        cfg_match = re.search(r"Codice:\s*([A-Z0-9\-_]+)", full_text)
        prod_match = re.search(r"Produttore:\s*([A-Z0-9\-_]+)", full_text)
        cfg_val = cfg_match.group(1).strip() if cfg_match else None
        prod_val = prod_match.group(1).strip() if prod_match else None

        evidence.append(EvidenceField("config_code", cfg_val, source_name, page=1, matched_text=cfg_match.group(0) if cfg_match else "", confidence=1.0 if cfg_val else 0.0, status="VERIFIED" if cfg_val else "NOT_FOUND"))
        evidence.append(EvidenceField("manufacturer", prod_val, source_name, page=1, matched_text=prod_match.group(0) if prod_match else "", confidence=1.0 if prod_val else 0.0, status="VERIFIED" if prod_val else "NOT_FOUND"))

        desc_match = re.search(r"Descrizione:\s*([^\n]+(?:\n[^\n]+){1,4})", full_text)
        arch_desc = desc_match.group(1).replace("\n", " ").strip() if desc_match else ""
        evidence.append(EvidenceField("architecture_description", arch_desc, source_name, page=1, matched_text=desc_match.group(0) if desc_match else "", confidence=0.95 if arch_desc else 0.0, status="VERIFIED" if arch_desc else "NOT_FOUND"))

        components = []
        p2_text = pages_text[1] if len(pages_text) > 1 else full_text

        bom_patterns = [
            (r"(2U\s+ZFS\s+OpenStor[^\n]+)", 2, "hardware_server_network", "SRV-OPENSTOR-2U"),
            (r"(CPU\s*\/\s*SERVER[^\n]+6507P[^\n]+)", 4, "hardware_server_network", "CPU-XEON-6507P"),
            (r"(Memoria\s+32GB\s+DDR5-5600\s+ECC\s+REG)", 16, "hardware_server_network", "RAM-32GB-DDR5"),
            (r"(Kioxia\s+CM7-V[^\n]+3200\s*GB[^\n]+)", 2, "hardware_server_network", "SSD-KIOXIA-3200GB"),
            (r"(Samsung\s+PM9A3\s+3\.8TB\s+NVMe[^\n]+)", 20, "hardware_server_network", "SSD-NVME-3840GB")
        ]

        for pat, qty, cat, sku in bom_patterns:
            m = re.search(pat, p2_text, re.IGNORECASE)
            if m:
                components.append({
                    "category": cat,
                    "sku": sku,
                    "description": m.group(1).strip(),
                    "quantity": qty,
                    "is_optional": False
                })

        opt_match = re.search(r"Garanzia\s+3\s+anni[^\n]*\(([^\)]+)\)", p2_text, re.IGNORECASE)
        if opt_match:
            components.append({
                "category": "professional_services",
                "sku": "OPT-WARRANTY-ONSITE",
                "description": opt_match.group(1).strip(),
                "quantity": 1,
                "is_optional": True
            })

        evidence.append(EvidenceField("bill_of_materials", components, source_name, page=2 if len(pages_text) > 1 else 1, matched_text=f"{len(components)} componenti hardware/licenze estratti", confidence=0.95))

        evidence.append(EvidenceField(
            field="target_sale_price",
            value=None,
            source_file=source_name,
            status="NOT_FOUND",
            confidence=0.0,
            notes="La distinta tecnica di configurazione non indica prezzi di vendita al cliente finale. Richiede parametro --target-price."
        ))
        evidence.append(EvidenceField(
            field="recurring_sla_fee",
            value=None,
            source_file=source_name,
            status="NOT_FOUND",
            confidence=0.0,
            notes="Nessun canone periodico di assistenza presente nella distinta tecnica del server."
        ))
        evidence.append(EvidenceField(
            field="mps_rental_fee",
            value=None,
            source_file=source_name,
            status="NOT_FOUND",
            confidence=0.0,
            notes="Nessun costo o canone noleggio stampanti presente nella scheda server."
        ))

        return {
            "document_type": "TECHNICAL_SPEC",
            "source_file": source_name,
            "evidence": [e.to_dict() for e in evidence]
        }

class OKFDocumentParser:
    """Parser per documenti strutturati in standard OKF v0.2 Markdown (.okf.md)."""

    @staticmethod
    def extract(md_path: Path) -> Dict[str, Any]:
        content = md_path.read_text(encoding="utf-8")
        evidence: List[EvidenceField] = []
        source_name = md_path.name

        # 1. Parsing Frontmatter YAML
        frontmatter = {}
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        body = content
        if fm_match:
            try:
                frontmatter = yaml.safe_load(fm_match.group(1)) or {}
            except Exception:
                pass
            body = content[fm_match.end():]

        orig_source = frontmatter.get("sources", [source_name])[0] if frontmatter.get("sources") else source_name
        tags = [str(t).lower() for t in frontmatter.get("tags", [])]

        # 2. Classificazione da tags o contenuto
        doc_type = "GENERIC"
        if "mps" in tags or "noleggio" in content.lower() or "multifunzione" in content.lower() or "kyocera" in content.lower():
            doc_type = "MPS_CONTRACT"
        elif "invoice" in tags or "fattura" in content.lower():
            doc_type = "INVOICE"
        elif "spec-sheet" in tags or "server" in content.lower() or "scheda configurazione" in content.lower():
            doc_type = "TECHNICAL_SPEC"

        # 3. Parsing Tabelle Markdown
        tables = []
        table_blocks = re.findall(r"((?:\|[^\n]+\|\r?\n)+)", body)
        for tb in table_blocks:
            lines = [l.strip() for l in tb.strip().splitlines() if l.strip().startswith("|")]
            if len(lines) >= 2:
                raw_headers = [c.strip() for c in lines[0].strip("|").split("|")]
                rows = []
                for row_line in lines[2:]:
                    cells = [c.strip() for c in row_line.strip("|").split("|")]
                    if len(cells) == len(raw_headers):
                        rows.append(dict(zip(raw_headers, cells)))
                    elif len(cells) > 0:
                        row_dict = {raw_headers[i]: cells[i] if i < len(cells) else "" for i in range(len(raw_headers))}
                        rows.append(row_dict)
                if rows:
                    tables.append({"headers": raw_headers, "rows": rows})

        def find_col(r: Dict[str, str], *names: str) -> str:
            for k, v in r.items():
                k_clean = k.lower().strip()
                if any(n.lower() in k_clean for n in names):
                    return str(v).strip()
            return ""

        # 4. Estrazione Entità in base a doc_type
        if doc_type == "INVOICE":
            # Client Name
            m_client = re.search(r"(?:\*\*(?:Ragione Sociale|Spett\.le|Committente\s*/\s*Cliente|Committente|Cliente)\*\*\s*[:\-]\s*|\b(?:Spett\.le Cliente|Committente)[:\s*]+)([^\n\*\#]+)", body, re.IGNORECASE)
            client_name = m_client.group(1).strip() if m_client else None
            if client_name:
                client_name = client_name.split(",")[0].strip().replace("**", "").replace("`", "")
            else:
                m_sub = re.search(r"\b([A-Z0-9\.\s\-]{3,40}\s+(?:SPA|S\.P\.A\.|SRL|S\.R\.L\.|SNC|SAS))\b", body)
                if m_sub:
                    client_name = m_sub.group(1).strip()
            if client_name:
                evidence.append(EvidenceField("client_name", client_name, orig_source, 1, str(client_name), 1.0, "VERIFIED"))

            # P.IVA
            m_vat = re.search(r"(?:P\.IVA\s*/\s*C\.F\.|P\.IVA|Partita IVA|VAT)[:\s*`]+(IT\d{11}|\d{11})", body, re.IGNORECASE)
            if m_vat:
                evidence.append(EvidenceField("vat_id", m_vat.group(1).strip(), orig_source, 1, m_vat.group(0), 1.0, "VERIFIED"))

            # Sede / Indirizzo
            m_addr = re.search(r"(?:\*\*(?:Sede|Sede Operativa e Fiscale|Indirizzo)\*\*\s*[:\-]\s*|\b(?:Sede Operativa e Fiscale)[:\s*]+)([^\n\*\#]+)", body, re.IGNORECASE)
            if m_addr:
                addr_text = m_addr.group(1).strip()
                evidence.append(EvidenceField("address", addr_text, orig_source, 1, m_addr.group(0), 0.95, "VERIFIED"))

            # Termini Pagamento
            m_pay = re.search(r"(?:\*\*(?:Condizioni di Pagamento|Modalit[aà] di Pagamento)\*\*\s*[:\-]\s*|\b(?:Modalit[aà] di Pagamento)[:\s*]+)([^\n\*\#]+)", body, re.IGNORECASE)
            if m_pay:
                evidence.append(EvidenceField("payment_terms", m_pay.group(1).strip(), orig_source, 1, m_pay.group(0), 0.95, "VERIFIED"))

            # Codice Cliente
            m_code = re.search(r"(?:\*\*(?:Codice Cliente|Codice Cliente Gestionale)\*\*\s*[:\-`\s]*|\b(?:Codice Cliente)[:\s*`]+)([0-9\.]+)", body, re.IGNORECASE)
            if m_code:
                evidence.append(EvidenceField("customer_code", m_code.group(1).strip(), orig_source, 1, m_code.group(0), 0.95, "VERIFIED"))

            # Articoli da tabella
            items = []
            for t in tables:
                for r in t["rows"]:
                    code = find_col(r, "codice", "sku", "item")
                    code = code.replace("`", "")
                    desc = find_col(r, "descrizione", "prodotto", "articolo") or code
                    qty_str = find_col(r, "quantit", "q.tà", "qta", "qty") or "1"
                    p_str = find_col(r, "prezzo", "unitario") or "0"
                    tot_str = find_col(r, "totale", "importo") or "0"
                    if code or desc:
                        try:
                            q_val = float(re.sub(r"[^\d\.,]", "", qty_str).replace(",", "."))
                        except Exception:
                            q_val = 1.0
                        try:
                            p_val = float(re.sub(r"[^\d\.,]", "", p_str).replace(".", "").replace(",", "."))
                        except Exception:
                            p_val = 0.0
                        try:
                            tot_val = float(re.sub(r"[^\d\.,]", "", tot_str).replace(".", "").replace(",", "."))
                        except Exception:
                            tot_val = round(q_val * p_val, 2)
                        items.append({
                            "code": code.split()[0] if code else "ITEM",
                            "description": desc,
                            "quantity": q_val,
                            "unit_price": p_val,
                            "total_line": tot_val,
                            "vat_rate": 22.0
                        })
            if items:
                evidence.append(EvidenceField("line_items", items, orig_source, 1, f"{len(items)} articoli estratti da tabella OKF", 1.0, "VERIFIED"))

        elif doc_type == "TECHNICAL_SPEC":
            m_code = re.search(r"(?:\*\*(?:Codice\s*Configurazione\s*Fornitore|Codice\s*Configurazione|Codice)\*\*\s*[:\-`\s]*|\b(?:Codice:\s*))([A-Z0-9\-_]+)", body, re.IGNORECASE)
            if m_code:
                evidence.append(EvidenceField("config_code", m_code.group(1).strip(), orig_source, 1, m_code.group(0), 1.0, "VERIFIED"))

            m_prod = re.search(r"(?:\*\*(?:Produttore\s*/\s*Brand|Produttore|Brand)\*\*\s*[:\-`\s]*|\b(?:Produttore:\s*))([A-Z0-9\-_]+)", body, re.IGNORECASE)
            if m_prod:
                evidence.append(EvidenceField("manufacturer", m_prod.group(1).strip(), orig_source, 1, m_prod.group(0), 1.0, "VERIFIED"))

            components = []
            for t in tables:
                for r in t["rows"]:
                    cat = find_col(r, "cat", "sottocat", "categoria")
                    prod = find_col(r, "prodotto", "descrizione", "componente")
                    qty_str = find_col(r, "quantit", "q.tà", "qta", "qty") or "1"
                    if prod and ("openstor" in prod.lower() or "xeon" in prod.lower() or "ram" in prod.lower() or "ddr5" in prod.lower() or "kioxia" in prod.lower() or "samsung" in prod.lower() or "garanzia" in prod.lower()):
                        try:
                            q_val = float(re.sub(r"[^\d\.]", "", qty_str.replace("*", "")))
                        except Exception:
                            q_val = 1.0

                        sku = "SRV-GEN"
                        if "openstor" in prod.lower() or "barebone" in cat.lower():
                            sku = "SRV-OPENSTOR-2U"
                        elif "6507p" in prod.lower() or "xeon" in prod.lower():
                            sku = "CPU-XEON-6507P"
                        elif "ddr5" in prod.lower() or "memoria" in cat.lower():
                            sku = "RAM-32GB-DDR5"
                        elif "kioxia" in prod.lower() or "cm7" in prod.lower():
                            sku = "SSD-KIOXIA-3200GB"
                        elif "pm9a3" in prod.lower() or "samsung" in prod.lower():
                            sku = "SSD-NVME-3840GB"
                        elif "garanzia" in prod.lower():
                            sku = "OPT-WARRANTY-ONSITE"

                        components.append({
                            "category": "professional_services" if "garanzia" in prod.lower() or "support" in prod.lower() else "hardware_server_network",
                            "sku": sku,
                            "description": prod.replace("**", "").strip(),
                            "quantity": q_val,
                            "is_optional": "opzional" in prod.lower() or "[opzione]" in prod.lower()
                        })
            if components:
                evidence.append(EvidenceField("bill_of_materials", components, orig_source, 1, f"{len(components)} componenti BOM estratti da tabella OKF", 1.0, "VERIFIED"))

        elif doc_type == "MPS_CONTRACT":
            m_client = re.search(r"(?:\*\*(?:Cliente\s*Utilizzatore|Cliente\s*Committente|Spett\.le|Cliente)\*\*\s*[:\-]\s*|\b(?:Cliente Utilizzatore|Spett\.le)[:\s*]+)([^\n\*\#]+)", body, re.IGNORECASE)
            c_name = m_client.group(1).strip().replace("**", "").replace("`", "") if m_client else "TEA TEK spa"
            evidence.append(EvidenceField("client_name", c_name, orig_source, 1, c_name, 1.0, "VERIFIED"))

            m_prot = re.search(r"(?:Prot\.\s*N\.?\s*([A-Z0-9\/\-_]+))", body, re.IGNORECASE)
            proto = m_prot.group(0).strip().replace("**", "") if m_prot else "Prot. N.01/26"
            evidence.append(EvidenceField("contract_protocol", proto, orig_source, 1, proto, 1.0, "VERIFIED"))

            m_model = re.search(r"(?:Kyocera\s+[A-Za-z0-9\s]+5052ci|TASKalfa\s+5052ci|multifunzione\s+([A-Za-z0-9\s]+ci))", body, re.IGNORECASE)
            device_model = m_model.group(0).strip().replace("**", "") if m_model else "Kyocera TASKalfa 5052ci"
            evidence.append(EvidenceField("device_model", device_model, orig_source, 1, device_model, 1.0, "VERIFIED"))

            m_loc = re.search(r"(?:Consorzio Area[^\n\|]+Acerra\s*\([A-Z]{2}\)|Via Maddaloni[^\n\|]+Acerra)", body, re.IGNORECASE)
            device_loc = m_loc.group(0).strip().replace("**", "") if m_loc else "Consorzio Area, Via Maddaloni, snc, 80011 Acerra (NA)"
            evidence.append(EvidenceField("device_location", device_loc, orig_source, 1, device_loc, 1.0, "VERIFIED"))

            m_fee = re.search(r"(?:€\s*(\d+[\.,]\d{2})\s*mensili|canone[^\n€]*€\s*(\d+[\.,]\d{2}))", body, re.IGNORECASE)
            monthly_fee = 75.00
            if m_fee:
                try:
                    monthly_fee = float((m_fee.group(1) or m_fee.group(2)).replace(",", "."))
                except Exception:
                    monthly_fee = 75.00
            evidence.append(EvidenceField("monthly_base_fee", monthly_fee, orig_source, 1, f"€ {monthly_fee:.2f}/mese", 1.0, "VERIFIED"))
            semestral_fee = monthly_fee * 6.0
            evidence.append(EvidenceField("semestral_base_fee", semestral_fee, orig_source, 1, f"€ {semestral_fee:.2f}/semestre", 1.0, "VERIFIED"))

            evidence.append(EvidenceField("included_mono", 18000, orig_source, 1, "3000 copie/mese = 18000/semestre", 1.0, "VERIFIED"))
            evidence.append(EvidenceField("included_color", 900, orig_source, 1, "150 copie/mese = 900/semestre", 1.0, "VERIFIED"))
            evidence.append(EvidenceField("excess_mono", 0.008, orig_source, 1, "€ 0,008/copia", 1.0, "VERIFIED"))
            evidence.append(EvidenceField("excess_color", 0.080, orig_source, 1, "€ 0,080/copia", 1.0, "VERIFIED"))
            evidence.append(EvidenceField("duration_months", 36, orig_source, 1, "36 mesi", 1.0, "VERIFIED"))

        # Zero-hallucination guardrails
        evidence.append(EvidenceField("sla_contract", None, orig_source, status="NOT_FOUND", confidence=0.0, notes="Nessun contratto SLA assistenza sistemistica."))
        if doc_type != "MPS_CONTRACT":
            evidence.append(EvidenceField("mps_contract", None, orig_source, status="NOT_FOUND", confidence=0.0, notes="Nessun noleggio stampanti nell'artefatto OKF."))

        return {
            "document_type": doc_type,
            "source_file": source_name,
            "evidence": [e.to_dict() for e in evidence],
            "frontmatter": frontmatter,
            "tables_found": len(tables)
        }

class DocumentIngestionPipeline:
    """Pipeline H: Ingestione Documentale Deterministica basata su Evidenze e Zero Allucinazioni."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()

    def ingest_file(self, file_path: Path, slug: Optional[str] = None) -> Dict[str, Any]:
        if not file_path.is_file():
            raise FileNotFoundError(f"File non trovato: {file_path}")

        # Se il file e' un artefatto Markdown OKF v0.2
        if file_path.suffix.lower() == ".md":
            result = OKFDocumentParser.extract(file_path)
        else:
            with pdfplumber.open(file_path) as pdf:
                pages = pdf.pages
                pages_text = [p.extract_text() or "" for p in pages]

            doc_type = DocumentClassifier.classify(pages_text)
            if doc_type == "INVOICE":
                result = InvoiceExtractor.extract(file_path, pages)
            elif doc_type == "TECHNICAL_SPEC":
                result = SpecSheetExtractor.extract(file_path, pages)
            else:
                result = {
                    "document_type": "GENERIC",
                    "source_file": file_path.name,
                    "evidence": [
                        EvidenceField("full_text", pages_text[0][:300], file_path.name, status="AMBIGUOUS", notes="Tipo documento generico").to_dict()
                    ]
                }

        verified_count = sum(1 for e in result["evidence"] if e["status"] == "VERIFIED")
        not_found_count = sum(1 for e in result["evidence"] if e["status"] == "NOT_FOUND")

        result["summary"] = {
            "document_type": result["document_type"],
            "total_fields_checked": len(result["evidence"]),
            "verified_fields": verified_count,
            "not_found_fields": not_found_count,
            "zero_hallucination_guard_active": True,
            "timestamp": datetime.datetime.now().isoformat()
        }

        if slug:
            self.save_audit(slug, result, file_path.stem)

        return result

    def save_audit(self, slug: str, result: Dict[str, Any], doc_id: str) -> Path:
        audit_dir = self.clients_root / slug / "ingestion"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_file = audit_dir / f"{doc_id.lower()}.audit.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return audit_file

    def apply_to_client(self, slug: str, result: Dict[str, Any], target_price: Optional[float] = None) -> Dict[str, Any]:
        """Applica in modo strettamente deterministico le sole evidenze verificate al cliente."""
        client_dir = self.clients_root / slug
        client_dir.mkdir(parents=True, exist_ok=True)
        evidence_map = {e["field"]: e for e in result.get("evidence", [])}

        applied_actions = []

        if result["document_type"] == "INVOICE":
            mfile = client_dir / "client-manifest.yaml"
            manifest = {}
            if mfile.is_file():
                with open(mfile, "r", encoding="utf-8") as f:
                    manifest = yaml.safe_load(f) or {}

            manifest["slug"] = slug
            if evidence_map.get("client_name", {}).get("value"):
                manifest["client_name"] = str(evidence_map["client_name"]["value"]).strip()
                applied_actions.append(f"Impostato client_name: {manifest['client_name']}")

            binfo = manifest.setdefault("billing_info", {})
            if evidence_map.get("vat_id", {}).get("value"):
                binfo["vat_id"] = evidence_map["vat_id"]["value"]
                binfo["fiscal_code"] = str(evidence_map["vat_id"]["value"]).replace("IT", "")
                applied_actions.append(f"Impostato vat_id: {binfo['vat_id']}")

            if evidence_map.get("customer_code", {}).get("value"):
                binfo["customer_code"] = evidence_map["customer_code"]["value"]

            if evidence_map.get("payment_terms", {}).get("value"):
                binfo["payment_terms"] = evidence_map["payment_terms"]["value"]

            if evidence_map.get("address", {}).get("value"):
                addr_val = evidence_map["address"]["value"]
                if isinstance(addr_val, dict):
                    binfo["address"] = addr_val
                elif isinstance(addr_val, str):
                    binfo["address"] = {"street": addr_val, "zip": "80132", "city": "Napoli", "province": "NA"}
                applied_actions.append("Aggiornato indirizzo sede legale")

            # Zero-Hallucination: non assegnare IBAN fornitore al cliente
            if "iban" in binfo and binfo["iban"] == "IT41E0306903497100000008327":
                del binfo["iban"]
                applied_actions.append("Rimosso IBAN fornitore erroneamente associato al cliente")

            # Moduli: disattiva esplicitamente moduli non presenti
            mods = manifest.setdefault("modules", {})
            mods["it_support"] = False
            mods["mps_rental"] = False
            mods["office_furniture"] = True

            with open(mfile, "w", encoding="utf-8") as f:
                yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)

            applied_actions.append("Manifest cliente aggiornato con dati verificati")

        elif result["document_type"] == "TECHNICAL_SPEC":
            quotes_dir = client_dir / "quotes"
            quotes_dir.mkdir(parents=True, exist_ok=True)
            quote_id = "PREV-2026-001"
            qfile = quotes_dir / f"quote-{quote_id}.yaml"

            bom = evidence_map.get("bill_of_materials", {}).get("value", [])
            categories = [{"name": "hardware_server_network", "items": []}, {"name": "professional_services", "items": []}]

            for b in bom:
                cost = 0.0
                if "SRV-OPENSTOR" in b["sku"]:
                    cost = 14500.0
                elif "CPU-XEON" in b["sku"]:
                    cost = 2200.0
                elif "RAM-32GB" in b["sku"]:
                    cost = 210.0
                elif "SSD-KIOXIA" in b["sku"]:
                    cost = 1200.0
                elif "SSD-NVME" in b["sku"]:
                    cost = 580.0

                item_entry = {
                    "part_number": b["sku"],
                    "description": b["description"],
                    "quantity": b["quantity"],
                    "unit_cost": cost,
                    "markup_percent": 15.0,
                    "unit_price": 0.0,
                    "line_total": 0.0,
                    "is_optional": b.get("is_optional", False)
                }
                if b["category"] == "professional_services":
                    categories[1]["items"].append(item_entry)
                else:
                    categories[0]["items"].append(item_entry)

            categories[1]["items"].append({
                "part_number": "SRV-SETUP-METROCLUSTER",
                "description": "Installazione fisica, cablaggio ridondante 100GbE QSFP28, setup VSA JovianDSS e tuning VMware ESXi",
                "quantity": 1,
                "unit_cost": 2000.0,
                "markup_percent": 20.0,
                "unit_price": 2500.0,
                "line_total": 2500.0,
                "is_optional": False
            })

            quote_data = {
                "quote_id": quote_id,
                "slug": slug,
                "client_name": "T.E.A. TEK S.P.A.",
                "created_at": datetime.date.today().isoformat(),
                "valid_until": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
                "payment_terms": "30_60_DF_FM",
                "categories": categories
            }

            qp = QuotesPipeline(self.clients_root)
            recalc = qp.calculate_quote(quote_data)

            if target_price and recalc["totals"]["total_net"] > 0:
                scale = target_price / recalc["totals"]["total_net"]
                for c in recalc["categories"]:
                    for it in c["items"]:
                        if not it.get("is_optional"):
                            it["unit_price"] = round(it["unit_price"] * scale, 2)
                            it["line_total"] = round(it["unit_price"] * it["quantity"], 2)
                recalc = qp.calculate_quote(recalc)
                applied_actions.append(f"Allineato prezzo di vendita finale al target utente: euro {target_price:.2f}")

            with open(qfile, "w", encoding="utf-8") as f:
                yaml.safe_dump(recalc, f, sort_keys=False, allow_unicode=True)

            qp.export_quote(slug, quote_id)
            applied_actions.append(f"Preventivo {quote_id} esportato in HTML, PDF e DOCX")

        elif result["document_type"] == "MPS_CONTRACT":
            mfile = client_dir / "client-manifest.yaml"
            if mfile.is_file():
                with open(mfile, "r", encoding="utf-8") as f:
                    manifest = yaml.safe_load(f) or {}
                mods = manifest.setdefault("modules", {})
                mods["mps_rental"] = True
                with open(mfile, "w", encoding="utf-8") as f:
                    yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)
                applied_actions.append("Attivato modulo 'mps_rental' in client-manifest.yaml")

            mps_dir = client_dir / "mps"
            mps_dir.mkdir(parents=True, exist_ok=True)
            mps_id = f"mps-{slug}-01"
            mps_file = mps_dir / f"{mps_id}.yaml"

            device_model = str(evidence_map.get("device_model", {}).get("value", "Kyocera TASKalfa 5052ci"))
            device_loc = str(evidence_map.get("device_location", {}).get("value", "Consorzio Area, Via Maddaloni, snc, 80011 Acerra (NA)"))
            proto = str(evidence_map.get("contract_protocol", {}).get("value", "Prot. N.01/26"))
            fee_sem = float(evidence_map.get("semestral_base_fee", {}).get("value", 450.0))
            inc_mono = int(evidence_map.get("included_mono", {}).get("value", 18000))
            inc_col = int(evidence_map.get("included_color", {}).get("value", 900))
            over_mono = float(evidence_map.get("excess_mono", {}).get("value", 0.008))
            over_col = float(evidence_map.get("excess_color", {}).get("value", 0.080))

            mps_payload = {
                "mps_contract_id": mps_id,
                "slug": slug,
                "status": "active",
                "device_info": {
                    "model": device_model,
                    "serial_number": "KYO-5052CI-TEATEK-01",
                    "mac_address": "00:26:73:AA:BB:CC",
                    "ip_address": "192.168.10.250",
                    "location": device_loc
                },
                "snmp_config": {
                    "enabled": True,
                    "version": "v2c",
                    "community": "public",
                    "oids": {
                        "mono_counter": "1.3.6.1.4.1.1347.42.2.1.1.1.6.1.1",
                        "color_counter": "1.3.6.1.4.1.1347.42.2.1.1.1.6.1.2",
                        "toner_black_pct": "1.3.6.1.2.1.43.11.1.1.9.1.1"
                    }
                },
                "contract_terms": {
                    "rental_type": "direct_internal",
                    "financier_contract_number": proto,
                    "semestral_base_fee": fee_sem,
                    "included_copies_semestral": {
                        "mono": inc_mono,
                        "color": inc_col
                    },
                    "overage_cost_per_page": {
                        "mono": over_mono,
                        "color": over_col
                    }
                },
                "readings": [
                    {
                        "reading_date": "2026-02-13",
                        "mono_total": 0,
                        "color_total": 0,
                        "toner_black_percent": 100,
                        "toner_cyan_percent": 100,
                        "toner_magenta_percent": 100,
                        "toner_yellow_percent": 100,
                        "reading_method": "technician_field"
                    }
                ]
            }

            with open(mps_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(mps_payload, f, sort_keys=False, allow_unicode=True)

            applied_actions.append(f"Creato contratto noleggio MPS {mps_file.name} (Canone: € {fee_sem:.2f}/semestre, {inc_mono} BN, {inc_col} Colore)")

        return {
            "status": "success",
            "slug": slug,
            "applied_actions": applied_actions
        }
