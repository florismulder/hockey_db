"""
fetch_topscorers.py
Haalt topscorerslijsten op van hockey.nl via Playwright
en koppelt doelpunten aan spelersprofielen in de database.

Gebruik:
    python3 scripts/fetch_topscorers.py
"""

import json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

DB_ROOT = Path(__file__).parent.parent

URLS = {
    "heren": "https://www.hockey.nl/topscorers-tulp-hoofdklasse-heren-2025-2026",
    "dames": "https://www.hockey.nl/topscorers-tulp-hoofdklasse-dames-2025-2026",
}

def slugify(naam):
    naam = naam.lower()
    for a,b in [("à","a"),("á","a"),("â","a"),("ä","a"),("è","e"),("é","e"),
                ("ê","e"),("ë","e"),("í","i"),("ï","i"),("ó","o"),("ô","o"),
                ("ö","o"),("ú","u"),("ü","u"),("ý","y"),("ñ","n"),("ç","c"),
                ("ě","e"),("š","s"),("č","c"),("ž","z"),("'",""),("'","")]:
        naam = naam.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", naam).strip("_")

def parse_topscorers(tekst):
    """
    Parseert de hockey.nl topscorerspagina.
    Formaat per scorer (tab-gescheiden regels):
      SPELER \t CLUB \t VD \t SC \t SB \t GOALS
    """
    scorers = []
    if "SPELER" in tekst:
        tekst = tekst[tekst.find("SPELER"):]

    regels = [r.strip() for r in tekst.split("\n") if r.strip()]
    SKIP = {"SPELER","CLUB","VD","SC","SB","GOALS"}

    i = 0
    while i < len(regels):
        regel = regels[i]
        if regel in SKIP or regel.startswith("VD =") or regel.startswith("Bijgewerkt"):
            i += 1
            continue
        # Elke scorer staat als 6 opeenvolgende regels: naam, club, vd, sc, sb, goals
        if i + 5 < len(regels):
            naam = regel
            club = regels[i+1]
            try:
                vd    = int(regels[i+2])
                sc    = int(regels[i+3])
                sb    = int(regels[i+4])
                goals = int(regels[i+5])
                scorers.append({
                    "naam":       naam,
                    "naam_slug":  slugify(naam),
                    "club":       club,
                    "vd":         vd,
                    "sc":         sc,
                    "sb":         sb,
                    "doelpunten": goals,
                    "seizoen":    "2025-2026",
                })
                i += 6
                continue
            except (ValueError, IndexError):
                pass
        i += 1
    return scorers

def koppel_aan_index(scorers, geslacht):
    """Koppelt doelpunten aan spelersprofielen in de centrale index."""
    index_pad = DB_ROOT / "spelers" / "index.json"
    if not index_pad.exists():
        print(f"  ⚠️  index.json niet gevonden")
        return 0

    index = json.loads(index_pad.read_text())
    gekoppeld = 0

    for speler in index.get("spelers", []):
        if speler.get("geslacht") != geslacht:
            continue
        slug = slugify(speler["naam"])
        for scorer in scorers:
            if scorer["naam_slug"] == slug:
                speler["doelpunten_seizoen"] = scorer["doelpunten"]
                speler["vd"] = scorer.get("vd", 0)
                speler["sc"] = scorer.get("sc", 0)
                speler["sb"] = scorer.get("sb", 0)
                gekoppeld += 1
                break

    index_pad.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    # Koppel ook aan individuele club-JSON's
    for pad in (DB_ROOT / "spelers" / geslacht).glob("*.json"):
        try:
            data = json.loads(pad.read_text())
            gewijzigd = False
            for speler in data.get("spelers", []):
                slug = slugify(speler["naam"])
                for scorer in scorers:
                    if scorer["naam_slug"] == slug:
                        speler["doelpunten_seizoen"] = scorer["doelpunten"]
                        speler["vd"] = scorer.get("vd", 0)
                        speler["sc"] = scorer.get("sc", 0)
                        speler["sb"] = scorer.get("sb", 0)
                        gewijzigd = True
                        break
            if gewijzigd:
                pad.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ⚠️  Fout bij {pad.name}: {e}")

    return gekoppeld

def run():
    from datetime import datetime
    vandaag = datetime.now().strftime("%Y-%m-%d")

    print("🏒 Topscorers ophalen van hockey.nl...\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for geslacht, url in URLS.items():
            print(f"📥 {geslacht.capitalize()} topscorers...")
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(4)
                tekst = page.inner_text("body")
                page.close()

                scorers = parse_topscorers(tekst)
                print(f"  {len(scorers)} scorers gevonden")
                if scorers:
                    for s in scorers[:3]:
                        print(f"    {s['naam']} ({s['club']}): {s['doelpunten']} goals")

                    # Opslaan als topscorers.json
                    pad = DB_ROOT / "competities" / geslacht / "topscorers.json"
                    pad.write_text(json.dumps({
                        "geslacht":    geslacht,
                        "seizoen":     "2025-2026",
                        "bijgewerkt":  vandaag,
                        "topscorers":  scorers,
                    }, indent=2, ensure_ascii=False))
                    print(f"  💾 Opgeslagen → competities/{geslacht}/topscorers.json")

                    gekoppeld = koppel_aan_index(scorers, geslacht)
                    print(f"  🔗 {gekoppeld} spelers gekoppeld")
                else:
                    print(f"  ⚠️  Geen scorers geparseerd — controleer de pagina")

            except Exception as e:
                print(f"  ❌ Fout: {e}")

        browser.close()
    print("\n✅ Klaar!")

if __name__ == "__main__":
    run()
