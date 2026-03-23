"""
Haalt standen en uitslagen op via de Nederlandse Wikipedia API
voor de Tulp Hoofdklasse Heren en Dames seizoen 2025/26.

Output:
    competities/heren/standen.json
    competities/dames/standen.json
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup, Tag

# ── Configuratie ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
WIKI_API = "https://nl.wikipedia.org/w/api.php"
USER_AGENT = "HockeyDB/1.0 (github.com/hockey_db; data-only bot)"

COMPETITIES: dict[str, dict] = {
    "heren": {
        "wiki_page": "Hoofdklasse_hockey_heren_2025/26",
        "output": BASE_DIR / "competities" / "heren" / "standen.json",
    },
    "dames": {
        "wiki_page": "Hoofdklasse_hockey_dames_2025/26",
        "output": BASE_DIR / "competities" / "dames" / "standen.json",
    },
}

# Mapping van Nederlandse kolomkoppen → genormaliseerde sleutels
STANDINGS_COL_MAP: dict[str, str] = {
    "#": "positie",
    "pos": "positie",
    "positie": "positie",
    "club": "club",
    "ploeg": "club",
    "team": "club",
    "wed": "gespeeld",
    "gesp": "gespeeld",
    "gespeeld": "gespeeld",
    "w": "gewonnen",
    "won": "gewonnen",
    "gewonnen": "gewonnen",
    "g": "gelijk",
    "gel": "gelijk",
    "gelijk": "gelijk",
    "v": "verloren",
    "ver": "verloren",
    "verloren": "verloren",
    "vr": "doelpunten_voor",
    "voor": "doelpunten_voor",
    "tg": "doelpunten_tegen",
    "tegen": "doelpunten_tegen",
    "ds": "doelsaldo",
    "+/-": "doelsaldo",
    "saldo": "doelsaldo",
    "pnt": "punten",
    "pts": "punten",
    "punten": "punten",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Wikipedia API ─────────────────────────────────────────────────────────────

def fetch_page_html(page_title: str) -> Optional[str]:
    """Haal de geparseerde HTML op van een Wikipedia-pagina via de Action API."""
    params = {
        "action": "parse",
        "page": page_title,
        "format": "json",
        "prop": "text",
        "redirects": "1",
        "disableeditsection": "1",
    }
    try:
        resp = requests.get(
            WIKI_API,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        log.error("Netwerkfout bij ophalen van '%s': %s", page_title, exc)
        return None

    if "error" in data:
        log.error(
            "Wikipedia API-fout voor '%s': %s",
            page_title,
            data["error"].get("info", "onbekende fout"),
        )
        return None

    html = data.get("parse", {}).get("text", {}).get("*")
    if not html:
        log.error("Geen HTML-inhoud ontvangen voor '%s'.", page_title)
        return None

    return html


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _norm_header(text: str) -> str:
    """Normaliseer kolomkop: lowercase, geen witruimte."""
    return re.sub(r"\s+", "", text.strip().lower())


def _is_standings_table(table: Tag) -> bool:
    """Bepaal of een wikitable een standenlijst is op basis van kolomkoppen."""
    headers = [_norm_header(th.get_text()) for th in table.find_all("th")]
    known = set(STANDINGS_COL_MAP.keys())
    return sum(1 for h in headers if h in known) >= 4


def _safe_int(text: str, fallback: int = 0) -> int:
    """Zet tekst om naar int; retourneer fallback bij mislukking."""
    cleaned = re.sub(r"[^\d\-]", "", text.strip())
    try:
        return int(cleaned) if cleaned else fallback
    except ValueError:
        return fallback


# ── Stand parsing ─────────────────────────────────────────────────────────────

def parse_standings(html: str) -> list[dict]:
    """Extraheer de standen uit Wikipedia-HTML."""
    soup = BeautifulSoup(html, "lxml")

    for table in soup.find_all("table", class_=re.compile(r"wikitable")):
        if not _is_standings_table(table):
            continue

        header_row = table.find("tr")
        if not header_row:
            continue

        raw_headers = [_norm_header(th.get_text()) for th in header_row.find_all("th")]
        col_keys = [STANDINGS_COL_MAP.get(h, h) for h in raw_headers]

        # Verifieer dat er een club-kolom is
        if "club" not in col_keys:
            continue

        rows: list[dict] = []
        for row_idx, tr in enumerate(table.find_all("tr")[1:], start=1):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            row: dict = {}
            for col_idx, cell in enumerate(cells):
                if col_idx >= len(col_keys):
                    break
                key = col_keys[col_idx]
                text = cell.get_text(strip=True)

                if key == "positie":
                    row[key] = _safe_int(re.sub(r"\D", "", text), fallback=row_idx)
                elif key == "club":
                    row[key] = text
                elif key in (
                    "gespeeld", "gewonnen", "gelijk", "verloren",
                    "doelpunten_voor", "doelpunten_tegen", "punten",
                ):
                    row[key] = _safe_int(text)
                elif key == "doelsaldo":
                    row[key] = _safe_int(re.sub(r"[^\d\-+]", "", text))
                else:
                    row[key] = text

            if row.get("club"):
                row.setdefault("positie", row_idx)
                rows.append(row)

        if rows:
            log.info("Stand geparseerd: %d clubs gevonden.", len(rows))
            return rows

    log.warning("Geen standenlijst gevonden in de Wikipedia-HTML.")
    return []


# ── Uitslagen parsing ─────────────────────────────────────────────────────────

def parse_results(html: str) -> list[dict]:
    """Extraheer wedstrijduitslagen uit Wikipedia-HTML."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    score_re = re.compile(r"^(\d+)\s*[–\-]\s*(\d+)$")
    date_re = re.compile(r"\d{1,2}[./-]\d{1,2}")

    for table in soup.find_all("table", class_=re.compile(r"wikitable")):
        header_text = " ".join(
            th.get_text(strip=True).lower() for th in table.find_all("th")
        )
        # Sla standenlijsten over
        if any(kw in header_text for kw in ("punten", "pts", "pnt", "gespeeld")):
            continue
        # Controleer op typische uitslag-kolommen
        if not any(kw in header_text for kw in ("thuis", "uit", "score", "datum", "uitslag")):
            continue

        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 3:
                continue

            # Zoek score-cel
            score_idx = next(
                (i for i, c in enumerate(cells) if score_re.match(c)), None
            )
            if score_idx is None or score_idx == 0:
                continue

            try:
                m = score_re.match(cells[score_idx])
                entry: dict = {
                    "thuis": cells[score_idx - 1],
                    "score_thuis": int(m.group(1)),
                    "score_uit": int(m.group(2)),
                    "uit": cells[score_idx + 1] if score_idx + 1 < len(cells) else "",
                }
                # Datum staat doorgaans in de eerste cellen
                for cell in cells[:3]:
                    if date_re.search(cell):
                        entry["datum"] = cell
                        break

                if entry["thuis"] and entry["uit"]:
                    results.append(entry)
            except (ValueError, IndexError):
                continue

    log.info("Uitslagen geparseerd: %d wedstrijden gevonden.", len(results))
    return results


# ── Opslaan ───────────────────────────────────────────────────────────────────

def save_output(data: dict, path: Path) -> None:
    """Sla data op als ingesprongen UTF-8 JSON-bestand."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    log.info("Opgeslagen: %s", path)


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def main() -> dict[str, bool]:
    """
    Haal standen en uitslagen op voor heren en dames via Wikipedia.

    Returns:
        Dict met succes-status per competitie, bv. {"heren": True, "dames": False}.
    """
    results: dict[str, bool] = {}

    for geslacht, config in COMPETITIES.items():
        log.info("Ophalen Wikipedia-pagina voor %s ...", geslacht)
        html = fetch_page_html(config["wiki_page"])

        if html is None:
            log.error("Overgeslagen: %s (geen HTML ontvangen).", geslacht)
            results[geslacht] = False
            continue

        stand = parse_standings(html)
        uitslagen = parse_results(html)

        output = {
            "seizoen": "2025/26",
            "geslacht": geslacht,
            "bron": f"https://nl.wikipedia.org/wiki/{quote(config['wiki_page'])}",
            "bijgewerkt": datetime.now(timezone.utc).isoformat(),
            "stand": stand,
            "uitslagen": uitslagen,
        }

        try:
            save_output(output, config["output"])
            results[geslacht] = True
        except OSError as exc:
            log.error("Fout bij opslaan van %s: %s", config["output"], exc)
            results[geslacht] = False

    return results


if __name__ == "__main__":
    success = main()
    sys.exit(0 if all(success.values()) else 1)
