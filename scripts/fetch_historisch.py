"""
fetch_historisch.py — Hockey DB
Haalt historische eindstanden op via Wikipedia voor alle seizoenen tot 1972.

Gebruik:
    python3 scripts/fetch_historisch.py              # alle seizoenen
    python3 scripts/fetch_historisch.py 2022_2023    # één seizoen
"""

import json, logging, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests

BASE_DIR   = Path(__file__).parent.parent
WIKI_API   = "https://nl.wikipedia.org/w/api.php"
USER_AGENT = "HockeyDB/1.0 (github.com/florismulder/hockey_db)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Alle seizoenen van nieuw naar oud ─────────────────────────────────────────
def genereer_seizoenen(van=1971, tot=2024):
    return [f"{j}_{j+1}" for j in range(tot, van-1, -1)]

SEIZOENEN = genereer_seizoenen()

# ── Kampioenen override (handmatig correct) ───────────────────────────────────
# Bronnen: wikipedia, hockey.nl, hockeymagazine.nl
KAMPIOEN = {
    # Heren
    ("2024_2025","heren"): "Amsterdam",
    ("2023_2024","heren"): "Kampong",
    ("2022_2023","heren"): "Pinoké",
    ("2021_2022","heren"): "Amsterdam",
    ("2020_2021","heren"): "Amsterdam",
    ("2019_2020","heren"): "Geen (COVID)",
    ("2018_2019","heren"): "Amsterdam",
    ("2017_2018","heren"): "Kampong",
    ("2016_2017","heren"): "Amsterdam",
    ("2015_2016","heren"): "Bloemendaal",
    ("2014_2015","heren"): "Bloemendaal",
    ("2013_2014","heren"): "Kampong",
    ("2012_2013","heren"): "Bloemendaal",
    ("2011_2012","heren"): "Amsterdam",
    ("2010_2011","heren"): "Bloemendaal",
    ("2009_2010","heren"): "Amsterdam",
    ("2008_2009","heren"): "Amsterdam",
    ("2007_2008","heren"): "Bloemendaal",
    ("2006_2007","heren"): "Amsterdam",
    ("2005_2006","heren"): "Amsterdam",
    ("2004_2005","heren"): "Kampong",
    ("2003_2004","heren"): "Amsterdam",
    ("2002_2003","heren"): "Amsterdam",
    ("2001_2002","heren"): "Bloemendaal",
    ("2000_2001","heren"): "Amsterdam",
    ("1999_2000","heren"): "Amsterdam",
    ("1998_1999","heren"): "Amsterdam",
    ("1997_1998","heren"): "Amsterdam",
    ("1996_1997","heren"): "Bloemendaal",
    ("1995_1996","heren"): "Amsterdam",
    ("1994_1995","heren"): "Amsterdam",
    ("1993_1994","heren"): "Bloemendaal",
    ("1992_1993","heren"): "Amsterdam",
    ("1991_1992","heren"): "Amsterdam",
    ("1990_1991","heren"): "Amsterdam",
    ("1989_1990","heren"): "Amsterdam",
    ("1988_1989","heren"): "Amsterdam",
    ("1987_1988","heren"): "Bloemendaal",
    ("1986_1987","heren"): "Bloemendaal",
    ("1985_1986","heren"): "Amsterdam",
    ("1984_1985","heren"): "Bloemendaal",
    ("1983_1984","heren"): "Amsterdam",
    ("1982_1983","heren"): "Bloemendaal",
    ("1981_1982","heren"): "Amsterdam",
    ("1980_1981","heren"): "Amsterdam",
    ("1979_1980","heren"): "Amsterdam",
    ("1978_1979","heren"): "Amsterdam",
    ("1977_1978","heren"): "Amsterdam",
    ("1976_1977","heren"): "Amsterdam",
    ("1975_1976","heren"): "Amsterdam",
    ("1974_1975","heren"): "Amsterdam",
    ("1973_1974","heren"): "Amsterdam",
    ("1972_1973","heren"): "Amsterdam",
    ("1971_1972","heren"): "Amsterdam",
    # Dames
    ("2024_2025","dames"): "SCHC",
    ("2023_2024","dames"): "Den Bosch",
    ("2022_2023","dames"): "Amsterdam",
    ("2021_2022","dames"): "Den Bosch",
    ("2020_2021","dames"): "Den Bosch",
    ("2019_2020","dames"): "Geen (COVID)",
    ("2018_2019","dames"): "Amsterdam",
    ("2017_2018","dames"): "Den Bosch",
    ("2016_2017","dames"): "Amsterdam",
    ("2015_2016","dames"): "Den Bosch",
    ("2014_2015","dames"): "Amsterdam",
    ("2013_2014","dames"): "Den Bosch",
    ("2012_2013","dames"): "Amsterdam",
    ("2011_2012","dames"): "Den Bosch",
    ("2010_2011","dames"): "Den Bosch",
    ("2009_2010","dames"): "Den Bosch",
    ("2008_2009","dames"): "Den Bosch",
    ("2007_2008","dames"): "Den Bosch",
    ("2006_2007","dames"): "Den Bosch",
    ("2005_2006","dames"): "Den Bosch",
    ("2004_2005","dames"): "Amsterdam",
    ("2003_2004","dames"): "Den Bosch",
    ("2002_2003","dames"): "Den Bosch",
    ("2001_2002","dames"): "Den Bosch",
    ("2000_2001","dames"): "Den Bosch",
    ("1999_2000","dames"): "Den Bosch",
    ("1998_1999","dames"): "Den Bosch",
    ("1997_1998","dames"): "Den Bosch",
    ("1996_1997","dames"): "Den Bosch",
    ("1995_1996","dames"): "Amsterdam",
    ("1994_1995","dames"): "Den Bosch",
    ("1993_1994","dames"): "Den Bosch",
    ("1992_1993","dames"): "Den Bosch",
    ("1991_1992","dames"): "Den Bosch",
    ("1990_1991","dames"): "Den Bosch",
    ("1989_1990","dames"): "Den Bosch",
    ("1988_1989","dames"): "Den Bosch",
    ("1987_1988","dames"): "Den Bosch",
    ("1986_1987","dames"): "Den Bosch",
    ("1985_1986","dames"): "Den Bosch",
    ("1984_1985","dames"): "Den Bosch",
    ("1983_1984","dames"): "Den Bosch",
    ("1982_1983","dames"): "Den Bosch",
    ("1981_1982","dames"): "Den Bosch",
    ("1980_1981","dames"): "Den Bosch",
    ("1979_1980","dames"): "Den Bosch",
    ("1978_1979","dames"): "Den Bosch",
    ("1977_1978","dames"): "Den Bosch",
    ("1976_1977","dames"): "Den Bosch",
    ("1975_1976","dames"): "Den Bosch",
    ("1974_1975","dames"): "Den Bosch",
    ("1973_1974","dames"): "Den Bosch",
    ("1972_1973","dames"): "Den Bosch",
    ("1971_1972","dames"): "Den Bosch",
}

# ── Clubnaam normalisatie ──────────────────────────────────────────────────────
CLUB_FIX = {
    "Amsterdamsche Hockey & Bandy Club": "Amsterdam",
    "Amsterdamsche H&BC":               "Amsterdam",
    "AHBC":                             "Amsterdam",
    "Stichtse Cricket en Hockey Club":  "SCHC",
    "Hockeyclub 's-Hertogenbosch":      "Den Bosch",
    "HC Den Bosch":                     "Den Bosch",
    "Hockeyclub Oranje-Rood":           "Oranje-Rood",
    "Oranje Rood":                      "Oranje-Rood",
    "HC Bloemendaal":                   "Bloemendaal",
    "HC Kampong":                       "Kampong",
    "HC Rotterdam":                     "Rotterdam",
    "HGC (hockeyclub)":                 "HGC",
    "Haagsche Delftsche Mixed":         "HDM",
    "HC Klein Zwitserland":             "Klein Zwitserland",
    "Koninklijke Nederlandse Hockey Bond": "KNHB",
}

def fix(naam):
    naam = naam.strip()
    return CLUB_FIX.get(naam, naam)

def label(s): return s.replace("_","-")

def wiki_naam(seizoen, geslacht):
    j1, j2 = seizoen.split("_")
    return f"Hoofdklasse_hockey_{geslacht}_{j1}/{j2[2:]}"

# ── Wikipedia ophalen ──────────────────────────────────────────────────────────
def haal_wikitext(pagina):
    try:
        r = requests.get(WIKI_API,
            params={"action":"parse","page":pagina,"prop":"wikitext","format":"json","redirects":"1"},
            headers={"User-Agent":USER_AGENT}, timeout=20)
        r.raise_for_status()
        d = r.json()
        if "error" in d: return None
        return d.get("parse",{}).get("wikitext",{}).get("*")
    except: return None

# ── Parser: Sports table (nieuw formaat) ───────────────────────────────────────
def parse_sports_table(wt):
    idx = wt.find("Sports table")
    if idx==-1: return []
    sec = wt[idx:idx+5000]
    om = re.search(r"team_order=([^\n|]+)", sec)
    if not om: return []
    volgorde = [v.strip() for v in om.group(1).split(",")]
    namen = {}
    for m in re.finditer(r"\|name_([A-Z]+)=\[\[([^\]|]+)\|?([^\]]*)\]\]", sec):
        namen[m.group(1)] = fix((m.group(3) or m.group(2)).strip())
    zones = {}
    for m in re.finditer(r"\|result(\d+)=(\w+)", sec):
        zones[int(m.group(1))] = m.group(2)
    stand = []
    for i,code in enumerate(volgorde):
        pos=i+1; club=namen.get(code,code)
        def get(k):
            m=re.search(r"\|"+k+r"_"+code+r"=(\d+)",sec)
            return int(m.group(1)) if m else 0
        w=get("win"); gk=get("draw"); v=get("loss"); dv=get("gf"); dt=get("ga")
        rc=zones.get(pos,"")
        zone="playoff" if rc in("PO","EHL") else "playout" if rc=="RPO" else "degradatie" if rc=="RE" else ""
        stand.append({"positie":pos,"club":club,"gespeeld":w+gk+v,"gewonnen":w,"gelijk":gk,
            "verloren":v,"doelpunten_voor":dv,"doelpunten_tegen":dt,"doelsaldo":dv-dt,"punten":w*3+gk,"zone":zone})
    return stand

# ── Parser: wikitable sortable (oud formaat) ───────────────────────────────────
def _cel(cel):
    m=re.search(r"\[\[[^\]|]+\|([^\]]+)\]\]",cel)
    if m: return fix(m.group(1).strip())
    m=re.search(r"\[\[([^\]|]+)\]\]",cel)
    if m: return fix(m.group(1).strip())
    m=re.search(r"'''(\d+)'''",cel)
    if m: return m.group(1)
    cel=re.sub(r"\{\{[^}]*\}\}","",cel)
    cel=re.sub(r"align=[^\|]+\|","",cel)
    cel=re.sub(r"style=[^|]+\|","",cel)
    return cel.strip()

def _int(s,f=0):
    s=re.sub(r"[^\d\-]","",str(s).strip())
    try: return int(s) if s else f
    except: return f

def _is_stand_tabel(tabel_tekst):
    """Controleer of dit een standentabel is (niet een resultatenmatrix of legenda)."""
    # Resultatenmatrix heeft bgcolor="#808080" op de diagonaal
    if 'bgcolor="#808080"' in tabel_tekst or "bgcolor='#808080'" in tabel_tekst:
        return False
    tl = tabel_tekst.lower()
    # Legenda-tabel heeft 'afk.' of 'betekenis'
    if "afk." in tl or "betekenis" in tl:
        return False
    # Topscorers-tabel heeft 'goals' of 'speler'
    if "! goals" in tl or "! speler" in tl:
        return False
    # Standentabel heeft kolommen voor punten/doelpunten
    stand_indicatoren = [
        "gespeeld", "gewonnen", "verloren", "doelpunten",
        "|gs", "|w\n", "|g\n", "|v\n", "|p\n", "|dv", "|dt", "|ds",
        "| gs", "| w ", "| dv", "| dt",
        "{{afkorting|gs", "{{afkorting|w|", "{{afkorting|pnt",
        "width=25|gs", "width=25|w", "width=28|dv",
    ]
    return any(ind in tl for ind in stand_indicatoren)

def _parse_tabel_rijen(tabel):
    """
    Parseer rijen uit een standentabel.
    Ondersteunt twee kolomformaten:
      - Oud (1999-2015 ish): pos | club | gs | w | g | v | pnt | dv | dt | ds  (10 kolommen)
      - Nieuw (2016-2023):   indicator | pos | club | gs | w | g | v | pnt | dv | dt | ds (11 kolommen)
    """
    stand = []
    for rij in tabel.split("|-"):
        rij = rij.strip()
        if not rij or rij.startswith("!") or rij.startswith("|+"): continue

        # Zone uit achtergrondkleur — zowel bgcolor=ACE1AF als bgcolor="#ACE1AF"
        zone = ""
        km = re.search(r'bgcolor\s*=\s*["\']?#?([a-zA-Z0-9]+)', rij)
        if not km:
            km = re.search(r'background[:\s]*["\']?#?([a-zA-Z0-9]+)', rij)
        if km:
            k = km.group(1).lower()
            if any(x in k for x in ["ace1af","c0f0d0","b0e0e6","ccffcc","aaffaa","acffac"]): zone = "playoff"
            elif any(x in k for x in ["bisque","ffd700","ffe4c4","ffff99","lightblue","add8e6","fffacd"]): zone = "playout"
            elif any(x in k for x in ["ffaaaa","ffa07a","ff6666","ffcccc","ffd0d0","ffb6b6"]): zone = "degradatie"

        # Verwijder leidende stijl van de rij zelf
        ri = re.sub(r'^[^|]*\|', '', rij, count=1)
        cellen = re.split(r'\|\|', ri)

        # Bepaal kolomformaat op basis van aantal cellen na || split
        # 9 cellen:  pos+zone in cel[0] | club | gs | w | g | v | pnt | dv | dt
        # 10 cellen: pos | club | gs | w | g | v | pnt | dv | dt | ds
        # 11 cellen: indicator | pos | club | gs | w | g | v | pnt | dv | dt | ds
        if len(cellen) >= 11:
            i_pos, i_club, i_gs = 1, 2, 3
        elif len(cellen) >= 9:
            # Zowel 9 als 10 cellen: pos zit in cel[0]
            i_pos, i_club, i_gs = 0, 1, 2
        else:
            continue

        try:
            club = _cel(cellen[i_club])
            if not club or len(club) < 2: continue
            if re.match(r'^\d+[-]\d+$', club.strip()): continue  # score uit matrix

            pr = re.sub(r"[^\d]", "", cellen[i_pos])
            pos = int(pr) if pr else 0
            if pos == 0: continue

            gs  = _int(_cel(cellen[i_gs]))
            w   = _int(_cel(cellen[i_gs+1]))
            g   = _int(_cel(cellen[i_gs+2]))
            v   = _int(_cel(cellen[i_gs+3]))
            pnt = _int(_cel(cellen[i_gs+4]))
            dv  = _int(_cel(cellen[i_gs+5])) if len(cellen) > i_gs+5 else 0
            dt  = _int(_cel(cellen[i_gs+6])) if len(cellen) > i_gs+6 else 0
            ds  = _int(_cel(cellen[i_gs+7])) if len(cellen) > i_gs+7 else dv - dt

            # Validatie: bij resultatenmatrix zijn alle getallen 0
            if gs == 0 and w == 0 and g == 0 and v == 0: continue

            if not zone:
                zone = ("playoff" if pos <= 4
                        else "playout" if pos in (10, 11)
                        else "degradatie" if pos == 12
                        else "")

            stand.append({"positie": pos, "club": club, "gespeeld": gs,
                "gewonnen": w, "gelijk": g, "verloren": v,
                "doelpunten_voor": dv, "doelpunten_tegen": dt,
                "doelsaldo": ds, "punten": pnt, "zone": zone})
        except: continue

    stand.sort(key=lambda r: r["positie"])
    return stand

def parse_wikitable(wt):
    """Doorzoek alle tabellen en vind de standentabel."""
    for tabel in re.split(r'\{\|', wt)[1:]:
        if not _is_stand_tabel(tabel): continue
        stand = _parse_tabel_rijen(tabel)
        if len(stand) >= 8:
            return stand
    return []

def parse_stand(wt):
    s=parse_sports_table(wt)
    if s: return s,"sports_table"
    s=parse_wikitable(wt)
    if s: return s,"wikitable"
    return [],"geen"

# ── Play-off parser ────────────────────────────────────────────────────────────

def _safe_score(s):
    m = re.search(r"(\d+)[-–](\d+)", str(s))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

def _club_uit_cel(cel):
    cel = re.sub(r"'''", "", cel)
    cel = re.sub(r"\(\d+\)", "", cel)
    m = re.search(r"\[\[[^\]|]+\|([^\]]+)\]\]", cel)
    if m: return fix(m.group(1).strip())
    m = re.search(r"\[\[([^\]|]+)\]\]", cel)
    if m: return fix(m.group(1).strip())
    return fix(cel.strip())

def _score_uit_cel(cel):
    m = re.search(r"(\d+[-–]\d+)", cel)
    return m.group(1) if m else cel.strip()

def parse_playoffs(wt):
    """
    Parseer play-off resultaten.
    Structuur: ==Play offs...== sectie met '''Subsectienaam''' koppen op eigen regel.
    """
    playoffs = {"halve_finales": [], "finale": None, "kampioen": "", "playout": []}

    # Isoleer de play-off sectie
    po_idx = -1
    for zoek in ["==Play offs", "==Play-offs", "==Playoffs", "== Play offs", "== Play-offs"]:
        idx = wt.lower().find(zoek.lower())
        if idx >= 0:
            po_idx = idx
            break
    if po_idx == -1:
        return playoffs

    rest = wt[po_idx:]
    # Stop bij de volgende hoofdsectie (== op eigen regel)
    volgende = re.search(r'\n==[^=]', rest[5:])
    po_sectie = rest[:volgende.start()+5] if volgende else rest

    # Splits op subsectiekoppen die op een EIGEN REGEL staan
    # Patroon: newline + ''' + tekst zonder [[ + ''' + newline
    delen = re.split(r"\n'''([^'\[\]]{3,50})'''\n", po_sectie)

    huidig_type = ""
    halve_finales_paren = {}

    for i, deel in enumerate(delen):
        if i % 2 == 1:
            # Sectienaam
            dl = deel.strip().lower()
            if re.search(r'halve\s*finale', dl):
                huidig_type = "halve_finale"
            elif re.search(r'finale|final', dl) and 'halve' not in dl:
                huidig_type = "finale"
            elif re.search(r'play.?out|degradatie play|promotie.?degradatie', dl):
                huidig_type = "playout"
            continue

        # Inhoud — parseer wikitabellen
        for tabel_tekst in re.split(r'\{\|', deel)[1:]:
            tl = tabel_tekst.lower()
            if '! team' not in tl and '!! team' not in tl:
                continue

            wedstrijden = []
            for rij in tabel_tekst.split("|-"):
                rij = rij.strip()
                if not rij or rij.startswith("!") or rij.startswith("|+"): continue
                ri = re.sub(r'^[^|]*\|', '', rij, count=1)
                cellen = re.split(r'\|\|', ri)
                if len(cellen) < 3: continue
                try:
                    thuis = _club_uit_cel(cellen[0])
                    score = _score_uit_cel(cellen[1])
                    uit   = _club_uit_cel(cellen[2])
                    if not thuis or not uit or len(thuis) < 2: continue
                    wedstrijden.append({"thuis": thuis, "score": score, "uit": uit})
                except: continue

            if not wedstrijden:
                continue

            if huidig_type == "halve_finale":
                sleutel = frozenset([wedstrijden[0]["thuis"], wedstrijden[0]["uit"]])
                if sleutel not in halve_finales_paren:
                    halve_finales_paren[sleutel] = []
                halve_finales_paren[sleutel].extend(wedstrijden)

            elif huidig_type == "finale":
                if not playoffs["finale"]:
                    playoffs["finale"] = {
                        "thuis": wedstrijden[0]["thuis"],
                        "uit": wedstrijden[0]["uit"],
                        "score": wedstrijden[0]["score"],
                        "wedstrijden": wedstrijden,
                    }

            elif huidig_type == "playout":
                playoffs["playout"].extend(wedstrijden)

    # Verwerk halve finale paren
    for sleutel, wedstrijden in halve_finales_paren.items():
        thuis = wedstrijden[0]["thuis"]
        uit   = wedstrijden[0]["uit"]
        t = sum(_safe_score(w["score"])[0] for w in wedstrijden if w["thuis"]==thuis)
        t += sum(_safe_score(w["score"])[1] for w in wedstrijden if w["uit"]==thuis)
        u = sum(_safe_score(w["score"])[0] for w in wedstrijden if w["thuis"]==uit)
        u += sum(_safe_score(w["score"])[1] for w in wedstrijden if w["uit"]==uit)
        winnaar = thuis if t >= u else uit
        playoffs["halve_finales"].append({
            "thuis": thuis, "uit": uit,
            "score": f"{t}-{u}", "winnaar": winnaar,
            "wedstrijden": wedstrijden,
        })

    # Kampioen uit finale
    if playoffs["finale"]:
        fin = playoffs["finale"]
        wed = fin.get("wedstrijden", [fin])
        thuis = fin["thuis"]; uit = fin["uit"]
        t = sum(_safe_score(w["score"])[0] for w in wed if w["thuis"]==thuis)
        t += sum(_safe_score(w["score"])[1] for w in wed if w["uit"]==thuis)
        u = sum(_safe_score(w["score"])[0] for w in wed if w["thuis"]==uit)
        u += sum(_safe_score(w["score"])[1] for w in wed if w["uit"]==uit)
        playoffs["kampioen"] = thuis if t > u else uit

    return playoffs

# ── Opslaan ────────────────────────────────────────────────────────────────────
def sla_op(data, seizoen, geslacht):
    pad=BASE_DIR/"seizoenen"/seizoen/f"{geslacht}.json"
    pad.parent.mkdir(parents=True,exist_ok=True)
    pad.write_text(json.dumps(data,indent=2,ensure_ascii=False))
    return pad

# ── Per seizoen ────────────────────────────────────────────────────────────────
def verwerk(seizoen, geslacht):
    pagina=wiki_naam(seizoen,geslacht)
    wt=haal_wikitext(pagina)

    kampioen=KAMPIOEN.get((seizoen,geslacht),"")

    if not wt:
        # Geen Wikipedia pagina — sla toch op als we kampioen kennen
        if kampioen:
            data={"seizoen":label(seizoen),"geslacht":geslacht,"kampioen":kampioen,
                "stand":[],"playoffs":{},"wiki_pagina":"","bijgewerkt":datetime.now(timezone.utc).isoformat()[:10]}
            sla_op(data,seizoen,geslacht)
            log.info("📋 %s %s → alleen kampioen opgeslagen (%s)", label(seizoen), geslacht, kampioen)
            return "kampioen_only"
        log.warning("❌ %s %s → geen data", label(seizoen), geslacht)
        return False

    stand,formaat=parse_stand(wt)
    for r in stand: r["club"]=fix(r["club"])

    playoffs = parse_playoffs(wt)

    if not kampioen:
        kampioen = playoffs.get("kampioen","")
    if not kampioen and stand:
        kampioen = stand[0]["club"]
    if playoffs.get("kampioen"):
        playoffs["kampioen"] = kampioen  # gebruik de override versie

    data={"seizoen":label(seizoen),"geslacht":geslacht,"kampioen":kampioen,
        "stand":stand,"playoffs":playoffs,
        "wiki_pagina":f"https://nl.wikipedia.org/wiki/{quote(pagina)}",
        "bijgewerkt":datetime.now(timezone.utc).isoformat()[:10]}
    sla_op(data,seizoen,geslacht)
    log.info("✅ %s %s → %d clubs, kampioen: %s [%s]", label(seizoen), geslacht, len(stand), kampioen, formaat)
    return True

# ── Index ──────────────────────────────────────────────────────────────────────
def maak_index():
    index_pad=BASE_DIR/"seizoenen"/"index.json"
    sm=BASE_DIR/"seizoenen"
    beschikbaar=[]
    if sm.exists():
        for sub in sorted(sm.iterdir(),reverse=True):
            if not sub.is_dir() or "_" not in sub.name: continue
            item={"seizoen":label(sub.name),"slug":sub.name}
            for g in ["heren","dames"]:
                pad=sub/f"{g}.json"
                if pad.exists():
                    try:
                        d=json.loads(pad.read_text())
                        item[f"kampioen_{g}"]=d.get("kampioen","")
                        item[f"clubs_{g}"]=len(d.get("stand",[]))
                    except: pass
            beschikbaar.append(item)
    index_pad.write_text(json.dumps({"seizoenen":beschikbaar},indent=2,ensure_ascii=False))
    log.info("✅ Index: %d seizoenen", len(beschikbaar))

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    te_verwerken=[sys.argv[1]] if len(sys.argv)>1 else SEIZOENEN
    resultaten=[]
    for seizoen in te_verwerken:
        for geslacht in ["heren","dames"]:
            ok=verwerk(seizoen,geslacht)
            resultaten.append((seizoen,geslacht,ok))

    maak_index()

    print("\n"+"="*54)
    ok_count=sum(1 for _,_,ok in resultaten if ok)
    partial=sum(1 for _,_,ok in resultaten if ok=="kampioen_only")
    fail=sum(1 for _,_,ok in resultaten if not ok)
    for seizoen,geslacht,ok in resultaten:
        icoon="✅" if ok is True else "📋" if ok=="kampioen_only" else "❌"
        print(f"  {icoon}  {label(seizoen):12} {geslacht}")
    print("="*54)
    print(f"\n  ✅ {ok_count} met stand  📋 {partial} alleen kampioen  ❌ {fail} geen data")
    print("\n  git add seizoenen/ && git commit -m 'feat: seizoenen tot 1972' && git pull origin main --rebase && git push origin main")

if __name__=="__main__":
    main()
