#!/usr/bin/env python3
"""
scripts/core/skills_manager.py — Antigravity Skills Manager (SPEC-20 Extension)
Interfaccia deterministica per esplorare, cercare e installare oltre 300+ skill per agenti
dal catalogo open-source rmyndharis/antigravity-skills (porting da Claude Code / Anthropic).
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configura encoding UTF-8 su Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_SKILLS_DIR = ROOT_DIR / ".agents" / "skills"
GLOBAL_SKILLS_DIR = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "skills"

CATALOG_URL = "https://raw.githubusercontent.com/rmyndharis/antigravity-skills/main/catalog.json"
BUNDLES_URL = "https://raw.githubusercontent.com/rmyndharis/antigravity-skills/main/bundles.json"
RAW_SKILLS_BASE = "https://raw.githubusercontent.com/rmyndharis/antigravity-skills/main/skills"


class SkillsManager:
    """Gestore del catalogo skill per Google Antigravity."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (ROOT_DIR / ".agents" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_cache_file = self.cache_dir / "skills_catalog.json"

    def load_catalog(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Carica il catalogo delle skill da cache locale o da remoto."""
        if not force_refresh and self.catalog_cache_file.exists():
            try:
                with open(self.catalog_cache_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception:
                pass

        try:
            req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "Antigravity/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            skills = data if isinstance(data, list) else data.get("skills", [])
            with open(self.catalog_cache_file, "w", encoding="utf-8") as fp:
                json.dump(skills, fp, ensure_ascii=False, indent=2)
            return skills
        except Exception as e:
            if self.catalog_cache_file.exists():
                with open(self.catalog_cache_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            print(f"[!] Errore scaricamento catalogo: {e}", file=sys.stderr)
            return []

    def search(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Cerca skill nel catalogo per parola chiave o token."""
        skills = self.load_catalog()
        if not query:
            return skills[:limit]

        tokens = query.lower().split()
        results = []

        for s in skills:
            sid = s.get("id", "").lower()
            sname = s.get("name", "").lower()
            sdesc = s.get("description", "").lower()
            scat = s.get("category", "").lower()
            stags = " ".join(s.get("tags", [])).lower()
            haystack = f"{sid} {sname} {sdesc} {scat} {stags}"

            if all(t in haystack for t in tokens):
                results.append(s)
                if len(results) >= limit:
                    break

        return results

    def info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Recupera le informazioni dettagliate di una skill."""
        skills = self.load_catalog()
        sid_clean = skill_id.strip().lower()
        for s in skills:
            if s.get("id", "").lower() == sid_clean:
                return s
        return None

    def install(
        self,
        skill_id: str,
        target_dir: Optional[Path] = None,
        global_install: bool = False
    ) -> Dict[str, Any]:
        """Scarica e installa la skill richiesta."""
        dest_root = GLOBAL_SKILLS_DIR if global_install else (target_dir or LOCAL_SKILLS_DIR)
        dest_root.mkdir(parents=True, exist_ok=True)

        info = self.info(skill_id)
        remote_id = info.get("id", skill_id) if info else skill_id

        url = f"{RAW_SKILLS_BASE}/{remote_id}/SKILL.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Antigravity/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8")
        except Exception as e:
            return {
                "success": False,
                "skill_id": remote_id,
                "error": f"Impossibile scaricare la skill da {url}: {e}"
            }

        skill_dir = dest_root / remote_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        dest_file = skill_dir / "SKILL.md"
        dest_file.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "skill_id": remote_id,
            "path": str(dest_file),
            "size_bytes": len(content),
            "global": global_install,
            "description": info.get("description", "") if info else ""
        }

    def list_installed(self, target_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Elenca tutte le skill installate localmente nel repository."""
        sdir = target_dir or LOCAL_SKILLS_DIR
        installed = []
        if sdir.is_dir():
            for item in sorted(sdir.iterdir(), key=lambda x: x.name):
                if item.is_dir() and (item / "SKILL.md").exists():
                    skill_file = item / "SKILL.md"
                    desc = ""
                    try:
                        lines = skill_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                        for l in lines[:25]:
                            if l.startswith("description:"):
                                desc = l.replace("description:", "").strip().strip('"').strip("'")
                                break
                    except Exception:
                        pass
                    installed.append({
                        "id": item.name,
                        "path": str(skill_file),
                        "description": desc
                    })
        return installed

    def list_bundles(self) -> Dict[str, Any]:
        """Recupera la lista dei bundle curati dal repository."""
        try:
            req = urllib.request.Request(BUNDLES_URL, headers={"User-Agent": "Antigravity/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {}
