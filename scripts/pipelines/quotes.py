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

                    # Rigenera anche la proposta formale HTML
                    self.export_quote_html(slug, quote_id)
                    return recalc
            except Exception:
                pass
        return None

    def export_quote_html(self, slug: str, quote_id: str) -> Optional[Path]:
        """Genera un documento di offerta formale commerciale in HTML elegante."""
        qdir = self.get_quotes_dir(slug)
        target_file = None
        quote_data = None
        for qf in qdir.glob("*.yaml"):
            try:
                with open(qf, "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                if d.get("quote_id") == quote_id:
                    target_file = qf
                    quote_data = self.calculate_quote(d)
                    break
            except Exception:
                pass

        if not quote_data:
            return None

        comp = self.config.get("company", {})
        vat_rate = float(comp.get("default_vat_rate", 22.0))
        tot_net = quote_data.get("totals", {}).get("total_net", 0.0)
        tot_vat = round(tot_net * (vat_rate / 100.0), 2)
        tot_gross = round(tot_net + tot_vat, 2)

        client_name = quote_data.get("client_name") or slug.upper()
        contact_info = f"<div style='font-size:13px; color:#475569;'>C.a.: <strong>{quote_data['client_contact']}</strong></div>" if quote_data.get("client_contact") else ""

        categories_html = []
        for cat in quote_data.get("categories", []):
            cat_name = cat.get("name", "").replace("_", " ").title()
            items_rows = "".join(
                f"""<tr style="{'background-color: #fefce8;' if it.get('is_optional') else ''}">
                  <td style="padding:8px; border-bottom:1px solid #e5e7eb;"><code>{it.get('part_number', '')}</code></td>
                  <td style="padding:8px; border-bottom:1px solid #e5e7eb;">{it.get('description', '')} {'<span style=\"color:#b45309; font-weight:bold; font-size:11px;\">[OPZIONE]</span>' if it.get('is_optional') else ''}</td>
                  <td style="padding:8px; border-bottom:1px solid #e5e7eb; text-align:center;">{it.get('quantity', 1)}</td>
                  <td style="padding:8px; border-bottom:1px solid #e5e7eb; text-align:right;">€ {it.get('unit_price', 0.0):.2f}</td>
                  <td style="padding:8px; border-bottom:1px solid #e5e7eb; text-align:right; font-weight:bold;">€ {it.get('line_total', 0.0):.2f}</td>
                </tr>"""
                for it in cat.get("items", [])
            )
            categories_html.append(f"""
            <h3 style="color:#1e3a8a; margin-top:24px; border-bottom:1px solid #cbd5e1; padding-bottom:6px;">{cat_name}</h3>
            <table style="width:100%; border-collapse: collapse; font-size:13px; margin-bottom:12px;">
              <thead>
                <tr style="background:#f8fafc; text-align:left; color:#475569;">
                  <th style="padding:8px;">Codice</th>
                  <th style="padding:8px;">Descrizione Articolo / Servizio</th>
                  <th style="padding:8px; text-align:center;">Q.tà</th>
                  <th style="padding:8px; text-align:right;">Prezzo Unit.</th>
                  <th style="padding:8px; text-align:right;">Totale Netto</th>
                </tr>
              </thead>
              <tbody>{items_rows}</tbody>
            </table>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Offerta Commerciale {quote_id} — {client_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 35px; color:#1e293b; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; }}
  .totals-box {{ width: 320px; margin-left: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; background:#f8fafc; margin-top:24px; }}
  .totals-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
  .grand-total {{ font-size: 16px; font-weight: bold; color: #1e40af; border-top: 1px dashed #cbd5e1; padding-top: 8px; margin-top: 8px; }}
  .terms-box {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-top: 30px; font-size: 13px; border-radius: 0 4px 4px 0; }}
  .sign-section {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 50px; }}
  .sign-line {{ border-top: 1px dashed #94a3b8; margin-top: 60px; text-align: center; font-size: 12px; color: #64748b; padding-top: 6px; }}
  @media print {{ body {{ margin: 10mm; font-size: 11pt; }} }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h2 style="margin:0; color:#1e40af;">PROPOSTA COMMERCIALE & PREVENTIVO</h2>
    <div style="font-size: 14px; color:#64748b; margin-top:4px;">ID Proposta: <strong>{quote_id}</strong> | Data: {quote_data.get('created_at')}</div>
    <div style="font-size: 13px; color:#64748b;">Validità Offerta: fino al {quote_data.get('valid_until')}</div>
  </div>
  <div style="text-align: right;">
    <h3 style="margin:0; color:#0f172a;">{comp.get('name', 'ITInfra')}</h3>
    <div style="font-size: 12px; color:#64748b;">P.IVA: {comp.get('vat_id')} | PEC: {comp.get('pec')}</div>
    <div style="margin-top:8px; font-size:14px;">Destinatario: <strong>{client_name}</strong></div>
    {contact_info}
  </div>
</div>

{"".join(categories_html)}

<div class="totals-box">
  <div class="totals-row"><span>Totale Fornitura Netta:</span><strong>€ {tot_net:.2f}</strong></div>
  <div class="totals-row"><span>IVA ({vat_rate:.0f}%):</span><span>€ {tot_vat:.2f}</span></div>
  <div class="totals-row grand-total"><span>Totale Offerta:</span><span>€ {tot_gross:.2f}</span></div>
</div>

<div class="terms-box">
  <strong>Condizioni di Fornitura:</strong><br>
  • Tempi di Consegna Stimati: {quote_data.get('delivery_time_weeks', 3)} settimane da conferma d'ordine.<br>
  • Termini di Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}.<br>
  • Garanzia Hardware: On-site con supporto tecnico certificato come da SLA.<br>
  • Note: Le voci contrassegnate come [OPZIONE] sono escluse dall'imponibile vincolante e attivabili su richiesta.
</div>

<div class="sign-section">
  <div>
    <strong>Per la Società Fornitrice:</strong>
    <div class="sign-line">{comp.get('name', 'ITInfra')}</div>
  </div>
  <div>
    <strong>Per Accettazione Cliente (Timbro e Firma):</strong>
    <div class="sign-line">{client_name}</div>
  </div>
</div>
</body>
</html>
"""
        out_html = qdir / f"{quote_id.lower()}.html"
        out_html.write_text(html_content, encoding="utf-8")
        return out_html
