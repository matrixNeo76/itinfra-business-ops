#!/usr/bin/env python3
"""
Contract Audit Engine (Pipeline A - Extension)
Analizzatore peritale per contratti di assistenza tecnica/sistemistica SLA:
rileva contraddizioni interne, anomalie tariffarie, refusi tipografici
e verifica la conformità con gli standard normativi italiani/UE a Settembre 2026 (GDPR Art. 28, NIS 2, Liability).
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


class ContractAuditEngine:
    """Motore di audit per contratti di consulenza e assistenza sistemistica."""

    @staticmethod
    def audit_contract_text(text: str, source_label: str = "Contratto") -> Dict[str, Any]:
        findings = []
        text_lower = text.lower()

        # 1. Controllo Conflitto Orari di Presidio
        hours_matches = re.findall(r"\b(\d{1,2}:\d{2})\s*(?:alle|-|–)\s*(\d{1,2}:\d{2})\b", text)
        distinct_windows = set(f"{h[0]}-{h[1]}" for h in hours_matches)
        if len(distinct_windows) > 1:
            findings.append({
                "id": "ERR-ORARI",
                "severity": "CRITICAL",
                "category": "Contraddizione Interna",
                "title": "Discrepanza Orari di Presidio Giornaliero",
                "description": f"Rilevateplurime finestre orarie divergenti nel testo: {', '.join(distinct_windows)} (es. Sez. 5.1 indica fino alle 17:00, Sez. 8.1 fino alle 18:00).",
                "recommendation": "Unificare l'orario di copertura a 'lun-ven 09:00 - 18:00' o chiarire esplicitamente la differenza tra presidio telefonico e interventi tecnici."
            })

        # 2. Controllo Recapiti Telefonici Divergenti
        phone_matches = set(re.findall(r"\b(?:3\d{2}\.?\d{6,7}|081\.?\d{6,7})\b", text))
        mobiles = [p for p in phone_matches if p.startswith("3")]
        if len(mobiles) > 1:
            findings.append({
                "id": "ERR-TEL",
                "severity": "WARNING",
                "category": "Recapiti e Comunicazioni",
                "title": "Discrepanza Numeri Mobili di Assistenza",
                "description": f"Nel documento figurano recapiti mobili differenti ({', '.join(mobiles)}) senza specificare se uno sia per reperibilità emergenze e l'altro per contatto amministrativo.",
                "recommendation": "Specificare il ruolo univoco di ciascun recapito (es. 'Reperibilità Urgenze: 333.7328065', 'Ufficio Tecnico: 392.8554426')."
            })

        # 3. Controllo Ambiguità Pacchetti Ore / Giornate
        if "24 oppure 12" in text or "oppure 12 giornate" in text:
            findings.append({
                "id": "ERR-PACCHETTO-AMBIGUO",
                "severity": "CRITICAL",
                "category": "Oggetto dell'Accordo",
                "title": "Ambiguità Quantitativa nel Corpo Contrattuale (Sez. 6)",
                "description": "La Sezione 6 riporta testualmente 'un pacchetto pari a n° 24 oppure 12 giornate', lasciando un'alternativa non risolta nel corpo dell'atto.",
                "recommendation": "Rimuovere la disgiunzione 'oppure' e fissare esattamente la quantità contrattualizzata (es. '24 giornate lavorative annue')."
            })

        # 4. Controllo Sostenibilità Economica e Tariffa Oraria Implicita
        m_days_list = [float(x) for x in re.findall(r"\b(\d+)\s*giornate", text, re.IGNORECASE)]
        m_fee = re.search(r"€\s*([0-9\.,]+)\s*(?:\+\s*iva)?\s*(?:/\s*anno|\(anno\)|all'anno|annuo|all’anno)", text, re.IGNORECASE)
        if m_days_list and m_fee:
            try:
                days = max(m_days_list)
                fee_annual = float(m_fee.group(1).replace(".", "").replace(",", "."))
                hours = days * 8.0
                hourly_rate = fee_annual / hours
                if hourly_rate < 50.0:
                    findings.append({
                        "id": "ERR-SOSTENIBILITA-ECONOMICA",
                        "severity": "CRITICAL",
                        "category": "Equilibrio Finanziario",
                        "title": f"Tariffa Oraria Implicita Anomala (€ {hourly_rate:.2f}/ora)",
                        "description": f"Con {int(days)} giornate ({int(hours)} ore) a € {fee_annual:.2f}/anno, il costo orario effettivo è di soli € {hourly_rate:.2f}/h (con trasferte incluse), largamente al di sotto dei costi operativi e dei parametri di mercato sistemistico B2B.",
                        "recommendation": "Verificare se si intendono '24 ore annue' (pari a 2 ore/mese a 150 €/h) oppure rimodulare il canone o ridurre le giornate incluse (es. 5-6 giornate/anno a € 300/mese)."
                    })
            except Exception:
                pass

        # 5. Controllo Mancanza Tariffa Fuori Pacchetto (Extra Overage)
        if not re.search(r"(?:eccedenz|extra|fuori monte|oltre il monte|sforamento).*?€\s*\d+", text, re.IGNORECASE):
            findings.append({
                "id": "GAP-EXTRA-RATE",
                "severity": "HIGH",
                "category": "Condizioni Economiche",
                "title": "Assenza Tariffa Oraria per Ore/Giornate Fuori Pacchetto",
                "description": "Il contratto non stabilisce la tariffa oraria applicabile nel caso in cui il cliente esaurisca il monte ore prima della scadenza annuale.",
                "recommendation": "Aggiungere clausola: 'Eventuali interventi eccedenti il monte pattuito saranno fatturati a consuntivo alla tariffa concordata di € 75,00 + IVA / ora'."
            })

        # 6. Controllo Mancanza Regole Scadenza / Rollover Ore
        if "residuo" not in text_lower and "decad" not in text_lower and "riport" not in text_lower:
            findings.append({
                "id": "GAP-HOURS-ROLLOVER",
                "severity": "MEDIUM",
                "category": "Gestione Monte Ore",
                "title": "Mancanza Clausola di Scadenza o Trasferibilità Ore Residue",
                "description": "Non è esplicitato se le ore o giornate non fruite entro i 12 mesi decadono definitivamente o se possono essere cumulate nell'annualità successiva.",
                "recommendation": "Specificare: 'Le giornate/ore non usufruite entro il periodo di validità di 12 mesi si intendono decadute e non rimborsabili, salvo rinnovo espresso'."
            })

        # 7. Controllo Refusi Tipografici Evidenti
        if "timrbo" in text_lower:
            findings.append({
                "id": "TYPO-TIMRBO",
                "severity": "LOW",
                "category": "Forma e Impaginazione",
                "title": "Refuso Tipografico nel Box Firme (Pag. 8)",
                "description": "È presente il refuso materiale 'TIMRBO E FIRMA DEL FORNITORE' anziché 'TIMBRO'.",
                "recommendation": "Correggere la dicitura in 'TIMBRO E FIRMA DEL FORNITORE'."
            })

        # 8. COMPLIANCE STANDARD ITALIANI & EUROPEI A SETTEMBRE 2026:
        # A) GDPR Art. 28 (Nomina a Responsabile del Trattamento)
        has_gdpr = bool(re.search(r"(?:nomina\s+a\s+)?responsabile\s+del\s+trattamento|data\s+processing\s+agreement|\bdpa\b|accordo\s+trattamento\s+dati|\ballegato\s+privacy\b", text_lower))
        if not has_gdpr:
            findings.append({
                "id": "COMPLIANCE-GDPR-ART28",
                "severity": "CRITICAL",
                "category": "Conformità Normativa (GDPR)",
                "title": "Mancanza Nomina a Responsabile del Trattamento (Art. 28 GDPR)",
                "description": "L'amministratore di sistema accede a server, credenziali, Active Directory, caselle email e backup aziendali. In Italia e UE l'accordo di nomina DPA è obbligatorio a pena di pesanti sanzioni del Garante Privacy.",
                "recommendation": "Integrare l'Art. 9 con l'allegato formale 'Accordo per il Trattamento dei Dati Personali (DPA)' ai sensi dell'Art. 28 Reg. UE 2016/679."
            })

        # B) Direttiva NIS 2 (Recepimento D.Lgs. 2024/2026 per MSP e Fornitori ICT)
        has_nis2 = bool(re.search(r"\bnis\s*2\b|direttiva\s+nis|resilienza\s+(?:operativa|cibernetica)|notifica\s+(?:incidenti|violazion)", text_lower))
        if not has_nis2:
            findings.append({
                "id": "COMPLIANCE-NIS2",
                "severity": "HIGH",
                "category": "Cybersecurity & NIS 2",
                "title": "Assenza Clausole di Resilienza Informatica & Notifica Incidenti (NIS 2)",
                "description": "A settembre 2026 i fornitori di servizi gestiti (MSP) sono soggetti a requisiti stringenti di igiene cibernetica (MFA obbligatorio, canale cifrato per teleassistenza, obbligo di segnalazione breach/incidenti critici entro 24h).",
                "recommendation": "Inserire una specifica clausola che impegni il fornitore all'uso esclusivo di canali remoti cifrati con MFA e disciplini la tempestiva cooperazione in caso di data breach o cyber attacco."
            })

        # C) Limitazione di Responsabilità & Backup (Liability Cap)
        has_liability_cap = bool(re.search(r"limitazione\s+di\s+responsabilit|liability\s+cap|massimale\s+risarcitor|salvaguardia\s+risarcitor", text_lower))
        if not has_liability_cap:
            findings.append({
                "id": "LEGAL-LIABILITY-CAP",
                "severity": "HIGH",
                "category": "Tutela Legale e Risarcitoria",
                "title": "Assenza Clausola di Limitazione di Responsabilità (Liability Cap)",
                "description": "Il contratto espone Aure System a rischi risarcitori illimitati in caso di disservizio, crash di sistema o attacco ransomware.",
                "recommendation": "Inserire una clausola di salvaguardia che escluda la responsabilità per danni indiretti/lucro cessante e limiti il risarcimento al massimo al canone annuo (€ 3.600,00), subordinando l'operatività alla presenza di backup validi sotto la custodia del cliente."
            })

        # D) Adeguamento ISTAT
        has_istat = bool(re.search(r"\bistat\b|\bfoi\b|adeguamento\s+istat|revisione\s+prezzi", text_lower))
        if not has_istat:
            findings.append({
                "id": "FIN-INDEXATION-ISTAT",
                "severity": "MEDIUM",
                "category": "Tutela Finanziaria",
                "title": "Assenza Clausola di Revisione Prezzi ISTAT",
                "description": "In caso di rinnovo tacito, il canone resta fisso indefinitamente esponendo l'azienda all'erosione inflattiva dei costi di manodopera.",
                "recommendation": "Introdurre l'adeguamento automatico del canone all'indice ISTAT FOI al momento di ciascun rinnovo annuale."
            })

        # Conteggi
        crit_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")
        warn_count = sum(1 for f in findings if f["severity"] in ("WARNING", "MEDIUM"))
        low_count = sum(1 for f in findings if f["severity"] == "LOW")

        return {
            "source": source_label,
            "findings_count": len(findings),
            "summary": {
                "critical": crit_count,
                "high": high_count,
                "warning": warn_count,
                "low": low_count
            },
            "findings": findings
        }

    @classmethod
    def audit_path(cls, path: Path) -> Dict[str, Any]:
        """Esegue l'audit su singolo file o su un intero package/directory di file .okf.md."""
        if not path.exists():
            raise FileNotFoundError(f"Percorso non trovato: {path}")

        combined_text = ""
        sources = []

        if path.is_dir():
            all_files = sorted(path.glob("*.okf.md"))
            contract_files = [f for f in all_files if "audit" not in f.name.lower()]
            files_to_read = contract_files if contract_files else all_files
            for f in files_to_read:
                combined_text += f"\n\n--- DOCUMENTO: {f.name} ---\n\n" + f.read_text(encoding="utf-8")
                sources.append(f.name)
            label = f"Package Directory: {path.name} ({len(sources)} file contrattuali)"
        else:
            combined_text = path.read_text(encoding="utf-8")
            sources.append(path.name)
            label = path.name

        res = cls.audit_contract_text(combined_text, source_label=label)
        res["files_scanned"] = sources
        return res
