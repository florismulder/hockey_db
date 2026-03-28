#!/usr/bin/env python3
"""
fetch_artikel.py — Haal een hockey.nl artikel op en kopieer de tekst naar klembord.

Gebruik:
    python3 scripts/fetch_artikel.py https://www.hockey.nl/nieuws/...

De artikeltekst wordt geprint zodat je hem kunt kopiëren en plakken in de invoerpagina.
"""

import sys
import re

def haal_artikel_op(url: str) -> str:
    try:
        import requests
    except ImportError:
        print("❌ requests niet geïnstalleerd. Voer uit: pip install requests")
        sys.exit(1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"🔗 Ophalen: {url}")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text

    # Verwijder scripts en styles
    html = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html, flags=re.IGNORECASE)

    # Probeer artikel body te vinden
    artikel = ""

    # Zoek op typische artikel-containers
    for patroon in [
        r'<article[^>]*>([\s\S]*?)</article>',
        r'class="article[^"]*"[^>]*>([\s\S]*?)</(?:div|section)>',
        r'class="content[^"]*"[^>]*>([\s\S]*?)</(?:div|section)>',
    ]:
        m = re.search(patroon, html, re.IGNORECASE)
        if m and len(m.group(1)) > 200:
            artikel = m.group(1)
            break

    if not artikel:
        artikel = html

    # Strip HTML
    tekst = re.sub(r'<[^>]+>', ' ', artikel)
    tekst = re.sub(r'&nbsp;', ' ', tekst)
    tekst = re.sub(r'&amp;', '&', tekst)
    tekst = re.sub(r'&lt;', '<', tekst)
    tekst = re.sub(r'&gt;', '>', tekst)
    tekst = re.sub(r'&#\d+;', ' ', tekst)
    tekst = re.sub(r'\s+', ' ', tekst).strip()

    return tekst[:6000]


def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 scripts/fetch_artikel.py <url>")
        print("Voorbeeld: python3 scripts/fetch_artikel.py https://www.hockey.nl/nieuws/hk-h-bloemendaal...")
        sys.exit(1)

    url = sys.argv[1]
    tekst = haal_artikel_op(url)

    print("\n" + "="*60)
    print("ARTIKELTEKST (kopieer en plak in de invoerpagina):")
    print("="*60 + "\n")
    print(tekst)
    print("\n" + "="*60)
    print(f"✅ Klaar! {len(tekst)} tekens opgehaald.")

    # Probeer naar klembord te kopiëren
    try:
        import subprocess
        proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc.communicate(tekst.encode('utf-8'))
        print("📋 Tekst is ook naar je klembord gekopieerd!")
    except Exception:
        pass


if __name__ == "__main__":
    main()
