"""
Scrapet wedstrijdresultaten en het programma van tulphoofdklasse.com
via Playwright (headless Chromium).

Paginastructuur (Tailwind):
  - <section class="mb-8"> per categorie (Women/Men × Standings/Results)
  - Resultaten: h2 + div.flex-col met alternerende datum-divs en match-groepen
  - Elke wedstrijd: div.grid-cols-[1fr_55px_1fr] met thuis/score/uit spans

Output:
    competities/heren/programma.json
    competities/dames/programma.json
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from playwright.sync_api import (
    Browser,
    Page,
    sync_playwright,
    TimeoutError as PlaywrightTimeout,
)

# ── Configuratie ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
TULP_URL = "https://tulphoofdklasse.com/en/matches-standings"

OUTPUT: dict[str, Path] = {
    "heren": BASE_DIR / "competities" / "heren" / "programma.json",
    "dames": BASE_DIR / "competities" / "dames" / "programma.json",
}

NAV_TIMEOUT_MS = 30_000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SCORE_RE = re.compile(r"^\s*(\d+)\s*[-–]\s*(\d+)\s*$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Browser ───────────────────────────────────────────────────────────────────

def fetch_html(url: str) -> Optional[str]:
    """Laad de pagina via Playwright en retourneer de volledige HTML."""
    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="nl-NL",
        )
        page: Page = ctx.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        log.info("Navigeren naar %s ...", url)
        try:
            page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            # Wacht tot match-content aanwezig is
            page.wait_for_selector("section.mb-8", timeout=15_000)
        except PlaywrightTimeout:
            log.warning("Timeout — verwerking gaat toch door met beschikbare HTML.")
        except Exception as exc:
            log.error("Kan pagina niet laden: %s", exc)
            browser.close()
            return None

        html = page.content()
        browser.close()
        log.info("HTML opgehaald: %d bytes", len(html))
        return html


# ── HTML parsing ──────────────────────────────────────────────────────────────

def _direct_text(tag: Tag) -> str:
    """
    Geef alleen de directe tekst-nodes van een tag terug,
    zonder tekst uit geneste elementen (bv. img-alt of inner spans).
    """
    parts = [
        str(node).strip()
        for node in tag.children
        if isinstance(node, NavigableString) and str(node).strip()
    ]
    return " ".join(parts).strip()


def _parse_score(span: Tag) -> Optional[tuple[int, int]]:
    """Parseer een score-span naar (score_thuis, score_uit)."""
    text = span.get_text(" ", strip=True)
    m = SCORE_RE.match(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_match_row(row: Tag, datum: str) -> Optional[dict]:
    """
    Parseer één wedstrijd-rij (div.grid-cols-[1fr_55px_1fr]).

    Structuur:
      span.justify-end  → thuisploeg
      span.text-center  → score (gespeeld) of tijd/TBD (gepland)
      span (3e)         → uitploeg
    """
    spans = row.find_all("span", recursive=False)
    if len(spans) < 3:
        return None

    thuis = _direct_text(spans[0])
    uit = _direct_text(spans[2])

    if not thuis or not uit:
        return None

    # Score of geplande tijd in de middelste span
    score = _parse_score(spans[1])
    midden_text = spans[1].get_text(" ", strip=True)

    record: dict = {
        "datum": datum,
        "thuis": thuis,
        "uit": uit,
    }

    if score:
        record["score_thuis"] = score[0]
        record["score_uit"] = score[1]
        record["gespeeld"] = True
    else:
        # Geen score → gepland; sla eventuele tijd op
        record["tijd"] = midden_text if midden_text and midden_text not in ("-", "–", "vs") else ""
        record["gespeeld"] = False

    return record


def _parse_results_section(section: Tag) -> list[dict]:
    """
    Parseer een <section class="mb-8"> met alternerend:
      div.border-b  → datum-header
      div.mb-2      → één of meer wedstrijden
    """
    matches: list[dict] = []
    flex = section.find("div", class_=re.compile(r"\bflex\b"))
    if not flex:
        return matches

    current_date = ""
    for child in (c for c in flex.children if isinstance(c, Tag)):
        child_cls = " ".join(child.get("class", []))

        # Datum-header
        if "border-b" in child_cls and "pb-3" in child_cls:
            current_date = child.get_text(strip=True)

        # Match-container
        elif "mb-2" in child_cls:
            for row in child.find_all("div", class_=re.compile(r"grid-cols-\[1fr")):
                record = _parse_match_row(row, current_date)
                if record:
                    matches.append(record)

    return matches


def parse_page(html: str) -> tuple[list[dict], list[dict]]:
    """
    Verwerk de volledige pagina-HTML en retourneer
    (heren_wedstrijden, dames_wedstrijden).
    """
    soup = BeautifulSoup(html, "lxml")
    heren: list[dict] = []
    dames: list[dict] = []

    for section in soup.find_all("section", class_="mb-8"):
        h2 = section.find("h2")
        if not h2:
            continue
        heading = h2.get_text(strip=True).lower()

        # Standen-secties overslaan (bevatten geen wedstrijdrijen)
        if any(kw in heading for kw in ("standings", "stand", "# team", "pl p w")):
            continue

        matches = _parse_results_section(section)
        if not matches:
            continue

        if "women" in heading or "dames" in heading:
            dames.extend(matches)
            log.info("Dames: %d wedstrijd(en) uit sectie '%s'", len(matches), h2.get_text(strip=True))
        else:
            heren.extend(matches)
            log.info("Heren: %d wedstrijd(en) uit sectie '%s'", len(matches), h2.get_text(strip=True))

    return heren, dames


# ── Opslaan ───────────────────────────────────────────────────────────────────

def save_programma(wedstrijden: list[dict], geslacht: str, path: Path) -> None:
    """Sla wedstrijdprogramma op als JSON.
    Bestaande komende fixtures blijven bewaard.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    bestaande_komend = []
    if path.exists():
        try:
            bestaand = json.loads(path.read_text())
            bestaande_komend = [
                w for w in bestaand.get("wedstrijden", [])
                if not w.get("gespeeld", False) and w.get("score_thuis") is None
            ]
        except Exception:
            pass
    gespeeld = [w for w in wedstrijden if w.get("gespeeld", False)]
    def key(w):
        return (w.get("thuis","").lower(), w.get("uit","").lower())
    gespeelde_keys = {key(w) for w in gespeeld}
    komend_gefilterd = [w for w in bestaande_komend if key(w) not in gespeelde_keys]
    alle = gespeeld + komend_gefilterd
    output = {
        "seizoen": "2025/26",
        "geslacht": geslacht,
        "bron": TULP_URL,
        "bijgewerkt": datetime.now(timezone.utc).isoformat(),
        "wedstrijden": alle,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    log.info("Opgeslagen: %s (%d gespeeld, %d komend)", path, len(gespeeld), len(komend_gefilterd))


# ── Hoofdfunctie ──────────────────────────────────────────────────────────────

def main() -> dict[str, bool]:
    """
    Scrape wedstrijdresultaten en programma van tulphoofdklasse.com.

    Returns:
        Dict met succes-status per competitie.
    """
    html = fetch_html(TULP_URL)
    if html is None:
        return {"heren": False, "dames": False}

    heren, dames = parse_page(html)
    log.info(
        "Totaal gevonden: %d heren-wedstrijd(en), %d dames-wedstrijd(en).",
        len(heren),
        len(dames),
    )

    results: dict[str, bool] = {}
    for geslacht, wedstrijden in [("heren", heren), ("dames", dames)]:
        try:
            save_programma(wedstrijden, geslacht, OUTPUT[geslacht])
            results[geslacht] = True
        except OSError as exc:
            log.error("Fout bij opslaan van %s: %s", OUTPUT[geslacht], exc)
            results[geslacht] = False

    return results


if __name__ == "__main__":
    success = main()
    sys.exit(0 if all(success.values()) else 1)
