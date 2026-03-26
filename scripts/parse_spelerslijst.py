"""
parse_spelerslijst.py
Leest de officiële KNHB spelerslijst PDF in en slaat alle spelers op
als JSON per club in /spelers/heren/ en /spelers/dames/

Gebruik:
    python3 scripts/parse_spelerslijst.py pad/naar/spelerslijst.pdf
"""

import json
import re
import sys
from pathlib import Path
import pdfplumber

DB_ROOT = Path(__file__).parent.parent

CLUB_SLUG = {
    "Amsterdam": "amsterdam",
    "Bloemendaal": "bloemendaal",
    "Den Bosch": "den_bosch",
    "HDM": "hdm",
    "HGC": "hgc",
    "Hurley": "hurley",
    "Kampong": "kampong",
    "Klein Zwitserland": "klein_zwitserland",
    "Laren": "laren",
    "Oranje-Rood": "oranje_rood",
    "Pinoké": "pinoke",
    "Rotterdam": "rotterdam",
    "Schaerweijde": "schaerweijde",
    "SCHC": "schc",
    "Tilburg": "tilburg",
}

def slugify(naam):
    naam = naam.lower()
    naam = re.sub(r"[àáâã]", "a", naam)
    naam = re.sub(r"[èéêë]", "e", naam)
    naam = re.sub(r"[ìíîï]", "i", naam)
    naam = re.sub(r"[òóôõ]", "o", naam)
    naam = re.sub(r"[ùúûü]", "u", naam)
    naam = re.sub(r"[^a-z0-9]", "_", naam)
    return re.sub(r"_+", "_", naam).strip("_")

def parse_pdf(pdf_pad):
    spelers = {}  # {(club, geslacht): [spelers]}

    with pdfplumber.open(pdf_pad) as pdf:
        for pagina in pdf.pages:
            tabel = pagina.extract_table()
            if not tabel:
                continue
            for rij in tabel:
                if not rij or len(rij) < 5:
                    continue
                # Skip header
                if rij[0] and "Klasse" in str(rij[0]):
                    continue
                # Verwacht: Klasse | Teamnaam | Positie | Naam_speler | Rugnummer | Keeper | Aanvoerder
                try:
                    teamnaam = str(rij[1] or "").strip()
                    naam     = str(rij[3] or "").strip()
                    rugnr    = str(rij[4] or "").strip()
                    keeper   = bool(rij[5] and rij[5].strip())
                    aanvoer  = bool(rij[6] and rij[6].strip()) if len(rij) > 6 else False

                    if not naam or not teamnaam:
                        continue

                    # Teamnaam splitsen: "Amsterdam H1" → club=Amsterdam, geslacht=heren
                    match = re.match(r"^(.+?)\s+(H|D)\d+$", teamnaam)
                    if not match:
                        continue

                    club_naam = match.group(1).strip()
                    geslacht  = "heren" if match.group(2) == "H" else "dames"
                    club_id   = CLUB_SLUG.get(club_naam, slugify(club_naam))

                    sleutel = (club_naam, club_id, geslacht)
                    if sleutel not in spelers:
                        spelers[sleutel] = []

                    spelers[sleutel].append({
                        "naam":       naam,
                        "id":         slugify(naam),
                        "rugnummer":  rugnr,
                        "keeper":     keeper,
                        "aanvoerder": aanvoer,
                        "club":       club_naam,
                        "club_id":    club_id,
                        "geslacht":   geslacht,
                    })
                except Exception:
                    continue

    return spelers

def sla_op(spelers):
    totaal = 0
    for (club_naam, club_id, geslacht), selectie in spelers.items():
        pad = DB_ROOT / "spelers" / geslacht / f"{club_id}.json"
        pad.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "club":     club_naam,
            "club_id":  club_id,
            "geslacht": geslacht,
            "seizoen":  "2025-2026",
            "bron":     "KNHB spelerslijst PDF",
            "spelers":  selectie,
        }
        pad.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  ✅ {club_naam} {geslacht}: {len(selectie)} spelers → {pad.relative_to(DB_ROOT)}")
        totaal += len(selectie)

    # Maak ook een gecombineerde index aan
    index = []
    for (club_naam, club_id, geslacht), selectie in spelers.items():
        for s in selectie:
            index.append(s)

    index_pad = DB_ROOT / "spelers" / "index.json"
    index_pad.write_text(json.dumps({
        "seizoen": "2025-2026",
        "totaal":  len(index),
        "spelers": index,
    }, indent=2, ensure_ascii=False))

    print(f"\n  📋 Index aangemaakt: {len(index)} spelers totaal")
    print(f"  📁 Opgeslagen in: {index_pad.relative_to(DB_ROOT)}")
    return totaal

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: python3 scripts/parse_spelerslijst.py <pad-naar-pdf>")
        sys.exit(1)

    pdf_pad = Path(sys.argv[1])
    if not pdf_pad.exists():
        print(f"❌ Bestand niet gevonden: {pdf_pad}")
        sys.exit(1)

    print(f"📄 PDF inlezen: {pdf_pad.name}")
    spelers = parse_pdf(pdf_pad)
    print(f"✅ {len(spelers)} clubs gevonden\n")
    totaal = sla_op(spelers)
    print(f"\n🏑 Klaar! {totaal} spelers verwerkt.")
