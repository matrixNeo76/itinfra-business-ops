import datetime
import hashlib
import math
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir
from scripts.core.bridge import ITInfraBridge
from scripts.pipelines.contracts import ContractsPipeline

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

    @staticmethod
    def calculate_tariff_multiplier(clock_in: str, clock_out: str, date_str: str) -> Dict[str, Any]:
        """
        Determina la fascia oraria dell'intervento e calcola il moltiplicatore tariffario:
        - Feriale diurno (08:00 - 20:00, lun-ven): 1.0x (standard)
        - Feriale notturno (prima delle 08:00 o dopo le 20:00): 1.20x (+20%)
        - Festivo/Weekend diurno: 1.50x (+50%)
        - Festivo/Weekend notturno: 1.75x (+75%)
        """
        d = datetime.date.fromisoformat(date_str)
        is_weekend_or_holiday = ContractsPipeline.is_italian_holiday_or_weekend(d)

        h_in = int(clock_in.split(":")[0])
        h_out = int(clock_out.split(":")[0])
        is_night = (h_in < 8 or h_in >= 20 or h_out > 20)

        if is_weekend_or_holiday:
            if is_night:
                multiplier = 1.75
                category = "festivo_notturno"
                desc = "Intervento Festivo/Weekend Notturno (+75%)"
            else:
                multiplier = 1.50
                category = "festivo_diurno"
                desc = "Intervento Festivo/Weekend Diurno (+50%)"
        else:
            if is_night:
                multiplier = 1.20
                category = "feriale_notturno"
                desc = "Intervento Feriale Notturno (+20%)"
            else:
                multiplier = 1.00
                category = "feriale_standard"
                desc = "Intervento Feriale Diurno Standard"

        return {
            "multiplier": multiplier,
            "category": category,
            "description": desc,
            "is_weekend_or_holiday": is_weekend_or_holiday,
            "is_night": is_night
        }

    @staticmethod
    def seal_report_sha256(report_data: Dict[str, Any]) -> str:
        """Calcola l'hash crittografico SHA-256 a garanzia dell'immutabilità del rapportino."""
        payload = f"{report_data.get('report_id')}|{report_data.get('slug')}|{report_data.get('date')}|" \
                  f"{report_data.get('clock_in')}|{report_data.get('clock_out')}|{report_data.get('technician')}|" \
                  f"{report_data.get('total_hours_rounded')}|{report_data.get('description')}|" \
                  f"{report_data.get('customer_sign_off', {}).get('signer_name')}|" \
                  f"{report_data.get('customer_sign_off', {}).get('signed_at')}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def generate_as_built_patch(
        self,
        slug: str,
        report_data: Optional[Dict[str, Any]] = None,
        replaced_assets: Optional[List[Dict[str, Any]]] = None,
        report_id: str = ""
    ) -> Optional[str]:
        """
        Rileva se nel rapportino sono stati installati ricambi o apparati con numero di serie
        non ancora presenti nell'As-Built (06-As-Built.md) di itinfra e genera la proposta di riga markdown.
        """
        try:
            known = self.bridge.get_known_serials(slug)
        except Exception:
            known = set()

        rep_data = report_data or {}
        rep_id = report_id or rep_data.get("report_id", "RAP-UNKNOWN")
        rep_date = rep_data.get("date", datetime.date.today().isoformat())

        new_items = []

        if replaced_assets:
            for a in replaced_assets:
                sn = str(a.get("serial") or a.get("serial_number") or "").strip().upper()
                new_items.append({
                    "component": a.get("model") or a.get("description") or a.get("role") or "Hardware",
                    "part_number": a.get("part_number", "N/A"),
                    "serial_number": sn,
                    "quantity": a.get("quantity", 1),
                    "installed_date": rep_date,
                    "report_id": rep_id
                })
        else:
            spare_parts = rep_data.get("spare_parts", [])
            for p in spare_parts:
                sn = str(p.get("serial_number", "")).strip().upper()
                if sn and sn not in known and sn not in ("-", "N/A", "NONE"):
                    new_items.append({
                        "component": p.get("description", "Ricambio Hardware"),
                        "part_number": p.get("part_number", "P/N"),
                        "serial_number": sn,
                        "quantity": p.get("quantity", 1),
                        "installed_date": rep_data.get("date", rep_date),
                        "report_id": rep_id
                    })

        if not new_items:
            return None

        lines = [
            f"<!-- REVERSE-HANDOVER-PATCH: Generato da Rapportino {rep_id} ({slug}) -->",
            "| Componente | Part Number | Seriale (S/N) | Data Installazione | Rif. Rapportino |",
            "|---|---|---|---|---|"
        ]
        for item in new_items:
            lines.append(f"| {item['component']} | `{item['part_number']}` | `{item['serial_number']}` | {item['installed_date']} | {item['report_id']} |")

        return "\n".join(lines)

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

    @staticmethod
    def calculate_travel_allowance(
        distance_km: float = 0.0,
        rate_per_km: float = 0.50,
        tolls_eur: float = 0.0,
        parking_eur: float = 0.0
    ) -> Dict[str, float]:
        """Calcola l'indennità chilometrica e il rimborso spese di trasferta."""
        km_reimbursement = round(float(distance_km) * float(rate_per_km), 2)
        total_allowance = round(km_reimbursement + float(tolls_eur) + float(parking_eur), 2)
        return {
            "distance_km": round(float(distance_km), 2),
            "rate_per_km": round(float(rate_per_km), 2),
            "km_reimbursement": km_reimbursement,
            "tolls_eur": round(float(tolls_eur), 2),
            "parking_eur": round(float(parking_eur), 2),
            "total_travel_allowance": total_allowance
        }

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
        spare_parts: Optional[List[Dict[str, Any]]] = None,
        distance_km: float = 0.0,
        rate_per_km: float = 0.50,
        tolls_eur: float = 0.0,
        parking_eur: float = 0.0
    ) -> Dict[str, Any]:
        """Crea, valida e salva fisicamente un nuovo rapportino di intervento con gestione over-budget, ricambi e trasferta."""
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

        # Calcolo tariffazione differenziata (straordinari / festivi / notturni)
        tariff_info = self.calculate_tariff_multiplier(clock_in, clock_out, date_str)
        effective_hours = round(calc["rounded_hours"] * tariff_info["multiplier"], 2)

        debited_h = effective_hours
        extra_h = 0.0

        # Se debit_contract, scala dal contratto attivo e gestisci over-budget
        if ledger_action == "debit_contract" and contract_id:
            res_debit = cp.debit_hours(slug, contract_id, effective_hours, rep_id)
            debited_h = res_debit["debited_contract_hours"]
            extra_h = res_debit["extra_hours"]

        travel_allowance = self.calculate_travel_allowance(distance_km, rate_per_km, tolls_eur, parking_eur)

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
            "tariff_policy": {
                "category": tariff_info["category"],
                "multiplier": tariff_info["multiplier"],
                "description": tariff_info["description"],
                "effective_billable_hours": effective_hours
            },
            "debited_contract_hours": debited_h,
            "extra_hours": extra_h,
            "travel_allowance": travel_allowance,
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

        # Sigillo di integrità SHA-256
        report_data["sha256_seal"] = self.seal_report_sha256(report_data)

        # Salvataggio file YAML
        target_file = tdir / f"{rep_id.lower()}.yaml"
        with open(target_file, "w", encoding="utf-8") as fp:
            yaml.safe_dump(report_data, fp, sort_keys=False, allow_unicode=True)

        # Rileva eventuali nuovi seriali hardware e crea patch proposta per itinfra/06-As-Built.md
        patch_content = self.generate_as_built_patch(slug, report_data)
        if patch_content:
            patch_file = tdir / f"{rep_id.lower()}.as-built-patch.md"
            patch_file.write_text(patch_content, encoding="utf-8")

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
        return html_content

    def export_report(self, slug: str, report_id: str, formats: Optional[List[str]] = None) -> Dict[str, Path]:
        """Esporta il rapportino di lavoro nei formati richiesti (docx, pdf). Default: tutti."""
        from scripts.core.document_renderer import DocumentRenderer

        tdir = self.get_timesheets_dir(slug)
        report_data = None
        for f in tdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("report_id") == report_id or f.stem == report_id.lower():
                    report_data = data
                    break
            except Exception:
                pass

        if not report_data:
            return {}

        selected_formats = [fmt.strip().lower() for fmt in formats] if formats else ["docx", "pdf"]
        if "all" in selected_formats:
            selected_formats = ["docx", "pdf"]

        results = {}
        rid_clean = report_data.get("report_id", report_id).lower().replace(":", "_")

        if "docx" in selected_formats:
            out_docx = tdir / f"{rid_clean}.docx"
            DocumentRenderer.render_report_to_docx(report_data, out_docx)
            results["docx"] = out_docx

        if "pdf" in selected_formats:
            out_pdf = tdir / f"{rid_clean}.pdf"
            DocumentRenderer.render_report_to_pdf(report_data, out_pdf)
            results["pdf"] = out_pdf

        return results

    def apply_as_built_patch_to_project(self, slug: str, report_id: str) -> Dict[str, Any]:
        """
        Applica atomicamente le modifiche hardware/ricambi documentate nel rapportino
        direttamente all'As-Built (06-As-Built.md) del repository federato itinfra.
        Garantisce idempotenza ed evita scritture duplicate.
        """
        tdir = self.get_timesheets_dir(slug)
        report_data = None
        for f in tdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                if d.get("report_id") == report_id or f.stem == report_id.lower():
                    report_data = d
                    break
            except Exception:
                pass

        if not report_data:
            return {
                "status": "error",
                "message": f"Rapportino {report_id} non trovato in {slug}/timesheets",
                "applied": False
            }

        pdir = self.bridge.get_project_dir(slug)
        if not pdir or not pdir.is_dir():
            return {
                "status": "error",
                "message": f"Progetto tecnico itinfra non trovato per slug '{slug}'",
                "applied": False
            }

        as_built_path = pdir / "06-As-Built.md"
        if not as_built_path.is_file():
            return {
                "status": "error",
                "message": f"File 06-As-Built.md non trovato in {pdir}",
                "applied": False
            }

        existing_content = as_built_path.read_text(encoding="utf-8")
        marker = f"<!-- REVERSE-HANDOVER-PATCH: Generato da Rapportino {report_id}"
        if marker in existing_content or f"Rapportino {report_id}" in existing_content:
            return {
                "status": "already_applied",
                "message": f"La patch del rapportino {report_id} è già presente in {as_built_path.name}",
                "applied": False,
                "target_file": str(as_built_path)
            }

        patch_content = self.generate_as_built_patch(slug, report_data)
        if not patch_content:
            return {
                "status": "skipped",
                "message": "Nessun componente hardware nuovo o ricambio censito con seriale nel rapportino",
                "applied": False
            }

        rep_date = report_data.get("date", datetime.date.today().isoformat())
        section_append = f"\n\n### Aggiornamento Componenti da Rapportino Tecnico {report_id} ({rep_date})\n{patch_content}\n"

        new_total_content = existing_content.rstrip() + section_append
        tmp_path = as_built_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(new_total_content, encoding="utf-8")
            tmp_path.replace(as_built_path)
        except Exception:
            as_built_path.write_text(new_total_content, encoding="utf-8")
            if tmp_path.exists():
                tmp_path.unlink()

        return {
            "status": "success",
            "message": f"Patch hardware del rapportino {report_id} applicata con successo a 06-As-Built.md",
            "applied": True,
            "target_file": str(as_built_path),
            "report_id": report_id
        }

    def create_incident_report_draft(self, slug: str, incident_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ambito 1 (SPEC-24): Genera una bozza di rapportino d'intervento straordinario
        da un evento di disservizio / fascicolo 10-RCA.md di itinfra:
        - Estrae estremi tecnici, apparati coinvolti e orari
        - Applica moltiplicatore tariffario CCNL (feriale 1.0x, notturno 1.20x, festivo 1.50x, notturno festivo 1.75x)
        - Prepara l'addebito sul contratto SLA attivo del cliente
        """
        inc_id = incident_payload.get("incident_id") or incident_payload.get("id") or "INC-UNKNOWN"
        title = incident_payload.get("title") or "Risoluzione Disservizio Tecnico"
        desc = incident_payload.get("description") or f"Intervento tecnico straordinario per ripristino operatività [{inc_id}] — {title}"
        technician = incident_payload.get("lead_engineer") or incident_payload.get("technician") or "Eduardo Possumato"
        date_str = incident_payload.get("date") or datetime.date.today().isoformat()
        clock_in = incident_payload.get("clock_in") or "09:00"
        clock_out = incident_payload.get("clock_out") or "11:30"
        contract_id = incident_payload.get("contract_id")

        impacted_assets = []
        raw_assets = incident_payload.get("affected_assets") or []
        for a in raw_assets:
            if isinstance(a, dict):
                impacted_assets.append(a)
            else:
                impacted_assets.append({"model": str(a), "serial": str(a)})

        report = self.create_report(
            slug=slug,
            technician=technician,
            description=desc,
            clock_in=clock_in,
            clock_out=clock_out,
            date_str=date_str,
            intervention_type="extraordinary",
            ledger_action="debit_contract",
            impacted_assets=impacted_assets,
            contract_id=contract_id
        )
        ccnl_type = incident_payload.get("ccnl_type", "ordinary")
        multipliers = {
            "ordinary": 1.00,
            "night": 1.20,
            "holiday": 1.30,
            "night_holiday": 1.50
        }
        multiplier = multipliers.get(ccnl_type, 1.00)
        report["status"] = "SUCCESS"
        report["incident_id"] = inc_id
        report["ccnl_type"] = ccnl_type
        report["ccnl_multiplier"] = multiplier
        report["hours_billed"] = round(report.get("total_hours_rounded", 0.0) * multiplier, 2)
        tdir = self.get_timesheets_dir(slug)
        report["report_file"] = str(tdir / f"{report['report_id'].lower()}.yaml")
        return report

