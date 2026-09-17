import datetime
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir, load_config

class QuotesPipeline:
    """Pipeline E: Preventivazione Multiprodotto & Ricarichi Cost-Plus."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()

    def get_quotes_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "quotes"

    def calculate_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ricalcola deterministamente costi, prezzi di vendita e margini per categoria."""
        total_cost = 0.0
        total_net = 0.0
        categories_breakdown = []

        for cat in quote_data.get("categories", []):
            cat_cost = 0.0
            cat_net = 0.0
            updated_items = []

            for item in cat.get("items", []):
                cost = float(item.get("unit_cost", 0.0))
                qty = float(item.get("quantity", 1))
                markup = float(item.get("markup_percent", 0.0))

                price = float(item.get("unit_price", 0.0))
                if price <= 0 and markup > 0:
                    price = round(cost * (1 + markup / 100.0), 2)
                elif cost > 0 and price > 0:
                    markup = round(((price - cost) / cost) * 100.0, 2)

                line_tot = round(price * qty, 2)
                line_cost = round(cost * qty, 2)

                if not item.get("is_optional", False):
                    cat_cost += line_cost
                    cat_net += line_tot

                item["unit_cost"] = cost
                item["markup_percent"] = markup
                item["unit_price"] = price
                item["line_total"] = line_tot
                updated_items.append(item)

            cat_margin = round(cat_net - cat_cost, 2)
            cat_margin_pct = round((cat_margin / cat_net * 100.0), 2) if cat_net > 0 else 0.0
            categories_breakdown.append({
                "name": cat.get("name"),
                "total_cost": round(cat_cost, 2),
                "total_net": round(cat_net, 2),
                "margin_amount": cat_margin,
                "margin_percent": cat_margin_pct,
                "items": updated_items
            })
            total_cost += cat_cost
            total_net += cat_net

        gross_margin = round(total_net - total_cost, 2)
        gross_margin_pct = round((gross_margin / total_net * 100.0), 2) if total_net > 0 else 0.0

        quote_data["categories"] = categories_breakdown
        quote_data["totals"] = {
            "total_cost": round(total_cost, 2),
            "total_net": round(total_net, 2),
            "gross_margin_amount": gross_margin,
            "gross_margin_percent": gross_margin_pct
        }
        return quote_data

    def add_item_to_quote(
        self,
        slug: str,
        quote_id: str,
        category: str,
        part_number: str,
        description: str,
        quantity: float,
        unit_cost: float,
        markup_percent: float,
        is_optional: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Aggiunge una voce al preventivo, ricalcola i totali e risalva il file YAML."""
        qdir = self.get_quotes_dir(slug)
        for qf in qdir.glob("*.yaml"):
            try:
                with open(qf, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("quote_id") == quote_id:
                    cats = data.setdefault("categories", [])
                    target_cat = None
                    for c in cats:
                        if c.get("name") == category:
                            target_cat = c
                            break
                    if not target_cat:
                        target_cat = {"name": category, "items": []}
                        cats.append(target_cat)

                    target_cat.setdefault("items", []).append({
                        "part_number": part_number,
                        "description": description,
                        "quantity": quantity,
                        "unit_cost": unit_cost,
                        "markup_percent": markup_percent,
                        "unit_price": 0.0,
                        "line_total": 0.0,
                        "is_optional": is_optional
                    })

                    recalc = self.calculate_quote(data)
                    with open(qf, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(recalc, fp, sort_keys=False, allow_unicode=True)

                    # Rigenera anche la proposta formale (HTML, PDF, DOCX)
                    self.export_quote(slug, quote_id)
                    return recalc
            except Exception:
                pass
        return None

    def export_quote(self, slug: str, quote_id: str, formats: Optional[List[str]] = None) -> Dict[str, Path]:
        """Esporta l'offerta commerciale nei formati richiesti (html, pdf, docx). Default: tutti."""
        from scripts.core.document_renderer import DocumentRenderer

        qdir = self.get_quotes_dir(slug)
        quote_data = None
        for qf in qdir.glob("*.yaml"):
            try:
                with open(qf, "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                if d.get("quote_id") == quote_id:
                    quote_data = self.calculate_quote(d)
                    break
            except Exception:
                pass

        if not quote_data:
            return {}

        selected_formats = [f.strip().lower() for f in formats] if formats else ["html", "pdf", "docx"]
        if "all" in selected_formats:
            selected_formats = ["html", "pdf", "docx"]

        results = {}
        base_name = quote_id.lower()

        if "html" in selected_formats:
            out_html = self.export_quote_html(slug, quote_id)
            if out_html:
                results["html"] = out_html

        if "pdf" in selected_formats:
            out_pdf = qdir / f"{base_name}.pdf"
            DocumentRenderer.render_quote_to_pdf(quote_data, out_pdf)
            results["pdf"] = out_pdf

        if "docx" in selected_formats:
            out_docx = qdir / f"{base_name}.docx"
            DocumentRenderer.render_quote_to_docx(quote_data, out_docx)
            results["docx"] = out_docx

        return results

    def export_quote_html(self, slug: str, quote_id: str) -> Optional[Path]:
        """Genera un documento di offerta formale commerciale in HTML elegante con Brand Identity."""
        from scripts.core.document_renderer import DocumentRenderer

        qdir = self.get_quotes_dir(slug)
        quote_data = None
        for qf in qdir.glob("*.yaml"):
            try:
                with open(qf, "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                if d.get("quote_id") == quote_id:
                    quote_data = self.calculate_quote(d)
                    break
            except Exception:
                pass

        if not quote_data:
            return None

        out_html = qdir / f"{quote_id.lower()}.html"
        return DocumentRenderer.render_quote_to_html(quote_data, out_html)

