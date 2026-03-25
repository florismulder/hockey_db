"""
Haalt selectiepagina's op van hockey.nl voor alle Oranje-teams
en detecteert wijzigingen in de selectie (nieuw opgeroepen, afgevallen,
debutanten).

Teams:
    Oranje Heren, Oranje Dames,
    Jong Oranje Heren, Jong Oranje Dames,
    Jongens O18, Meisjes O18, Jongens O16, Meisjes O16

Output:
    spelers/oranje/{team-sleutel}.json
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── Configuratie ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "spelers" / "oranje"
USER_AGENT = "HockeyDB/1.0 (github.com/hockey_db; data-only bot)"

TEAMS: dict[str, dict] = {
    "oranje-heren": {
        "naam": "Oranje Heren",
        "url": "https://www.hockey.nl/oranje/oranje-heren/",
        "output": OUTPUT_DIR / "oranje-heren.json",
    },
    "oranje-dames": {
        "naam": "Oranje Dames",
        "url": "https://www.hockey.nl/oranje/oranje-dames/",
        "output": OUTPUT_DIR / "oranje-dames.json",
    },
    "jong-oranje-heren": {
        "naam": "Jong Oranje Heren",
        "url": "https://www.hockey.nl/oranje/jong-oranje-heren",
        "output": OUTPUT_DIR / "jong-oranje-heren.json",
    },
    "jong-oranje-dames": {
        "naam": "Jong Oranje Dames",
        "url": "https://www.hockey.nl/oranje/jong-oranje-dames",
        "output": OUTPUT_DIR / "jong-oranje-dames.json",
    },
    "jongens-o18": {
        "naam": "Jongens O18",
        "url": "https://www.hockey.nl/jeugd/jongens-o18",
        "output": OUTPUT_DIR / "jongens-o18.json",
    },
    "meisjes-o18": {
        "naam": "Meisjes O18",
        "url": "https://www.hockey.nl/jeugd/meisjes-o18",
        "output": OUTPUT_DIR / "meisjes-o18.json",
    },
    "jongens-o16": {
        "naam": "Jongens O16",
        "url": "https://www.hockey.nl/jeugd/jongens-o16",
        "output": OUTPUT_DIR / "jongens-o16.json",
    },
    "meisjes-o16": {
        "naam": "Meisjes O16",
        "url": "https://www.hockey.nl/jeugd/meisjes-o16",
        "output": OUTPUT_DIR / "meisjes-o16.json",
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Ophalen & parsen ──────────────────────────────────────────────────────────

def fetch_page(url: str) -> Optional[str]:
    """Haal de HTML van een selectiepagina op."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        log.error("Netwerkfout bij ophalen van '%s': %s", url, exc)
        return None


def parse_players(html: str) -> list[dict]:
    """
    Extraheer spelersinformatie uit de selectiepagina.

    Probeert meerdere bekende hockey.nl-paginastructuren:
    1. Spelerkaarten (.player-card, .player-item, article.player)
    2. Tabellen met spelersinformatie
    3. Generieke naam+club extractie via JSON-LD of meta-data
    """
    soup = BeautifulSoup(html, "lxml")
    players: list[dict] = []

    # ── Strategie 1: Spelerkaarten (meest voorkomend op hockey.nl) ─────────
    card_selectors = [
        ".player-card",
        ".player-item",
        ".player",
        "[class*='player']",
        "article.team-member",
        ".team-member",
        "[class*='team-member']",
        ".squad-member",
        "[class*='squad']",
    ]
    for selector in card_selectors:
        cards = soup.select(selector)
        if len(cards) >= 3:  # Minimaal 3 kaarten = waarschijnlijk een selectie
            log.debug("Spelerkaarten via '%s': %d gevonden.", selector, len(cards))
            for card in cards:
                player = _parse_player_card(card)
                if player:
                    players.append(player)
            if players:
                return players

    # ── Strategie 2: Tabel met spelersinformatie ───────────────────────────
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if any(kw in " ".join(headers) for kw in ("naam", "name", "speler", "player")):
            col_map = _build_column_map(headers)
            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if not any(cells):
                    continue
                player = _parse_player_row(cells, col_map)
                if player:
                    players.append(player)
            if players:
                log.debug("Spelers via tabel: %d gevonden.", len(players))
                return players

    # ── Strategie 3: Generieke h3/h4-namen in een sectie ──────────────────
    # Zoek een sectie die een selectie-achtige context heeft
    for section in soup.find_all(["section", "div"], class_=re.compile(r"select|squad|team", re.I)):
        names = []
        for heading in section.find_all(["h2", "h3", "h4", "h5", "strong"]):
            text = heading.get_text(strip=True)
            # Filter kopteksten (te kort of bevatten getallen/speciale tekens)
            if 3 < len(text) < 50 and not re.search(r"\d{4}|selecteer|menu|nav", text, re.I):
                names.append({"naam": text, "positie": "", "club": ""})
        if len(names) >= 5:
            log.debug("Spelers via h-tags in sectie: %d gevonden.", len(names))
            return names

    log.warning("Geen spelersinformatie gevonden op de pagina.")
    return []


def _parse_player_card(card) -> Optional[dict]:
    """Extraheer spelersinformatie uit één kaart-element."""
    # Naam: zoek in h-tags of specifieke naam-klassen
    naam = ""
    for tag in card.find_all(["h2", "h3", "h4", "h5", "strong",
                               "[class*='name']", "[class*='naam']"]):
        text = tag.get_text(strip=True)
        if text and 2 < len(text) < 60:
            naam = text
            break

    if not naam:
        # Fallback: eerste betekenisvolle tekst
        text = card.get_text(" ", strip=True)
        parts = [p for p in text.split() if len(p) > 1]
        naam = " ".join(parts[:3]) if parts else ""

    if not naam or len(naam) < 3:
        return None

    # Positie
    positie = ""
    for kw in ("positie", "position", "pos", "role"):
        el = card.find(class_=re.compile(kw, re.I))
        if el:
            positie = el.get_text(strip=True)
            break
    if not positie:
        # Zoek bekende hockeyposities in de tekst
        pos_re = re.compile(
            r"\b(keeper|verdediger|midfielder|aanvaller|forward|back|midfield|goalkeeper)\b",
            re.I,
        )
        match = pos_re.search(card.get_text())
        if match:
            positie = match.group(0).capitalize()

    # Club
    club = ""
    for kw in ("club", "team", "vereniging"):
        el = card.find(class_=re.compile(kw, re.I))
        if el:
            club = el.get_text(strip=True)
            break

    return {"naam": naam, "positie": positie, "club": club}


def _build_column_map(headers: list[str]) -> dict[str, int]:
    """Bouw een mapping van kolomnaam → index op basis van kopteksten."""
    mapping: dict[str, int] = {}
    keyword_map = {
        "naam": "naam", "name": "naam", "speler": "naam", "player": "naam",
        "positie": "positie", "position": "positie", "pos": "positie",
        "club": "club", "vereniging": "club", "team": "club",
        "geboortedatum": "geboortedatum", "dob": "geboortedatum",
        "caps": "caps", "interlands": "caps",
    }
    for i, header in enumerate(headers):
        for kw, key in keyword_map.items():
            if kw in header and key not in mapping:
                mapping[key] = i
    return mapping


def _parse_player_row(cells: list[str], col_map: dict[str, int]) -> Optional[dict]:
    """Extraheer spelersinformatie uit een tabelrij."""
    naam = cells[col_map["naam"]] if "naam" in col_map and col_map["naam"] < len(cells) else ""
    if not naam or len(naam) < 2:
        return None

    player: dict = {"naam": naam, "positie": "", "club": ""}
    for key in ("positie", "club", "geboortedatum", "caps"):
        if key in col_map and col_map[key] < len(cells):
            player[key] = cells[col_map[key]]

    return player


# ── Vergelijken & changelog ───────────────────────────────────────────────────

def load_existing(path: Path) -> dict:
    """Laad bestaand selectiebestand; retourneer leeg skelet bij afwezigheid."""
    if not path.exists():
        return {"spelers": [], "changelog": [], "alle_namen": []}
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Kon bestaand bestand '%s' niet laden: %s", path, exc)
        return {"spelers": [], "changelog": [], "alle_namen": []}


def detect_changes(
    previous_names: list[str],
    all_time_names: list[str],
    current_names: list[str],
) -> dict:
    """
    Vergelijk de huidige selectie met de vorige en detecteer wijzigingen.

    Args:
        previous_names: Namen uit de vorige opgeslagen selectie.
        all_time_names: Alle namen die ooit in de selectie zaten (voor debutanten).
        current_names: Namen in de huidige selectie.

    Returns:
        Dict met 'nieuw', 'afgevallen', 'debutanten'.
    """
    prev_set = set(previous_names)
    curr_set = set(current_names)
    all_set = set(all_time_names)

    nieuw = sorted(curr_set - prev_set)
    afgevallen = sorted(prev_set - curr_set)
    debutanten = sorted(n for n in nieuw if n not in all_set)

    return {
        "nieuw": nieuw,
        "afgevallen": afgevallen,
        "debutanten": debutanten,
    }


def build_changelog_entry(changes: dict, datum: str) -> Optional[dict]:
    """Maak een changelog-entry aan als er wijzigingen zijn."""
    if not changes["nieuw"] and not changes["afgevallen"]:
        return None
    return {
        "datum": datum,
        "nieuw_opgeroepen": changes["nieuw"],
        "afgevallen": changes["afgevallen"],
        "debutanten": changes["debutanten"],
    }


# ── Opslaan ───────────────────────────────────────────────────────────────────

def save_selectie(data: dict, path: Path) -> None:
    """Sla selectiedata op als JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    log.info("Opgeslagen: %s (%d spelers)", path, len(data.get("spelers", [])))


# ── Verwerk één team ──────────────────────────────────────────────────────────

def process_team(team_key: str, config: dict) -> bool:
    """
    Haal de selectie op voor één team, vergelijk met vorige versie
    en sla op met changelog.

    Returns:
        True bij succes, False bij fout.
    """
    log.info("Ophalen selectie voor %s ...", config["naam"])
    html = fetch_page(config["url"])
    if html is None:
        return False

    spelers = parse_players(html)
    if not spelers:
        log.warning("Geen spelers gevonden voor %s.", config["naam"])
        # Sla leeg resultaat op zodat changelog intact blijft
        spelers = []

    current_names = [s["naam"] for s in spelers]
    existing = load_existing(config["output"])
    previous_names = [s["naam"] for s in existing.get("spelers", [])]
    all_time_names = existing.get("alle_namen", previous_names)

    now_iso = datetime.now(timezone.utc).isoformat()
    changes = detect_changes(previous_names, all_time_names, current_names)
    entry = build_changelog_entry(changes, now_iso)

    if entry:
        log.info(
            "%s — nieuw: %d, afgevallen: %d, debutanten: %d",
            config["naam"],
            len(changes["nieuw"]),
            len(changes["afgevallen"]),
            len(changes["debutanten"]),
        )
    else:
        log.info("%s — geen wijzigingen in selectie.", config["naam"])

    # Bijgewerkte alle-namen lijst
    updated_all_names = sorted(set(all_time_names) | set(current_names))

    changelog = existing.get("changelog", [])
    if entry:
        changelog.insert(0, entry)  # Nieuwste eerst

    output = {
        "team": config["naam"],
        "bron": config["url"],
        "bijgewerkt": now_iso,
        "spelers": spelers,
        "alle_namen": updated_all_names,
        "changelog": changelog,
    }

    try:
        save_selectie(output, config["output"])
        return True
    except OSError as exc:
        log.error("Fout bij opslaan van %s: %s", config["output"], exc)
        return False


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def main() -> dict[str, bool]:
    """
    Haal selecties op voor alle Oranje-teams.

    Returns:
        Dict met succes-status per team-sleutel.
    """
    results: dict[str, bool] = {}
    for team_key, config in TEAMS.items():
        results[team_key] = process_team(team_key, config)
    return results


if __name__ == "__main__":
    success = main()
    sys.exit(0 if all(success.values()) else 1)
