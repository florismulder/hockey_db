#!/usr/bin/env python3
"""
verwerk_tekst.py — Verwerk gestructureerde wedstrijdtekst naar de database.

Gebruik:
    python3 scripts/verwerk_tekst.py

Het script vraagt om tekst via stdin (plak, dan Ctrl+D) of via een bestand:
    python3 scripts/verwerk_tekst.py wedstrijden.txt

Formaat dat herkend wordt:
    Club A – Club B (score_a-score_b)
    Doelpuntenmakers Club A: Naam (minuut'), Naam (minuut', SC)
    Doelpuntenmakers Club B: Naam (minuut')
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent

CLUB_MAPPING = {
    "amsterdam": "Amsterdam",
    "bloemendaal": "Bloemendaal",
    "den bosch": "Den Bosch",
    "hdm": "HDM",
    "hurley": "Hurley",
    "kampong": "Kampong",
    "klein zwitserland": "Klein Zwitserland",
    "laren": "Laren",
    "oranje-rood": "Oranje-Rood",
    "pinoké": "Pinoké",
    "pinoke": "Pinoké",
    "rotterdam": "Rotterdam",
    "schaerweijde": "Schaerweijde",
    # Dames
    "amsterdam dames": "Amsterdam",
    "bloemendaal dames": "Bloemendaal",
    "den bosch dames": "Den Bosch",
    "hgc": "HGC",
    "schc": "SCHC",
    "tilburg": "Tilburg",
    "hdm dames": "HDM",
    "oranje-rood dames": "Oranje-Rood",
}

def normaliseer_club(naam: str) -> str:
    key = naam.lower().strip()
    return CLUB_MAPPING.get(key, naam.strip())

def parse_minuut(tekst: str):
    m = re.search(r"(\d+)'", tekst)
    return int(m.group(1)) if m else None

def parse_type(tekst: str) -> str:
    t = tekst.upper()
    if "SB" in t: return "sb"
    if "SC" in t or "STRAFCORNER" in t: return "sc"
    return "veld"

def parse_scorers(regel: str, club: str) -> list:
    """Parseer een scorersregel zoals: Naam (25'), Naam (30', SC) en Naam (35')"""
    scorers = []
    # Verwijder prefix zoals "Doelpuntenmakers Club:"
    if ":" in regel:
        regel = regel.split(":", 1)[1]

    # Verwijder trailing punt
    regel = regel.rstrip(".")

    # Vervang " en " door komma voor uniforme verwerking
    regel = re.sub(r"\s+en\s+", ", ", regel)

    # Splits op komma, maar niet binnen haakjes
    delen = re.split(r",\s*(?![^()]*\))", regel)
    for deel in delen:
        deel = deel.strip()
        if not deel:
            continue
        # Naam en info tussen haakjes
        m = re.match(r"(.+?)\s*\(([^)]+)\)", deel)
        if m:
            naam = m.group(1).strip()
            info = m.group(2)
            minuut = parse_minuut(info)
            type_ = parse_type(info)
            if naam:
                scorers.append({
                    "naam": naam,
                    "club": club,
                    "minuut": minuut,
                    "type": type_
                })
        else:
            # Geen haakjes, gewoon naam
            naam = deel.strip()
            if naam and len(naam) > 2:
                scorers.append({"naam": naam, "club": club, "minuut": None, "type": "veld"})
    return scorers

def parse_wedstrijden(tekst: str, datum: str = None, geslacht: str = "heren") -> list:
    wedstrijden = []
    huidige = None
    regels = tekst.split("\n")

    for regel in regels:
        regel = regel.lstrip('•·*\-– ').strip()
        regel = regel.strip()
        if not regel or regel.startswith("*") and len(regel) < 3:
            continue

        # Wedstrijd header: "Club A – Club B (score-score)" of "Club A - Club B (score-score)"
        m = re.match(
            r"^(.+?)\s*[–]\s*(.+?)\s*\((\d+)\s*[-–]\s*(\d+)\)",
            regel
        )
        if m:
            if huidige:
                wedstrijden.append(huidige)
            thuis = normaliseer_club(m.group(1))
            uit = normaliseer_club(m.group(2))
            score_thuis = int(m.group(3))
            score_uit = int(m.group(4))
            huidige = {
                "thuis": thuis,
                "uit": uit,
                "score_thuis": score_thuis,
                "score_uit": score_uit,
                "datum": datum or "",
                "tijdstip": "15:00",
                "gespeeld": True,
                "scorers": [],
                "kaarten": []
            }
            continue

        if huidige is None:
            continue

        # Scorers thuis of uit
        m_scorer = re.match(r"Doelpuntenmaker(?:s)?\s+(.+?)\s*[:\-]\s*(.+)", regel, re.IGNORECASE)
        if m_scorer:
            club_naam = m_scorer.group(1).strip().rstrip(":")
            scorer_tekst = m_scorer.group(2)
            # Match op clubnaam (gedeeltelijk)
            club_match = huidige["thuis"] if club_naam.lower() in huidige["thuis"].lower() or huidige["thuis"].lower() in club_naam.lower() else None
            if not club_match:
                club_match = huidige["uit"] if club_naam.lower() in huidige["uit"].lower() or huidige["uit"].lower() in club_naam.lower() else club_naam
            huidige["scorers"].extend(parse_scorers(scorer_tekst, club_match))
            continue

        # Algemene scorers (geen clubnaam erbij, bijv. bij 1 team)
        if re.match(r"Doelpuntenmaker", regel, re.IGNORECASE):
            rest = re.sub(r"Doelpuntenmaker[s]?\s*[:\-]?\s*", "", regel, flags=re.IGNORECASE).strip()
            if rest:
                # Bepaal club op basis van wie er maar 1 scoorde
                club = huidige["thuis"] if huidige["score_thuis"] == 1 else huidige["uit"]
                huidige["scorers"].extend(parse_scorers(rest, club))

    if huidige:
        wedstrijden.append(huidige)

    return wedstrijden

def sla_op(nieuwe_wedstrijden: list, geslacht: str):
    pad = BASE_DIR / "competities" / geslacht / "programma.json"
    pad.parent.mkdir(parents=True, exist_ok=True)

    bestaand = {"wedstrijden": [], "seizoen": "2025/26", "geslacht": geslacht}
    if pad.exists():
        try:
            bestaand = json.loads(pad.read_text())
        except Exception:
            pass

    bestaande_ws = bestaand.get("wedstrijden", [])

    def key(w):
        return (
            (w.get("thuis", "") or "").lower().strip(),
            (w.get("uit", "") or "").lower().strip(),
            (w.get("datum", "") or "").strip()
        )

    index = {key(w): i for i, w in enumerate(bestaande_ws)}
    toegevoegd = bijgewerkt = 0

    for nw in nieuwe_wedstrijden:
        k = key(nw)
        if k in index:
            bestaande_ws[index[k]].update(nw)
            bijgewerkt += 1
        else:
            bestaande_ws.append(nw)
            toegevoegd += 1

    bestaande_ws.sort(key=lambda w: w.get("datum", "") or "")
    bestaand["wedstrijden"] = bestaande_ws
    bestaand["bijgewerkt"] = datetime.now(timezone.utc).isoformat()

    pad.write_text(json.dumps(bestaand, ensure_ascii=False, indent=2))
    print(f"✅ Opgeslagen: {toegevoegd} nieuw, {bijgewerkt} bijgewerkt")

def main():
    geslacht = "dames" if "--dames" in sys.argv else "heren"

    # Datum argument
    datum = ""
    for arg in sys.argv[1:]:
        if re.match(r"\d{4}-\d{2}-\d{2}", arg):
            datum = arg

    # Invoer lezen
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        tekst = Path(sys.argv[1]).read_text()
    else:
        if sys.stdin.isatty():
            print("Plak de wedstrijdtekst hieronder en druk op Ctrl+D als je klaar bent:")
            print("(Of geef een bestandsnaam mee: python3 scripts/verwerk_tekst.py bestand.txt)")
            print()
        tekst = sys.stdin.read()

    if not datum:
        datum_input = input("\nDatum (YYYY-MM-DD, bijv. 2026-03-22): ").strip()
        datum = datum_input if re.match(r"\d{4}-\d{2}-\d{2}", datum_input) else ""

    wedstrijden = parse_wedstrijden(tekst, datum, geslacht)

    if not wedstrijden:
        print("❌ Geen wedstrijden herkend. Controleer het formaat.")
        sys.exit(1)

    print(f"\n📊 {len(wedstrijden)} wedstrijd(en) gevonden:")
    for w in wedstrijden:
        scorers = len(w.get("scorers", []))
        print(f"   {w['thuis']} {w['score_thuis']}-{w['score_uit']} {w['uit']} — {scorers} scorers")

    sla_op(wedstrijden, geslacht)
    print(f"\nCommit en push:")
    print(f"   cd ~/hockey_db && git add competities/ && git commit -m 'data: wedstrijden {datum}' && git pull origin main --rebase && git push origin main")

if __name__ == "__main__":
    main()
