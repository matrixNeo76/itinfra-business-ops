import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from scripts.core.config import get_itinfra_dir

class ITInfraBridge:
    """
    Connettore deterministico in sola lettura verso il repository itinfra.
    Legge le specifiche tecniche di projects/<slug> per abilitare
    il cross-check con contratti, rapportini e noleggi.
    """

    def __init__(self, itinfra_root: Optional[Path] = None):
        self.itinfra_root = itinfra_root or get_itinfra_dir()

    def get_project_dir(self, slug: str) -> Optional[Path]:
        """Restituisce il percorso della cartella progetto in itinfra se esistente."""
        target = self.itinfra_root / "projects" / slug
        if target.is_dir():
            return target
        return None

    def project_exists(self, slug: str) -> bool:
        """Verifica se il progetto tecnico esiste in itinfra."""
        return self.get_project_dir(slug) is not None

    def load_technical_manifest(self, slug: str) -> Optional[Dict[str, Any]]:
        """Carica project-manifest.yaml o manifest.yaml da itinfra."""
        pdir = self.get_project_dir(slug)
        if not pdir:
            return None

        candidates = [pdir / "project-manifest.yaml", pdir / "manifest.yaml"]
        for cand in candidates:
            if cand.is_file():
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    pass
        return None

    def extract_as_built_assets(self, slug: str) -> List[Dict[str, str]]:
        """
        Estrae la lista deterministica degli asset hardware (seriale, hostname, modello)
        dal file 06-As-Built.md di itinfra.
        """
        pdir = self.get_project_dir(slug)
        if not pdir:
            return []

        as_built_file = pdir / "06-As-Built.md"
        if not as_built_file.is_file():
            return []

        content = as_built_file.read_text(encoding="utf-8")
        assets: List[Dict[str, str]] = []

        # Estrazione tabelle markdown: sia formato a coppie chiave-valore che a colonne (Service Tag / Serial)
        current_asset: Dict[str, str] = {}
        table_headers: Optional[List[str]] = None

        for line in content.splitlines():
            line_str = line.strip()

            # Riconoscimento sezioni 4.X
            if line_str.startswith("### 4."):
                if current_asset.get("serial_number"):
                    assets.append(current_asset)
                current_asset = {"section": line_str.replace("###", "").strip()}
                table_headers = None
                continue

            # Riconoscimento intestazioni tabella markdown a colonne
            if line_str.startswith("|") and ("serial" in line_str.lower() or "service tag" in line_str.lower()) and "---" not in line_str:
                table_headers = [c.strip().lower() for c in line_str.split("|")[1:-1]]
                continue

            if table_headers and line_str.startswith("|"):
                if "---" in line_str:
                    continue
                row_vals = [c.strip() for c in line_str.split("|")[1:-1]]
                if len(row_vals) >= len(table_headers):
                    row_dict = dict(zip(table_headers, row_vals))
                    serial_val = None
                    host_val = None
                    model_val = None
                    for k, v in row_dict.items():
                        clean_v = v.strip("`").strip()
                        if clean_v.startswith("<") and clean_v.endswith(">"):
                            continue
                        if "serial" in k or "service tag" in k:
                            serial_val = clean_v
                        elif "hostname" in k or "host" in k:
                            host_val = clean_v
                        elif "modello" in k or "model" in k:
                            model_val = clean_v

                    if serial_val and serial_val not in ["-", "N/A", "none", "", "..."]:
                        assets.append({
                            "serial_number": serial_val,
                            "hostname": host_val or "",
                            "model": model_val or ""
                        })
                continue

            # Match chiave / valore markdown
            m_serial = re.search(r"\|\s*\*\*Numero di Serie\*\*\s*\|\s*`?([A-Za-z0-9\-_]+)`?\s*\|", line, re.IGNORECASE)
            if m_serial:
                current_asset["serial_number"] = m_serial.group(1).strip()

            m_host = re.search(r"\|\s*\*\*Hostname[^\*]*\*\*\s*\|\s*`?([A-Za-z0-9\-_]+)`?\s*\|", line, re.IGNORECASE)
            if m_host:
                current_asset["hostname"] = m_host.group(1).strip()

            m_model = re.search(r"\|\s*\*\*Modello[^\*]*\*\*\s*\|\s*`?([^`\|]+)`?\s*\|", line, re.IGNORECASE)
            if m_model:
                current_asset["model"] = m_model.group(1).strip()

            m_mac = re.search(r"\|\s*\*\*MAC[^\*]*\*\*\s*\|\s*`?([A-Fa-f0-9:]{17})`?\s*\|", line, re.IGNORECASE)
            if m_mac:
                current_asset["mac_address"] = m_mac.group(1).strip()

        if current_asset.get("serial_number"):
            assets.append(current_asset)

        return assets

    def get_known_serials(self, slug: str) -> Set[str]:
        """Restituisce il set di serial number noti nell'As-Built tecnico."""
        assets = self.extract_as_built_assets(slug)
        return {a["serial_number"].upper() for a in assets if "serial_number" in a}
