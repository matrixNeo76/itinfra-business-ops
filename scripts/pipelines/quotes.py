import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir

class QuotesPipeline:
    """Pipeline E: Preventivazione Multiprodotto & Ricarichi Cost-Plus."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

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

                # Se unit_price non specificato o calcolato da markup
                price = float(item.get("unit_price", 0.0))
                if price <= 0 and markup > 0:
                    price = round(cost * (1 + markup / 100.0), 2)
                elif cost > 0 and price > 0:
                    markup = round(((price - cost) / cost) * 100.0, 2)

                line_tot = round(price * qty, 2)
                line_cost = round(cost * qty, 2)

                # Se non è opzionale, concorre ai totali
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
                "category": cat.get("name"),
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
