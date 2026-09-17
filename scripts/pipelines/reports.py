import datetime
import math
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir
from scripts.core.bridge import ITInfraBridge

class ReportsPipeline:
    """Pipeline B: Rapportini di Assistenza, Time-Tracking & Ledger Debit."""

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.bridge = ITInfraBridge()

    def get_timesheets_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "timesheets"

    @staticmethod
    def calculate_rounded_hours(clock_in: str, clock_out: str, break_minutes: int = 0, step_minutes: int = 30) -> Dict[str, float]:
        """Calcola ore lorde e arrotondate a scatti prestabiliti (es. 30 min)."""
        t_in = datetime.datetime.strptime(clock_in, "%H:%M")
        t_out = datetime.datetime.strptime(clock_out, "%H:%M")
        diff_minutes = (t_out - t_in).total_seconds() / 60.0 - break_minutes
        if diff_minutes < 0:
            diff_minutes = 0

        raw_hours = round(diff_minutes / 60.0, 2)
        # Arrotondamento al multiplo superiore di step_minutes
        steps = math.ceil(diff_minutes / step_minutes)
        rounded_minutes = steps * step_minutes
        rounded_hours = round(rounded_minutes / 60.0, 2)

        return {
            "raw_hours": raw_hours,
            "rounded_hours": rounded_hours,
            "net_minutes": int(diff_minutes)
        }

    def list_reports(self, slug: str) -> List[Dict[str, Any]]:
        tdir = self.get_timesheets_dir(slug)
        if not tdir.is_dir():
            return []
        reports = []
        for f in sorted(tdir.glob("*.yaml")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    reports.append(data)
            except Exception:
                pass
        return reports

    def get_ledger_summary(self, slug: str) -> Dict[str, Any]:
        reports = self.list_reports(slug)
        summary = {
            "slug": slug,
            "total_reports": len(reports),
            "contract_debit_hours": 0.0,
            "invoice_spot_hours": 0.0,
            "included_flat_hours": 0.0,
            "unbilled_spot_reports": []
        }

        for r in reports:
            hours = float(r.get("total_hours_rounded", 0.0))
            action = r.get("ledger_action", "debit_contract")
            rid = r.get("report_id", r.get("_file"))

            if action == "debit_contract":
                summary["contract_debit_hours"] += hours
            elif action == "invoice_spot":
                summary["invoice_spot_hours"] += hours
                summary["unbilled_spot_reports"].append({
                    "report_id": rid,
                    "date": r.get("date"),
                    "hours": hours,
                    "technician": r.get("technician"),
                    "description": r.get("description", "").split("\n")[0]
                })
            elif action == "included_flat":
                summary["included_flat_hours"] += hours

        summary["contract_debit_hours"] = round(summary["contract_debit_hours"], 2)
        summary["invoice_spot_hours"] = round(summary["invoice_spot_hours"], 2)
        summary["included_flat_hours"] = round(summary["included_flat_hours"], 2)
        return summary

    def create_report(
        self,
        slug: str,
        technician: str,
        description: str,
        clock_in: str,
        clock_out: str,
        date_str: Optional[str] = None,
        intervention_type: str = "ordinary",
        ledger_action: str = "debit_contract",
        impacted_assets: Optional[List[Dict[str, str]]] = None,
        contract_id: Optional[str] = None,
        break_minutes: int = 0,
        customer_signed: bool = False,
        signer_name: str = "",
        spare_parts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Crea, valida e salva fisicamente un nuovo rapportino di intervento con gestione over-budget e ricambi."""
        if not date_str:
            date_str = datetime.date.today().isoformat()
        date_compact = date_str.replace("-", "")

        tdir = self.get_timesheets_dir(slug)
        tdir.mkdir(parents=True, exist_ok=True)
        existing_count = len(list(tdir.glob(f"rap-{date_compact}-*.yaml"))) + 1
        rep_id = f"RAP-{date_compact}-{existing_count:03d}"

        calc = self.calculate_rounded_hours(clock_in, clock_out, break_minutes)

        # Se contract_id non specificato e action è debit_contract, trova il primo attivo
        from scripts.pipelines.contracts import ContractsPipeline
        cp = ContractsPipeline(self.clients_root)
        if not contract_id and ledger_action == "debit_contract":
            active = cp.get_contract_summary(slug).get("active_contracts", [])
            if active:
                contract_id = active[0]["contract_id"]

        debited_h = calc["rounded_hours"]
        extra_h = 0.0

        # Se debit_contract, scala dal contratto attivo e gestisci over-budget
        if ledger_action == "debit_contract" and contract_id:
            res_debit = cp.debit_hours(slug, contract_id, calc["rounded_hours"], rep_id)
            debited_h = res_debit["debited_contract_hours"]
            extra_h = res_debit["extra_hours"]

        report_data = {
            "report_id": rep_id,
            "slug": slug,
            "contract_id": contract_id or "",
            "ticket_id": "",
            "technician": technician,
            "date": date_str,
            "clock_in": clock_in,
            "clock_out": clock_out,
            "break_minutes": break_minutes,
            "total_hours_raw": calc["raw_hours"],
            "total_hours_rounded": calc["rounded_hours"],
            "debited_contract_hours": debited_h,
            "extra_hours": extra_h,
            "rounding_step_minutes": 30,
            "intervention_type": intervention_type,
            "ledger_action": ledger_action,
            "impacted_assets": impacted_assets or [],
            "spare_parts": spare_parts or [],
            "description": description.strip(),
            "customer_sign_off": {
                "signed": customer_signed,
                "signer_name": signer_name,
                "signed_at": f"{date_str} {clock_out}" if customer_signed else ""
            }
        }

        # Salvataggio file YAML
        target_file = tdir / f"{rep_id.lower()}.yaml"
        with open(target_file, "w", encoding="utf-8") as fp:
            yaml.safe_dump(report_data, fp, sort_keys=False, allow_unicode=True)

        # Genera anche HTML interattivo di cortesia con Canvas Firma
        html_content = self.generate_printable_html(report_data)
        html_file = tdir / f"{rep_id.lower()}.html"
        html_file.write_text(html_content, encoding="utf-8")

        return report_data

    def generate_printable_html(self, report_data: Dict[str, Any]) -> str:
        """Genera un foglio di intervento stampabile e firmabile interattivamente su tablet con HTML5 Canvas."""
        rid = report_data.get("report_id", "RAP")
        slug = report_data.get("slug", "")
        tech = report_data.get("technician", "")
        date = report_data.get("date", "")
        cin = report_data.get("clock_in", "")
        cout = report_data.get("clock_out", "")
        h_round = report_data.get("total_hours_rounded", 0.0)
        debited_h = report_data.get("debited_contract_hours", h_round)
        extra_h = report_data.get("extra_hours", 0.0)
        action = report_data.get("ledger_action", "")
        desc = report_data.get("description", "").replace("\n", "<br/>")
        cid = report_data.get("contract_id", "N/A")
        signer = report_data.get("customer_sign_off", {}).get("signer_name", "")

        assets_html = "".join(
            f"<li><strong>{a.get('serial_number')}:</strong> {a.get('role', '')} — {a.get('description', '')}</li>"
            for a in report_data.get("impacted_assets", [])
        ) or "<li>Nessun apparato specifico segnalato.</li>"

        parts = report_data.get("spare_parts", [])
        if parts:
            parts_rows = "".join(
                f"<tr><td><code>{p.get('code')}</code></td><td>{p.get('description')}</td><td style='text-align:center;'>{p.get('quantity')}</td><td style='text-align:right;'>€ {p.get('unit_price', 0.0):.2f}</td></tr>"
                for p in parts
            )
            parts_html = f"""
            <h4 style="margin: 16px 0 8px 0; color:#1e40af;">Ricambi & Materiali Impiegati:</h4>
            <table style="width:100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px;">
              <thead>
                <tr style="background:#f3f4f6; text-align:left;">
                  <th style="padding:6px; border:1px solid #e5e7eb;">Codice</th>
                  <th style="padding:6px; border:1px solid #e5e7eb;">Descrizione</th>
                  <th style="padding:6px; border:1px solid #e5e7eb; text-align:center;">Q.tà</th>
                  <th style="padding:6px; border:1px solid #e5e7eb; text-align:right;">Prezzo Unit.</th>
                </tr>
              </thead>
              <tbody>{parts_rows}</tbody>
            </table>
            """
        else:
            parts_html = ""

        overbudget_badge = f"<span style='background:#fee2e2; color:#991b1b; padding:3px 6px; border-radius:4px; font-size:11px; margin-left:8px;'>EXTRA-SOGLIA: {extra_h} h</span>" if extra_h > 0 else ""

        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rapportino {rid} — {slug}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; color: #1f2937; line-height: 1.4; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px; }}
  .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; background: #e0e7ff; color: #3730a3; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .box {{ border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px; background: #f9fafb; }}
  .desc-box {{ border: 1px solid #e5e7eb; border-radius: 6px; padding: 14px; min-height: 80px; margin-bottom: 20px; background: #fff; }}
  .sig-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 30px; }}
  canvas#sig-pad {{ border: 1px solid #d1d5db; border-radius: 4px; width: 100%; height: 120px; touch-action: none; background: #ffffff; cursor: crosshair; }}
  .canvas-controls {{ margin-top: 6px; display: flex; gap: 8px; }}
  .btn {{ font-size: 11px; padding: 4px 8px; border-radius: 4px; border: 1px solid #d1d5db; background: #fff; cursor: pointer; }}
  .btn:hover {{ background: #f3f4f6; }}
  @media print {{
    body {{ margin: 10mm; font-size: 11pt; }}
    .no-print {{ display: none !important; }}
    canvas#sig-pad {{ border: 1px dashed #9ca3af; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h2 style="margin:0; color:#1e40af;">RAPPORTINO DI INTERVENTO TECNICO</h2>
    <span style="font-size: 13px; color:#6b7280;">ID: <strong>{rid}</strong> | Cliente: <strong>{slug}</strong></span>
  </div>
  <div style="text-align: right;">
    <span class="badge">{action.upper()}</span>{overbudget_badge}
    <div style="font-size: 12px; margin-top: 4px; color:#4b5563;">Contratto Rif: {cid}</div>
  </div>
</div>

<div class="grid">
  <div class="box">
    <strong>Dettagli Intervento:</strong><br>
    Data: {date}<br>
    Orario: {cin} &rarr; {cout}<br>
    Ore Totali Consuntivate: <strong>{h_round} h</strong> (a canone: {debited_h} h{f', extra: {extra_h} h' if extra_h > 0 else ''})<br>
    Tecnico Incaricato: <strong>{tech}</strong>
  </div>
  <div class="box">
    <strong>Apparati Impattati / S/N:</strong>
    <ul style="margin: 6px 0 0 16px; padding: 0; font-size: 13px;">
      {assets_html}
    </ul>
  </div>
</div>

<strong>Descrizione Attività Svolta:</strong>
<div class="desc-box">
  {desc}
</div>

{parts_html}

<div class="sig-container">
  <div>
    <strong>Firma Tecnico Esecutore:</strong>
    <div style="margin-top: 40px; border-top: 1px dashed #9ca3af; text-align: center; font-size: 12px; color: #4b5563; padding-top: 4px;">
      {tech}
    </div>
  </div>
  <div>
    <strong>Firma Cliente per Accettazione:</strong>
    <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Firma qui sotto (Touch / Pennino):</div>
    <canvas id="sig-pad"></canvas>
    <div class="canvas-controls no-print">
      <button type="button" class="btn" onclick="clearCanvas()">Pulisci Firma</button>
      <button type="button" class="btn" onclick="window.print()">Stampa / PDF</button>
    </div>
    <div style="font-size: 11px; color:#6b7280; margin-top: 4px;">Referente: <strong>{signer or "Referente Autorizzato"}</strong></div>
  </div>
</div>

<script>
  const canvas = document.getElementById('sig-pad');
  if (canvas) {{
    const ctx = canvas.getContext('2d');
    let drawing = false;

    function resize() {{
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#1e3a8a';
    }}
    resize();
    window.addEventListener('resize', resize);

    function start(e) {{
      drawing = true;
      ctx.beginPath();
      const pos = getPos(e);
      ctx.moveTo(pos.x, pos.y);
    }}
    function end() {{ drawing = false; }}
    function draw(e) {{
      if (!drawing) return;
      e.preventDefault();
      const pos = getPos(e);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
    }}
    function getPos(e) {{
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {{ x: clientX - rect.left, y: clientY - rect.top }};
    }}

    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mouseup', end);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('touchstart', start);
    canvas.addEventListener('touchend', end);
    canvas.addEventListener('touchmove', draw);

    window.clearCanvas = function() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }};
  }}
</script>
</body>
</html>
"""
