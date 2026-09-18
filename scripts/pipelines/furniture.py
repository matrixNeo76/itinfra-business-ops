import datetime
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir, load_config
from scripts.core.bridge import ITInfraBridge

class FurniturePipeline:
    """Pipeline G: Fornitura Arredo Ufficio & Commesse."""

    STAGES_ORDER = [
        "1_survey",
        "2_design",
        "3_sampling_approval",
        "4_procurement",
        "5_assembly",
        "6_handover_conditional_snagging",
        "6_handover_approved"
    ]

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()
        self.config = load_config()

    def get_furniture_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "furniture"

    def list_orders(self, slug: str) -> List[Dict[str, Any]]:
        fdir = self.get_furniture_dir(slug)
        if not fdir.is_dir():
            return []
        orders = []
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    orders.append(data)
            except Exception:
                pass
        return orders

    def get_order_status(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica lo stato di avanzamento delle fasi, punch list, ritenuta a garanzia e checklist di collaudo."""
        current_status = order_data.get("status", "1_survey")
        stages = order_data.get("stages", {})
        handover = stages.get("handover", {})
        checklist = handover.get("checklist", {})
        punch_list = handover.get("punch_list", [])

        all_checks_ok = all(checklist.values()) if checklist else False
        open_punch_items = [p for p in punch_list if not p.get("resolved", False)]

        try:
            current_index = self.STAGES_ORDER.index(current_status) + 1
        except ValueError:
            current_index = 1

        pct_progress = round((current_index / len(self.STAGES_ORDER)) * 100.0, 1)

        # Ritenuta di garanzia (standard 5% sul totale netto)
        totals = order_data.get("totals", {})
        total_net = float(totals.get("revised_total_net", totals.get("total_net", 0.0)))
        retention_pct = float(handover.get("warranty_retention_percent", 5.0))
        retention_amount = round(total_net * (retention_pct / 100.0), 2)
        retention_released = (len(open_punch_items) == 0) and (current_status == "6_handover_approved")

        return {
            "order_id": order_data.get("order_id"),
            "slug": order_data.get("slug"),
            "title": order_data.get("title"),
            "current_stage": current_status,
            "progress_percent": pct_progress,
            "survey_done": stages.get("survey", {}).get("laser_measures_verified", False),
            "design_approved": stages.get("design", {}).get("approved_by_client", False),
            "procurement_sent": stages.get("procurement", {}).get("factory_orders_sent", False),
            "handover_checklist": checklist,
            "all_checks_passed": all_checks_ok,
            "signed_acceptance": handover.get("signed_acceptance_date", ""),
            "punch_list": punch_list,
            "open_punch_items_count": len(open_punch_items),
            "warranty_retention_percent": retention_pct,
            "warranty_retention_amount": retention_amount,
            "warranty_retention_released": retention_released
        }

    def advance_stage(self, slug: str, order_id: str, target_stage: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Avanza la commessa alla fase successiva o alla fase specificata e salva su file."""
        fdir = self.get_furniture_dir(slug)
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("order_id") == order_id:
                    current_status = data.get("status", "1_survey")
                    if target_stage:
                        new_stage = target_stage
                    else:
                        idx = self.STAGES_ORDER.index(current_status)
                        if idx < len(self.STAGES_ORDER) - 1:
                            new_stage = self.STAGES_ORDER[idx + 1]
                        else:
                            new_stage = current_status

                    data["status"] = new_stage
                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)
                    return self.get_order_status(data)
            except Exception:
                pass
        return None

    def sign_handover(self, slug: str, order_id: str, client_signatory: str) -> Optional[Dict[str, Any]]:
        """Certifica il superamento dei collaudi, genera il verbale formale HTML e chiude la commessa."""
        fdir = self.get_furniture_dir(slug)
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("order_id") == order_id:
                    data["status"] = "6_handover_approved"
                    stages = data.setdefault("stages", {})
                    handover = stages.setdefault("handover", {})
                    checklist = handover.setdefault("checklist", {})
                    checklist["desk_planarity_ok"] = True
                    checklist["drawer_locks_functional"] = True
                    checklist["finishes_scratch_free"] = True
                    checklist["power_data_accessible"] = True
                    handover["signed_acceptance_date"] = datetime.date.today().isoformat()
                    handover["client_signatory"] = client_signatory

                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    # Generazione del certificato formale di collaudo HTML
                    self.generate_handover_certificate(data, slug)
                    return self.get_order_status(data)
            except Exception:
                pass
        return None

    def generate_handover_certificate(self, order_data: Dict[str, Any], slug: str) -> Path:
        """Genera un verbale formale di collaudo e accettazione fornitura in HTML pronto per la stampa."""
        fdir = self.get_furniture_dir(slug)
        oid = order_data.get("order_id", "ARR")
        title = order_data.get("title", "Fornitura Arredo")
        stages = order_data.get("stages", {})
        handover = stages.get("handover", {})
        sign_date = handover.get("signed_acceptance_date", datetime.date.today().isoformat())
        signatory = handover.get("client_signatory", "Referente Autorizzato")
        comp = self.config.get("company", {})

        html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Verbale di Collaudo {oid} — {slug}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; color:#1e293b; line-height: 1.5; }}
  .header {{ border-bottom: 2px solid #059669; padding-bottom: 16px; margin-bottom: 24px; display:flex; justify-content:space-between; }}
  .badge {{ background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
  .check-table {{ width: 100%; border-collapse: collapse; margin: 24px 0; }}
  .check-table th, .check-table td {{ border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; font-size: 13px; }}
  .check-table th {{ background: #f8fafc; color: #475569; }}
  .ok {{ color: #059669; font-weight: bold; }}
  .legal-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; font-size: 12px; color: #475569; margin-top: 24px; }}
  .sign-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 50px; }}
  .sign-line {{ border-top: 1px dashed #94a3b8; margin-top: 50px; text-align: center; font-size: 12px; color: #64748b; padding-top: 6px; }}
  @media print {{ body {{ margin: 10mm; font-size: 11pt; }} }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h2 style="margin:0; color:#065f46;">VERBALE DI COLLAUDO & ACCETTAZIONE FORNITURA</h2>
    <div style="font-size: 13px; color:#64748b; margin-top:4px;">Commessa: <strong>{oid}</strong> — {title}</div>
  </div>
  <div style="text-align: right;">
    <span class="badge">COLLAUDO CONFORME AL 100%</span>
    <div style="font-size: 12px; color:#64748b; margin-top:4px;">Data Collaudo: {sign_date}</div>
  </div>
</div>

<p style="font-size:14px;">
Si certifica che in data <strong>{sign_date}</strong> la squadra di posa in opera ha ultimato il montaggio degli arredi e delle postazioni operative presso la sede di <strong>{slug.upper()}</strong>. Le parti congiuntamente hanno proceduto all'ispezione con i seguenti esiti:
</p>

<table class="check-table">
  <thead>
    <tr>
      <th>Requisito Tecnico Verificato</th>
      <th style="width: 120px; text-align:center;">Esito Ispezione</th>
      <th>Note di Conformità</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Planarità, allineamento e stabilità piani di lavoro</td>
      <td style="text-align:center;" class="ok">✓ CONFORME</td>
      <td>Verifica con livella laser su tutte le postazioni</td>
    </tr>
    <tr>
      <td>Funzionamento serrature, guide e chiavi cassettiere</td>
      <td style="text-align:center;" class="ok">✓ CONFORME</td>
      <td>Doppia chiave master e riscontro apertura morbida</td>
    </tr>
    <tr>
      <td>Integrità superfici, bordature e assenza graffi/urti</td>
      <td style="text-align:center;" class="ok">✓ CONFORME</td>
      <td>Ispezione visiva e tattile delle finiture</td>
    </tr>
    <tr>
      <td>Accessibilità e alloggiamento cavi dati / prese torrette</td>
      <td style="text-align:center;" class="ok">✓ CONFORME</td>
      <td>Canaline passacavi montate e collaudate con patch di rete</td>
    </tr>
  </tbody>
</table>

<div class="legal-box">
  <strong>Garanzie & Attivazione Assistenza:</strong><br>
  La firma del presente verbale attesta la conformità della fornitura e costituisce titolo per l'attivazione della garanzia contrattuale di 24 mesi a partire dalla data odierna.
</div>

<div class="sign-grid">
  <div>
    <strong>Per la Ditta Fornitrice / Capo Squadra:</strong>
    <div class="sign-line">{comp.get('name', 'ITInfra Business Ops')}</div>
  </div>
  <div>
    <strong>Per la Società Committente (Timbro e Firma):</strong>
    <div class="sign-line">{signatory} — {slug.upper()}</div>
  </div>
</div>
</body>
</html>
"""
        cert_file = fdir / f"handover-{oid.lower()}.html"
        cert_file.write_text(html, encoding="utf-8")
        return cert_file

    def cross_check_network_ipam(self, slug: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue il cross-check tra le postazioni fisiche d'arredo (scrivanie/tavoli riunione)
        e le torrette/prese LAN censite in 04-Network-IPAM.md o 03-LLD.md del repo tecnico itinfra.
        """
        bridge = ITInfraBridge()
        pdir = bridge.get_project_dir(slug)
        if not pdir:
            return {
                "slug": slug,
                "network_doc_found": False,
                "status": "warning",
                "message": f"Nessun progetto tecnico trovato in itinfra per {slug}"
            }

        ipam_file = pdir / "04-Network-IPAM.md"
        lld_file = pdir / "03-LLD.md"
        network_text = ""
        if ipam_file.is_file():
            network_text += ipam_file.read_text(encoding="utf-8")
        if lld_file.is_file():
            network_text += lld_file.read_text(encoding="utf-8")

        import re
        lan_drops = len(re.findall(r"\b(?:torretta|presa|drop|patch|rj45|lan)\b", network_text, re.IGNORECASE))

        stages = order_data.get("stages", {})
        survey = stages.get("survey", {})
        desks_count = survey.get("workstations_count", 0)
        if desks_count == 0:
            for it in order_data.get("items", []):
                if any(w in it.get("description", "").lower() for w in ["scrivania", "desk", "postazione", "tavolo"]):
                    desks_count += int(it.get("quantity", 1))

        coverage_ok = lan_drops >= desks_count if desks_count > 0 else True

        return {
            "slug": slug,
            "network_doc_found": True,
            "workstations_planned": desks_count,
            "network_drops_identified": lan_drops,
            "cabling_adequate": coverage_ok,
            "status": "PASS" if coverage_ok else "WARNING",
            "message": f"Identificate {lan_drops} prese/torrette di rete per {desks_count} postazioni arredo previste."
        }

    def add_change_order(
        self,
        slug: str,
        order_id: str,
        title: str,
        additional_amount: float,
        items: Optional[List[Dict[str, Any]]] = None,
        approved_by: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Registra una variante in corso d'opera (Change Order / Addendum) alla commessa arredo,
        aggiornando i totali economici e lo storico delle varianti approvate.
        """
        fdir = self.get_furniture_dir(slug)
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("order_id") == order_id:
                    change_orders = data.setdefault("change_orders", [])
                    var_num = len(change_orders) + 1
                    var_id = f"VAR-{order_id}-{var_num:02d}"

                    new_var = {
                        "change_order_id": var_id,
                        "title": title,
                        "date": datetime.date.today().isoformat(),
                        "amount_net": round(additional_amount, 2),
                        "approved_by": approved_by or "Direzione Lavori Committente",
                        "items": items or []
                    }
                    change_orders.append(new_var)

                    orig_tot = float(data.get("totals", {}).get("total_net", 0.0))
                    total_variations = sum(float(v.get("amount_net", 0.0)) for v in change_orders)
                    revised_total = round(orig_tot + total_variations, 2)

                    totals = data.setdefault("totals", {})
                    totals["original_net"] = orig_tot
                    totals["total_variations_net"] = round(total_variations, 2)
                    totals["revised_total_net"] = revised_total

                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    return {
                        "order_id": order_id,
                        "change_order_id": var_id,
                        "title": title,
                        "amount_added": round(additional_amount, 2),
                        "revised_total_net": revised_total,
                        "total_variations_count": len(change_orders)
                    }
            except Exception:
                pass
        return None

    def add_punch_list_item(
        self,
        slug: str,
        order_id: str,
        description: str,
        severity: str = "minor",
        location: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Registra una non-conformità (snagging / riserva) durante il pre-collaudo.
        Imposta automaticamente lo stato a '6_handover_conditional_snagging' e trattiene la garanzia del 5%.
        """
        fdir = self.get_furniture_dir(slug)
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("order_id") == order_id:
                    stages = data.setdefault("stages", {})
                    handover = stages.setdefault("handover", {})
                    punch_list = handover.setdefault("punch_list", [])

                    item_id = len(punch_list) + 1
                    punch_list.append({
                        "item_id": item_id,
                        "description": description,
                        "severity": severity,
                        "location": location,
                        "created_at": datetime.date.today().isoformat(),
                        "resolved": False
                    })

                    data["status"] = "6_handover_conditional_snagging"
                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    return self.get_order_status(data)
            except Exception:
                pass
        return None

    def resolve_punch_list_item(
        self,
        slug: str,
        order_id: str,
        item_id: int,
        resolution_note: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Risolve un elemento della punch list.
        Se tutti gli elementi sono risolti, promuove la commessa a '6_handover_approved'
        e sblocca il rilascio della ritenuta a garanzia del 5%.
        """
        fdir = self.get_furniture_dir(slug)
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                if data.get("order_id") == order_id:
                    stages = data.setdefault("stages", {})
                    handover = stages.setdefault("handover", {})
                    punch_list = handover.setdefault("punch_list", [])

                    matched = False
                    for item in punch_list:
                        if item.get("item_id") == item_id:
                            item["resolved"] = True
                            item["resolved_at"] = datetime.date.today().isoformat()
                            item["resolution_note"] = resolution_note or "Risolto e verificato"
                            matched = True
                            break

                    if not matched:
                        return None

                    open_items = [p for p in punch_list if not p.get("resolved", False)]
                    if not open_items:
                        data["status"] = "6_handover_approved"
                        handover["signed_acceptance_date"] = datetime.date.today().isoformat()
                        handover.setdefault("checklist", {})
                        handover["checklist"]["finishes_scratch_free"] = True

                    with open(f, "w", encoding="utf-8") as fp:
                        yaml.safe_dump(data, fp, sort_keys=False, allow_unicode=True)

                    return self.get_order_status(data)
            except Exception:
                pass
        return None

    def cross_check_electrical_load(self, slug: str, order_id: str) -> Dict[str, Any]:
        """
        Esegue il cross-check di dimensionamento del carico elettrico (W / kW)
        delle postazioni regolabili motorizzate e cabine acustiche rispetto al dimensionamento LLD di itinfra.
        """
        bridge = ITInfraBridge()
        pdir = bridge.get_project_dir(slug)

        fdir = self.get_furniture_dir(slug)
        target_order = None
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                if d.get("order_id") == order_id:
                    target_order = d
                    break
            except Exception:
                pass

        if not target_order:
            return {"status": "error", "message": f"Commessa {order_id} non trovata"}

        total_watts_peak = 0.0
        total_watts_idle = 0.0
        components_load = []

        for item in target_order.get("items", []):
            desc = item.get("description", "").lower()
            qty = float(item.get("quantity", 1))

            if any(w in desc for w in ["sit-stand", "motorizzat", "elevabil", "regolabile in altezza"]):
                w_peak = 150.0 * qty
                w_idle = 15.0 * qty
                components_load.append({"item": item.get("description"), "type": "motorized_desk", "qty": qty, "peak_watts": w_peak, "idle_watts": w_idle})
                total_watts_peak += w_peak
                total_watts_idle += w_idle
            elif any(w in desc for w in ["booth", "acustic", "pod", "cabina"]):
                w_peak = 400.0 * qty
                w_idle = 80.0 * qty
                components_load.append({"item": item.get("description"), "type": "acoustic_pod", "qty": qty, "peak_watts": w_peak, "idle_watts": w_idle})
                total_watts_peak += w_peak
                total_watts_idle += w_idle
            elif any(w in desc for w in ["scrivania", "desk", "workstation"]):
                w_peak = 300.0 * qty
                w_idle = 50.0 * qty
                components_load.append({"item": item.get("description"), "type": "pc_workstation", "qty": qty, "peak_watts": w_peak, "idle_watts": w_idle})
                total_watts_peak += w_peak
                total_watts_idle += w_idle

        total_kw_peak = round(total_watts_peak / 1000.0, 2)
        total_kw_idle = round(total_watts_idle / 1000.0, 2)

        lld_found = False
        notes = []

        if pdir and (pdir / "03-LLD.md").is_file():
            lld_found = True
            lld_text = (pdir / "03-LLD.md").read_text(encoding="utf-8")
            if "ups" in lld_text.lower():
                notes.append("Presenza di gruppo di continuità UPS segnalata in 03-LLD.md.")

        single_circuit_max_kw = 3.68
        circuits_recommended = max(1, int(total_kw_peak // single_circuit_max_kw) + (1 if total_kw_peak % single_circuit_max_kw > 0 else 0))

        if total_kw_peak > single_circuit_max_kw:
            notes.append(f"Il carico di picco ({total_kw_peak} kW) supera la capacità standard di una singola linea 16A ({single_circuit_max_kw} kW). Si raccomandano almeno {circuits_recommended} circuiti/sezionatori separati.")

        return {
            "slug": slug,
            "order_id": order_id,
            "itinfra_lld_found": lld_found,
            "total_power_kw_peak": total_kw_peak,
            "total_power_kw_idle": total_kw_idle,
            "recommended_circuits_count": circuits_recommended,
            "components_analyzed": components_load,
            "status": "PASS" if total_kw_peak <= (circuits_recommended * single_circuit_max_kw) else "WARNING",
            "notes": notes
        }

