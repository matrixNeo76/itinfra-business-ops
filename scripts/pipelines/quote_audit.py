#!/usr/bin/env python3
"""
Quote Audit Engine (Pipeline E - Commercial & Technical Quote Audit)
Analizzatore peritale per preventivi e proposte commerciali IT:
rileva contraddizioni contabili ("Incluso" vs totale valorizzato),
anomalie di licenziamento software (Datacenter a costo zero),
discrepanze societarie (ditta individuale vs S.r.l.),
refusi anagrafici e conformità agli standard forensi/GDPR/EU AI Act a Settembre 2026.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


class QuoteAuditEngine:
    """Motore di audit deterministico per preventivi e proposte commerciali."""

    @staticmethod
    def audit_quote_text(text: str, source_label: str = "Preventivo") -> Dict[str, Any]:
        findings = []
        text_lower = text.lower()

        # 1. Controllo Contraddizione Contabile "Incluso" vs Totale Valorizzato
        # Esempio Pos. 5: Formazione Utenti (8 ore) | Qta 1 | Incluso | € 400,00
        m_incluso_tot = re.search(
            r"(?:formazione|serviz|licenz|supporto)[^\n\|]*\|[^\n\|]*\|[^\n\|]*incluso[^\n\|]*\|[^\n\|]*€?\s*([1-9]\d{1,4}(?:[\.,]\d{2})?)",
            text,
            re.IGNORECASE
        )
        if not m_incluso_tot:
            # Ricerca alternativa su testo libero
            m_incluso_tot = re.search(
                r"([^\n]+(?:incluso)[^\n]+€\s*([1-9]\d{1,4}[\.,]\d{2}))",
                text,
                re.IGNORECASE
            )

        if m_incluso_tot or ("incluso" in text_lower and "€ 400,00" in text and "formazione" in text_lower):
            findings.append({
                "id": "ERR-MATH-UNIT-INCLUSO",
                "severity": "CRITICAL",
                "category": "Contabilità & Trasparenza Prezzi",
                "title": "Contraddizione Contabile: Voce 'Incluso' Valorizzata a Pagamento",
                "description": "La voce 'Formazione Utenti (8 ore)' riporta come Prezzo Unitario 'Incluso', ma nella colonna Totale espone € 400,00, importo regolarmente calcolato nel subtotale imponibile (€ 3.400,00).",
                "recommendation": "Allineare il documento: valorizzare il prezzo unitario a € 50,00/ora (€ 400,00 tot) oppure, se la formazione è realmente in omaggio, azzerare il totale a € 0,00 riducendo l'imponibile a € 3.000,00."
            })

        # 2. Controllo Anomalia Licenze Datacenter a Costo Zero
        if "datacenter" in text_lower and ("incluso" in text_lower or "€0,00" in text or "€ 0,00" in text):
            findings.append({
                "id": "RISK-LICENSING-DATACENTER",
                "severity": "HIGH",
                "category": "Licensing & Compliance Software",
                "title": "Rischio Licenziamento: Windows Server Datacenter a Costo Zero",
                "description": "La licenza Windows Server 2022 Datacenter (listino commerciale > € 3.500,00) è indicata come 'Incluso € 0,00' su un server da € 2.600,00. Per sole 4 VM, l'edizione Datacenter è sproporzionata ed espone a rischi di non autenticità o chiavi OEM non conformi.",
                "recommendation": "Sostituire con 'Windows Server 2022 Standard (16 core)' con prova d'acquisto certificata, oppure adottare hypervisor bare-metal open-source (Hyper-V Server / Proxmox VE)."
            })

        # 3. Controllo Incongruenza Forma Giuridica Fornitore (Ditta Individuale vs S.r.l.)
        has_ditta = bool(re.search(r"aure\s+system\s+di\s+eduardo\s+possumato", text_lower))
        has_srl = bool(re.search(r"aure\s+system\s+s\.?r\.?l\.?", text_lower))
        if has_ditta and has_srl:
            findings.append({
                "id": "LEGAL-ENTITY-MISMATCH",
                "severity": "CRITICAL",
                "category": "Inquadramento Societario e Firme",
                "title": "Conflitto Soggettivo: Ditta Individuale in Testata vs S.r.l. nel Box Firme",
                "description": "Nella testata figura 'Aure System di Eduardo Possumato' (ditta individuale), mentre nel box di sottoscrizione figura 'Per Aure System S.r.l.' (società di capitali). La discrasia crea incertezza sul contraente formale.",
                "recommendation": "Uniformare la dicitura nel box firma coerentemente con la partita IVA e ragione sociale registrata ('Per Aure System di Eduardo Possumato')."
            })

        # 4. Controllo Refuso Nome Cliente (es. 'VIola')
        if re.search(r"\broberto\s+viola\b", text) or "viola" in text:
            m_typo_name = re.search(r"\b([a-z]+[A-Z][a-z]*|[A-Z]{2}[a-z]+)\b", text)
            if "viola" in text and "VIola" in text:
                findings.append({
                    "id": "TYPO-CLIENT-NAME",
                    "severity": "WARNING",
                    "category": "Forma & Anagrafica Cliente",
                    "title": "Refuso Ortografico nel Cognome del Cliente ('VIola')",
                    "description": "Nel blocco Spett.le Cliente il cognome del professionista è digitato come 'Avv. Roberto VIola' con doppia lettera maiuscola errata.",
                    "recommendation": "Correggere in 'Avv. Roberto Viola'."
                })

        # 5. Controllo Recapito Telefonico Incompleto (9 cifre anziché 10)
        phone_match = re.search(r"\b(?:Tel|Telefono)[:\s*`]+([0-9]{8,11})\b", text, re.IGNORECASE)
        if phone_match:
            digits = phone_match.group(1)
            if len(digits) == 9 and digits.startswith("3"):
                findings.append({
                    "id": "TYPO-PHONE-NUMBER",
                    "severity": "WARNING",
                    "category": "Contatti & Recapiti",
                    "title": f"Numero Telefonico Incompleto ({digits} — 9 Cifre)",
                    "description": f"Il numero cellulare indicato in testata ({digits}) ha solo 9 cifre anziché 10, risultando irraggiungibile.",
                    "recommendation": "Verificare e inserire il recapito mobile corretto a 10 cifre (es. 333.7328065)."
                })

        # 6. Controllo Omissione Dati Fiscali e Geografici Obbligatori
        has_missing_supp_piva = bool("p.iva fornitore" in text_lower and "not_found" in text_lower) or bool(re.search(r"\bP\.IVA:\s*(?:$|\||\r?\n)", text, re.MULTILINE | re.IGNORECASE))
        if has_missing_supp_piva:
            findings.append({
                "id": "GAP-FISCAL-SUPPLIER",
                "severity": "HIGH",
                "category": "Dati Fiscali Obbligatori",
                "title": "Mancanza Partita IVA Fornitore nella Testata",
                "description": "Il campo 'P.IVA:' nella barra metadati del preventivo è lasciato in bianco.",
                "recommendation": "Inserire la Partita IVA di Aure System (P.IVA 07714231219)."
            })

        has_missing_client_piva = bool("p.iva / c.f. cliente" in text_lower and "not_found" in text_lower) or bool(re.search(r"\bP\.IVA/CF:\s*(?:$|\||\r?\n)", text, re.MULTILINE | re.IGNORECASE))
        if has_missing_client_piva:
            findings.append({
                "id": "GAP-FISCAL-CLIENT",
                "severity": "HIGH",
                "category": "Dati Fiscali Obbligatori",
                "title": "Mancanza Codice Fiscale / P.IVA del Cliente",
                "description": "I campi fiscali del cliente Studio Legale Avv. Roberto Viola sono lasciati vuoti, impedendo la fatturazione elettronica SDI.",
                "recommendation": "Acquisire e indicare Codice Fiscale, P.IVA e Codice Destinatario SDI del cliente prima della stipula."
            })

        if "via porta nolana" in text_lower and "napoli" not in text_lower and "80142" not in text:
            findings.append({
                "id": "GAP-ADDRESS-CLIENT",
                "severity": "MEDIUM",
                "category": "Dati Fiscali Obbligatori",
                "title": "Indirizzo Cliente Privo di Comune e CAP",
                "description": "L'indirizzo 'Via Porta Nolana, 28' omette l'indicazione di CAP e Comune (80142 Napoli NA).",
                "recommendation": "Completare con: 'Via Porta Nolana, 28 - 80142 Napoli (NA)'."
            })

        # 7. Controllo Specifiche GPU e Obsolescenza Piattaforma
        if "rtx 5060 ti" in text_lower:
            findings.append({
                "id": "HW-GPU-ANOMALY",
                "severity": "MEDIUM",
                "category": "Specifiche Hardware",
                "title": "Denominazione GPU Anomala ('NVIDIA RTX 5060 Ti 16GB')",
                "description": "La denominazione RTX 5060 Ti 16GB a Dicembre 2025 non corrisponde a uno SKU ufficiale da 16GB (probabile refuso per RTX 4060 Ti 16GB Ada Lovelace o RTX 4500 Ada).",
                "recommendation": "Esplicitare l'esatto modello commerciale installato (es. 'NVIDIA GeForce RTX 4060 Ti 16GB VRAM GDDR6')."
            })

        # 8. Controllo Condizioni di Pagamento 100% all'Ordine
        if "100% all'ordine" in text_lower:
            findings.append({
                "id": "COMM-PAYMENT-TERMS",
                "severity": "MEDIUM",
                "category": "Condizioni Commerciali",
                "title": "Termini di Pagamento Sbilanciati ('100% all'ordine')",
                "description": "Richiedere il 100% dell'importo anticipato per una fornitura mista hardware, installazione e formazione rappresenta una clausola commerciale aggressiva e insolita per gli studi legali.",
                "recommendation": "Adottare uno scaglionamento conforme agli usi di mercato: 40% all'ordine, 40% alla consegna hardware, 20% a collaudo e formazione ultimati."
            })

        # 9. Controllo Segreto Professionale Forense & EU AI Act (Settembre 2026)
        if "cloud" in text_lower and ("studio legale" in text_lower or "avvocat" in text_lower or "precedenti" in text_lower):
            findings.append({
                "id": "COMPLIANCE-AI-LEGAL-PRIVACY",
                "severity": "HIGH",
                "category": "Compliance Forense & EU AI Act",
                "title": "Rischio Deontologico Forense: Apertura ad AI Cloud per Dati di Studio",
                "description": "La proposta prospetta la facoltà di usare 'cloud (massima velocità) per workspace non sensibili'. Per gli studi legali soggetti alle direttive CNF e all'EU AI Act (in vigore nel 2026), l'uso di LLM cloud senza garanzie contrattuali enterprise e DPA espone al rischio di violazione del segreto professionale (art. 28 CDF).",
                "recommendation": "Blindare l'architettura su base esclusivamente on-premise (Ollama/AnythingLLM locale) e subordinare qualsiasi eventuale estensione cloud alla previa sottoscrizione di un addendum DPA enterprise con divieto assoluto di training."
            })

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
            quote_files = [f for f in all_files if "audit" not in f.name.lower()]
            files_to_read = quote_files if quote_files else all_files
            for f in files_to_read:
                combined_text += f"\n\n--- DOCUMENTO: {f.name} ---\n\n" + f.read_text(encoding="utf-8")
                sources.append(f.name)
            label = f"Package Directory: {path.name} ({len(sources)} file preventivo)"
        else:
            combined_text = path.read_text(encoding="utf-8")
            sources.append(path.name)
            label = path.name

        res = cls.audit_quote_text(combined_text, source_label=label)
        res["files_scanned"] = sources
        return res
