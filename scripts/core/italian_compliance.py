#!/usr/bin/env python3
"""
scripts/core/italian_compliance.py — Presidio di Conformità Nazionale Italiana (SPEC-24)
Governance deterministica per:
- Validazione Partita IVA (algoritmo di Luhn modificato italiano)
- Validazione Codice Fiscale (DM 23/12/1976 con omocodie e persone giuridiche)
- Validazione canali SDI (B2B 7 car, PA IPA 6 car, 0000000 + PEC)
- Calcolo interessi di mora e indennizzo forfettario ex D.Lgs. 231/2002
- Generazione lettere di sollecito graduate a 3 stadi
"""

import datetime
import re
from typing import Any, Dict, List, Optional, Tuple


class ItalianComplianceGuard:
    """Guard deterministico per la conformità normativa e fiscale italiana."""

    # Tabelle DM 23/12/1976 per carattere di controllo Codice Fiscale
    _CF_DISPARI = {
        '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
        'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
        'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
        'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23
    }

    _CF_PARI = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
        'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19,
        'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25
    }

    _CF_REGEX = re.compile(r'^[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-EHLMPR-T][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$')

    @classmethod
    def validate_partita_iva(cls, piva: str) -> Dict[str, Any]:
        """
        Valida una Partita IVA italiana (11 cifre numeriche) con algoritmo di controllo ufficiale.
        Accetta stringhe con o senza prefisso 'IT'.
        """
        raw = str(piva or "").strip().upper()
        if raw.startswith("IT"):
            raw = raw[2:]

        if not raw.isdigit() or len(raw) != 11:
            return {
                "valid": False,
                "error": f"Lunghezza o formato errato (richieste 11 cifre numeriche, fornite: '{raw}')",
                "normalized": raw
            }

        # Prime 7 cifre: matricola, successive 3: ufficio provinciale, 11ª: controllo
        ufficio = int(raw[7:10])
        # Nota: 001..100 uffici provinciali, valori superiori riservati a soggetti non residenti o speciali
        if ufficio == 0:
            return {
                "valid": False,
                "error": f"Codice ufficio provinciale non valido ('000')",
                "normalized": raw
            }

        s_dispari = sum(int(raw[i]) for i in (0, 2, 4, 6, 8))
        s_pari = 0
        for i in (1, 3, 5, 7, 9):
            x = int(raw[i]) * 2
            s_pari += x if x < 10 else (x - 9)

        totale = s_dispari + s_pari
        check = (10 - (totale % 10)) % 10
        expected = int(raw[10])

        if check != expected:
            return {
                "valid": False,
                "error": f"Cifra di controllo non valida: calcolata {check}, presente {expected}",
                "normalized": raw
            }

        return {
            "valid": True,
            "error": None,
            "normalized": f"IT{raw}",
            "office_code": f"{ufficio:03d}"
        }

    @classmethod
    def validate_codice_fiscale(cls, cf: str) -> Dict[str, Any]:
        """
        Valida un Codice Fiscale italiano:
        - 16 caratteri alfanumerici per persone fisiche (con gestione omocodie)
        - 11 cifre numeriche per persone giuridiche / enti (tramite algoritmo Partita IVA)
        """
        raw = str(cf or "").strip().upper()

        if len(raw) == 11 and raw.isdigit():
            # Persona giuridica / Società: il codice fiscale coincide con la Partita IVA
            piva_res = cls.validate_partita_iva(raw)
            return {
                "valid": piva_res["valid"],
                "type": "persona_giuridica",
                "error": piva_res.get("error"),
                "normalized": raw
            }

        if len(raw) != 16:
            return {
                "valid": False,
                "type": "persona_fisica",
                "error": f"Lunghezza errata (richiesti 16 caratteri, forniti {len(raw)})",
                "normalized": raw
            }

        if not cls._CF_REGEX.match(raw):
            return {
                "valid": False,
                "type": "persona_fisica",
                "error": "Formato sintattico non conforme alla struttura ministeriale DM 23/12/1976",
                "normalized": raw
            }

        # Calcolo carattere di controllo (16° carattere)
        totale = 0
        for i in range(15):
            char = raw[i]
            if (i + 1) % 2 != 0:  # Posizione dispari (1, 3, 5, ..., 15)
                totale += cls._CF_DISPARI.get(char, 0)
            else:  # Posizione pari (2, 4, 6, ..., 14)
                totale += cls._CF_PARI.get(char, 0)

        expected_char = chr(ord('A') + (totale % 26))
        actual_char = raw[15]

        if expected_char != actual_char:
            return {
                "valid": False,
                "type": "persona_fisica",
                "error": f"Carattere di controllo non valido: calcolato '{expected_char}', presente '{actual_char}'",
                "normalized": raw
            }

        return {
            "valid": True,
            "type": "persona_fisica",
            "error": None,
            "normalized": raw
        }

    @classmethod
    def validate_sdi_recipient(cls, sdi_code: str, pec: str = "") -> Dict[str, Any]:
        """
        Valida il canale di recapito per la Fattura Elettronica SDI:
        - 7 caratteri per B2B / B2C
        - 6 caratteri per Pubblica Amministrazione (Codice Univoco Ufficio IPA)
        - '0000000' valido solo se accompagnato da PEC valida
        """
        code = str(sdi_code or "").strip().upper()
        pec_clean = str(pec or "").strip()

        if len(code) == 7 and code.isalnum() and code != "0000000":
            return {"valid": True, "type": "B2B_SDI", "code": code, "error": None}

        if len(code) == 6 and code.isalnum():
            return {"valid": True, "type": "PA_IPA", "code": code, "error": None}

        if code == "0000000":
            # Richiede PEC valida
            if pec_clean and "@" in pec_clean and "." in pec_clean:
                return {"valid": True, "type": "PEC_FALLBACK", "code": code, "pec": pec_clean, "error": None}
            return {
                "valid": False,
                "type": "PEC_REQUIRED",
                "code": code,
                "error": "Codice SDI '0000000' richiede una PEC aziendale valida per il recapito telematico"
            }

        return {
            "valid": False,
            "type": "INVALID_SDI",
            "code": code,
            "error": f"Codice SDI non valido ('{code}'). Richiesti 7 caratteri alfanumerici B2B o 6 caratteri PA."
        }

    @classmethod
    def calculate_dlgs231_interest(
        cls,
        amount: float,
        due_date: str,
        ref_date: Optional[str] = None,
        bce_rate: float = 0.0350
    ) -> Dict[str, Any]:
        """
        Calcola gli interessi legali di mora e l'indennizzo forfettario ex D.Lgs. 231/2002:
        - Tasso applicabile: Tasso BCE + spread legale 8.0 punti percentuali (Art. 5)
        - Base di calcolo: 365 giorni
        - Risarcimento forfettario spese recupero: € 40,00 fisso per fattura (Art. 6, comma 2)
        """
        try:
            d_due = datetime.date.fromisoformat(str(due_date))
        except Exception:
            return {"error": f"Data di scadenza non valida: {due_date}", "days_overdue": 0, "interest": 0.0}

        if ref_date:
            try:
                d_ref = datetime.date.fromisoformat(str(ref_date))
            except Exception:
                d_ref = datetime.date.today()
        else:
            d_ref = datetime.date.today()

        days_overdue = (d_ref - d_due).days
        spread = 0.08  # 8% legale
        total_rate = bce_rate + spread  # es. 3.5% + 8.0% = 11.5%

        if days_overdue > 0 and amount > 0:
            interest = round(amount * total_rate * days_overdue / 365.0, 2)
            lump_sum_fee = 40.00  # Spese forfettarie legali ex D.Lgs. 231/2002 Art. 6
            total_due = round(amount + interest + lump_sum_fee, 2)
        else:
            days_overdue = max(0, days_overdue)
            interest = 0.0
            lump_sum_fee = 0.0
            total_due = round(amount, 2)

        return {
            "amount_capital": round(amount, 2),
            "due_date": d_due.isoformat(),
            "reference_date": d_ref.isoformat(),
            "days_overdue": days_overdue,
            "bce_rate_pct": round(bce_rate * 100, 2),
            "legal_spread_pct": 8.0,
            "total_mora_rate_pct": round(total_rate * 100, 2),
            "interest_mora": interest,
            "lump_sum_fee": lump_sum_fee,
            "total_due_dlgs231": total_due,
            "legal_basis": "D.Lgs. 231/2002 modificato da D.Lgs. 192/2012, Art. 4-5-6"
        }

    @classmethod
    def generate_reminder_letter(
        cls,
        slug: str,
        invoice_data: Dict[str, Any],
        stage: int = 1,
        creditor_name: str = "Aure System di Eduardo Possumato",
        creditor_iban: str = "IT77X0306909606100000123456"
    ) -> str:
        """
        Genera una lettera di sollecito conforme al diritto commerciale italiano in 3 stadi:
        - Stadio 1 (7-14 gg ritardo): Avviso amichevole di cortesia
        - Stadio 2 (15-30 gg ritardo): Sollecito formale con addebito interessi di mora 231/2002 e 40€
        - Stadio 3 (>30 gg ritardo): Diffida ad adempiere e costituzione in mora ex Art. 1219 c.c.
        """
        client_name = invoice_data.get("client_name", slug)
        inv_num = invoice_data.get("invoice_number", "N/D")
        inv_date = invoice_data.get("invoice_date", "N/D")
        due_date = invoice_data.get("due_date", "N/D")
        capital = float(invoice_data.get("amount", 0.0))

        calc = cls.calculate_dlgs231_interest(capital, due_date)
        days = calc.get("days_overdue", 0)
        interest = calc.get("interest_mora", 0.0)
        fee = calc.get("lump_sum_fee", 0.0)
        tot = calc.get("total_due_dlgs231", capital)

        today_str = datetime.date.today().strftime("%d/%m/%Y")

        if stage == 1:
            return f"""================================================================================
                    AVVISO DI CORTESIA / PROMEMORIA SCADENZA
================================================================================
Data: {today_str}
Spett.le {client_name}

Oggetto: Promemoria scadenza fattura n. {inv_num} del {inv_date}

Gentile Cliente,
dai nostri registri contabili risulta che la fattura n. {inv_num} del {inv_date}, 
avente scadenza originaria in data {due_date} per l'importo di € {capital:.2f}, 
non risulta ancora regolarizzata.

Confidando che si tratti di un mero disguido amministrativo, Vi invitiamo a voler 
provvedere al saldo mediante bonifico bancario sulle seguenti coordinate:

Beneficiario : {creditor_name}
IBAN         : {creditor_iban}
Causale      : Saldo Fattura n. {inv_num} del {inv_date}

Qualora il pagamento fosse già stato disposto, Vi preghiamo di considerare nulla 
la presente comunicazione o di inoltrarci la relativa contabile.

Cordiali saluti,
Ufficio Amministrazione — {creditor_name}
================================================================================"""

        elif stage == 2:
            return f"""================================================================================
          SOLLECITO FORMALE CON ADDEBITO MORA EX D.LGS. 231/2002
================================================================================
Data: {today_str}
Spett.le {client_name}

Oggetto: Sollecito pagamento fattura n. {inv_num} e conteggio interessi D.Lgs. 231/2002

Facendo seguito al nostro precedente promemoria, rileviamo con rammarico che 
la fattura n. {inv_num} del {inv_date} risulta tuttora insoluta, con un ritardo 
accumulato pari a {days} giorni dalla scadenza ({due_date}).

Ai sensi e per gli effetti del D.Lgs. 9 ottobre 2002 n. 231 (modificato dal D.Lgs. 
192/2012 in attuazione della Direttiva 2011/7/UE), Vi comunichiamo l'avvenuta 
decorrenza automatica degli interessi moratori commerciali e il diritto all'indennizzo 
forfettario per i costi di recupero:

- Quota Capitale Fattura           : € {capital:>10.2f}
- Interessi di Mora ({calc.get('total_mora_rate_pct'):.2f}% annuo) : € {interest:>10.2f}  ({days} gg ritardo)
- Risarcimento Forfettario (Art. 6): € {fee:>10.2f}
--------------------------------------------------------------------------------
TOTALE DOVUTO AD OGGI              : € {tot:>10.2f}

Vi intimiamo pertanto di provvedere all'integrale corresponsione di € {tot:.2f} 
entro e non oltre 7 (sette) giorni dal ricevimento della presente, tramite bonifico:

IBAN    : {creditor_iban}
Causale : Saldo Fattura {inv_num} + Mora ex D.Lgs. 231/2002

In difetto di riscontro, saremo costretti ad attivare le tutele legali previste 
e a procedere alla sospensione dell'erogazione dei servizi di supporto SLA.

Ufficio Crediti & Recupero — {creditor_name}
================================================================================"""

        else:  # Stage 3
            return f"""================================================================================
       DIFFIDA AD ADEMPIERE E COSTITUZIONE IN MORA EX ART. 1219 C.C.
================================================================================
Data: {today_str}
Spett.le {client_name}
Trasmessa a mezzo PEC con valore legale

Oggetto: Atto formale di costituzione in mora per fattura n. {inv_num} — D.Lgs. 231/2002

Noi sottoscritti, {creditor_name},
PREMESSO CHE
- In data {inv_date} è stata emessa la fattura n. {inv_num} per l'importo di € {capital:.2f};
- La predetta somma doveva essere corrisposta entro e non oltre il termine del {due_date};
- I precedenti solleciti sono rimasti privi di esito e il ritardo è pari a {days} giorni;
- Trovano piena applicazione gli artt. 4, 5 e 6 del D.Lgs. 231/2002 e succ. mod.;

Tutto ciò premesso, con la presente
VI DIFFIDIAMO FORMALMENTE E VI COSTITUIAMO IN MORA
ai sensi e per gli effetti dell'art. 1219 del Codice Civile, intimandoVi di pagare 
entro e non oltre il termine perentorio di 5 (cinque) giorni dalla ricezione della 
presente l'importo complessivo di:

  € {tot:.2f}
(di cui € {capital:.2f} per sorte capitale, € {interest:.2f} per interessi moratori al {calc.get('total_mora_rate_pct'):.2f}% 
e € {fee:.2f} a titolo di risarcimento forfettario ex lege).

Coordinate di versamento:
IBAN    : {creditor_iban}
Causale : Diffida ad adempiere fattura {inv_num}

CON ESPRESSO AVVERTIMENTO CHE
Decorso infruttuosamente detto termine, senza ulteriore preavviso:
1. I servizi di assistenza tecnica, manutenzione sistemistica e supporto SLA 
   verranno immediatamente SOSPESI a tutela dell'esposizione economica;
2. La pratica verrà rimessa ai nostri legali per l'avvio della procedura monitoria 
   presso il Tribunale competente (Ricorso per Decreto Ingiuntivo provvisoriamente esecutivo) 
   con aggravio di spese giudiziali, diritti e onorari a Vostro esclusivo carico.

Con salvezza di ogni diritto ed azione.

{creditor_name}
================================================================================"""
