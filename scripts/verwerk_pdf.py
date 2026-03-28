#!/usr/bin/env python3
"""
verwerk_pdf.py — Verwerk een hockey.nl PDF naar de database.

Gebruik:
    python3 scripts/verwerk_pdf.py artikel.pdf
    python3 scripts/verwerk_pdf.py artikel.pdf --dames

Het script:
1. Leest de PDF tekst
2. Stuurt naar Claude API voor analyse
3. Slaat wedstrijden op in competities/heren/programma.json
"""

import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime, timezone

# ── Configuratie ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MAANDEN = {
    "januari": "01", "februari": "02", "maart": "03", "april": "04",
    "mei": "05", "juni": "06", "juli": "07", "augustus": "08",
    "september": "09", "oktober": "10", "november": "11", "december": "12"
}

def lees_pdf(pad: Path) -> str:
    """Lees tekst uit PDF."""
    try:
        import pdfplumber
        with pdfplumber.open(pad) as pdf:
            tekst = ""
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    tekst += t + "\n"
            return tekst
    except ImportError:
        pass

    try:
        import pypdf
        reader = pypdf.PdfReader(str(pad))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        pass

    print("❌ Installeer pdfplumber: pip install pdfplumber")
    sys.exit(1)


def analyseer_met_claude(tekst: str, geslacht: str) -> dict:
    """Stuur tekst naar Claude API voor wedstrijdanalyse."""
    import urllib.request
    import urllib.error

    if not ANTHROPIC_KEY:
        print("❌ Geen API key. Stel in: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    system = """Je analyseert een hockey artikel of match center export over de Tulp Hoofdklasse.
Extraheer ALLE wedstrijden die in de tekst beschreven worden.

Voor elke wedstrijd bepaal je:
- thuis/uit club (zonder H1/D1 suffix)
- score_thuis en score_uit (getallen)
- datum als YYYY-MM-DD (jaar is 2025 of 2026)
- tijdstip als HH:MM
- scorers: naam, club, minuut (getal), type (veld/sc/sb voor strafcorner/strafbal)
- kaarten: naam, club, minuut, type (groen/geel/rood)

Geef ALLEEN een geldig JSON object terug, geen uitleg:
{
  "wedstrijden": [
    {
      "thuis": "Kampong",
      "uit": "Bloemendaal",
      "score_thuis": 3,
      "score_uit": 5,
      "datum": "2026-03-22",
      "tijdstip": "15:00",
      "gespeeld": true,
      "scorers": [
        {"naam": "Floris Wortelboer", "club": "Bloemendaal", "minuut": 8, "type": "sc"}
      ],
      "kaarten": [
        {"naam": "Sander van de Putte", "club": "Kampong", "minuut": 55, "type": "groen"}
      ]
    }
  ]
}"""

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 3000,
        "system": system,
        "messages": [{"role": "user", "content": tekst[:12000]}]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            tekst_result = result["content"][0]["text"]
            tekst_result = re.sub(r"```json|```", "", tekst_result).strip()
            return json.loads(tekst_result)
    except Exception as e:
        print(f"❌ Claude API fout: {e}")
        sys.exit(1)


def sla_op(nieuwe_wedstrijden: list, geslacht: str):
    """Sla wedstrijden op in programma.json, update bestaande."""
    pad = BASE_DIR / "competities" / geslacht / "programma.json"
    pad.parent.mkdir(parents=True, exist_ok=True)

    # Laad bestaande data
    bestaand = {"wedstrijden": []}
    if pad.exists():
        try:
            bestaand = json.loads(pad.read_text())
        except Exception:
            pass

    bestaande_ws = bestaand.get("wedstrijden", [])

    def match_key(w):
        return (
            (w.get("thuis", "") or "").lower().strip(),
            (w.get("uit", "") or "").lower().strip(),
            (w.get("datum", "") or "").strip()
        )

    # Index bestaande wedstrijden
    bestaand_index = {match_key(w): i for i, w in enumerate(bestaande_ws)}

    toegevoegd = 0
    bijgewerkt = 0

    for nw in nieuwe_wedstrijden:
        key = match_key(nw)
        if key in bestaand_index:
            # Update bestaande wedstrijd
            idx = bestaand_index[key]
            bestaande_ws[idx].update(nw)
            bijgewerkt += 1
        else:
            # Voeg nieuwe toe
            bestaande_ws.append(nw)
            toegevoegd += 1

    # Sorteer op datum
    bestaande_ws.sort(key=lambda w: w.get("datum", "") or "")

    bestaand["wedstrijden"] = bestaande_ws
    bestaand["bijgewerkt"] = datetime.now(timezone.utc).isoformat()
    bestaand.setdefault("seizoen", "2025/26")
    bestaand.setdefault("geslacht", geslacht)

    pad.write_text(json.dumps(bestaand, ensure_ascii=False, indent=2))
    print(f"✅ Opgeslagen in {pad}")
    print(f"   Nieuw: {toegevoegd} · Bijgewerkt: {bijgewerkt}")


def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 scripts/verwerk_pdf.py <bestand.pdf> [--dames]")
        sys.exit(1)

    pdf_pad = Path(sys.argv[1])
    geslacht = "dames" if "--dames" in sys.argv else "heren"

    if not pdf_pad.exists():
        print(f"❌ Bestand niet gevonden: {pdf_pad}")
        sys.exit(1)

    print(f"📄 Lezen: {pdf_pad.name}")
    tekst = lees_pdf(pdf_pad)
    print(f"   {len(tekst)} tekens gelezen")

    print("🤖 Analyseren met Claude...")
    resultaat = analyseer_met_claude(tekst, geslacht)

    wedstrijden = resultaat.get("wedstrijden", [])
    if not wedstrijden:
        print("❌ Geen wedstrijden gevonden in het artikel.")
        sys.exit(1)

    print(f"\n📊 Gevonden: {len(wedstrijden)} wedstrijd(en)")
    for w in wedstrijden:
        scorers = len(w.get("scorers", []))
        kaarten = len(w.get("kaarten", []))
        print(f"   {w.get('thuis')} {w.get('score_thuis')}-{w.get('score_uit')} {w.get('uit')} ({w.get('datum')}) — {scorers} doelpunten, {kaarten} kaarten")

    sla_op(wedstrijden, geslacht)
    print(f"\n✅ Klaar! Commit en push om de site bij te werken:")
    print(f"   cd {BASE_DIR.name} && git add competities/ && git commit -m 'data: wedstrijden {wedstrijden[0].get('datum', '')}' && git pull origin main --rebase && git push origin main")


if __name__ == "__main__":
    main()
