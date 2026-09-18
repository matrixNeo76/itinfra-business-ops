#!/usr/bin/env python3
"""
scripts/pipelines/quote_simulator.py — Interactive Commercial Quote Simulator (SPEC-20)
Genera simulatori di preventivo HTML5 interattivi con slider di margine in tempo reale.
"""

import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from scripts.core.config import get_clients_dir


class QuoteSimulatorPipeline:
    """Generatore di interfacce interattive per negoziazione e simulazione economica."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def generate_interactive_simulator(
        self,
        slug: str,
        quote_id: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> str:
        cdir = self.clients_root / slug / "quotes"
        if not cdir.is_dir():
            raise FileNotFoundError(f"Cartella preventivi non trovata per {slug}")

        quote_files = list(cdir.glob("*.yaml"))
        if not quote_files:
            raise FileNotFoundError(f"Nessun preventivo YAML trovato in {cdir}")

        target_file = quote_files[0]
        if quote_id:
            for qf in quote_files:
                if quote_id.lower() in qf.name.lower():
                    target_file = qf
                    break

        with open(target_file, "r", encoding="utf-8") as fp:
            qdata = yaml.safe_load(fp) or {}

        title = qdata.get("title", f"Preventivo {slug.title()}")
        items = qdata.get("items", [])
        tot_cost = float(qdata.get("financial_summary", {}).get("total_cost", 0.0))
        tot_price = float(qdata.get("financial_summary", {}).get("total_net_price", 0.0))
        if tot_price == 0.0:
            tot_price = sum(float(i.get("unit_price", 0.0)) * float(i.get("quantity", 1.0)) for i in items)
        if tot_cost == 0.0:
            tot_cost = sum(float(i.get("unit_cost", 0.0)) * float(i.get("quantity", 1.0)) for i in items)

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulatore Preventivo — {title}</title>
<style>
  :root {{
    --bg-main: #0f172a;
    --bg-card: #1e293b;
    --border-color: #334155;
    --accent-cyan: #38bdf8;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  body {{ background-color: var(--bg-main); color: var(--text-primary); padding: 30px; }}
  .container {{ max-width: 950px; margin: 0 auto; }}
  .header {{ border-bottom: 2px solid var(--border-color); padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
  .brand {{ font-size: 20px; font-weight: 800; color: #fff; }}
  .brand span {{ color: var(--accent-cyan); }}
  .card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
  .slider-group {{ margin-bottom: 20px; }}
  .slider-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 600; font-size: 14px; }}
  input[type=range] {{ width: 100%; accent-color: var(--accent-cyan); }}
  .kpi-row {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 20px; }}
  .kpi-box {{ background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 6px; padding: 16px; text-align: center; }}
  .kpi-title {{ font-size: 11px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }}
  .kpi-val {{ font-size: 24px; font-weight: 800; color: #fff; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
  th {{ text-align: left; padding: 10px; border-bottom: 2px solid var(--border-color); color: var(--text-muted); }}
  td {{ padding: 12px 10px; border-bottom: 1px solid rgba(51, 65, 85, 0.5); }}
  .btn {{ background: var(--accent-emerald); color: #fff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 700; cursor: pointer; }}
  .btn:hover {{ opacity: 0.9; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="brand">AURE <span>SYSTEM</span> &bull; Generative UI Quote Simulator</div>
      <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">{title} ({slug})</div>
    </div>
    <button class="btn" onclick="window.print()">Esporta / Stampa</button>
  </div>

  <div class="card">
    <h3 style="margin-bottom: 18px;">Regolatori Dinamici di Marginalità</h3>

    <div class="slider-group">
      <div class="slider-header">
        <span>Margine Hardware / Prodotti</span>
        <span id="lbl-hw-margin" style="color: var(--accent-cyan);">25%</span>
      </div>
      <input type="range" id="slider-hw" min="10" max="50" value="25" step="1" oninput="recalculate()">
    </div>

    <div class="slider-group">
      <div class="slider-header">
        <span>Tariffa Oraria Servizi Sistemici (€/h)</span>
        <span id="lbl-hourly-rate" style="color: var(--accent-emerald);">€75 / h</span>
      </div>
      <input type="range" id="slider-rate" min="60" max="130" value="75" step="5" oninput="recalculate()">
    </div>

    <div class="slider-group">
      <div class="slider-header">
        <span>Sconto Commerciale SLA (%)</span>
        <span id="lbl-discount" style="color: var(--accent-amber);">0%</span>
      </div>
      <input type="range" id="slider-disc" min="0" max="25" value="0" step="1" oninput="recalculate()">
    </div>

    <div class="kpi-row">
      <div class="kpi-box">
        <div class="kpi-title">Costo Totale Industriale</div>
        <div class="kpi-val" id="val-cost" style="color: var(--text-muted);">€{tot_cost:,.2f}</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-title">Prezzo Finale al Cliente (Imponibile)</div>
        <div class="kpi-val" id="val-price" style="color: var(--accent-cyan);">€{tot_price:,.2f}</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-title">Margine Operativo Lordo (MOL)</div>
        <div class="kpi-val" id="val-mol" style="color: var(--accent-emerald);">€{(tot_price - tot_cost):,.2f}</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h3 style="margin-bottom: 14px;">Dettaglio Voci Preventivate</h3>
    <table>
      <thead>
        <tr>
          <th>Descrizione</th>
          <th>Quantità</th>
          <th>Costo Unitario</th>
          <th>Prezzo Unitario</th>
          <th style="text-align: right;">Totale Netto</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f"<tr><td>{i.get('description', '')}</td><td>{i.get('quantity', 1)}</td><td>€{float(i.get('unit_cost', 0)):,.2f}</td><td>€{float(i.get('unit_price', 0)):,.2f}</td><td style='text-align: right; font-weight: bold;'>€{(float(i.get('unit_price', 0)) * float(i.get('quantity', 1))):,.2f}</td></tr>" for i in items)}
      </tbody>
    </table>
  </div>
</div>

<script>
const baseCost = {tot_cost};
const basePrice = {tot_price};

function recalculate() {{
  const hwMargin = parseFloat(document.getElementById('slider-hw').value);
  const rate = parseFloat(document.getElementById('slider-rate').value);
  const disc = parseFloat(document.getElementById('slider-disc').value);

  document.getElementById('lbl-hw-margin').textContent = hwMargin + '%';
  document.getElementById('lbl-hourly-rate').textContent = '€' + rate + ' / h';
  document.getElementById('lbl-discount').textContent = disc + '%';

  // Calcolo dinamico
  let newPrice = basePrice * (1 + (hwMargin - 25) / 100);
  newPrice = newPrice * (1 - (disc / 100));
  let mol = newPrice - baseCost;

  document.getElementById('val-price').textContent = '€' + newPrice.toLocaleString('it-IT', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
  document.getElementById('val-mol').textContent = '€' + mol.toLocaleString('it-IT', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
}}
</script>
</body>
</html>
"""
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(html_content, encoding="utf-8")

        return html_content
