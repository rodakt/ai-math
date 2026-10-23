"""Audyt czytelności slajdów: rozmiar i kontrast każdego widocznego tekstu.

Otwiera wyrenderowane _output/slajdy.html w chromium bez okna (1280×720), odsłania
na każdym slajdzie kolejno wszystkie kroki (fragmenty) i dla każdego tekstu widocznego
w którymkolwiek kroku mierzy:
- rozmiar fontu w px slajdu 1280×720 (dla SVG po przeskalowaniu viewBoxa),
- kontrast z tłem (WCAG; tło = kształt SVG albo tło HTML pod środkiem tekstu,
  dalej kolor tła slajdu, dalej biel; tła półprzezroczyste nakładane na to pod spodem).
Przejścia CSS są wyłączone, żeby mierzyć stan docelowy każdego kroku. Pomija podpisy źródeł (.zrodla, a w podpisach pod zdjęciem klasa .zrodlo): muszą być na slajdzie, ale sala nie musi ich czytać.

Użycie: python3 narzedzia/audyt_czytelnosci.py [--min-px 24] [--min-kontrast 4.5] [--wszystko]
Kod wyjścia 1, gdy jakiś tekst ma kontrast poniżej progu (rozmiar na razie tylko raport).
"""

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent
SLAJDY = KATALOG / "_output" / "slajdy.html"

POMIAR = r"""
<style>*, *::before, *::after { transition: none !important; animation: none !important; }</style>
<script>
Reveal.on("ready", () => {
  const rgba = c => { const m = c.match(/[\d.]+/g); return m ? [+m[0], +m[1], +m[2], m[3] === undefined ? 1 : +m[3]] : null; };
  const nałóż = (g, d) => [0, 1, 2].map(k => g[k] * g[3] + d[k] * (1 - g[3])).concat(1);
  const lum = c => { const [r, g, b] = c.slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const kolor = css => { const d = document.createElement("div"); d.style.color = css; document.body.appendChild(d); const v = getComputedStyle(d).color; d.remove(); return rgba(v); };
  const tłoSlajdu = el => { const s = el.closest("section[data-background-color]"); return s ? kolor(s.getAttribute("data-background-color")) : [255, 255, 255, 1]; };
  const widoczny = el => { for (let e = el; e && e !== document.body; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity < 0.2) return false; } return true; };
  // warstwy tła pod punktem, od góry; półprzezroczyste nakładamy na to, co pod nimi
  const tło = (el, x, y) => {
    const warstwy = [];
    for (const e of document.elementsFromPoint(x, y)) {
      if (!e.closest(".slides") || (e !== el && el.contains(e)) || e.tagName === "text" || e.tagName === "tspan") continue;
      const cs = getComputedStyle(e);
      if (!widoczny(e)) continue;  // także ukryta grupa-rodzic (np. wstawka, która już zniknęła)
      let c = null;
      if (e instanceof SVGElement) {
        if (["rect", "circle", "path", "polygon", "ellipse"].includes(e.tagName) && cs.fill !== "none" && !cs.fill.startsWith("url")) {
          c = rgba(cs.fill); if (c) c[3] *= +cs.fillOpacity * +cs.opacity;
        }
      } else { c = rgba(cs.backgroundColor); }
      if (c && c[3] > 0.02) { warstwy.push(c); if (c[3] >= 0.99) break; }
    }
    let wynik = warstwy.length && warstwy[warstwy.length - 1][3] >= 0.99 ? warstwy.pop() : tłoSlajdu(el);
    while (warstwy.length) wynik = nałóż(warstwy.pop(), wynik);
    return wynik;
  };
  const wynik = [];
  Reveal.getSlides().forEach((s, i) => {
    const idx = Reveal.getIndices(s);
    const tytuł = ((s.querySelector("h1,h2") || {}).textContent || s.id || "").trim();
    const kroki = new Set([...s.querySelectorAll(".fragment")].map(f => +(f.getAttribute("data-fragment-index") || 0)));
    const zapisane = new Map();  // element → pomiar; kontrast najgorszy ze wszystkich kroków, w których tekst widać
    for (const f of [-1, ...[...kroki].sort((p, q) => p - q)]) {
      Reveal.slide(idx.h, idx.v, f);
      const w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT), były = new Set();
      let n;
      while ((n = w.nextNode())) {
        const t = n.textContent.trim(), el = n.parentElement;
        if (!t || były.has(el)) continue; były.add(el);
        if (el.closest("aside.notes, script, style, .slide-number, .zrodla, .zrodlo") || !widoczny(el)) continue;
        const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
        const cs = getComputedStyle(el);
        let px = parseFloat(cs.fontSize);
        if (el instanceof SVGElement) { const m = el.ownerSVGElement.getScreenCTM(); px *= Math.hypot(m.a, m.b) / Reveal.getScale(); }
        const c = rgba(el instanceof SVGElement ? cs.fill : cs.color); if (!c) continue;
        if (el instanceof SVGElement) c[3] *= +cs.fillOpacity;
        const b = tło(el, r.left + r.width / 2, r.top + r.height / 2), cc = nałóż(c, b);
        const [hi, lo] = [lum(cc), lum(b)].sort((p, q) => q - p);
        const pomiar = { nr: i + 1, tytul: tytuł, klasa: el.getAttribute("class") || el.tagName.toLowerCase(), tekst: t,
                         px: Math.round(px * 10) / 10, kolor: el instanceof SVGElement ? cs.fill : cs.color,
                         tlo: `rgb(${b.slice(0, 3).map(Math.round).join(", ")})`, kontrast: Math.round((hi + 0.05) / (lo + 0.05) * 100) / 100 };
        const było = zapisane.get(el);
        if (!było || pomiar.kontrast < było.kontrast) zapisane.set(el, pomiar);
      }
    }
    wynik.push(...zapisane.values());
  });
  const pre = document.createElement("pre"); pre.id = "audyt-czytelnosci"; pre.textContent = JSON.stringify(wynik); document.body.appendChild(pre);
});
</script>
"""


def zmierz(plik):
    src = plik.read_text(encoding="utf-8")
    i = src.rfind("</body>")
    with tempfile.TemporaryDirectory() as tmp:
        kopia = Path(tmp) / "audyt.html"
        kopia.write_text(src[:i] + POMIAR + src[i:], encoding="utf-8")
        dom = subprocess.run(["chromium", "--headless=new", "--window-size=1280,720", "--virtual-time-budget=20000",
                              "--dump-dom", kopia.as_uri()], capture_output=True, text=True, timeout=300).stdout
    m = re.search(r'<pre id="audyt-czytelnosci">(.*?)</pre>', dom, re.S)
    if not m:
        sys.exit("audyt: brak wyniku pomiaru (czy _output/slajdy.html jest wyrenderowany?)")
    return json.loads(html.unescape(m.group(1)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min-px", type=float, default=24)
    ap.add_argument("--min-kontrast", type=float, default=4.5)
    ap.add_argument("--wszystko", action="store_true", help="wypisz też za małe teksty, nie tylko liczby")
    ap.add_argument("plik", nargs="?", type=Path, default=SLAJDY)
    a = ap.parse_args()

    teksty = zmierz(a.plik)
    slajdy = defaultdict(list)
    for t in teksty:
        slajdy[(t["nr"], t["tytul"])].append(t)

    print(f"{'nr':>3}  {'slajd':36} {'min px':>6}  {'< ' + str(a.min_px) + ' px':>9}  {'kontrast < ' + str(a.min_kontrast):>14}")
    for (nr, tytul), ts in sorted(slajdy.items()):
        male = sum(t["px"] < a.min_px for t in ts)
        slabe = sum(t["kontrast"] < a.min_kontrast for t in ts)
        print(f"{nr:>3}  {tytul[:36]:36} {min(t['px'] for t in ts):6.1f}  {male:>4}/{len(ts):<4}  {slabe:>14}")

    slabe = [t for t in teksty if t["kontrast"] < a.min_kontrast]
    print(f"\nKontrast poniżej {a.min_kontrast}:1 — {len(slabe)}")
    for t in slabe:
        print(f"  {t['nr']:>3} {t['klasa'][:28]:28} {t['kontrast']:5.2f}  {t['kolor']} na {t['tlo']}  „{t['tekst'][:40]}”")
    if a.wszystko:
        male = sorted((t for t in teksty if t["px"] < a.min_px), key=lambda t: (t["nr"], t["px"]))
        print(f"\nPoniżej {a.min_px} px — {len(male)}")
        for t in male:
            print(f"  {t['nr']:>3} {t['klasa'][:28]:28} {t['px']:5.1f}  „{t['tekst'][:40]}”")
    print(f"\nRazem: {len(teksty)} tekstów, {sum(t['px'] < a.min_px for t in teksty)} poniżej {a.min_px} px, "
          f"{len(slabe)} z kontrastem poniżej {a.min_kontrast}:1")
    return 1 if slabe else 0


if __name__ == "__main__":
    sys.exit(main())
