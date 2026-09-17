import os
import yaml
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def load_config() -> Dict[str, Any]:
    """Carica la configurazione da config.yaml con risoluzione percorsi."""
    config_file = ROOT_DIR / "config.yaml"
    if not config_file.exists():
        return {
            "itinfra_path": "../itinfra",
            "company": {"name": "ITInfra Business Ops", "currency": "EUR"},
            "storage": {
                "clients_dir": "clients",
                "schemas_dir": "schemas",
                "templates_dir": "templates",
            }
        }
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    return config

def get_itinfra_dir() -> Path:
    """Risolve il percorso assoluto della directory itinfra (Ground Truth Tecnico)."""
    cfg = load_config()
    raw_path = os.environ.get("ITINFRA_PATH", cfg.get("itinfra_path", "../itinfra"))
    path = Path(raw_path)
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve()
    return path

def get_clients_dir() -> Path:
    """Risolve la cartella dei clienti."""
    cfg = load_config()
    clients_dir = cfg.get("storage", {}).get("clients_dir", "clients")
    return (ROOT_DIR / clients_dir).resolve()

def get_schemas_dir() -> Path:
    """Risolve la cartella degli schemi."""
    cfg = load_config()
    schemas_dir = cfg.get("storage", {}).get("schemas_dir", "schemas")
    return (ROOT_DIR / schemas_dir).resolve()

def get_templates_dir() -> Path:
    """Risolve la cartella dei template."""
    cfg = load_config()
    templates_dir = cfg.get("storage", {}).get("templates_dir", "templates")
    return (ROOT_DIR / templates_dir).resolve()
