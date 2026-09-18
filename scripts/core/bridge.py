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

    def __init__(self, itinfra_root: Optional[Path] = None, clients_root: Optional[Path] = None):
        self.itinfra_root = itinfra_root or get_itinfra_dir()
        from scripts.core.config import get_clients_dir
        self.clients_root = clients_root or get_clients_dir()

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

    def extract_ipam_subnets_and_ips(self, slug: str) -> Dict[str, Any]:
        """
        Estrae le subnet IPAM (CIDR, VLAN, Gateway) e le assegnazioni IP
        dal documento 04-Network-IPAM.md di itinfra.
        """
        pdir = self.get_project_dir(slug)
        if not pdir:
            return {"slug": slug, "found": False, "subnets": [], "allocations": []}

        ipam_file = pdir / "04-Network-IPAM.md"
        if not ipam_file.is_file():
            return {"slug": slug, "found": False, "subnets": [], "allocations": []}

        content = ipam_file.read_text(encoding="utf-8")
        subnets = []
        allocations = []

        subnet_matches = re.findall(r"(\b(?:\d{1,3}\.){3}\d{1,3}\/\d{1,2}\b)", content)
        for s in set(subnet_matches):
            subnets.append({"cidr": s})

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str.startswith("|") or "---" in line_str:
                continue
            cols = [c.strip().strip("`") for c in line_str.split("|")[1:-1]]
            if len(cols) >= 3:
                ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", cols[0]) or re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", cols[1])
                if ip_match:
                    ip_addr = ip_match.group(0)
                    allocations.append({
                        "ip": ip_addr,
                        "device_or_hostname": cols[1] if ip_addr == cols[0] else cols[0],
                        "description": cols[2] if len(cols) > 2 else ""
                    })

        return {
            "slug": slug,
            "found": True,
            "subnets": subnets,
            "allocations_count": len(allocations),
            "allocations": allocations
        }

    def cross_check_sla_assets_coverage(
        self,
        slug: str,
        contract_id: Optional[str] = None,
        clients_root: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Cross-check bidirezionale tra gli asset hardware in 06-As-Built.md (itinfra)
        e gli apparati censiti sotto copertura nei contratti SLA (itinfra-business-ops).
        Identifica asset non coperti (Shadow IT / Unbilled Assets) e ghost assets.
        """
        as_built_assets = self.extract_as_built_assets(slug)
        as_built_serials = {a["serial_number"].upper(): a for a in as_built_assets if "serial_number" in a}

        c_root = clients_root or self.clients_root
        cdir = c_root / slug / "contracts"
        covered_serials: Dict[str, Dict[str, Any]] = {}

        if cdir.is_dir():
            for f in cdir.glob("*.yaml"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        cdata = yaml.safe_load(fp) or {}
                    cid = cdata.get("contract_id", f.name)
                    if contract_id and cid != contract_id:
                        continue
                    if cdata.get("status") == "active":
                        for ast in cdata.get("covered_assets", []):
                            sn = str(ast.get("serial_number", "")).strip().upper()
                            if sn:
                                covered_serials[sn] = {"contract_id": cid, "asset_info": ast}
                except Exception:
                    pass

        covered_in_contract = []
        missing_from_contract = []
        ghost_contract_assets = []

        for sn, ast in as_built_serials.items():
            if sn in covered_serials:
                covered_in_contract.append({
                    "serial_number": sn,
                    "model": ast.get("model", ""),
                    "hostname": ast.get("hostname", ""),
                    "contract_id": covered_serials[sn]["contract_id"]
                })
            else:
                missing_from_contract.append({
                    "serial_number": sn,
                    "model": ast.get("model", ""),
                    "hostname": ast.get("hostname", ""),
                    "risk": "UNBILLED_ASSET_SHADOW_IT"
                })

        for sn, c_info in covered_serials.items():
            if sn not in as_built_serials:
                ghost_contract_assets.append({
                    "serial_number": sn,
                    "contract_id": c_info["contract_id"],
                    "note": "Presente a contratto ma assente in As-Built"
                })

        tot_as_built = len(as_built_serials)
        coverage_pct = round((len(covered_in_contract) / tot_as_built * 100.0), 1) if tot_as_built > 0 else 100.0

        return {
            "slug": slug,
            "total_as_built_assets": tot_as_built,
            "total_covered_in_contract": len(covered_in_contract),
            "coverage_ratio_percent": coverage_pct,
            "covered_assets": covered_in_contract,
            "missing_from_contract": missing_from_contract,
            "ghost_contract_assets": ghost_contract_assets,
            "status": "PASS" if not missing_from_contract else "WARNING"
        }
