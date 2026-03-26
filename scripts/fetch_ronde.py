"""
fetch_ronde.py
Haalt wedstrijddetails op voor een hele speelronde.
Geef URLs of match IDs mee als argumenten, of in een tekstbestand.

Gebruik:
    python3 scripts/fetch_ronde.py 1891257 1891258 1891259
    python3 scripts/fetch_ronde.py https://www.hockey.nl/match-center/#/match/1891257 https://...
    python3 scripts/fetch_ronde.py --bestand urls.txt
"""

import json, re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

DB_ROOT = Path(__file__).parent.parent

# ── Dezelfde parseer-logica als fetch_wedstrijd.py ────────────────────────────

MAANDEN = {
    "januari":1,"februari":2,"maart":3,"april":4,"mei":5,"juni":6,
    "juli":7,"augustus":8,"september":9,"oktober":10,"november":11,"december":12
}

def strip_team(naam):
    if not naam: return naam
    return re.sub(r"\s+[HhDd]\d+$", "", naam).strip()

def datum_naar_iso(dag, maand_naam):
    mnd = MAANDEN.get(maand_naam.lower(), 1)
    jaar = 2026 if mnd < 8 else 2025
    return f"{jaar}-{mnd:02d}-{int(dag):02d}"

def slugify(naam):
    naam = naam.lower()
    for a,b in [("à","a"),("á","a"),("â","a"),("ä","a"),("è","e"),("é","e"),
                ("ê","e"),("ë","e"),("í","i"),("ï","i"),("ó","o"),("ô","o"),
                ("ö","o"),("ú","u"),("ü","u"),("ý","y"),("ñ","n"),("ç","c"),
                ("ě","e"),("š","s"),("č","c"),("ž","z"),("'",""),("'","")]:
        naam = naam.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", naam).strip("_")

# Laad spelersindex eenmalig
_SPELERS_INDEX = None
def laad_spelers():
    global _SPELERS_INDEX
    if _SPELERS_INDEX is None:
        pad = DB_ROOT / "spelers" / "index.json"
        if pad.exists():
            _SPELERS_INDEX = json.loads(pad.read_text()).get("spelers", [])
        else:
            _SPELERS_INDEX = []
    return _SPELERS_INDEX

def bepaal_club(naam):
    for speler in laad_spelers():
        sn = speler["naam"].lower()
        zn = naam.lower()
        if sn == zn or zn in sn or sn in zn:
            return speler.get("club", "")
    return ""

def parse_wedstrijd(tekst, match_id):
    regels = [r.strip() for r in tekst.split("\n") if r.strip()]
    wedstrijd = {
        "wedstrijdnummer": match_id,
        "gespeeld": True,
        "scorers": [],
        "kaarten": [],
    }

    # Score + teams vinden
    for i, r in enumerate(regels):
        score_match = re.match(r"^(\d+)\s*-\s*(\d+)$", r)
        if score_match:
            wedstrijd["score_thuis"] = int(score_match.group(1))
            wedstrijd["score_uit"]   = int(score_match.group(2))
            if i >= 4:
                wedstrijd["thuis"] = strip_team(regels[i-4])
                wedstrijd["uit"]   = strip_team(regels[i+1]) if i+1 < len(regels) else ""
            for j in range(max(0, i-3), i):
                dm = re.match(r"^(\d{1,2})\s+(januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)$", regels[j].lower())
                if dm:
                    wedstrijd["datum_tekst"] = regels[j]
                    wedstrijd["datum"] = datum_naar_iso(dm.group(1), dm.group(2))
                tm = re.match(r"^(\d{1,2}):(\d{2})$", regels[j])
                if tm:
                    wedstrijd["tijdstip"] = regels[j]
            break

    # Wedstrijdinfo
    for i, r in enumerate(regels):
        if r == "Wedstrijdnummer" and i+1 < len(regels):
            wedstrijd["wedstrijdnummer"] = regels[i+1]
        if r in ["Accommodatie","Accomodatie"] and i+1 < len(regels):
            wedstrijd["locatie"] = regels[i+1]
        if r == "Adres" and i+1 < len(regels):
            wedstrijd["adres"] = regels[i+1]

    # Events parsen
    SKIP = {"start wedstrijd","einde wedstrijd","start 2de kwart","einde 2de kwart",
            "start 3de kwart","einde 3de kwart","start 4de kwart","einde 4de kwart",
            "einde 1ste kwart","start 1ste kwart","Wedstrijdinfo","Wedstrijdnummer",
            "Accommodatie","Accomodatie","Adres","Doelpunt","Groene kaart",
            "Gele kaart","Rode kaart"}

    def is_minuut(s): return bool(re.match(r"^\d{1,3}'$", s))
    def is_naam(s): return s not in SKIP and not is_minuut(s) and len(s) > 2

    i = 0
    while i < len(regels):
        r = regels[i]
        event = None
        if r == "Doelpunt":      event = "doelpunt"
        elif r == "Groene kaart": event = "groen"
        elif r == "Gele kaart":   event = "geel"
        elif r == "Rode kaart":   event = "rood"

        if event:
            naam = None
            minuut = None
            # Zoek naam en minuut in de omliggende regels
            kandidaten = regels[max(0,i-2):i] + regels[i+1:min(len(regels),i+4)]
            for k in kandidaten:
                if is_minuut(k) and minuut is None:
                    minuut = int(k.rstrip("'"))
                elif is_naam(k) and naam is None:
                    naam = k

            if naam:
                club = bepaal_club(naam)
                if event == "doelpunt":
                    wedstrijd["scorers"].append({
                        "naam": naam, "club": club,
                        "minuut": minuut, "type": "veld"
                    })
                else:
                    wedstrijd["kaarten"].append({
                        "naam": naam, "club": club,
                        "minuut": minuut, "type": event
                    })
        i += 1

    return wedstrijd

def sla_op(wedstrijd):
    thuis = wedstrijd.get("thuis", "")
    # Geslacht bepalen
    geslacht = "heren"
    for speler in laad_spelers():
        if speler.get("club", "").lower() in thuis.lower():
            geslacht = speler.get("geslacht", "heren")
            break

    pad = DB_ROOT / "competities" / geslacht / "programma.json"
    data = json.loads(pad.read_text())
    wedstrijden = data.get("wedstrijden", [])

    gevonden = False
    for w in wedstrijden:
        wt = strip_team(w.get("thuis","")).lower()
        wu = strip_team(w.get("uit","")).lower()
        if wt == thuis.lower() and wu == wedstrijd.get("uit","").lower():
            w.update(wedstrijd)
            gevonden = True
            break
        if w.get("wedstrijdnummer") == wedstrijd.get("wedstrijdnummer"):
            w.update(wedstrijd)
            gevonden = True
            break

    if not gevonden:
        wedstrijden.append(wedstrijd)

    data["wedstrijden"] = wedstrijden
    pad.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return geslacht

def druk_af(wedstrijd, idx, totaal):
    thuis = wedstrijd.get("thuis","?")
    uit   = wedstrijd.get("uit","?")
    st    = wedstrijd.get("score_thuis","?")
    su    = wedstrijd.get("score_uit","?")
    print(f"\n  [{idx}/{totaal}] {thuis} {st}–{su} {uit}")
    print(f"         📅 {wedstrijd.get('datum','')}  🕒 {wedstrijd.get('tijdstip','')}")
    if wedstrijd.get("locatie"):
        print(f"         📍 {wedstrijd['locatie']}")
    if wedstrijd.get("scorers"):
        sc_str = ", ".join(s["naam"] + " " + str(s["minuut"]) + "'" for s in wedstrijd["scorers"])
        print(f"         ⚽ Scorers: {sc_str}")
    if wedstrijd.get("kaarten"):
        sym = {"groen":"🟩","geel":"🟨","rood":"🟥"}
        k_str = ", ".join(sym.get(k["type"],"?") + k["naam"] for k in wedstrijd["kaarten"])
        print(f"         🟨 Kaarten: {k_str}")

# ── Main ──────────────────────────────────────────────────────────────────────

def extraheer_ids(args):
    ids = []
    if "--bestand" in args:
        idx = args.index("--bestand")
        if idx+1 < len(args):
            pad = Path(args[idx+1])
            if pad.exists():
                for lijn in pad.read_text().splitlines():
                    lijn = lijn.strip()
                    if lijn:
                        m = re.search(r"/match/(\d+)", lijn)
                        ids.append(m.group(1) if m else lijn)
    else:
        for arg in args:
            m = re.search(r"/match/(\d+)", arg)
            ids.append(m.group(1) if m else arg.strip())
    return [x for x in ids if x.isdigit()]

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Gebruik: python3 scripts/fetch_ronde.py <match_id_of_url> [...]")
        print("\nVoorbeelden:")
        print("  python3 scripts/fetch_ronde.py 1891257 1891258 1891259")
        print("  python3 scripts/fetch_ronde.py https://hockey.nl/match-center/#/match/1891257 https://...")
        print("  python3 scripts/fetch_ronde.py --bestand urls.txt")
        sys.exit(1)

    match_ids = extraheer_ids(args)
    if not match_ids:
        print("❌ Geen geldige match IDs gevonden.")
        sys.exit(1)

    print(f"\n🏒 {len(match_ids)} wedstrijd(en) ophalen...\n")
    resultaten = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i, match_id in enumerate(match_ids, 1):
            url = f"https://www.hockey.nl/match-center/#/match/{match_id}"
            print(f"  [{i}/{len(match_ids)}] Ophalen {match_id}...", end=" ", flush=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(4)
                tekst = page.inner_text("body")
                page.close()
                wedstrijd = parse_wedstrijd(tekst, match_id)
                resultaten.append(wedstrijd)
                thuis = wedstrijd.get("thuis","?")
                uit   = wedstrijd.get("uit","?")
                st    = wedstrijd.get("score_thuis","?")
                su    = wedstrijd.get("score_uit","?")
                print(f"✅ {thuis} {st}–{su} {uit}")
            except Exception as e:
                print(f"❌ Fout: {e}")
                resultaten.append(None)
        browser.close()

    # Overzicht
    print(f"\n{'─'*60}")
    print(f"  Overzicht ({len([r for r in resultaten if r])} succesvol)")
    print(f"{'─'*60}")
    for i, w in enumerate(resultaten, 1):
        if w: druk_af(w, i, len(resultaten))

    print(f"\n{'─'*60}")
    antwoord = input("Alles opslaan in programma JSON? (j/n): ").strip().lower()

    if antwoord == "j":
        opgeslagen = 0
        for w in resultaten:
            if w:
                try:
                    geslacht = sla_op(w)
                    opgeslagen += 1
                    print(f"  ✅ {w.get('thuis')} vs {w.get('uit')} → {geslacht}/programma.json")
                except Exception as e:
                    print(f"  ❌ Fout bij opslaan {w.get('thuis')}: {e}")
        print(f"\n✅ {opgeslagen} wedstrijd(en) opgeslagen!")

        # Git commit tip
        print(f"\nVerget niet te committen:")
        datum_str = resultaten[0].get("datum_tekst","") if resultaten else ""
        print(f"  git add competities/ && git commit -m 'data: ronde " + datum_str + " toegevoegd' && git push")
    else:
        print("Niet opgeslagen.")
