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

        # Estrazione tabelle markdown: | **Numero di Serie** | `CZC8492K1L` |
        # o | **Hostname ...** | `...` |
        # Cerchiamo blocchi o coppie di valori
        current_asset: Dict[str, str] = {}
        for line in content.splitlines():
            # Riconoscimento sezioni 4.X
            if line.startswith("### 4."):
                if current_asset.get("serial_number"):
                    assets.append(current_asset)
                current_asset = {"section": line.replace("###", "").strip()}

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
