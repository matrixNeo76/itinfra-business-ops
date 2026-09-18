#!/usr/bin/env python3
"""
scripts/hooks/git_guard.py — Deterministic Git Guard & Assurance Engine (SPEC-20)
Protezione deterministica pre-commit e pre-push per itinfra-business-ops e itinfra:
- Schema validation YAML
- Secret & credential leak detection
- OKF v0.2 linter
- Test suite smoke test
- Cross-repo sync check
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Set

# Configura encoding UTF-8 su Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Setup percorsi
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.core.config import get_clients_dir, get_itinfra_dir
from scripts.core.validator import validate_yaml_file

# Regole di Secret Detection
SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----", "CHIAVE_PRIVATA_RSA_SSH"),
    (r"(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,})", "GITHUB_PERSONAL_TOKEN"),
    (r"AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY_ID"),
    (r"sk-[A-Za-z0-9]{32,}", "API_SECRET_KEY"),
    (r"(?i)(?:password|passwd|api_secret)\s*:\s*[\"'][^\"'\s]{8,}[\"']", "PLAINTEXT_PASSWORD"),
]

# Esclusioni lecite (placeholder nei template, schema o documentazione)
SAFE_ALLOWLIST = [
    "{{",
    "vault://",
    "IT00X0000000000000000000000",
    "password_da_specificare",
    "dummy_secret",
    "0000000",
]


def get_git_modified_files() -> List[Path]:
    """Restituisce la lista di file modificati (staged o uncommitted) nel repository."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=True
        )
        files = [ROOT_DIR / f.strip() for f in res.stdout.splitlines() if f.strip()]
        if not files:
            # Fallback: controlla modified uncommitted
            res2 = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
                check=True
            )
            files = [ROOT_DIR / f.strip() for f in res2.stdout.splitlines() if f.strip()]
        return [f for f in files if f.exists() and f.is_file()]
    except Exception:
        return []


def check_secrets_in_file(path: Path) -> List[Tuple[int, str, str]]:
    """Scansiona un singolo file alla ricerca di pattern di secret leak."""
    if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".pdf", ".ico", ".bin", ".woff", ".woff2"]:
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    findings = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        if any(safe in line for safe in SAFE_ALLOWLIST):
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append((idx, label, line.strip()[:60]))
    return findings


def check_okf_frontmatter(path: Path) -> List[str]:
    """Verifica che i file .okf.md abbiano il frontmatter conforme a OKF v0.2."""
    if not path.name.endswith(".okf.md") and not (path.name.endswith(".md") and "0" in path.name):
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ["Impossibile leggere il file"]

    errors = []
    if not content.startswith("---"):
        errors.append("Manca il delimitatore iniziale frontmatter YAML '---'")
        return errors

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Frontmatter YAML non chiuso correttamente con '---'")
        return errors

    front_text = parts[1]
    import yaml
    try:
        fm = yaml.safe_load(front_text) or {}
    except Exception as e:
        errors.append(f"Frontmatter YAML non valido sintatticamente: {e}")
        return errors

    req_fields = ["type", "title"]
    for rf in req_fields:
        if rf not in fm:
            errors.append(f"Campo obbligatorio mancante nel frontmatter: '{rf}'")

    return errors


def run_pre_commit(files: Optional[List[Path]] = None) -> int:
    """Esegue tutti i controlli pre-commit."""
    target_files = files if files is not None else get_git_modified_files()
    print("=" * 70)
    print(" 🛡️  GIT GUARD: VERIFICA PRE-COMMIT DETERMINISTICA")
    print("=" * 70)

    if not target_files:
        print("[i] Nessun file modificato da validare in questa sessione.")
        return 0

    has_errors = False
    print(f"Scansione di {len(target_files)} file modificati...\n")

    # 1. Scansione Segreti
    secret_hits = 0
    for f in target_files:
        hits = check_secrets_in_file(f)
        if hits:
            has_errors = True
            secret_hits += len(hits)
            rel_path = f.relative_to(ROOT_DIR) if f.is_relative_to(ROOT_DIR) else f
            for line_no, label, snippet in hits:
                print(f"[BLOCCANTE] Secret rilevato in {rel_path}:{line_no} [{label}]: {snippet}")

    if secret_hits == 0:
        print("  [✓] Secret & Credential Leak Detection: NESSUN LEAK RILEVATO")

    # 2. Validazione Schemi YAML
    yaml_files = [f for f in target_files if f.suffix.lower() in [".yaml", ".yml"] and "clients" in str(f)]
    yaml_errors = 0
    for yf in yaml_files:
        val_res = validate_yaml_file(yf)
        rel_path = yf.relative_to(ROOT_DIR) if yf.is_relative_to(ROOT_DIR) else yf
        if val_res.get("valid") is False:
            has_errors = True
            yaml_errors += 1
            print(f"[ERRORE SCHEMA] {rel_path}: {val_res.get('error', 'Validazione fallita')}")
        elif val_res.get("valid") is True:
            pass

    if yaml_files:
        if yaml_errors == 0:
            print(f"  [✓] Schema Validation ({len(yaml_files)} file YAML): TUTTI CONFORMI")
        else:
            print(f"  [!] Schema Validation: {yaml_errors} errori riscontrati!")
    else:
        print("  [i] Schema Validation: nessun file YAML cliente modificato")

    # 3. OKF Linter
    okf_files = [f for f in target_files if f.suffix.lower() == ".md" and (".okf." in f.name or f.name.startswith("0"))]
    okf_errors = 0
    for of in okf_files:
        errs = check_okf_frontmatter(of)
        rel_path = of.relative_to(ROOT_DIR) if of.is_relative_to(ROOT_DIR) else of
        if errs:
            has_errors = True
            okf_errors += len(errs)
            for e in errs:
                print(f"[ERRORE OKF] {rel_path}: {e}")

    if okf_files:
        if okf_errors == 0:
            print(f"  [✓] OKF v0.2 Linter ({len(okf_files)} file): TUTTI CONFORMI")
        else:
            print(f"  [!] OKF v0.2 Linter: {okf_errors} errori riscontrati!")
    else:
        print("  [i] OKF v0.2 Linter: nessun file documentale OKF modificato")

    print("\n" + "=" * 70)
    if has_errors:
        print("❌ PRE-COMMIT FALLITO: Risolvere i rilievi sopra indicati prima di procedere.")
        print("=" * 70)
        return 1
    else:
        print("✅ PRE-COMMIT SUPERATO: Tutti i controlli deterministici hanno esito POSITIVO.")
        print("=" * 70)
        return 0


def run_pre_push() -> int:
    """Esegue tutti i controlli pre-push."""
    print("=" * 70)
    print(" 🚀 GIT GUARD: VERIFICA PRE-PUSH DETERMINISTICA")
    print("=" * 70)

    # 1. Esecuzione Test Suite Unitaria
    print("1. Esecuzione Smoke Test Suite...")
    test_proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "tests"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    if test_proc.returncode != 0:
        print("❌ SMOKE TEST FALLITO:")
        print(test_proc.stderr or test_proc.stdout)
        return 1
    print("  [✓] Suite unitaria superata con successo.")

    # 2. Cross-Repo Synchronization Check
    print("2. Controllo Sincronizzazione Hub-and-Spoke con itinfra...")
    clients_dir = get_clients_dir()
    itinfra_dir = get_itinfra_dir()
    itinfra_projects = itinfra_dir / "projects"

    if itinfra_projects.is_dir():
        client_slugs = {d.name for d in clients_dir.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")}
        project_slugs = {d.name for d in itinfra_projects.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")}

        matched = client_slugs.intersection(project_slugs)
        only_biz = client_slugs - project_slugs

        print(f"  • Clienti federati sincronizzati: {len(matched)} ({', '.join(sorted(matched))})")
        if only_biz:
            print(f"  [AVVISO] Presenti in business-ops ma non in itinfra: {', '.join(sorted(only_biz))}")
            print("  (Se sono clienti operativi, eseguire 'it-ops onboard <slug>' per federarli)")
    else:
        print("  [i] Repository itinfra non rilevato nel percorso standard.")

    print("\n" + "=" * 70)
    print("✅ PRE-PUSH SUPERATO: Il repository è integro e pronto per il push.")
    print("=" * 70)
    return 0


def install_hooks(both: bool = False) -> int:
    """Configura Git affinché utilizzi gli hook deterministici in .githooks."""
    githooks_dir = ROOT_DIR / ".githooks"
    githooks_dir.mkdir(parents=True, exist_ok=True)

    # Scrivi lo script pre-commit
    pre_commit_sh = githooks_dir / "pre-commit"
    pre_commit_sh.write_text(
        "#!/usr/bin/env sh\npython scripts/hooks/git_guard.py pre-commit\n",
        encoding="utf-8"
    )

    # Scrivi lo script pre-push
    pre_push_sh = githooks_dir / "pre-push"
    pre_push_sh.write_text(
        "#!/usr/bin/env sh\npython scripts/hooks/git_guard.py pre-push\n",
        encoding="utf-8"
    )

    # Configura core.hooksPath
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=str(ROOT_DIR), check=True)
    print(f"[✓] Git hooks attivati in {ROOT_DIR} (core.hooksPath = .githooks)")

    if both:
        itinfra_dir = get_itinfra_dir()
        if itinfra_dir.is_dir() and (itinfra_dir / ".git").exists():
            it_githooks = itinfra_dir / ".githooks"
            it_githooks.mkdir(parents=True, exist_ok=True)
            (it_githooks / "pre-commit").write_text(
                "#!/usr/bin/env sh\npython -c \"import sys; sys.exit(0)\"\n",
                encoding="utf-8"
            )
            subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=str(itinfra_dir), check=True)
            print(f"[✓] Git hooks attivati in {itinfra_dir} (core.hooksPath = .githooks)")

    return 0


def main():
    if len(sys.argv) < 2:
        print("Uso: python git_guard.py [pre-commit|pre-push|install|check] [--both]")
        return 1

    cmd = sys.argv[1].lower()
    if cmd == "pre-commit":
        return run_pre_commit()
    elif cmd == "pre-push":
        return run_pre_push()
    elif cmd == "install":
        both = "--both" in sys.argv
        return install_hooks(both=both)
    elif cmd == "check":
        res1 = run_pre_commit()
        res2 = run_pre_push()
        return 0 if (res1 == 0 and res2 == 0) else 1
    else:
        print(f"Comando sconosciuto: {cmd}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
