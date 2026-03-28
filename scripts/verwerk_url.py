#!/usr/bin/env python3
"""
verwerk_url.py — Haal een hockey.nl artikel op en verwerk het direct.

Gebruik:
    python3 scripts/verwerk_url.py https://www.hockey.nl/nieuws/... 2026-03-22
    python3 scripts/verwerk_url.py https://www.hockey.nl/nieuws/... 2026-03-22 --dames
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent

# Importeer verwerk_tekst functies
sys.path.insert(0, str(Path(__file__).parent))
from verwerk_tekst import parse_wedstrijden, sla_op

def haal_op(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright niet geïnstalleerd. Voer uit:")
        print("   pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"🔗 Ophalen: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=25000)
        page.wait_for_timeout(2000)

        tekst = ""
        for selector in ["article", "main", ".article-body", ".content", "body"]:
            try:
                el = page.query_selector(selector)
                if el:
                    t = el.inner_text()
                    if len(t) > 300:
                        tekst = t
                        break
            except:
                pass

        browser.close()
        return tekst[:10000]

def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 scripts/verwerk_url.py <url> [datum] [--dames]")
        print("Voorbeeld: python3 scripts/verwerk_url.py https://www.hockey.nl/nieuws/... 2026-03-22")
        sys.exit(1)

    url = sys.argv[1]
    geslacht = "dames" if "--dames" in sys.argv else "heren"
    datum = ""
    for arg in sys.argv[2:]:
        if re.match(r"\d{4}-\d{2}-\d{2}", arg):
            datum = arg

    tekst = haal_op(url)
    if len(tekst) < 100:
        print("❌ Weinig tekst opgehaald. Probeer de PDF methode.")
        sys.exit(1)

    print(f"   {len(tekst)} tekens opgehaald")

    if not datum:
        datum = input("Datum (YYYY-MM-DD): ").strip()

    wedstrijden = parse_wedstrijden(tekst, datum, geslacht)

    if not wedstrijden:
        print("❌ Geen wedstrijden herkend.")
        print("Probeer de tekst handmatig te structureren en gebruik verwerk_tekst.py")
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
