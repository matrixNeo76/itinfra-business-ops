# -*- coding: utf-8 -*-
"""
ITInfra Business Ops — Universal Document Renderer (SPEC-16)
Motore universale di rendering ed esportazione documentale:
- Preventivi Commerciali (.docx, .pdf, .html)
- Contratti SLA & Manutenzione (.docx, .pdf, .html)
- Rapportini Tecnici di Intervento (.docx, .pdf, .html)
- Fatture Elettroniche XML SDI (.html, .pdf)
Tutti i documenti integrano automaticamente il logo e la Brand Identity ufficiale (SPEC-16).
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from scripts.core.document_branding import BrandConfig, DocumentBranding


class DocumentRenderer:
    """Motore universale di visualizzazione ed esportazione documentale."""

    # -------------------------------------------------------------------------
    # 1. PREVENTIVI COMMERCIALI (QUOTES)
    # -------------------------------------------------------------------------
    @staticmethod
    def render_quote_to_docx(quote_data: Dict[str, Any], out_docx_path: Path) -> Path:
        """Esporta il preventivo in formato professionale Microsoft Word (.docx)."""
        doc = docx.Document()
        DocumentBranding.apply_docx_margins(doc)

        # Header istituzionale con logo
        qid = quote_data.get("quote_id", "PREV")
        cdate = quote_data.get("created_at", "")
        vdate = quote_data.get("valid_until", "")
        sub_info = f"ID Documento: {qid}  |  Data Offerta: {cdate}  |  Validità: fino al {vdate}"
        DocumentBranding.add_docx_branded_header(doc, "PROPOSTA COMMERCIALE & PREVENTIVO", sub_info)

        # Tabella Contraenti
        doc.add_paragraph()
        parties_table = doc.add_table(rows=1, cols=2)
        parties_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        parties_table.autofit = True

        cell_f = parties_table.cell(0, 0)
        p_f = cell_f.paragraphs[0]
        p_f.add_run("SOCIETÀ FORNITRICE:\n").bold = True
        p_f.add_run(f"{BrandConfig.COMPANY_NAME}\n{BrandConfig.ADDRESS}\nP.IVA: {BrandConfig.VAT_ID}\nTel: {BrandConfig.PHONE}")

        cell_c = parties_table.cell(0, 1)
        p_c = cell_c.paragraphs[0]
        p_c.add_run("SPETTABILE COMMITTENTE:\n").bold = True
        p_c.add_run(f"{quote_data.get('client_name', 'Cliente')}\n")
        if quote_data.get("client_contact"):
            p_c.add_run(f"C.a.: {quote_data['client_contact']}\n")
        p_c.add_run(f"Termini di Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}")

        doc.add_paragraph()

        # Tabelle Categorie
        for cat in quote_data.get("categories", []):
            cat_name = cat.get("name", "").replace("_", " ").title()
            h_cat = doc.add_heading(cat_name, level=2)
            if h_cat.runs:
                h_cat.runs[0].font.color.rgb = BrandConfig.RGB_PRIMARY

            items = cat.get("items", [])
            table = doc.add_table(rows=1, cols=5)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            hdr_cells = table.rows[0].cells
            hdr_titles = ["Codice", "Descrizione", "Q.tà", "Prezzo Unit.", "Totale Netto"]
            for i, text in enumerate(hdr_titles):
                hdr_cells[i].text = text
                if hdr_cells[i].paragraphs[0].runs:
                    hdr_cells[i].paragraphs[0].runs[0].bold = True
                    hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(9.5)
                    hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

            for idx, it in enumerate(items):
                row_cells = table.add_row().cells
                row_cells[0].text = it.get("part_number", "")
                
                desc_text = it.get("description", "")
                if it.get("is_optional"):
                    desc_text += "  [OPZIONE]"
                row_cells[1].text = desc_text
                row_cells[2].text = str(it.get("quantity", 1))
                row_cells[3].text = f"€ {it.get('unit_price', 0.0):.2f}"
                row_cells[4].text = f"€ {it.get('line_total', 0.0):.2f}"

                for cell in row_cells:
                    if cell.paragraphs[0].runs:
                        cell.paragraphs[0].runs[0].font.size = Pt(9)

            doc.add_paragraph()

        # Box Totali
        tot_net = quote_data.get("totals", {}).get("total_net", 0.0)
        tot_vat = round(tot_net * 0.22, 2)
        tot_gross = round(tot_net + tot_vat, 2)

        tot_table = doc.add_table(rows=3, cols=2)
        tot_table.alignment = WD_TABLE_ALIGNMENT.RIGHT
        tot_table.cell(0, 0).text = "Totale Fornitura Netta:"
        tot_table.cell(0, 1).text = f"€ {tot_net:.2f}"
        tot_table.cell(1, 0).text = "IVA (22%):"
        tot_table.cell(1, 1).text = f"€ {tot_vat:.2f}"
        tot_table.cell(2, 0).text = "TOTALE PROPOSTA:"
        tot_table.cell(2, 1).text = f"€ {tot_gross:.2f}"

        for r in tot_table.rows:
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()

        # Condizioni di Fornitura
        doc.add_heading("Condizioni Generali di Fornitura", level=3)
        doc.add_paragraph(f"• Tempi di Consegna Stimati: {quote_data.get('delivery_time_weeks', 3)} settimane da conferma d'ordine.")
        doc.add_paragraph(f"• Termini di Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}.")
        doc.add_paragraph("• Garanzia Hardware: On-site con supporto tecnico certificato come da accordi SLA.")
        doc.add_paragraph("• Le voci contrassegnate come [OPZIONE] sono attivabili su richiesta ed escluse dal totale.")

        doc.add_paragraph()

        # Firme
        sign_table = doc.add_table(rows=2, cols=2)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sign_table.cell(0, 0).text = f"Per la Società Fornitrice:\n{BrandConfig.LEGAL_SIGNATURE}"
        sign_table.cell(0, 1).text = f"Per Accettazione Committente (Timbro e Firma):\n{quote_data.get('client_name')}"
        sign_table.cell(1, 0).text = "\n\n__________________________________"
        sign_table.cell(1, 1).text = f"\n\n__________________________________\n{quote_data.get('client_name')}"

        DocumentBranding.add_docx_branded_footer(doc)
        out_docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_docx_path)
        return out_docx_path

    @staticmethod
    def render_quote_to_pdf(quote_data: Dict[str, Any], out_pdf_path: Path) -> Path:
        """Esporta il preventivo in formato PDF stampabile A4 ad alta risoluzione."""
        doc = SimpleDocTemplate(
            str(out_pdf_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=colors.HexColor(BrandConfig.HEX_PRIMARY), alignment=1)
        subtitle_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor(BrandConfig.HEX_MUTED), alignment=1)
        h2_style = ParagraphStyle('CatHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor(BrandConfig.HEX_SECONDARY), spaceBefore=12, spaceAfter=4)
        normal_style = ParagraphStyle('NormText', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11)
        bold_style = ParagraphStyle('BoldText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11)

        story = []
        # Header istituzionale con logo
        qid = quote_data.get("quote_id", "PREV")
        cdate = quote_data.get("created_at", "")
        vdate = quote_data.get("valid_until", "")
        story.append(DocumentBranding.get_pdf_branded_header("PROPOSTA COMMERCIALE & PREVENTIVO", qid, cdate, vdate))
        story.append(Spacer(1, 10))

        story.append(Paragraph("PROPOSTA COMMERCIALE & PREVENTIVO", title_style))
        story.append(Paragraph(f"ID Proposta: <b>{qid}</b>  |  Data: {cdate}  |  Validità: fino al {vdate}", subtitle_style))
        story.append(Spacer(1, 10))

        # Box Contraenti
        client_contact = f"<br/>C.a.: <b>{quote_data['client_contact']}</b>" if quote_data.get('client_contact') else ""
        parties_data = [
            [
                Paragraph(f"<b>FORNITORE:</b><br/>{BrandConfig.COMPANY_NAME}<br/>{BrandConfig.ADDRESS}<br/>P.IVA: {BrandConfig.VAT_ID}", normal_style),
                Paragraph(f"<b>COMMITTENTE:</b><br/><b>{quote_data.get('client_name', 'Cliente')}</b>{client_contact}<br/>Termini Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}", normal_style)
            ]
        ]
        t_parties = Table(parties_data, colWidths=[260, 260])
        t_parties.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_parties)
        story.append(Spacer(1, 8))

        # Tabelle Categorie
        for cat in quote_data.get("categories", []):
            cat_name = cat.get("name", "").replace("_", " ").title()
            story.append(Paragraph(cat_name, h2_style))

            table_data = [[
                Paragraph("<b>Codice</b>", bold_style),
                Paragraph("<b>Descrizione Articolo / Servizio</b>", bold_style),
                Paragraph("<b>Q.tà</b>", bold_style),
                Paragraph("<b>Prezzo Unit.</b>", bold_style),
                Paragraph("<b>Totale Netto</b>", bold_style)
            ]]

            for it in cat.get("items", []):
                desc = it.get("description", "")
                if it.get("is_optional"):
                    desc += f" <b><font color='{BrandConfig.HEX_ACCENT}'>[OPZIONE]</font></b>"
                table_data.append([
                    Paragraph(f"<code>{it.get('part_number', '')}</code>", normal_style),
                    Paragraph(desc, normal_style),
                    Paragraph(str(it.get("quantity", 1)), normal_style),
                    Paragraph(f"€ {it.get('unit_price', 0.0):.2f}", normal_style),
                    Paragraph(f"€ {it.get('line_total', 0.0):.2f}", bold_style)
                ])

            t_cat = Table(table_data, colWidths=[80, 250, 40, 75, 75])
            t_cat.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BrandConfig.HEX_PRIMARY)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ]))
            story.append(t_cat)
            story.append(Spacer(1, 6))

        # Box Totali
        tot_net = quote_data.get("totals", {}).get("total_net", 0.0)
        tot_vat = round(tot_net * 0.22, 2)
        tot_gross = round(tot_net + tot_vat, 2)

        tot_data = [
            [Paragraph("Totale Fornitura Netta:", normal_style), Paragraph(f"<b>€ {tot_net:.2f}</b>", normal_style)],
            [Paragraph("IVA (22%):", normal_style), Paragraph(f"<b>€ {tot_vat:.2f}</b>", normal_style)],
            [Paragraph("<b>TOTALE OFFERTA:</b>", bold_style), Paragraph(f"<b><font size='10' color='{BrandConfig.HEX_PRIMARY}'>€ {tot_gross:.2f}</font></b>", bold_style)]
        ]
        t_tot = Table(tot_data, colWidths=[140, 90], hAlign='RIGHT')
        t_tot.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(Spacer(1, 8))
        story.append(t_tot)

        # Condizioni e Firme
        story.append(Spacer(1, 10))
        terms_text = f"<b>Condizioni di Fornitura:</b><br/>" \
                     f"• Tempi di Consegna: {quote_data.get('delivery_time_weeks', 3)} settimane da conferma d'ordine.<br/>" \
                     f"• Termini di Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}.<br/>" \
                     f"• Garanzia Hardware: On-site con supporto tecnico certificato SLA.<br/>" \
                     f"• Le voci contrassegnate come [OPZIONE] sono escluse dall'imponibile vincolante."
        story.append(Paragraph(terms_text, normal_style))

        sign_data = [
            [
                Paragraph(f"<b>Per la Società Fornitrice:</b><br/>{BrandConfig.LEGAL_SIGNATURE}<br/><br/><br/>__________________________________", normal_style),
                Paragraph(f"<b>Per Accettazione Committente (Timbro e Firma):</b><br/>{quote_data.get('client_name')}<br/><br/><br/>__________________________________", normal_style)
            ]
        ]
        t_sign = Table(sign_data, colWidths=[260, 260])
        t_sign.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 10)]))
        story.append(Spacer(1, 14))
        story.append(t_sign)

        out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        return out_pdf_path

    @staticmethod
    def render_quote_to_html(quote_data: Dict[str, Any], out_html_path: Path) -> Path:
        """Esporta il preventivo in formato HTML stand-alone print-ready con logo Base64 incorporato."""
        logo_b64 = BrandConfig.get_logo_base64()
        qid = quote_data.get("quote_id", "PREV")
        client_name = quote_data.get("client_name", "Cliente")
        created_at = quote_data.get("created_at", "")
        valid_until = quote_data.get("valid_until", "")

        categories_html = []
        for cat in quote_data.get("categories", []):
            cat_name = cat.get("name", "").replace("_", " ").title()
            rows_html = ""
            for it in cat.get("items", []):
                opt_badge = f"<span style='color:{BrandConfig.HEX_ACCENT}; font-weight:bold; font-size:11px;'>[OPZIONE]</span>" if it.get("is_optional") else ""
                rows_html += f"""<tr>
                  <td><code>{it.get('part_number', '')}</code></td>
                  <td>{it.get('description', '')} {opt_badge}</td>
                  <td class='text-center'>{it.get('quantity', 1)}</td>
                  <td class='text-right'>€ {it.get('unit_price', 0.0):.2f}</td>
                  <td class='text-right'><strong>€ {it.get('line_total', 0.0):.2f}</strong></td>
                </tr>"""

            categories_html.append(f"""
            <h3 style='color:{BrandConfig.HEX_PRIMARY}; margin-top:20px; border-bottom:1px solid {BrandConfig.HEX_BORDER}; padding-bottom:4px;'>{cat_name}</h3>
            <table class='data-table'>
              <thead>
                <tr>
                  <th>Codice</th><th>Descrizione</th><th class='text-center'>Q.tà</th><th class='text-right'>Prezzo Unit.</th><th class='text-right'>Totale Netto</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
            """)

        tot_net = quote_data.get("totals", {}).get("total_net", 0.0)
        tot_vat = round(tot_net * 0.22, 2)
        tot_gross = round(tot_net + tot_vat, 2)

        html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Proposta Commerciale {qid} — {client_name}</title>
<style>{DocumentBranding.get_html_print_css()}</style>
</head>
<body>
<div class="brand-header">
  <div>
    <img src="data:image/png;base64,{logo_b64}" class="brand-logo-img" alt="Logo">
  </div>
  <div class="brand-company-info">
    <div class="brand-company-name">{BrandConfig.COMPANY_NAME}</div>
    {BrandConfig.ADDRESS}<br>
    P.IVA: <strong>{BrandConfig.VAT_ID}</strong> | Tel: {BrandConfig.PHONE}<br>
    PEC: {BrandConfig.PEC} | Web: {BrandConfig.WEBSITE}
  </div>
</div>

<div class="doc-title-box">
  <h1>PROPOSTA COMMERCIALE & PREVENTIVO</h1>
  <div class="doc-meta">ID Documento: <strong>{qid}</strong> | Data Emissione: {created_at} | Validità: fino al {valid_until}</div>
</div>

<div class="card-grid">
  <div class="party-card">
    <div class="party-card-title">Società Fornitrice</div>
    <strong>{BrandConfig.COMPANY_NAME}</strong><br>
    {BrandConfig.ADDRESS}<br>
    P.IVA: {BrandConfig.VAT_ID}<br>
    Email / PEC: {BrandConfig.PEC}
  </div>
  <div class="party-card">
    <div class="party-card-title">Spettabile Committente</div>
    <strong>{client_name}</strong><br>
    {f"C.a.: <strong>{quote_data.get('client_contact')}</strong><br>" if quote_data.get('client_contact') else ""}
    Termini Pagamento: <strong>{quote_data.get('payment_terms', '30_60_DF_FM')}</strong>
  </div>
</div>

{"".join(categories_html)}

<div class="totals-card">
  <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
    <span>Totale Fornitura Netta:</span><strong>€ {tot_net:.2f}</strong>
  </div>
  <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
    <span>IVA (22%):</span><strong>€ {tot_vat:.2f}</strong>
  </div>
  <div class="grand-total">
    <span>TOTALE PROPOSTA:</span><span>€ {tot_gross:.2f}</span>
  </div>
</div>

<div style="background:#eff6ff; border-left:4px solid {BrandConfig.HEX_SECONDARY}; padding:10px 14px; margin-top:24px; font-size:12.5px; border-radius:0 4px 4px 0;">
  <strong>Condizioni Generali di Fornitura:</strong><br>
  • Tempi di Consegna Stimati: {quote_data.get('delivery_time_weeks', 3)} settimane da conferma d'ordine.<br>
  • Termini di Pagamento: {quote_data.get('payment_terms', '30_60_DF_FM')}.<br>
  • Garanzia Hardware: On-site con supporto tecnico certificato SLA.<br>
  • Le voci contrassegnate come [OPZIONE] sono escluse dall'imponibile vincolante.
</div>

<div class="sign-grid">
  <div>
    <div style="font-size:12px; color:{BrandConfig.HEX_MUTED};">Per la Società Fornitrice:</div>
    <div style="font-weight:600; font-size:13px; margin-top:2px;">{BrandConfig.LEGAL_SIGNATURE}</div>
    <div class="sign-box">Firma e Timbro</div>
  </div>
  <div>
    <div style="font-size:12px; color:{BrandConfig.HEX_MUTED};">Per Accettazione Committente:</div>
    <div style="font-weight:600; font-size:13px; margin-top:2px;">{client_name}</div>
    <div class="sign-box">Firma Legale Rappresentante</div>
  </div>
</div>

<div class="footer-legal">
  {BrandConfig.COMPANY_NAME} — Documento Riservato ad uso esclusivo del destinatario ai sensi del Reg. UE 2016/679 (GDPR).
</div>
</body>
</html>
"""
        out_html_path.parent.mkdir(parents=True, exist_ok=True)
        out_html_path.write_text(html, encoding="utf-8")
        return out_html_path

    # -------------------------------------------------------------------------
    # 2. CONTRATTI DI ASSISTENZA SLA & DPA
    # -------------------------------------------------------------------------
    @staticmethod
    def render_contract_to_docx(contract_data: Dict[str, Any], out_docx_path: Path) -> Path:
        """Esporta il contratto SLA in formato Microsoft Word (.docx)."""
        doc = docx.Document()
        DocumentBranding.apply_docx_margins(doc)

        cid = contract_data.get("contract_id", "CTR")
        vfrom = contract_data.get("valid_from", "")
        vto = contract_data.get("valid_to", "")
        sub_info = f"Contratto N: {cid}  |  Decorrenza: {vfrom}  |  Scadenza: {vto}"
        DocumentBranding.add_docx_branded_header(doc, "CONTRATTO DI ASSISTENZA SISTEMISTICA & SLA", sub_info)

        doc.add_paragraph()
        p_c = doc.add_paragraph()
        p_c.add_run(f"COMMITTENTE: {contract_data.get('slug', 'Cliente').upper()}\n").bold = True
        p_c.add_run(f"Formula Contrattuale: {contract_data.get('formula', 'hours_bank').upper()}\n")
        p_c.add_run(f"Stato: {contract_data.get('status', 'active').upper()}")

        # SLA Matrix
        sla = contract_data.get("sla", {})
        doc.add_heading("1. Livelli di Servizio Garantiti (SLA)", level=2)
        table_sla = doc.add_table(rows=4, cols=2)
        table_sla.cell(0, 0).text = "Tier / Livello SLA:"
        table_sla.cell(0, 1).text = str(sla.get("tier", "standard")).upper()
        table_sla.cell(1, 0).text = "Finestra di Reperibilità:"
        table_sla.cell(1, 1).text = str(sla.get("coverage_window", "10:00-17:00 Lun-Ven"))
        table_sla.cell(2, 0).text = "Presa in Carico (First Response):"
        table_sla.cell(2, 1).text = f"{sla.get('first_response_hours', 8.0)} ore lavorative"
        table_sla.cell(3, 0).text = "Risoluzione Obiettivo (Target Resolution):"
        table_sla.cell(3, 1).text = f"{sla.get('target_resolution_hours', 16.0)} ore lavorative"

        for r in table_sla.rows:
            r.cells[0].paragraphs[0].runs[0].bold = True

        # Economica
        fin = contract_data.get("financial", {})
        doc.add_heading("2. Condizioni Economiche e Monte Ore", level=2)
        table_fin = doc.add_table(rows=4, cols=2)
        table_fin.cell(0, 0).text = "Canone Ricorrente:"
        table_fin.cell(0, 1).text = f"€ {fin.get('recurring_fee', 0.0):.2f} ({fin.get('billing_period', 'annuale')})"
        table_fin.cell(1, 0).text = "Monte Ore Incluso:"
        table_fin.cell(1, 1).text = f"{fin.get('total_hours_included', 0.0)} ore"
        table_fin.cell(2, 0).text = "Tariffa Fuori Pacchetto:"
        table_fin.cell(2, 1).text = f"€ {fin.get('extra_hourly_rate', 75.0):.2f}/ora + IVA"
        table_fin.cell(3, 0).text = "Diritto Fisso di Chiamata/Trasferta:"
        table_fin.cell(3, 1).text = f"€ {fin.get('travel_fee_fixed', 0.0):.2f}"

        for r in table_fin.rows:
            r.cells[0].paragraphs[0].runs[0].bold = True

        # Apparati As-Built Coperti
        assets = contract_data.get("covered_assets", [])
        if assets:
            doc.add_heading("3. Perimetro Tecnologico Coperto (Apparati)", level=2)
            t_ass = doc.add_table(rows=1, cols=4)
            hdr = t_ass.rows[0].cells
            hdr[0].text = "Seriale"
            hdr[1].text = "Hostname"
            hdr[2].text = "Ruolo / Servizio"
            hdr[3].text = "Modello Apparato"
            for c in hdr:
                c.paragraphs[0].runs[0].bold = True

            for a in assets:
                r_cells = t_ass.add_row().cells
                r_cells[0].text = str(a.get("serial_number", ""))
                r_cells[1].text = str(a.get("hostname", ""))
                r_cells[2].text = str(a.get("role", ""))
                r_cells[3].text = str(a.get("model", ""))

        # Firme
        doc.add_paragraph()
        sign_table = doc.add_table(rows=2, cols=2)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sign_table.cell(0, 0).text = f"Per il Fornitore:\n{BrandConfig.LEGAL_SIGNATURE}"
        sign_table.cell(0, 1).text = f"Per il Committente (Timbro e Firma):\n{contract_data.get('slug', 'Cliente')}"
        sign_table.cell(1, 0).text = "\n\n__________________________________"
        sign_table.cell(1, 1).text = "\n\n__________________________________"

        DocumentBranding.add_docx_branded_footer(doc)
        out_docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_docx_path)
        return out_docx_path

    @staticmethod
    def render_contract_to_pdf(contract_data: Dict[str, Any], out_pdf_path: Path) -> Path:
        """Esporta il contratto SLA in formato PDF A4 ad alta risoluzione."""
        doc = SimpleDocTemplate(str(out_pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold')
        h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor(BrandConfig.HEX_SECONDARY), spaceBefore=10, spaceAfter=4)

        story = []
        cid = contract_data.get("contract_id", "CTR")
        story.append(DocumentBranding.get_pdf_branded_header("CONTRATTO DI ASSISTENZA SISTEMISTICA & SLA", cid, contract_data.get("valid_from", "")))
        story.append(Spacer(1, 12))

        sla = contract_data.get("sla", {})
        fin = contract_data.get("financial", {})

        info_text = f"<b>CONTRATTO DI ASSISTENZA SISTEMISTICA & SLA</b><br/>" \
                    f"Identificativo: <b>{cid}</b>  |  Committente: <b>{contract_data.get('slug', 'Cliente').upper()}</b><br/>" \
                    f"Validità: dal <b>{contract_data.get('valid_from')}</b> al <b>{contract_data.get('valid_to')}</b> (Rinnovo automatico: {contract_data.get('renewal', {}).get('automatic', True)})"
        story.append(Paragraph(info_text, normal))
        story.append(Spacer(1, 10))

        story.append(Paragraph("1. Parametri e Tempi di Presa in Carico SLA", h2))
        sla_data = [
            [Paragraph("Tier SLA:", bold), Paragraph(str(sla.get("tier", "high")).upper(), normal)],
            [Paragraph("Finestra Oraria Presidio:", bold), Paragraph(str(sla.get("coverage_window", "10:00-17:00 Lun-Ven")), normal)],
            [Paragraph("Tempo Presa in Carico:", bold), Paragraph(f"{sla.get('first_response_hours', 8.0)} ore lavorative", normal)],
            [Paragraph("Risoluzione Obiettivo:", bold), Paragraph(f"{sla.get('target_resolution_hours', 16.0)} ore lavorative", normal)],
        ]
        t_sla = Table(sla_data, colWidths=[200, 320])
        t_sla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_sla)

        story.append(Paragraph("2. Condizioni Economiche & Monte Ore", h2))
        fin_data = [
            [Paragraph("Canone Periodico:", bold), Paragraph(f"€ {fin.get('recurring_fee', 0.0):.2f} + IVA ({fin.get('billing_period', 'semestrale')})", normal)],
            [Paragraph("Monte Ore Incluso:", bold), Paragraph(f"{fin.get('total_hours_included', 0.0)} ore", normal)],
            [Paragraph("Tariffa Fuori Pacchetto:", bold), Paragraph(f"€ {fin.get('extra_hourly_rate', 80.0):.2f}/ora + IVA", normal)],
        ]
        t_fin = Table(fin_data, colWidths=[200, 320])
        t_fin.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_fin)

        # Apparati
        assets = contract_data.get("covered_assets", [])
        if assets:
            story.append(Paragraph("3. Apparati e Server Inclusi nella Copertura", h2))
            ass_data = [[Paragraph("Seriale", bold), Paragraph("Hostname", bold), Paragraph("Ruolo", bold), Paragraph("Modello", bold)]]
            for a in assets:
                ass_data.append([
                    Paragraph(str(a.get("serial_number", "")), normal),
                    Paragraph(str(a.get("hostname", "")), normal),
                    Paragraph(str(a.get("role", "")), normal),
                    Paragraph(str(a.get("model", "")), normal),
                ])
            t_ass = Table(ass_data, colWidths=[100, 100, 150, 170])
            t_ass.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BrandConfig.HEX_PRIMARY)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_ass)

        # Firme
        sign_data = [
            [
                Paragraph(f"<b>Per il Fornitore:</b><br/>{BrandConfig.LEGAL_SIGNATURE}<br/><br/><br/>__________________________________", normal),
                Paragraph(f"<b>Per il Committente:</b><br/>{contract_data.get('slug', 'Cliente').upper()}<br/><br/><br/>__________________________________", normal)
            ]
        ]
        t_sign = Table(sign_data, colWidths=[260, 260])
        t_sign.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 14)]))
        story.append(Spacer(1, 16))
        story.append(t_sign)

        out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        return out_pdf_path

    # -------------------------------------------------------------------------
    # 3. RAPPORTINI TECNICI DI INTERVENTO (REPORTS / TIMESHEETS)
    # -------------------------------------------------------------------------
    @staticmethod
    def render_report_to_docx(report_data: Dict[str, Any], out_docx_path: Path) -> Path:
        """Esporta il rapportino di lavoro in formato Microsoft Word (.docx)."""
        doc = docx.Document()
        DocumentBranding.apply_docx_margins(doc)

        rid = report_data.get("report_id", "RAP")
        rdate = report_data.get("date", "")
        tech = report_data.get("technician", "Tecnico")
        sub_info = f"Rapportino N: {rid}  |  Data Intervento: {rdate}  |  Operatore: {tech}"
        DocumentBranding.add_docx_branded_header(doc, "RAPPORTINO DI INTERVENTO TECNICO", sub_info)

        doc.add_paragraph()
        table_meta = doc.add_table(rows=4, cols=2)
        table_meta.cell(0, 0).text = "Committente / Cliente:"
        table_meta.cell(0, 1).text = str(report_data.get("slug", "Cliente")).upper()
        table_meta.cell(1, 0).text = "Contratto SLA di Riferimento:"
        table_meta.cell(1, 1).text = str(report_data.get("contract_id", "CTR"))
        table_meta.cell(2, 0).text = "Orario Intervento:"
        table_meta.cell(2, 1).text = f"{report_data.get('clock_in', '')} - {report_data.get('clock_out', '')} (Ore rendicontate: {report_data.get('total_hours_rounded', 0.0)} h)"
        table_meta.cell(3, 0).text = "Azione Contabile:"
        table_meta.cell(3, 1).text = str(report_data.get("ledger_action", "debit_contract")).upper()

        for r in table_meta.rows:
            r.cells[0].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()
        doc.add_heading("Descrizione Attività Svolta", level=2)
        doc.add_paragraph(report_data.get("description", "Intervento di manutenzione ordinaria."))

        assets = report_data.get("impacted_assets", [])
        if assets:
            doc.add_heading("Apparati Coinvolti", level=3)
            t_ass = doc.add_table(rows=1, cols=3)
            hdr = t_ass.rows[0].cells
            hdr[0].text = "Seriale"
            hdr[1].text = "Ruolo"
            hdr[2].text = "Descrizione"
            for c in hdr:
                c.paragraphs[0].runs[0].bold = True
            for a in assets:
                rc = t_ass.add_row().cells
                rc[0].text = str(a.get("serial_number", ""))
                rc[1].text = str(a.get("role", ""))
                rc[2].text = str(a.get("description", ""))

        doc.add_paragraph()
        sign_table = doc.add_table(rows=2, cols=2)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sign_table.cell(0, 0).text = f"Tecnico Esecutore:\n{tech}"
        sign_table.cell(0, 1).text = f"Per Ricevuta e Accettazione Cliente:\n{report_data.get('customer_sign_off', {}).get('signer_name', 'Firma Cliente')}"
        sign_table.cell(1, 0).text = "\n\n__________________________________"
        sign_table.cell(1, 1).text = "\n\n__________________________________"

        DocumentBranding.add_docx_branded_footer(doc)
        out_docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_docx_path)
        return out_docx_path

    @staticmethod
    def render_report_to_pdf(report_data: Dict[str, Any], out_pdf_path: Path) -> Path:
        """Esporta il rapportino di lavoro in formato PDF A4 ad alta risoluzione."""
        doc = SimpleDocTemplate(str(out_pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold')
        h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor(BrandConfig.HEX_SECONDARY), spaceBefore=10, spaceAfter=4)

        story = []
        rid = report_data.get("report_id", "RAP")
        story.append(DocumentBranding.get_pdf_branded_header("RAPPORTINO DI INTERVENTO TECNICO", rid, report_data.get("date", "")))
        story.append(Spacer(1, 10))

        info_data = [
            [Paragraph("Identificativo Rapportino:", bold), Paragraph(rid, normal)],
            [Paragraph("Cliente / Committente:", bold), Paragraph(str(report_data.get("slug", "Cliente")).upper(), normal)],
            [Paragraph("Tecnico Esecutore:", bold), Paragraph(str(report_data.get("technician", "")), normal)],
            [Paragraph("Data Intervento:", bold), Paragraph(str(report_data.get("date", "")), normal)],
            [Paragraph("Finestra Oraria:", bold), Paragraph(f"{report_data.get('clock_in', '')} - {report_data.get('clock_out', '')}", normal)],
            [Paragraph("Ore Totali Fatturabili:", bold), Paragraph(f"<b>{report_data.get('total_hours_rounded', 0.0)} ore</b> (Azione: {report_data.get('ledger_action', 'debit_contract')})", normal)],
        ]
        t_info = Table(info_data, colWidths=[180, 340])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_info)

        story.append(Paragraph("Descrizione Attività e Risoluzione", h2))
        story.append(Paragraph(report_data.get("description", "").replace("\n", "<br/>"), normal))
        story.append(Spacer(1, 10))

        assets = report_data.get("impacted_assets", [])
        if assets:
            story.append(Paragraph("Apparati Impattati", h2))
            ass_data = [[Paragraph("Seriale", bold), Paragraph("Ruolo", bold), Paragraph("Attività", bold)]]
            for a in assets:
                ass_data.append([
                    Paragraph(str(a.get("serial_number", "")), normal),
                    Paragraph(str(a.get("role", "")), normal),
                    Paragraph(str(a.get("description", "")), normal),
                ])
            t_ass = Table(ass_data, colWidths=[120, 130, 270])
            t_ass.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BrandConfig.HEX_PRIMARY)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_ass)

        # Firme
        cust = report_data.get("customer_sign_off", {})
        signer = cust.get("signer_name", "Cliente")
        sign_data = [
            [
                Paragraph(f"<b>Tecnico Fornitore:</b><br/>{report_data.get('technician', '')}<br/><br/><br/>__________________________________", normal),
                Paragraph(f"<b>Firma Committente per Accettazione:</b><br/>{signer}<br/><br/><br/>__________________________________", normal)
            ]
        ]
        t_sign = Table(sign_data, colWidths=[260, 260])
        t_sign.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 14)]))
        story.append(Spacer(1, 16))
        story.append(t_sign)

        out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        return out_pdf_path

    # -------------------------------------------------------------------------
    # 4. FATTURA ELETTRONICA XML SDI
    # -------------------------------------------------------------------------
    @staticmethod
    def render_xml_invoice_to_html(xml_path: Path, out_html_path: Optional[Path] = None) -> Path:
        """Legge un file XML FatturaPA SDI FPR12 e genera una vista grafica HTML human-readable con brand logo."""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        def find_text(elem, *tags):
            curr = elem
            for t in tags:
                if curr is None:
                    return ""
                found = None
                for child in curr:
                    tag_name = child.tag.split("}")[-1]
                    if tag_name == t:
                        found = child
                        break
                curr = found
            return curr.text.strip() if curr is not None and curr.text else ""

        dati_trasm = None
        cedente = None
        cessionario = None
        dati_doc = None
        dati_beni = None
        dati_pag = None

        for child in root:
            tag = child.tag.split("}")[-1]
            if tag == "FatturaElettronicaHeader":
                for h_child in child:
                    htag = h_child.tag.split("}")[-1]
                    if htag == "DatiTrasmissione":
                        dati_trasm = h_child
                    elif htag == "CedentePrestatore":
                        cedente = h_child
                    elif htag == "CessionarioCommittente":
                        cessionario = h_child
            elif tag == "FatturaElettronicaBody":
                for b_child in child:
                    btag = b_child.tag.split("}")[-1]
                    if btag == "DatiGenerali":
                        for dg_child in b_child:
                            if dg_child.tag.split("}")[-1] == "DatiGeneraliDocumento":
                                dati_doc = dg_child
                    elif btag == "DatiBeniServizi":
                        dati_beni = b_child
                    elif btag == "DatiPagamento":
                        dati_pag = b_child

        ced_nome = find_text(cedente, "DatiAnagrafici", "Anagrafica", "Denominazione")
        if not ced_nome:
            ced_nome = f"{find_text(cedente, 'DatiAnagrafici', 'Anagrafica', 'Nome')} {find_text(cedente, 'DatiAnagrafici', 'Anagrafica', 'Cognome')}".strip()
        ced_piva = find_text(cedente, "DatiAnagrafici", "IdFiscaleIVA", "IdCodice")
        ced_via = find_text(cedente, "Sede", "Indirizzo")
        ced_cap = find_text(cedente, "Sede", "CAP")
        ced_comune = find_text(cedente, "Sede", "Comune")
        ced_prov = find_text(cedente, "Sede", "Provincia")

        ces_nome = find_text(cessionario, "DatiAnagrafici", "Anagrafica", "Denominazione")
        if not ces_nome:
            ces_nome = f"{find_text(cessionario, 'DatiAnagrafici', 'Anagrafica', 'Nome')} {find_text(cessionario, 'DatiAnagrafici', 'Anagrafica', 'Cognome')}".strip()
        ces_piva = find_text(cessionario, "DatiAnagrafici", "IdFiscaleIVA", "IdCodice")
        ces_cf = find_text(cessionario, "DatiAnagrafici", "CodiceFiscale")
        ces_via = find_text(cessionario, "Sede", "Indirizzo")
        ces_cap = find_text(cessionario, "Sede", "CAP")
        ces_comune = find_text(cessionario, "Sede", "Comune")
        ces_prov = find_text(cessionario, "Sede", "Provincia")

        doc_tipo = find_text(dati_doc, "TipoDocumento") or "TD01"
        doc_data = find_text(dati_doc, "Data")
        doc_numero = find_text(dati_doc, "Numero")
        doc_totale = float(find_text(dati_doc, "ImportoTotaleDocumento") or 0.0)
        cod_sdi = find_text(dati_trasm, "CodiceDestinatario")
        pec_dest = find_text(dati_trasm, "PECDestinatario")

        lines_html = []
        if dati_beni:
            for item in dati_beni:
                if item.tag.split("}")[-1] == "DettaglioLinee":
                    nl = find_text(item, "NumeroLinea")
                    ds = find_text(item, "Descrizione")
                    qt = find_text(item, "Quantita") or "1"
                    pu = float(find_text(item, "PrezzoUnitario") or 0.0)
                    pt = float(find_text(item, "PrezzoTotale") or 0.0)
                    iv = find_text(item, "AliquotaIVA") or "22.00"
                    lines_html.append(f"""
                    <tr>
                      <td class='text-center'>{nl}</td>
                      <td>{ds}</td>
                      <td class='text-center'>{qt}</td>
                      <td class='text-right'>€ {pu:.2f}</td>
                      <td class='text-center'>{float(iv):.0f}%</td>
                      <td class='text-right'><strong>€ {pt:.2f}</strong></td>
                    </tr>
                    """)

        logo_b64 = BrandConfig.get_logo_base64()
        html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Fattura Elettronica {doc_numero} — {ces_nome}</title>
<style>{DocumentBranding.get_html_print_css()}</style>
</head>
<body>
<div class="brand-header">
  <div><img src="data:image/png;base64,{logo_b64}" class="brand-logo-img" alt="Logo"></div>
  <div class="brand-company-info">
    <div class="brand-company-name">{ced_nome}</div>
    {ced_via}<br>{ced_cap} {ced_comune} ({ced_prov})<br>
    P.IVA: <strong>{ced_piva}</strong>
  </div>
</div>

<div class="doc-title-box">
  <h1>FATTURA ELETTRONICA (COPIA DI CORTESIA)</h1>
  <div class="doc-meta">Numero: <strong>{doc_numero}</strong> | Data: {doc_data} | Tipo: {doc_tipo} | Codice SDI: <strong>{cod_sdi}</strong></div>
</div>

<div class="card-grid">
  <div class="party-card">
    <div class="party-card-title">Cedente / Prestatore</div>
    <strong>{ced_nome}</strong><br>{ced_via}<br>{ced_cap} {ced_comune} ({ced_prov})<br>P.IVA: {ced_piva}
  </div>
  <div class="party-card">
    <div class="party-card-title">Cessionario / Committente</div>
    <strong>{ces_nome}</strong><br>{ces_via}<br>{ced_cap} {ces_comune} ({ces_prov})<br>
    P.IVA: {ces_piva} {f"| CF: {ces_cf}" if ces_cf else ""}
  </div>
</div>

<table class="data-table">
  <thead>
    <tr>
      <th class="text-center">N°</th><th>Descrizione Beni / Servizi</th><th class="text-center">Q.tà</th><th class="text-right">Prezzo Unit.</th><th class="text-center">IVA</th><th class="text-right">Importo</th>
    </tr>
  </thead>
  <tbody>{"".join(lines_html)}</tbody>
</table>

<div class="totals-card">
  <div class="grand-total">
    <span>TOTALE FATTURA:</span><span>€ {doc_totale:.2f}</span>
  </div>
</div>

<div class="footer-legal">
  Documento privo di valenza fiscale ai sensi dell'art. 21 D.P.R. 633/72. L'originale della fattura elettronica è disponibile nell'area riservata SDI.
</div>
</body>
</html>
"""
        target_path = out_html_path or xml_path.with_suffix(".html")
        target_path.write_text(html, encoding="utf-8")
        return target_path

    @staticmethod
    def render_xml_invoice_to_pdf(xml_path: Path, out_pdf_path: Optional[Path] = None) -> Path:
        """Genera copia di cortesia PDF a partire dal file XML FatturaPA SDI con brand identity."""
        target_pdf = out_pdf_path or xml_path.with_suffix(".pdf")
        tree = ET.parse(xml_path)
        root = tree.getroot()

        def find_text(elem, *tags):
            curr = elem
            for t in tags:
                if curr is None:
                    return ""
                found = None
                for child in curr:
                    tag_name = child.tag.split("}")[-1]
                    if tag_name == t:
                        found = child
                        break
                curr = found
            return curr.text.strip() if curr is not None and curr.text else ""

        dati_trasm = None
        cedente = None
        cessionario = None
        dati_doc = None
        dati_beni = None

        for child in root:
            tag = child.tag.split("}")[-1]
            if tag == "FatturaElettronicaHeader":
                for h in child:
                    htag = h.tag.split("}")[-1]
                    if htag == "DatiTrasmissione":
                        dati_trasm = h
                    elif htag == "CedentePrestatore":
                        cedente = h
                    elif htag == "CessionarioCommittente":
                        cessionario = h
            elif tag == "FatturaElettronicaBody":
                for b in child:
                    btag = b.tag.split("}")[-1]
                    if btag == "DatiGenerali":
                        for dg in b:
                            if dg.tag.split("}")[-1] == "DatiGeneraliDocumento":
                                dati_doc = dg
                    elif btag == "DatiBeniServizi":
                        dati_beni = b

        ced_nome = find_text(cedente, "DatiAnagrafici", "Anagrafica", "Denominazione") or BrandConfig.COMPANY_NAME
        ced_piva = find_text(cedente, "DatiAnagrafici", "IdFiscaleIVA", "IdCodice") or BrandConfig.VAT_ID
        ced_via = find_text(cedente, "Sede", "Indirizzo")
        ced_cap = find_text(cedente, "Sede", "CAP")
        ced_comune = find_text(cedente, "Sede", "Comune")
        ced_prov = find_text(cedente, "Sede", "Provincia")

        ces_nome = find_text(cessionario, "DatiAnagrafici", "Anagrafica", "Denominazione") or "Cessionario"
        ces_piva = find_text(cessionario, "DatiAnagrafici", "IdFiscaleIVA", "IdCodice")
        ces_via = find_text(cessionario, "Sede", "Indirizzo")
        ces_cap = find_text(cessionario, "Sede", "CAP")
        ces_comune = find_text(cessionario, "Sede", "Comune")
        ces_prov = find_text(cessionario, "Sede", "Provincia")

        doc_numero = find_text(dati_doc, "Numero")
        doc_data = find_text(dati_doc, "Data")
        doc_totale = float(find_text(dati_doc, "ImportoTotaleDocumento") or 0.0)
        cod_sdi = find_text(dati_trasm, "CodiceDestinatario")

        doc_pdf = SimpleDocTemplate(str(target_pdf), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold')

        story = []
        story.append(DocumentBranding.get_pdf_branded_header(f"FATTURA ELETTRONICA N. {doc_numero}", doc_numero, doc_data))
        story.append(Spacer(1, 12))

        parties = [
            [
                Paragraph(f"<b>CEDENTE / PRESTATORE:</b><br/><b>{ced_nome}</b><br/>{ced_via}<br/>{ced_cap} {ced_comune} ({ced_prov})<br/>P.IVA: {ced_piva}", normal),
                Paragraph(f"<b>CESSIONARIO / COMMITTENTE:</b><br/><b>{ces_nome}</b><br/>{ces_via}<br/>{ces_cap} {ces_comune} ({ces_prov})<br/>P.IVA: {ces_piva}<br/>Codice SDI: <b>{cod_sdi}</b>", normal)
            ]
        ]
        t_parties = Table(parties, colWidths=[260, 260])
        t_parties.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_parties)
        story.append(Spacer(1, 10))

        lines_table = [[Paragraph("N°", bold), Paragraph("Descrizione Beni / Servizi", bold), Paragraph("Q.tà", bold), Paragraph("Prezzo Unit.", bold), Paragraph("IVA", bold), Paragraph("Totale", bold)]]
        if dati_beni:
            for item in dati_beni:
                if item.tag.split("}")[-1] == "DettaglioLinee":
                    nl = find_text(item, "NumeroLinea")
                    ds = find_text(item, "Descrizione")
                    qt = find_text(item, "Quantita") or "1"
                    pu = float(find_text(item, "PrezzoUnitario") or 0.0)
                    pt = float(find_text(item, "PrezzoTotale") or 0.0)
                    iv = float(find_text(item, "AliquotaIVA") or 22.0)
                    lines_table.append([
                        Paragraph(nl, normal),
                        Paragraph(ds, normal),
                        Paragraph(qt, normal),
                        Paragraph(f"€ {pu:.2f}", normal),
                        Paragraph(f"{iv:.0f}%", normal),
                        Paragraph(f"€ {pt:.2f}", bold)
                    ])

        t_lines = Table(lines_table, colWidths=[30, 270, 35, 65, 45, 75])
        t_lines.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BrandConfig.HEX_PRIMARY)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(BrandConfig.HEX_BORDER)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ]))
        story.append(t_lines)
        story.append(Spacer(1, 10))

        tot_box = [[Paragraph("<b>TOTALE DOCUMENTO:</b>", bold), Paragraph(f"<b><font size='11' color='{BrandConfig.HEX_PRIMARY}'>€ {doc_totale:.2f}</font></b>", bold)]]
        t_tot = Table(tot_box, colWidths=[160, 100], hAlign='RIGHT')
        t_tot.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BrandConfig.HEX_SURFACE)),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(BrandConfig.HEX_SECONDARY)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(t_tot)

        doc_pdf.build(story)
        return target_pdf
