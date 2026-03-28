#!/usr/bin/env python3
"""
fetch_artikel.py — Haal een hockey.nl artikel op via Playwright en kopieer naar klembord.

Gebruik:
    python3 scripts/fetch_artikel.py https://www.hockey.nl/nieuws/...
"""

import sys
import re
import subprocess

def haal_artikel_op(url: str) -> str:
    from playwright.sync_api import sync_playwright

    print(f"🔗 Ophalen: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(2000)

        # Probeer artikel tekst te pakken
        tekst = ""
        for selector in ["article", ".article-body", ".article__body", "main", ".content"]:
            try:
                el = page.query_selector(selector)
                if el:
                    t = el.inner_text()
                    if len(t) > 200:
                        tekst = t
                        break
            except:
                pass

        if not tekst:
            tekst = page.inner_text("body")

        browser.close()
        return tekst[:6000]

def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 scripts/fetch_artikel.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    tekst = haal_artikel_op(url)

    print("\n" + "="*60)
    print("ARTIKELTEKST:")
    print("="*60 + "\n")
    print(tekst)
    print("\n" + "="*60)
    print(f"✅ {len(tekst)} tekens opgehaald.")

    try:
        proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc.communicate(tekst.encode('utf-8'))
        print("📋 Tekst gekopieerd naar klembord!")
    except:
        pass

if __name__ == "__main__":
    main()
