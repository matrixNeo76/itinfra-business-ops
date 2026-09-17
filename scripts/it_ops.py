#!/usr/bin/env python3
"""
itinfra-business-ops — Master CLI Dispatcher (it-ops)
Gestione integrata Hub-and-Spoke per Contratti, Rapportini, Fatturazione, MPS e Arredo.
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

    # Scaffolding da template
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

    # 1. Manifest
    mfile = client_dir / "client-manifest.yaml"
    if mfile.exists():
        with open(mfile, "r", encoding="utf-8") as fp:
            manifest = yaml.safe_load(fp) or {}
            print(f" Ragione Sociale : {manifest.get('client_name')}")
            print(f" P.IVA / SDI     : {manifest.get('billing_info', {}).get('vat_id')} / {manifest.get('billing_info', {}).get('sdi_code')}")
            print(f" Termini Pagam.  : {manifest.get('billing_info', {}).get('payment_terms')}")
            mods = [k for k, v in manifest.get("modules", {}).items() if v]
            print(f" Moduli Attivi   : {', '.join(mods)}")

    # 2. Bridge itinfra
    bridge = ITInfraBridge()
    has_tech = bridge.project_exists(slug)
    tech_icon = "✓ Connesso" if has_tech else "✗ Non presente in itinfra"
    print(f" Ground Truth IT : {tech_icon} (../itinfra/projects/{slug})")
    if has_tech:
        serials = bridge.get_known_serials(slug)
        print(f" Apparati As-Built: {len(serials)} seriali hardware rilevati")

    # 3. Contratti SLA & Monte Ore
    cp = ContractsPipeline()
    c_summary = cp.get_contract_summary(slug)
    print("\n--- [A] Contratti SLA & Monte Ore ---")
    print(f" Contratti Totali: {c_summary['total_contracts']} (Attivi: {len(c_summary['active_contracts'])})")
    for act in c_summary["active_contracts"]:
        print(f"  • {act['contract_id']} [{act['formula']}]: Ore {act['consumed_hours']}/{act['total_hours']} (Residue: {act['remaining_hours']} h)")
    for alert in c_summary["alerts"]:
        print(f"  ⚠️  {alert}")

    # 4. Rapportini
    rp = ReportsPipeline()
    r_summary = rp.get_ledger_summary(slug)
    print("\n--- [B] Rendicontazione Interventi ---")
    print(f" Rapportini Totali : {r_summary['total_reports']}")
    print(f" Ore a Contratto   : {r_summary['contract_debit_hours']} h")
    print(f" Ore Spot da Fatt. : {r_summary['invoice_spot_hours']} h ({len(r_summary['unbilled_spot_reports'])} rapportini)")

    # 5. MPS Multifunzione
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

    # 6. Arredo Ufficio
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
    res = cp.get_contract_summary(slug)
    print(json.dumps(res, indent=2))
    return 0

def cmd_report(args):
    slug = args.slug.strip().lower()
    rp = ReportsPipeline()
    res = rp.get_ledger_summary(slug)
    print(json.dumps(res, indent=2))
    return 0

def cmd_mps(args):
    slug = args.slug.strip().lower()
    mp = MPSPipeline()
    contracts = mp.list_mps_contracts(slug)
    results = [mp.calculate_settlement(c) for c in contracts]
    print(json.dumps(results, indent=2))
    return 0

def cmd_billing(args):
    slug = args.slug.strip().lower()
    bp = BillingPipeline()
    batch = bp.aggregate_monthly_batch(slug)
    print(json.dumps(batch, indent=2))
    return 0

def cmd_furniture(args):
    slug = args.slug.strip().lower()
    fp = FurniturePipeline()
    orders = fp.list_orders(slug)
    results = [fp.get_order_status(o) for o in orders]
    print(json.dumps(results, indent=2))
    return 0

def cmd_quote(args):
    slug = args.slug.strip().lower()
    qp = QuotesPipeline()
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

def main():
    parser = argparse.ArgumentParser(description="itinfra-business-ops CLI Master Engine")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sottocomando da eseguire")

    # init
    p_init = subparsers.add_parser("init", help="Inizializza una nuova anagrafica cliente")
    p_init.add_argument("slug", help="Slug univoco del cliente (es. cliente-rossi-srl)")
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
    p_contract.set_defaults(func=cmd_contract)

    # report
    p_report = subparsers.add_parser("report", help="Gestione rapportini e time tracking")
    p_report.add_argument("slug", help="Slug cliente")
    p_report.set_defaults(func=cmd_report)

    # mps
    p_mps = subparsers.add_parser("mps", help="Gestione stampanti e costo copia")
    p_mps.add_argument("slug", help="Slug cliente")
    p_mps.set_defaults(func=cmd_mps)

    # billing
    p_billing = subparsers.add_parser("billing", help="Batch di fatturazione e scadenziario")
    p_billing.add_argument("slug", help="Slug cliente")
    p_billing.set_defaults(func=cmd_billing)

    # furniture
    p_furniture = subparsers.add_parser("furniture", help="Gestione commesse arredo ufficio")
    p_furniture.add_argument("slug", help="Slug cliente")
    p_furniture.set_defaults(func=cmd_furniture)

    # quote
    p_quote = subparsers.add_parser("quote", help="Preventivazione e margini")
    p_quote.add_argument("slug", help="Slug cliente")
    p_quote.set_defaults(func=cmd_quote)

    # validate
    p_val = subparsers.add_parser("validate", help="Valida file YAML a fronte degli schemi")
    p_val.add_argument("target", help="File o cartella da validare")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        return 0

    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
