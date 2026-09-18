#!/usr/bin/env python3
"""
itinfra-business-ops — Master CLI Dispatcher (it-ops v0.3.0)
Governance Operativa, Commerciale, Contratti SLA, MPS e Arredo Ufficio.
"""

import argparse
import datetime
import json
import os
import sys
import yaml
from pathlib import Path

# Configura encoding UTF-8 su Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Assicura import corretti
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.core.config import get_clients_dir, get_templates_dir, load_config
from scripts.core.bridge import ITInfraBridge
from scripts.core.validator import validate_yaml_file
from scripts.pipelines.contracts import ContractsPipeline
from scripts.pipelines.reports import ReportsPipeline
from scripts.pipelines.billing import BillingPipeline
from scripts.pipelines.jira_sync import JiraSyncPipeline
from scripts.pipelines.quotes import QuotesPipeline
from scripts.pipelines.mps import MPSPipeline
from scripts.pipelines.furniture import FurniturePipeline
from scripts.pipelines.ingestion import DocumentIngestionPipeline
from scripts.pipelines.onboard import OnboardPipeline
from scripts.pipelines.mission_control import MissionControlPipeline
from scripts.core.swarm import Auditor231Agent, FinanceReconcilerAgent, InfrastructureSentinelAgent, ContractGuardianAgent, DeterministicSwarm
from scripts.pipelines.quote_simulator import QuoteSimulatorPipeline
from scripts.pipelines.daemon import MPSDaemon, SLADaemon

def cmd_init(args):
    slug = args.slug.strip().lower()
    client_name = args.client or slug.replace("-", " ").title()
    clients_dir = get_clients_dir()
    target_dir = clients_dir / slug

    if target_dir.exists():
        print(f"[!] Cartella cliente già esistente: {target_dir}")
        return 1

    subdirs = ["contracts", "timesheets", "invoices", "quotes", "mps", "furniture"]
    for s in subdirs:
        (target_dir / s).mkdir(parents=True, exist_ok=True)

    templates_dir = get_templates_dir()
    replacements = {
        "{{SLUG}}": slug,
        "{{CLIENT_NAME}}": client_name,
        "{{CURRENT_DATE}}": datetime.date.today().isoformat(),
        "{{DATE_COMPACT}}": datetime.date.today().strftime("%Y%m%d"),
        "{{YEAR}}": str(datetime.date.today().year),
        "{{VALID_UNTIL_DATE}}": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
        "{{ID}}": "001"
    }

    def copy_template(tmpl_name, dest_file):
        src = templates_dir / tmpl_name
        if src.exists():
            content = src.read_text(encoding="utf-8")
            for k, v in replacements.items():
                content = content.replace(k, v)
            dest_file.write_text(content, encoding="utf-8")

    copy_template("client-manifest.template.yaml", target_dir / "client-manifest.yaml")
    copy_template("contract.template.yaml", target_dir / "contracts" / f"ctr-{slug}-{datetime.date.today().year}.yaml")
    copy_template("report.template.yaml", target_dir / "timesheets" / f"rap-{datetime.date.today().strftime('%Y%m%d')}-001.yaml")
    copy_template("mps-contract.template.yaml", target_dir / "mps" / f"mps-{slug}-01.yaml")
    copy_template("furniture-order.template.yaml", target_dir / "furniture" / f"arr-{slug}-01.yaml")
    copy_template("quote.template.yaml", target_dir / "quotes" / f"quote-{slug}-01.yaml")

    print(f"[✓] Cliente '{client_name}' inizializzato con successo!")
    print(f"    Percorso: {target_dir}")
    print(f"    Sottocartelle: {', '.join(subdirs)}")
    return 0

def cmd_status(args):
    slug = args.slug.strip().lower()
    clients_dir = get_clients_dir()
    client_dir = clients_dir / slug

    if not client_dir.exists():
        print(f"[ERRORE] Cliente '{slug}' non trovato in {clients_dir}")
        return 1

    print("=" * 70)
    print(f" 🏢 SCHEDA ESECUTIVA CLIENTE: {slug.upper()}")
    print("=" * 70)

    mfile = client_dir / "client-manifest.yaml"
    if mfile.exists():
        with open(mfile, "r", encoding="utf-8") as fp:
            manifest = yaml.safe_load(fp) or {}
            print(f" Ragione Sociale : {manifest.get('client_name')}")
            print(f" P.IVA / SDI     : {manifest.get('billing_info', {}).get('vat_id')} / {manifest.get('billing_info', {}).get('sdi_code')}")
            print(f" Termini Pagam.  : {manifest.get('billing_info', {}).get('payment_terms')}")
            mods = [k for k, v in manifest.get("modules", {}).items() if v]
            print(f" Moduli Attivi   : {', '.join(mods)}")

    bridge = ITInfraBridge()
    has_tech = bridge.project_exists(slug)
    tech_icon = "✓ Connesso" if has_tech else "✗ Non presente in itinfra"
    print(f" Ground Truth IT : {tech_icon} (../itinfra/projects/{slug})")
    if has_tech:
        serials = bridge.get_known_serials(slug)
        print(f" Apparati As-Built: {len(serials)} seriali hardware rilevati")

    cp = ContractsPipeline()
    c_summary = cp.get_contract_summary(slug)
    print("\n--- [A] Contratti SLA & Monte Ore ---")
    print(f" Contratti Totali: {c_summary['total_contracts']} (Attivi: {len(c_summary['active_contracts'])})")
    for act in c_summary["active_contracts"]:
        print(f"  • {act['contract_id']} [{act['formula']}]: Ore {act['consumed_hours']}/{act['total_hours']} (Residue: {act['remaining_hours']} h)")
    for alert in c_summary["alerts"]:
        print(f"  ⚠️  {alert}")

    rp = ReportsPipeline()
    r_summary = rp.get_ledger_summary(slug)
    print("\n--- [B] Rendicontazione Interventi ---")
    print(f" Rapportini Totali : {r_summary['total_reports']}")
    print(f" Ore a Contratto   : {r_summary['contract_debit_hours']} h")
    print(f" Ore Spot da Fatt. : {r_summary['invoice_spot_hours']} h ({len(r_summary['unbilled_spot_reports'])} rapportini)")

    mp = MPSPipeline()
    mps_list = mp.list_mps_contracts(slug)
    print("\n--- [F] Parco Stampanti & Noleggio MPS ---")
    print(f" Multifunzione Attive: {len(mps_list)}")
    for m in mps_list:
        settlement = mp.calculate_settlement(m)
        print(f"  • {m.get('mps_contract_id')} ({m.get('device_info', {}).get('model')} - S/N: {settlement['serial_number']})")
        print(f"    Copie Semestre: Mono {settlement['mono_produced']} (Ecc: {settlement['mono_excess']}), Colore {settlement['color_produced']} (Ecc: {settlement['color_excess']})")
        for alert in settlement["alerts"]:
            print(f"    ⚠️  {alert}")

    fp = FurniturePipeline()
    orders = fp.list_orders(slug)
    if orders:
        print("\n--- [G] Commesse Fornitura Arredo ---")
        for o in orders:
            st = fp.get_order_status(o)
            print(f"  • {st['order_id']} '{st['title']}': Fase {st['current_stage']} ({st['progress_percent']}%)")
            ch_status = "TUTTI PASSATI" if st["all_checks_passed"] else "IN CORSO"
            print(f"    Collaudo Finale: {ch_status}")

    print("=" * 70)
    return 0

def cmd_check(args):
    slug = args.slug.strip().lower()
    cp = ContractsPipeline()
    res = cp.check_asset_coverage(slug)

    print(f"🔍 Cross-Check Apparati As-Built per '{slug}':")
    if not res["itinfra_project_found"]:
        print(f"[-] Nessun progetto tecnico trovato in ../itinfra/projects/{slug}")
        return 0

    print(f"[✓] Progetto itinfra trovato. Seriali censiti in As-Built: {len(res['itinfra_known_serials'])}")
    all_ok = True
    for c in res["checks"]:
        verified = c["verified_in_as_built"]
        status = "[✓ OK]" if verified else "[!] NON TROVATO IN AS-BUILT"
        if not verified:
            all_ok = False
        print(f"    {status} Contratto: {c['contract_id']} | Seriale: {c['serial_number']} | Ruolo: {c['role']}")

    if all_ok:
        print("\n[✓] Tutti gli apparati contrattuali risultano correttamente certificati nell'As-Built!")
    else:
        print("\n[!] Attenzione: uno o più apparati a contratto non risultano censiti nell'As-Built tecnico.")
    return 0

def cmd_contract(args):
    slug = args.slug.strip().lower()
    cp = ContractsPipeline()
    action = args.action or "status"

    if action == "audit":
        from scripts.pipelines.contract_audit import ContractAuditEngine
        target_str = getattr(args, "doc_path", None)
        target = Path(target_str) if target_str else Path("docs/severino-sla")
        if not target.exists():
            print(f"[ERRORE] Percorso da verificare non trovato: {target}")
            return 1
        res = ContractAuditEngine.audit_path(target)
        print("=" * 70)
        print(f" 🛡️  AUDIT QUALITÀ & CONFORMITÀ CONTRATTUALE (Settembre 2026)")
        print(f" Sorgente Analizzata: {res['source']}")
        print("=" * 70)
        print(f" Totale Rilievi Rilevati: {res['findings_count']}")
        print(f"   • Critici (Blocker)   : {res['summary']['critical']}")
        print(f"   • Elevati (High)      : {res['summary']['high']}")
        print(f"   • Medi / Warning      : {res['summary']['warning']}")
        print(f"   • Bassa priorità      : {res['summary']['low']}")
        print("-" * 70)
        for f in res["findings"]:
            sev_badge = f"[{f['severity']}]"
            print(f"\n{sev_badge:<12} {f['title']} ({f['category']})")
            print(f"  Descrizione: {f['description']}")
            print(f"  Azione/Fix : {f['recommendation']}")
        print("=" * 70)
        return 0

    if action == "renew":
        cid = args.contract_id
        if not cid:
            print("[ERRORE] Specificare il contract_id da rinnovare con --contract-id")
            return 1
        res = cp.renew_contract(slug, cid)
        if res:
            print(f"[✓] Bozza di rinnovo contrattuale creata con successo: {res.name}")
        else:
            print(f"[!] Contratto {cid} non trovato.")
        return 0

    if action == "export":
        cid = getattr(args, "contract_id", None) or getattr(args, "id", None)
        if not cid:
            contracts = cp.list_contracts(slug)
            if contracts:
                cid = contracts[0].get("contract_id", contracts[0]["_file"])
            else:
                print(f"[ERRORE] Nessun contratto trovato per {slug}")
                return 1
        fmts = args.format.split(",") if hasattr(args, "format") and args.format else None
        paths = cp.export_contract(slug, cid, formats=fmts)
        if paths:
            print(f"[✓] Contratto SLA esportato con successo per {cid}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
        else:
            print(f"[!] Impossibile esportare: contratto {cid} non trovato per {slug}.")
        return 0

    res = cp.get_contract_summary(slug)
    print(json.dumps(res, indent=2))
    return 0


def cmd_report(args):
    slug = args.slug.strip().lower()
    rp = ReportsPipeline()
    action = args.action or "list"

    if action == "new":
        if not args.tech or not args.desc or not args.clock_in or not args.clock_out:
            print("[ERRORE] Per creare un rapportino specificare: --tech, --desc, --in, --out")
            return 1
        assets = []
        if args.assets:
            for s in args.assets.split(","):
                assets.append({"serial_number": s.strip(), "role": "Apparato", "description": "Intervento"})

        spare_parts = []
        if args.parts:
            # Formato: CODE:Descrizione:Qta:Prezzo
            for item in args.parts.split(","):
                parts = item.split(":")
                if len(parts) >= 4:
                    spare_parts.append({
                        "code": parts[0].strip(),
                        "description": parts[1].strip(),
                        "quantity": float(parts[2].strip()),
                        "unit_price": float(parts[3].strip())
                    })

        rep = rp.create_report(
            slug=slug,
            technician=args.tech,
            description=args.desc,
            clock_in=args.clock_in,
            clock_out=args.clock_out,
            date_str=args.date,
            ledger_action=args.ledger_action or "debit_contract",
            impacted_assets=assets,
            customer_signed=args.signed,
            signer_name=args.signer or "",
            spare_parts=spare_parts
        )
        print(f"[✓] Rapportino creato con successo: {rep['report_id']}")
        print(f"    Ore Totali: {rep['total_hours_rounded']} h (A canone: {rep['debited_contract_hours']} h, Extra: {rep['extra_hours']} h)")
        print(f"    File generati: {rep['report_id'].lower()}.yaml e {rep['report_id'].lower()}.html (Firma Canvas Integrata)")
        return 0

    if action == "export":
        rid = getattr(args, "report_id", None) or getattr(args, "id", None)
        if not rid:
            reports = rp.list_reports(slug)
            if reports:
                rid = reports[-1].get("report_id", reports[-1]["_file"])
            else:
                print(f"[ERRORE] Nessun rapportino trovato per {slug}")
                return 1
        fmts = args.format.split(",") if hasattr(args, "format") and args.format else None
        paths = rp.export_report(slug, rid, formats=fmts)
        if paths:
            print(f"[✓] Rapportino di lavoro esportato con successo per {rid}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
        else:
            print(f"[!] Impossibile esportare: rapportino {rid} non trovato per {slug}.")
        return 0

    res = rp.get_ledger_summary(slug)
    print(json.dumps(res, indent=2))
    return 0


def cmd_billing(args):
    slug = args.slug.strip().lower()
    bp = BillingPipeline()
    action = args.action or "summary"

    if action == "generate":
        batch = bp.aggregate_monthly_batch(slug, period=args.period)
        paths = bp.save_batch(slug, batch)
        print(f"[✓] Batch di fatturazione generato e salvato con successo:")
        print(f"    JSON Batch : {paths['json']}")
        print(f"    FatturaPA  : {paths['xml']} (SDI v1.2 FPR12)")
        if "html" in paths:
            print(f"    HTML View  : {paths['html']} (Copia di Cortesia)")
        if "pdf" in paths:
            print(f"    PDF View   : {paths['pdf']} (Copia di Cortesia A4)")
        print(f"    Totale Doc : € {batch['invoice_draft']['totals']['total_gross']:.2f}")
        print(f"    Rate Scadenzario ({len(batch['scadenzario']['installments'])} rate):")
        for inst in batch['scadenzario']['installments']:
            print(f"      • Rata {inst['number']}: € {inst['amount']:.2f} scadenza {inst['due_date']} [{inst['status'].upper()}]")
        return 0

    if action in ("view", "render"):
        target_id = args.batch_id or args.period or ""
        paths = bp.render_invoice(slug, target_id)
        if paths:
            print(f"[✓] Documenti grafici generati con successo per {target_id or slug}:")
            print(f"    XML Sorgente : {paths.get('xml')}")
            print(f"    HTML Visual  : {paths.get('html')}")
            print(f"    PDF Cortesia : {paths.get('pdf')}")
        else:
            print(f"[!] Nessuna fattura XML trovata corrispondente a '{target_id}' per '{slug}'.")
        return 0

    if action == "pay":
        if not args.batch_id:
            print("[ERRORE] Specificare --batch-id per registrare il pagamento")
            return 1
        ok = bp.mark_installment_paid(slug, args.batch_id, installment_num=args.inst, tx_id=args.tx or "")
        if ok:
            print(f"[✓] Rata {args.inst} del batch {args.batch_id} segnata come PAGATA!")
        else:
            print(f"[!] Batch {args.batch_id} non trovato in invoices.")
        return 0

    batch = bp.aggregate_monthly_batch(slug, period=args.period)
    print(json.dumps(batch, indent=2))
    return 0

def cmd_jira(args):
    slug = args.slug.strip().lower()
    jp = JiraSyncPipeline()
    action = args.action or "schedule"

    if action == "schedule":
        if not args.issue or not args.summary or not args.start:
            print("[ERRORE] Per schedulare un appuntamento specificare: --issue, --summary, --start (es. 2026-09-20T09:00:00)")
            return 1
        rec = jp.create_appointment(
            slug=slug,
            issue_key=args.issue,
            summary=args.summary,
            start_dt=args.start,
            duration_hours=args.duration or 2.0,
            technician=args.tech or "Tecnico"
        )
        print(f"[✓] Appuntamento schedulato per {args.issue}:")
        print(f"    Data/Ora: {rec['appointment']['start_datetime']} &rarr; {rec['appointment']['end_datetime']}")
        print(f"    File ICS: appointment-{args.issue.lower()}.ics (Pronto per Outlook/Google Calendar)")
        return 0

    print(f"Nessuna azione specificata per Jira.")
    return 0

def cmd_mps(args):
    slug = args.slug.strip().lower()
    mp = MPSPipeline()
    action = args.action or "calculate"

    if action == "poll":
        res = mp.poll_device(slug, mps_id=args.id, ip_override=args.ip)
        if res.get("status") == "success":
            print(f"[✓] Telemetria SNMP acquisita con successo da {res['ip']}:")
            settlement = res["settlement"]
            print(f"    Copie Totali: Mono {settlement['mono_produced']} | Colore {settlement['color_produced']}")
            print(f"    Prossimo Conguaglio: € {settlement['total_settlement_next_period']:.2f}")
        else:
            print(f"[!] {res.get('message')}")
        return 0

    if action == "read":
        if not args.id or args.mono is None or args.color is None:
            print("[ERRORE] Specificare --id, --mono e --color per registrare la lettura contatori")
            return 1
        st = mp.record_reading(
            slug=slug,
            mps_id=args.id,
            mono_total=args.mono,
            color_total=args.color,
            toner_black=args.bk or 80,
            toner_cyan=args.c or 70,
            toner_magenta=args.m or 65,
            toner_yellow=args.y or 75
        )
        if st:
            print(f"[✓] Lettura contatori salvata per {args.id}!")
            print(f"    Copie Semestre: Mono {st['mono_produced']} (Ecc: {st['mono_excess']}), Colore {st['color_produced']} (Ecc: {st['color_excess']})")
            print(f"    Prossimo Conguaglio: € {st['total_settlement_next_period']:.2f}")
        return 0

    contracts = mp.list_mps_contracts(slug)
    results = [mp.calculate_settlement(c) for c in contracts]
    print(json.dumps(results, indent=2))
    return 0

def cmd_furniture(args):
    slug = args.slug.strip().lower()
    fp = FurniturePipeline()
    action = args.action or "status"

    if action == "advance":
        if not args.id:
            print("[ERRORE] Specificare l'ID commessa con --id (es. --id ARR-2026-SEVERINO-01)")
            return 1
        st = fp.advance_stage(slug, args.id, target_stage=args.stage)
        if st:
            print(f"[✓] Commessa {args.id} avanzata a: {st['current_stage']} (Avanzamento: {st['progress_percent']}%)")
        else:
            print(f"[!] Commessa {args.id} non trovata.")
        return 0

    if action == "sign":
        if not args.id or not args.signatory:
            print("[ERRORE] Specificare --id e --signatory per firmare il verbale di collaudo")
            return 1
        st = fp.sign_handover(slug, args.id, args.signatory)
        if st:
            print(f"[✓] Collaudo finale completato e controfirmato per {args.id}!")
            print(f"    Stato: {st['current_stage']} (100.0%) | Firmatario: {args.signatory}")
            print(f"    Generato Certificato: handover-{args.id.lower()}.html")
        return 0

    orders = fp.list_orders(slug)
    results = [fp.get_order_status(o) for o in orders]
    print(json.dumps(results, indent=2))
    return 0

def cmd_quote(args):
    slug = args.slug.strip().lower()
    qp = QuotesPipeline()
    action = args.action or "calculate"

    if action == "add-item":
        if not args.id or not args.cat or not args.desc or args.cost is None:
            print("[ERRORE] Specificare: --id, --cat, --desc, --cost [--markup, --qty, --sku]")
            return 1
        res = qp.add_item_to_quote(
            slug=slug,
            quote_id=args.id,
            category=args.cat,
            part_number=args.sku or "SKU-GEN",
            description=args.desc,
            quantity=args.qty or 1.0,
            unit_cost=args.cost,
            markup_percent=args.markup or 25.0
        )
        if res:
            print(f"[✓] Articolo aggiunto a {args.id}!")
            print(f"    Nuovo Totale Netto: € {res['totals']['total_net']:.2f} (Margine: {res['totals']['gross_margin_percent']}%)")
            print(f"    Aggiornata Offerta Formale: {args.id.lower()}.html")
        return 0

    if action == "audit":
        from scripts.pipelines.quote_audit import QuoteAuditEngine
        target_str = getattr(args, "doc_path", None)
        target = Path(target_str) if target_str else Path("docs/viola-preventivo")
        if not target.exists():
            print(f"[ERRORE] Percorso preventivo non trovato: {target}")
            return 1
        res = QuoteAuditEngine.audit_path(target)
        print("=" * 70)
        print(f" 🛡️  AUDIT QUALITÀ, CONGRUITA & COMPLIANCE PREVENTIVO (Settembre 2026)")
        print(f" Sorgente Analizzata: {res['source']}")
        print("=" * 70)
        print(f" Totale Rilievi Rilevati: {res['findings_count']}")
        print(f"   • Critici (Blocker)   : {res['summary']['critical']}")
        print(f"   • Elevati (High)      : {res['summary']['high']}")
        print(f"   • Medi / Warning      : {res['summary']['warning']}")
        print(f"   • Bassa priorità      : {res['summary']['low']}")
        print("-" * 70)
        for f in res["findings"]:
            sev_badge = f"[{f['severity']}]"
            print(f"\n{sev_badge:<12} {f['title']} ({f['category']})")
            print(f"  Descrizione: {f['description']}")
            print(f"  Azione/Fix : {f['recommendation']}")
        print("=" * 70)
        return 0

    if action == "ui":
        qsp = QuoteSimulatorPipeline()
        out_path = Path("clients") / slug / "quotes" / f"simulator-{slug}.html"
        qsp.generate_interactive_simulator(slug, quote_id=getattr(args, "id", None), output_path=out_path)
        print(f"[✓] Simulatore di preventivo interattivo generato: {out_path}")
        return 0

    if action == "export":
        if not args.id:
            print("[ERRORE] Specificare --id del preventivo da esportare")
            return 1
        fmts = args.format.split(",") if hasattr(args, "format") and args.format else None
        paths = qp.export_quote(slug, args.id, formats=fmts)
        if paths:
            print(f"[✓] Proposta commerciale formale esportata con successo per {args.id}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
        else:
            print(f"[!] Impossibile esportare: preventivo {args.id} non trovato per {slug}.")
        return 0

    qdir = qp.get_quotes_dir(slug)
    for qf in qdir.glob("*.yaml"):
        with open(qf, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
            calc = qp.calculate_quote(data)
            print(f"--- Preventivo: {calc.get('quote_id')} ---")
            print(f"Costo Totale: € {calc['totals']['total_cost']:.2f}")
            print(f"Vendita Netta: € {calc['totals']['total_net']:.2f}")
            print(f"Margine Lordo: € {calc['totals']['gross_margin_amount']:.2f} ({calc['totals']['gross_margin_percent']}%)")
    return 0

def cmd_ingest(args):
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERRORE] File o cartella documento non trovato: {file_path}")
        return 1

    ip = DocumentIngestionPipeline()
    slug = args.slug.strip().lower() if args.slug else None

    print("=" * 70)
    print(f" 📑 INGESTIONE DOCUMENTALE & VERIFICA EVIDENZE: {file_path.name}")
    print("=" * 70)

    try:
        res = ip.ingest_file(file_path, slug=slug)
    except Exception as e:
        print(f"[!] Errore durante l'ingestione del documento: {e}")
        return 1

    if args.as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    print(f" Tipo Documento Rilevato : {res['document_type']}")
    print(f" Protezione Allucinazioni: ATTIVA (Strict Evidence Extraction)")
    print("-" * 70)

    print("\n🔍 EVIDENZE CERTIFICATE ESTRATTE DAL DOCUMENTO:")
    for ev in res.get("evidence", []):
        st = ev["status"]
        if st == "VERIFIED":
            if ev["field"] in ("contract_audit", "quote_audit") and isinstance(ev["value"], list):
                header_title = "AUDIT QUALITÀ & CONGRUITÀ PREVENTIVO (Settembre 2026)" if ev["field"] == "quote_audit" else "AUDIT QUALITÀ & CONFORMITÀ NORMATIVA (Settembre 2026)"
                print(f"\n🛡️  {header_title} — {len(ev['value'])} rilievi individuati:")
                for item in ev["value"]:
                    print(f"    [{item['severity']}] {item['title']} ({item['category']})")
                    print(f"        └─ {item['description']}")
                    print(f"        └─ Raccomandazione: {item['recommendation']}")
                print()
                continue
            icon = "[✓ CERTIFICATO]"
            val_str = str(ev['value'])
            if len(val_str) > 60:
                val_str = val_str[:57] + "..."
            print(f"  {icon} {ev['field']:<25} = {val_str} (Conf: {ev['confidence']*100:.0f}%, Pag: {ev['page']})")
            if ev.get("matched_text"):
                snip = ev['matched_text'].replace('\n', ' ')
                if len(snip) > 70:
                    snip = snip[:67] + "..."
                print(f"      └─ Evidenza testo: \"{snip}\"")

    print("\n⚠️  CAMPI NON PRESENTI NEL DOCUMENTO (Zero-Hallucination Guard):")
    for ev in res.get("evidence", []):
        if ev["status"] == "NOT_FOUND":
            print(f"  [-] {ev['field']:<25} : NON PRESENTE nel testo")
            if ev.get("notes"):
                print(f"      └─ Nota: {ev['notes']}")

    if slug:
        audit_path = ip.clients_root / slug / "ingestion" / f"{file_path.stem.lower()}.audit.json"
        print(f"\n[✓] Report di audit peritale salvato in:")
        print(f"    {audit_path}")

    if args.apply:
        if not slug:
            print("\n[!] Specificare --slug per applicare i dati al cliente.")
            return 1
        target_price = float(args.target_price) if args.target_price else None
        force_audit = getattr(args, "force_audit", False)
        try:
            app_res = ip.apply_to_client(slug, res, target_price=target_price, force_audit=force_audit)
        except Exception as e:
            print(f"\n[!] Impossibile applicare le modifiche: {e}")
            return 1
        print(f"\n[✓] Applicazione deterministica completata su '{slug}':")
        for act in app_res.get("applied_actions", []):
            print(f"    • {act}")

    print("=" * 70)
    return 0

def cmd_export(args):
    slug = args.slug.strip().lower()
    doc_type = args.type.strip().lower()
    doc_id = getattr(args, "id", None)
    fmts = args.format.split(",") if hasattr(args, "format") and args.format else None

    if doc_type in ("quote", "preventivo"):
        qp = QuotesPipeline()
        if not doc_id:
            qdir = qp.get_quotes_dir(slug)
            qfiles = sorted(qdir.glob("*.yaml"))
            if qfiles:
                with open(qfiles[-1], "r", encoding="utf-8") as fp:
                    d = yaml.safe_load(fp) or {}
                doc_id = d.get("quote_id", qfiles[-1].stem)
            else:
                print(f"[ERRORE] Nessun preventivo trovato per {slug}")
                return 1
        paths = qp.export_quote(slug, doc_id, formats=fmts)
        if paths:
            print(f"[✓] Preventivo commerciale esportato con logo ufficiale per {doc_id}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
            return 0
        else:
            print(f"[!] Impossibile esportare: preventivo {doc_id} non trovato per {slug}.")
            return 1

    elif doc_type in ("contract", "contratto"):
        cp = ContractsPipeline()
        if not doc_id:
            cfiles = cp.list_contracts(slug)
            if cfiles:
                doc_id = cfiles[0].get("contract_id", cfiles[0]["_file"])
            else:
                print(f"[ERRORE] Nessun contratto trovato per {slug}")
                return 1
        paths = cp.export_contract(slug, doc_id, formats=fmts)
        if paths:
            print(f"[✓] Contratto SLA esportato con logo ufficiale per {doc_id}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
            return 0
        else:
            print(f"[!] Impossibile esportare: contratto {doc_id} non trovato per {slug}.")
            return 1

    elif doc_type in ("report", "rapportino"):
        rp = ReportsPipeline()
        if not doc_id:
            rfiles = rp.list_reports(slug)
            if rfiles:
                doc_id = rfiles[-1].get("report_id", rfiles[-1]["_file"])
            else:
                print(f"[ERRORE] Nessun rapportino trovato per {slug}")
                return 1
        paths = rp.export_report(slug, doc_id, formats=fmts)
        if paths:
            print(f"[✓] Rapportino di lavoro esportato con logo ufficiale per {doc_id}:")
            for fmt_name, p in paths.items():
                print(f"    • {fmt_name.upper():<5}: {p}")
            return 0
        else:
            print(f"[!] Impossibile esportare: rapportino {doc_id} non trovato per {slug}.")
            return 1

    print(f"[ERRORE] Tipo documento '{doc_type}' non supportato. Scegli tra: quote, contract, report")
    return 1

def cmd_validate(args):

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"[ERRORE] Percorso non trovato: {target_path}")
        return 1

    schema_map = {
        "client-manifest.yaml": "client-manifest.schema.yaml",
        "ctr-": "contract.schema.yaml",
        "rap-": "report.schema.yaml",
        "mps-": "mps.schema.yaml",
        "arr-": "furniture.schema.yaml",
        "quote-": "quote.schema.yaml",
        "ga-": "gap_analysis.schema.yaml",
    }

    files_to_check = []
    if target_path.is_file():
        files_to_check.append(target_path)
    else:
        files_to_check.extend(target_path.rglob("*.yaml"))

    total_valid = 0
    total_errors = 0

    for f in files_to_check:
        schema = None
        for k, v in schema_map.items():
            if k in f.name:
                schema = v
                break

        if not schema:
            continue

        ok, errors = validate_yaml_file(f, schema)
        if ok:
            print(f" [✓ PASS] {f.name} -> {schema}")
            total_valid += 1
        else:
            print(f" [✗ FAIL] {f.name} -> {schema}")
            for err in errors:
                print(f"          - {err}")
            total_errors += 1

    print(f"\nRiepilogo Validazione: {total_valid} PASS, {total_errors} FAIL")
    return 0 if total_errors == 0 else 1

def check_auto_sync_memory():
    """Verifica e sincronizza la memoria con il peer se necessario."""
    try:
        from scripts.core.memory_engine import MemoryEngine
        engine = MemoryEngine()
        if engine.peer_root:
            peer_reg_file = engine.peer_root / ".agents" / "memory" / "registry.yaml"
            if peer_reg_file.exists() and engine.registry_file.exists():
                if peer_reg_file.stat().st_mtime > engine.registry_file.stat().st_mtime:
                    engine.sync_with_peer()
    except Exception:
        pass

def cmd_learn(args):
    """Dispatcher per il sistema di memoria auto-correttiva e apprendimento attestato OKF v0.2."""
    from scripts.pipelines.learn import LearnPipeline
    pipeline = LearnPipeline()
    action = args.action
    if action == "list":
        return pipeline.list_nodes(domain=getattr(args, "domain", None))
    elif action == "attest":
        return pipeline.attest_node(args.id, attester=getattr(args, "by", "human:possumato"))
    elif action == "compile":
        return pipeline.compile_rules()
    elif action == "sync":
        return pipeline.sync_memory()
    elif action == "audit":
        return pipeline.audit_memory()
    elif action == "test":
        return pipeline.test_rules()
    elif action == "promotables":
        return pipeline.list_promotables()
    elif action == "promote":
        entry_id = getattr(args, "entry", None) or getattr(args, "id", None)
        if not entry_id:
            print("[ERRORE] Specificare l'ID della voce dello scratchpad con --entry (es. mem-bp01zt)")
            return 1
        node_id = getattr(args, "node_id", None) or getattr(args, "id", None)
        title = getattr(args, "title", None) or f"Regola {entry_id}"
        domain = getattr(args, "domain", "technical")
        return pipeline.promote_entry(
            entry_id=entry_id,
            domain=domain,
            node_id=node_id,
            title=title,
            guardrail=getattr(args, "guardrail", None),
            by=getattr(args, "by", "human:possumato"),
        )
    return 0

def cmd_gap(args):
    """Dispatcher per la pipeline di Gap Analysis & Compliance 231 (SPEC-19)."""
    from scripts.pipelines.gap_analysis import GapAnalysisPipeline
    pipeline = GapAnalysisPipeline()
    slug = args.slug
    action = args.action

    if action == "init":
        return pipeline.cmd_init(slug, title=getattr(args, "title", None))
    elif action == "status":
        return pipeline.cmd_status(slug)
    elif action == "interview":
        return pipeline.cmd_interview(
            slug,
            area=getattr(args, "area", None),
            notes=getattr(args, "notes", None),
            score=getattr(args, "score", 0.0)
        )
    elif action == "va":
        return pipeline.cmd_va(slug, finding_json=getattr(args, "finding", None))
    elif action == "calculate":
        return pipeline.cmd_calculate(slug)
    elif action == "remediation":
        return pipeline.cmd_remediation(slug)
    elif action == "report":
        return pipeline.cmd_report(slug)
    elif action == "check":
        return pipeline.cmd_check(slug)
    else:
        print(f"[ERRORE] Azione '{action}' non riconosciuta per gap.")
        return 1


def cmd_onboard(args):
    slug = args.slug.strip().lower()
    client_name = args.client or slug.replace("-", " ").title()
    vat_id = getattr(args, "vat", None)
    sdi_code = getattr(args, "sdi", None)
    subnet = getattr(args, "subnet", "192.168.10.0/24") or "192.168.10.0/24"
    tier = getattr(args, "tier", "gold") or "gold"
    domain = getattr(args, "domain", None)

    pipeline = OnboardPipeline()
    try:
        res = pipeline.onboard_client(
            slug=slug,
            client_name=client_name,
            vat_id=vat_id,
            sdi_code=sdi_code,
            primary_subnet=subnet,
            tier=tier,
            domain=domain
        )
    except Exception as e:
        print(f"[ERRORE ONBOARDING] {e}")
        return 1

    print("=" * 70)
    print(f" 🚀 ONBOARDING CLIENTE COMPLETATO: {res['client_name'].upper()}")
    print("=" * 70)
    print(f" Slug                  : {res['slug']}")
    print(f" P.IVA                 : {res['vat_id']}")
    print(f" Livello SLA           : {res['tier'].upper()} ({res['hours_allocated']}h incluse)")
    print(f" Subnet Primaria / GW  : {res['primary_subnet']} (GW: {res['gateway_ip']})")
    print(f" Cartella Business Ops : {res['business_ops_path']}")
    if res["itinfra_created"]:
        print(f" Cartella itinfra      : {res['itinfra_path']}")
        print(f" Cross-Check Status    : {res['cross_check_status']}")
        drift_txt = "[✓ ZERO-DRIFT CERTIFICATO]" if res["zero_drift_certified"] else "[!] VERIFICA MANUALE RICHIESTA"
        print(f" Certificazione Drift  : {drift_txt}")
    else:
        print(" [i] itinfra non presente, creato solo workspace business-ops.")
    print(f" Sigillo SHA-256       : {res['sha256_seal']}")
    print(f" File generati ({len(res['created_files'])}):")
    for f in res['created_files']:
        print(f"   • {f}")
    print("=" * 70)
    return 0

def cmd_hooks(args):
    action = args.action or "check"
    from scripts.hooks.git_guard import run_pre_commit, run_pre_push, install_hooks
    if action == "install":
        return install_hooks(both=getattr(args, "both", False))
    elif action == "check":
        r1 = run_pre_commit()
        r2 = run_pre_push()
        return 0 if (r1 == 0 and r2 == 0) else 1
    elif action == "pre-commit":
        return run_pre_commit()
    elif action == "pre-push":
        return run_pre_push()
    else:
        print(f"[ERRORE] Azione '{action}' non valida per hooks.")
        return 1

def cmd_mission_control(args):
    pipeline = MissionControlPipeline()
    if getattr(args, "html", False):
        out_p = getattr(args, "out", None) or Path("docs") / "mission-control.html"
        pipeline.render_html(output_path=out_p)
        print(f"[✓] Mission Control Dashboard HTML generata con successo: {out_p}")
        return 0
    else:
        print(pipeline.render_tui())
        return 0

def cmd_ui(args):
    pipeline = MissionControlPipeline()
    out_p = Path("docs") / "mission-control.html"
    pipeline.render_html(output_path=out_p)
    print(f"[✓] Mission Control Dashboard HTML aggiornata: {out_p}")
    return 0

def cmd_agent(args):
    agent_type = args.type.lower()
    slug = args.slug.strip().lower()
    as_json = getattr(args, "json", False)

    if agent_type == "audit-231":
        ag = Auditor231Agent()
        res = ag.run(slug)
    elif agent_type == "finance-reconciler":
        ag = FinanceReconcilerAgent()
        res = ag.run(slug)
    elif agent_type == "infrastructure-sentinel":
        ag = InfrastructureSentinelAgent()
        res = ag.run(slug)
    elif agent_type == "contract-guardian":
        ag = ContractGuardianAgent()
        res = ag.run(slug)
    elif agent_type == "swarm":
        sw = DeterministicSwarm()
        res = sw.execute_swarm(slug)
    else:
        print(f"[ERRORE] Tipo agente '{agent_type}' non riconosciuto.")
        return 1

    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print("=" * 70)
        print(f" 🤖 AGENT RESULT: {agent_type.upper()} ({slug})")
        print("=" * 70)
        for k, v in res.items():
            if isinstance(v, dict):
                print(f" {k}:")
                for sk, sv in v.items():
                    print(f"   • {sk}: {sv}")
            else:
                print(f" {k:<25}: {v}")
        print("=" * 70)
    return 0

def cmd_daemon(args):
    service = args.service.lower()
    interval = getattr(args, "interval", 3600) or 3600
    once = getattr(args, "once", False)

    if service == "mps":
        d = MPSDaemon()
        d.run_loop(interval_seconds=interval, once=once)
        return 0
    elif service == "sla":
        d = SLADaemon()
        d.run_loop(interval_seconds=interval, once=once)
        return 0
    else:
        print(f"[ERRORE] Servizio demone '{service}' non riconosciuto.")
        return 1


def cmd_skills(args):
    action = args.action or "list"
    from scripts.core.skills_manager import SkillsManager
    sm = SkillsManager()

    if action == "list":
        installed = sm.list_installed()
        print("=" * 70)
        print(f" 📦 SKILLS INSTALLATE NEL WORKSPACE ({len(installed)} totali)")
        print("=" * 70)
        for s in installed:
            desc_prev = (s['description'][:75] + "...") if len(s['description']) > 75 else s['description']
            print(f"  • {s['id']:<32} | {desc_prev}")
        print("=" * 70)
        return 0

    elif action == "search":
        query = getattr(args, "query", None) or getattr(args, "skill_id", "") or ""
        limit = getattr(args, "limit", 15) or 15
        results = sm.search(query, limit=limit)
        print("=" * 70)
        print(f" 🔍 RISULTATI RICERCA SKILLS CATALOG (Query: '{query}') — Trovate {len(results)}")
        print("=" * 70)
        for r in results:
            desc = r.get("description", "")
            desc_prev = (desc[:75] + "...") if len(desc) > 75 else desc
            print(f"  • {r.get('id'):<35} | {desc_prev}")
        print("-" * 70)
        print("  Per installare: .\\it-ops.cmd skills install <skill_id>")
        print("=" * 70)
        return 0

    elif action == "info":
        skill_id = getattr(args, "skill_id", None)
        if not skill_id:
            print("[ERRORE] Specificare l'ID della skill (es. .\\it-ops.cmd skills info c4-architecture-c4-architecture)")
            return 1
        info = sm.info(skill_id)
        if not info:
            print(f"[!] Skill '{skill_id}' non trovata nel catalogo.")
            return 1
        print("=" * 70)
        print(f" ℹ️  DETTAGLIO SKILL: {info.get('id')}")
        print("=" * 70)
        print(f" Nome       : {info.get('name', '')}")
        print(f" Categoria  : {info.get('category', 'N/A')}")
        print(f" Tags       : {', '.join(info.get('tags', []))}")
        print(f" Triggers   : {', '.join(info.get('triggers', []))}")
        print(f"\n Descrizione:\n {info.get('description', '')}")
        print("=" * 70)
        return 0

    elif action == "install":
        skill_id = getattr(args, "skill_id", None)
        if not skill_id:
            print("[ERRORE] Specificare l'ID della skill da installare")
            return 1
        is_global = getattr(args, "global_install", False)
        res = sm.install(skill_id, global_install=is_global)
        if res.get("success"):
            print(f"[✓] Skill '{res['skill_id']}' installata con successo!")
            print(f"    Percorso : {res['path']}")
            print(f"    Modalità : {'Globale' if res['global'] else 'Locale workspace'}")
        else:
            print(f"[!] Errore durante l'installazione: {res.get('error')}")
            return 1
        return 0

    elif action == "bundles":
        b = sm.list_bundles()
        print("=" * 70)
        print(" 📦 BUNDLES SKILLS DISPONIBILI (rmyndharis/antigravity-skills)")
        print("=" * 70)
        bundles = b.get("bundles", {})
        for bname, bdata in bundles.items():
            s_list = bdata.get("skills", []) if isinstance(bdata, dict) else bdata
            bdesc = bdata.get("description", "") if isinstance(bdata, dict) else ""
            print(f"  • {bname:<16} ({len(s_list)} skills): {', '.join(s_list[:5])}...")
            if bdesc:
                print(f"    Descrizione: {bdesc[:75]}...")
        print("=" * 70)
        return 0

    else:
        print(f"[ERRORE] Azione '{action}' non valida per skills.")
        return 1

def main():
    check_auto_sync_memory()
    parser = argparse.ArgumentParser(description="itinfra-business-ops CLI Master Engine (v0.3.0)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sottocomando da eseguire")

    # init
    p_init = subparsers.add_parser("init", help="Inizializza una nuova anagrafica cliente")
    p_init.add_argument("slug", help="Slug cliente")
    p_init.add_argument("--client", help="Ragione Sociale del cliente")
    p_init.set_defaults(func=cmd_init)

    # status
    p_status = subparsers.add_parser("status", help="Visualizza scheda esecutiva 360°")
    p_status.add_argument("slug", help="Slug cliente")
    p_status.set_defaults(func=cmd_status)

    # check
    p_check = subparsers.add_parser("check", help="Cross-check apparati con itinfra As-Built")
    p_check.add_argument("slug", help="Slug cliente")
    p_check.set_defaults(func=cmd_check)

    # contract
    p_contract = subparsers.add_parser("contract", help="Gestione contratti SLA e monte ore")
    p_contract.add_argument("slug", help="Slug cliente")
    p_contract.add_argument("action", nargs="?", default="status", choices=["status", "balance", "renew", "audit", "export"])
    p_contract.add_argument("--contract-id", "--id", dest="contract_id", help="ID contratto")
    p_contract.add_argument("--doc", "--doc-path", dest="doc_path", help="Percorso del documento contrattuale da verificare (default: docs/severino-sla)")
    p_contract.add_argument("--format", default="all", help="Formati di esportazione: all, pdf, docx (default: all)")
    p_contract.set_defaults(func=cmd_contract)

    # report
    p_report = subparsers.add_parser("report", help="Gestione rapportini e time tracking")
    p_report.add_argument("slug", help="Slug cliente")
    p_report.add_argument("action", nargs="?", default="list", choices=["list", "balance", "new", "export"])
    p_report.add_argument("--id", dest="report_id", help="ID del rapportino")
    p_report.add_argument("--tech", help="Nome tecnico incaricato")
    p_report.add_argument("--desc", help="Descrizione dettagliata intervento")
    p_report.add_argument("--in", dest="clock_in", help="Orario inizio (HH:MM)")
    p_report.add_argument("--out", dest="clock_out", help="Orario fine (HH:MM)")
    p_report.add_argument("--date", help="Data intervento (YYYY-MM-DD)")
    p_report.add_argument("--action-type", dest="ledger_action", choices=["debit_contract", "invoice_spot", "included_flat"], default="debit_contract")
    p_report.add_argument("--assets", help="Seriale apparati impattati separati da virgola")
    p_report.add_argument("--parts", help="Ricambi nel formato CODICE:Descrizione:Qta:PrezzoUnit, separati da virgola")
    p_report.add_argument("--signed", action="store_true", help="Segna come firmato dal cliente")
    p_report.add_argument("--signer", help="Nome referente cliente firmatario")
    p_report.add_argument("--format", default="all", help="Formati di esportazione: all, pdf, docx (default: all)")
    p_report.set_defaults(func=cmd_report)

    # billing
    p_billing = subparsers.add_parser("billing", help="Batch di fatturazione, scadenziario e viste cortesia")
    p_billing.add_argument("slug", help="Slug cliente")
    p_billing.add_argument("action", nargs="?", default="summary", choices=["summary", "generate", "pay", "view", "render"])
    p_billing.add_argument("--period", help="Periodo contabile YYYY-MM")
    p_billing.add_argument("--batch-id", "--invoice-id", dest="batch_id", help="ID del batch o della fattura da gestire/visualizzare")
    p_billing.add_argument("--inst", type=int, default=1, help="Numero rata (default: 1)")
    p_billing.add_argument("--tx", help="Identificativo transazione bancaria / CRO")
    p_billing.set_defaults(func=cmd_billing)

    # jira
    p_jira = subparsers.add_parser("jira", help="Sincronizzazione Jira & Calendario")
    p_jira.add_argument("slug", help="Slug cliente")
    p_jira.add_argument("action", nargs="?", default="schedule", choices=["schedule"])
    p_jira.add_argument("--issue", help="Key del task Jira (es. IT-142)")
    p_jira.add_argument("--summary", help="Titolo/Sintesi dell'intervento")
    p_jira.add_argument("--start", help="Data e ora inizio (YYYY-MM-DDTHH:MM:SS)")
    p_jira.add_argument("--duration", type=float, default=2.0, help="Durata in ore (default: 2.0)")
    p_jira.add_argument("--tech", help="Tecnico incaricato")
    p_jira.set_defaults(func=cmd_jira)

    # mps
    p_mps = subparsers.add_parser("mps", help="Gestione stampanti e costo copia")
    p_mps.add_argument("slug", help="Slug cliente")
    p_mps.add_argument("action", nargs="?", default="calculate", choices=["calculate", "read", "poll"])
    p_mps.add_argument("--id", help="ID contratto MPS")
    p_mps.add_argument("--ip", help="Indirizzo IP per interrogazione SNMP diretta")
    p_mps.add_argument("--mono", type=int, help="Lettura contatore mono totale")
    p_mps.add_argument("--color", type=int, help="Lettura contatore colore totale")
    p_mps.add_argument("--bk", type=int, help="Toner nero %")
    p_mps.add_argument("--c", type=int, help="Toner ciano %")
    p_mps.add_argument("--m", type=int, help="Toner magenta %")
    p_mps.add_argument("--y", type=int, help="Toner giallo %")
    p_mps.set_defaults(func=cmd_mps)

    # furniture
    p_furniture = subparsers.add_parser("furniture", help="Gestione commesse arredo ufficio")
    p_furniture.add_argument("slug", help="Slug cliente")
    p_furniture.add_argument("action", nargs="?", default="status", choices=["status", "advance", "sign"])
    p_furniture.add_argument("--id", help="ID commessa arredo")
    p_furniture.add_argument("--stage", help="Fase specifica a cui avanzare")
    p_furniture.add_argument("--signatory", help="Nome firmatario accettazione fornitura")
    p_furniture.set_defaults(func=cmd_furniture)

    # quote
    p_quote = subparsers.add_parser("quote", help="Preventivazione e margini")
    p_quote.add_argument("slug", help="Slug cliente")
    p_quote.add_argument("action", nargs="?", default="calculate", choices=["calculate", "add-item", "export", "audit", "ui"])
    p_quote.add_argument("--id", "--quote-id", dest="id", help="ID preventivo")
    p_quote.add_argument("--doc", "--doc-path", dest="doc_path", help="Percorso del preventivo o cartella da verificare (default: docs/viola-preventivo)")
    p_quote.add_argument("--cat", help="Categoria merceologica (hardware_server_network, professional_services, ecc.)")
    p_quote.add_argument("--sku", help="Codice articolo / SKU")
    p_quote.add_argument("--desc", help="Descrizione articolo")
    p_quote.add_argument("--cost", type=float, help="Costo acquisto unitario")
    p_quote.add_argument("--markup", type=float, default=25.0, help="Markup percentuale (default: 25%)")
    p_quote.add_argument("--qty", type=float, default=1.0, help="Quantità (default: 1.0)")
    p_quote.add_argument("--format", default="all", help="Formati di esportazione: all, html, pdf, docx (default: all)")
    p_quote.set_defaults(func=cmd_quote)

    # export
    p_export = subparsers.add_parser("export", help="Esportazione formale unificata documenti con logo ufficiale (quote, contract, report)")
    p_export.add_argument("slug", help="Slug cliente")
    p_export.add_argument("type", choices=["quote", "contract", "report", "preventivo", "contratto", "rapportino"], help="Tipologia di documento")
    p_export.add_argument("id", nargs="?", help="ID documento (opzionale: se omesso esporta il documento più recente)")
    p_export.add_argument("--format", default="all", help="Formati: all, pdf, docx, html (default: all)")
    p_export.set_defaults(func=cmd_export)

    # validate

    p_val = subparsers.add_parser("validate", help="Valida file YAML a fronte degli schemi")
    p_val.add_argument("target", help="File o cartella da validare")
    p_val.set_defaults(func=cmd_validate)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingestione deterministica PDF con verifica evidenze e audit anti-allucinazione")
    p_ingest.add_argument("file", help="Percorso del file PDF da analizzare")
    p_ingest.add_argument("--slug", help="Slug cliente da associare")
    p_ingest.add_argument("--apply", action="store_true", help="Applica i dati verificati all'anagrafica o preventivo")
    p_ingest.add_argument("--target-price", type=float, help="Prezzo di vendita desiderato (per distinte tecniche)")
    p_ingest.add_argument("--force-audit", action="store_true", help="Ignora i blocchi per rilievi critici emersi dall'audit di qualità/congruita")
    p_ingest.add_argument("--json", dest="as_json", action="store_true", help="Output in formato JSON")
    p_ingest.set_defaults(func=cmd_ingest)

    # learn
    p_learn = subparsers.add_parser("learn", help="Sistema di Memoria Auto-Correttiva & Apprendimento Attestato (OKF v0.2)")
    p_learn.add_argument("action", nargs="?", default="list", choices=["list", "attest", "compile", "sync", "audit", "test", "promotables", "promote"], help="Azione da eseguire (default: list)")
    p_learn.add_argument("--id", help="ID del nodo di memoria (es. LES-UI-001 o LES-NET-002)")
    p_learn.add_argument("--entry", help="ID voce scratchpad da promuovere (es. mem-bp01zt)")
    p_learn.add_argument("--domain", help="Filtra o assegna dominio (core, ui, engineering, documents, technical, business_ops)")
    p_learn.add_argument("--title", help="Titolo del guardrail per promote")
    p_learn.add_argument("--guardrail", help="Contenuto markdown personalizzato")
    p_learn.add_argument("--by", default="human:possumato", help="Certificatore attestation (default: human:possumato)")
    p_learn.set_defaults(func=cmd_learn)

    # gap
    p_gap = subparsers.add_parser("gap", help="Pipeline di Gap Analysis e Compliance D.Lgs. 231/2001 (SPEC-19)")
    p_gap.add_argument("slug", help="Slug cliente")
    p_gap.add_argument("action", nargs="?", default="status", choices=["status", "init", "interview", "va", "calculate", "remediation", "report", "check"], help="Azione da eseguire (default: status)")
    p_gap.add_argument("--title", help="Titolo dell'assessment (per init)")
    p_gap.add_argument("--area", help="Area canonica di intervista (ciso_security, it_operations, risk_compliance, procurement_contracts, facility_physical_security)")
    p_gap.add_argument("--notes", help="Note o verbali dell'intervista")
    p_gap.add_argument("--score", type=float, default=0.0, help="Punteggio evidenze (0-100)")
    p_gap.add_argument("--finding", help="Rilievo di Vulnerability Assessment (JSON o desc)")
    p_gap.set_defaults(func=cmd_gap)

    
    # onboard (Pipeline 11 - SPEC-20)
    p_onboard = subparsers.add_parser("onboard", help="Onboarding unificato cliente dual-repo (SPEC-20)")
    p_onboard.add_argument("slug", help="Slug cliente")
    p_onboard.add_argument("--client", help="Ragione Sociale del cliente")
    p_onboard.add_argument("--vat", help="Partita IVA")
    p_onboard.add_argument("--sdi", help="Codice Destinatario SDI")
    p_onboard.add_argument("--subnet", default="192.168.10.0/24", help="Subnet primaria CIDR (default: 192.168.10.0/24)")
    p_onboard.add_argument("--tier", choices=["silver", "gold", "platinum"], default="gold", help="Livello SLA (default: gold)")
    p_onboard.add_argument("--domain", help="Dominio Active Directory / LAN")
    p_onboard.set_defaults(func=cmd_onboard)

    # hooks (SPEC-20)
    p_hooks = subparsers.add_parser("hooks", help="Gestione Git Guard Hooks deterministici (SPEC-20)")
    p_hooks.add_argument("action", nargs="?", default="check", choices=["check", "install", "pre-commit", "pre-push"], help="Azione hook")
    p_hooks.add_argument("--both", action="store_true", help="Installa gli hook anche nel repository federato itinfra")
    p_hooks.set_defaults(func=cmd_hooks)

    # mission-control & ui (SPEC-20)
    p_mc = subparsers.add_parser("mission-control", aliases=["mc"], help="Mission Control Executive Dashboard 360° (SPEC-20)")
    p_mc.add_argument("--html", action="store_true", help="Genera ed esporta la dashboard HTML stand-alone")
    p_mc.add_argument("--out", help="Percorso di destinazione file HTML")
    p_mc.set_defaults(func=cmd_mission_control)

    p_ui = subparsers.add_parser("ui", help="Genera e visualizza la Mission Control Dashboard HTML (SPEC-20)")
    p_ui.set_defaults(func=cmd_ui)

    # agent (SPEC-20)
    p_agent = subparsers.add_parser("agent", help="Sciame Agenti Deterministici Bounded (SPEC-20)")
    p_agent.add_argument("type", choices=["audit-231", "finance-reconciler", "infrastructure-sentinel", "contract-guardian", "swarm"], help="Tipologia di agente")
    p_agent.add_argument("slug", help="Slug cliente")
    p_agent.add_argument("--json", action="store_true", help="Output in formato JSON")
    p_agent.set_defaults(func=cmd_agent)

    # daemon (SPEC-20)
    p_daemon = subparsers.add_parser("daemon", help="Demoni di monitoraggio proattivo in background (SPEC-20)")
    p_daemon.add_argument("service", choices=["mps", "sla"], help="Servizio demone da avviare")
    p_daemon.add_argument("--interval", type=int, default=3600, help="Intervallo di scansione in secondi (default: 3600)")
    p_daemon.add_argument("--once", action="store_true", help="Esegui un unico ciclo di controllo e termina")
    p_daemon.set_defaults(func=cmd_daemon)

    
    # skills (SPEC-20 Extension — rmyndharis/antigravity-skills)
    p_skills = subparsers.add_parser("skills", help="Gestore catalogo skills (rmyndharis/antigravity-skills)")
    p_skills.add_argument("action", nargs="?", default="list", choices=["list", "search", "info", "install", "bundles"], help="Azione da eseguire")
    p_skills.add_argument("skill_id", nargs="?", help="ID della skill (per info o install)")
    p_skills.add_argument("--query", "-q", help="Testo da cercare nel catalogo")
    p_skills.add_argument("--limit", type=int, default=15, help="Limite risultati ricerca (default: 15)")
    p_skills.add_argument("--global", dest="global_install", action="store_true", help="Installa a livello globale (~/.gemini/antigravity/skills/)")
    p_skills.set_defaults(func=cmd_skills)

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        return 0

    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
