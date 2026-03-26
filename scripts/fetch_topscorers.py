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

def haal_topscorers(browser, url, geslacht):
    """Haalt topscorers op via Playwright."""
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Probeer tabel te vinden
        scorers = []

        # Strategie 1: zoek een tabel met score/goal kolom
        rows = page.locator("table tr").all()
        for row in rows:
            tekst = row.inner_text()
            delen = tekst.strip().split("\t")
            if len(delen) < 3:
                delen = tekst.strip().split()
            # Zoek rijen met een getal (doelpunten)
            if any(d.isdigit() for d in delen):
                # Probeer naam en doelpunten te extraheren
                try:
                    # Kolommen: positie, naam, club, doelpunten
                    nums = [i for i,d in enumerate(delen) if d.isdigit()]
                    if nums and len(delen) >= 3:
                        doelpunten = int(delen[nums[-1]])
                        naam = " ".join(d for d in delen if not d.isdigit() and d.strip())
                        naam = re.sub(r"^\d+\.\s*", "", naam).strip()
                        if naam and doelpunten > 0:
                            scorers.append({
                                "naam": naam,
                                "naam_slug": slugify(naam),
                                "doelpunten": doelpunten,
                                "seizoen": "2025-2026",
                            })
                except:
                    continue

        # Strategie 2: zoek op specifieke CSS selectors
        if not scorers:
            items = page.locator(".scorer, .topscorer, [class*='scorer'], [class*='player']").all()
            for item in items[:50]:
                try:
                    tekst = item.inner_text().strip()
                    match = re.search(r"(\d+)\s*$", tekst)
                    if match:
                        doelpunten = int(match.group(1))
                        naam = tekst[:match.start()].strip()
                        naam = re.sub(r"^\d+\.\s*", "", naam).strip()
                        if naam and doelpunten > 0:
                            scorers.append({
                                "naam": naam,
                                "naam_slug": slugify(naam),
                                "doelpunten": doelpunten,
                                "seizoen": "2025-2026",
                            })
                except:
                    continue

        # Strategie 3: dump volledige paginatekst en parseer
        if not scorers:
            tekst = page.locator("main, article, .content, body").first.inner_text()
            # Zoek patronen zoals "1. Naam Naam 15" of "Naam Naam - 15"
            for lijn in tekst.split("\n"):
                lijn = lijn.strip()
                match = re.match(r"^\d+[\.\)]\s+(.+?)\s+(\d+)\s*$", lijn)
                if match:
                    naam = match.group(1).strip()
                    doelpunten = int(match.group(2))
                    if naam and doelpunten > 0 and len(naam) > 3:
                        scorers.append({
                            "naam": naam,
                            "naam_slug": slugify(naam),
                            "doelpunten": doelpunten,
                            "seizoen": "2025-2026",
                        })

        return scorers
    except Exception as e:
        print(f"  ⚠️  Fout bij ophalen {url}: {e}")
        return []
    finally:
        page.close()

def koppel_aan_spelers(scorers, geslacht):
    """Koppelt doelpunten aan spelersprofielen in de database."""
    if not scorers:
        return 0

    # Laad alle spelersbestanden voor dit geslacht
    speler_paden = list((DB_ROOT / "spelers" / geslacht).glob("*.json"))
    gekoppeld = 0

    for pad in speler_paden:
        try:
            data = json.loads(pad.read_text())
            gewijzigd = False
            for speler in data.get("spelers", []):
                slug = slugify(speler["naam"])
                for scorer in scorers:
                    if scorer["naam_slug"] == slug or \
                       scorer["naam"].lower() in speler["naam"].lower() or \
                       speler["naam"].lower() in scorer["naam"].lower():
                        speler["doelpunten_seizoen"] = scorer["doelpunten"]
                        gewijzigd = True
                        gekoppeld += 1
                        break
            if gewijzigd:
                pad.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ⚠️  Fout bij {pad}: {e}")

    # Update ook de centrale index
    index_pad = DB_ROOT / "spelers" / "index.json"
    if index_pad.exists():
        try:
            index = json.loads(index_pad.read_text())
            for speler in index.get("spelers", []):
                if speler.get("geslacht") != geslacht:
                    continue
                slug = slugify(speler["naam"])
                for scorer in scorers:
                    if scorer["naam_slug"] == slug or \
                       scorer["naam"].lower() in speler["naam"].lower():
                        speler["doelpunten_seizoen"] = scorer["doelpunten"]
                        break
            index_pad.write_text(json.dumps(index, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ⚠️  Fout bij index: {e}")

    return gekoppeld

def sla_topscorers_op(scorers, geslacht):
    """Slaat topscorers op als apart JSON-bestand."""
    pad = DB_ROOT / "competities" / geslacht / "topscorers.json"
    pad.write_text(json.dumps({
        "geslacht": geslacht,
        "seizoen": "2025-2026",
        "bron": URLS[geslacht],
        "topscorers": scorers,
    }, indent=2, ensure_ascii=False))
    print(f"  ✅ {len(scorers)} topscorers opgeslagen → {pad.relative_to(DB_ROOT)}")

def run():
    print("🏒 Topscorers ophalen van hockey.nl...\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for geslacht, url in URLS.items():
            print(f"📥 {geslacht.capitalize()} topscorers...")
            scorers = haal_topscorers(browser, url, geslacht)
            if scorers:
                sla_topscorers_op(scorers, geslacht)
                gekoppeld = koppel_aan_spelers(scorers, geslacht)
                print(f"  🔗 {gekoppeld} spelers gekoppeld")
            else:
                print(f"  ⚠️  Geen topscorers gevonden — pagina mogelijk JS-rendered")
                print(f"      Probeer handmatig: {url}")
        browser.close()
    print("\n✅ Klaar!")

if __name__ == "__main__":
    run()
