"""Generuje figury SVG do slajdów: mapę województw z grafem sąsiedztwa (cztery barwy),
tory pocisków (tabela strzelnicza), piramidę rachmistrzów Prony'ego
trzy sposoby liczenia 347 · 28 (w pamięci, słupek, kalkulator)
dwie części dowodu Appela i Hakena (stos kartek ze skanem tablicy, diament Birkhoffa)
pętlę budowania tego dowodu (reguły → przypadki → lista → maszyna), pętlę FunSearch i jego funkcje priority
grę AlphaTensor (tensor mnożenia 2×2 jako cztery plansze, ruchy Strassena) i rekordy dla macierzy 4×4
dwie drogi programowania (quicksort i wagi LeNet-5 z narzedzia/trenuj_lenet.py)
miarkę: rekordy FrontierMath do nasycenia, ścianę otwartych problemów Erdősa z warunkami i wynikami,
schodki olimpiady (AlphaGeometry, srebro, złoto), przybliżenie bloku 2021–2026 (zagęszczenie),
siatkę autorstwa (kto przejął które szczeble drabiny),
poglądowy wykres wybuchu (Navier–Stokes), zadanie demo (z demo-automorfizmy/zadanie.json)
i kod QR do repozytorium prezentacji (wymaga biblioteki segno).

Wyniki trafiają do figury/ i są commitowane, bo render ma działać bez Pythona.

Użycie:
    python narzedzia/generuj_figury.py [WOJEWODZTWA.geojson]

Bez GeoJSON-u mapa nie jest generowana (zostaje poprzednia).

GeoJSON: https://github.com/ppatrzyk/polska-geojson (wojewodztwa-min.geojson,
licencja MIT, dane źródłowe: GUGiK, PRG).
"""

import base64
import itertools
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

KATALOG = Path(__file__).resolve().parent.parent
FIGURY = KATALOG / "figury"

# --- mapa województw -------------------------------------------------------

KOLORY_MAPY = ["#4e79a7", "#f28e2b", "#59a14f", "#edc948"]
SZEROKOSC_MAPY = 600
KROK_ANIMACJI = 0.35  # sekundy między kolejnymi województwami


def rzutuj(punkty, lon0, lat0, skala):
    """Rzut równoodległościowy z poprawką cos(φ): wystarcza dla obszaru Polski."""
    kx = math.cos(math.radians(52))
    return [((lon - lon0) * kx * skala, (lat0 - lat) * skala) for lon, lat in punkty]


def pierscienie(geometria):
    if geometria["type"] == "Polygon":
        return geometria["coordinates"]
    return [r for poligon in geometria["coordinates"] for r in poligon]


def koloruj(sasiedzi, kolejnosc, k):
    """Kolorowanie z nawrotami; zwraca słownik albo None."""
    kolor = {}

    def krok(i):
        if i == len(kolejnosc):
            return True
        v = kolejnosc[i]
        for c in range(k):
            if all(kolor.get(u) != c for u in sasiedzi[v]):
                kolor[v] = c
                if krok(i + 1):
                    return True
                del kolor[v]
        return False

    return dict(kolor) if krok(0) else None


def odleglosc_od_odcinka(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def wewnatrz(p, r):
    x, y = p
    w = False
    for (ax, ay), (bx, by) in zip(r, r[1:] + r[:1]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            w = not w
    return w


def srodek(r):
    """Punkt wewnątrz wielokąta najdalszy od granicy: kropka grafu nie ląduje
    przy granicy, jak bywa ze środkiem ciężkości. Siatka zagęszczana wokół
    najlepszego punktu; odległość liczona do uproszczonego obwodu."""
    obwod = r[::5]
    krawedzie = list(zip(obwod, obwod[1:] + obwod[:1]))

    def ocena(p):
        if not wewnatrz(p, r):
            return -1
        return min(odleglosc_od_odcinka(p, a, b) for a, b in krawedzie)

    xs, ys = [p[0] for p in r], [p[1] for p in r]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    zasieg, krok = max(max(xs) - min(xs), max(ys) - min(ys)) / 2, 12
    while krok >= 1:
        siatka = [(cx + i * krok, cy + j * krok)
                  for i in range(-int(zasieg / krok), int(zasieg / krok) + 1)
                  for j in range(-int(zasieg / krok), int(zasieg / krok) + 1)]
        cx, cy = max(siatka, key=ocena)
        zasieg, krok = 2 * krok, krok / 3
    return cx, cy


def mapa(sciezka_geojson):
    dane = json.loads(Path(sciezka_geojson).read_text(encoding="utf-8"))
    cechy = dane["features"]
    wszystkie = [p for f in cechy for r in pierscienie(f["geometry"]) for p in r]
    lon_min = min(p[0] for p in wszystkie)
    lon_max = max(p[0] for p in wszystkie)
    lat_min = min(p[1] for p in wszystkie)
    lat_max = max(p[1] for p in wszystkie)
    kx = math.cos(math.radians(52))
    skala = SZEROKOSC_MAPY / ((lon_max - lon_min) * kx)
    wysokosc = (lat_max - lat_min) * skala

    nazwy, sciezki, punkty, srodki = [], [], [], []
    for f in cechy:
        nazwy.append(f["properties"]["nazwa"])
        czesci, zbior, najwiekszy = [], set(), []
        for r in pierscienie(f["geometry"]):
            xy = [(round(x, 1), round(y, 1)) for x, y in rzutuj(r, lon_min, lat_max, skala)]
            xy = [p for i, p in enumerate(xy) if i == 0 or p != xy[i - 1]]
            zbior.update(xy)
            czesci.append("M" + "L".join(f"{x:g},{y:g}" for x, y in xy) + "Z")
            if len(xy) > len(najwiekszy):
                najwiekszy = xy
        sciezki.append("".join(czesci))
        punkty.append(zbior)
        srodki.append(srodek(najwiekszy))

    # sąsiedztwo: wspólny odcinek granicy, czyli co najmniej dwa wspólne punkty
    n = len(cechy)
    sasiedzi = {i: set() for i in range(n)}
    for i, j in itertools.combinations(range(n), 2):
        if len(punkty[i] & punkty[j]) >= 2:
            sasiedzi[i].add(j)
            sasiedzi[j].add(i)

    # kolejność animacji: wszerz od zachodniopomorskiego
    start = nazwy.index("zachodniopomorskie")
    kolejnosc, kolejka = [], [start]
    while kolejka:
        v = kolejka.pop(0)
        if v not in kolejnosc:
            kolejnosc.append(v)
            kolejka.extend(sorted(sasiedzi[v] - set(kolejnosc)))
    assert len(kolejnosc) == n

    trzy = koloruj(sasiedzi, kolejnosc, 3)
    kolor = koloruj(sasiedzi, kolejnosc, 4)
    assert kolor is not None
    for i, j in itertools.combinations(range(n), 2):
        if j in sasiedzi[i]:
            assert kolor[i] != kolor[j]

    linie = [
        f'<svg viewBox="-2 -2 {SZEROKOSC_MAPY + 4:g} {wysokosc + 4:.0f}" class="mapa-woj" '
        'role="img" aria-label="Mapa 16 województw kolorowana czterema kolorami">'
    ]
    for poz, i in enumerate(kolejnosc):
        linie.append(
            f'<path d="{sciezki[i]}" style="--c:{KOLORY_MAPY[kolor[i]]};'
            f'--d:{poz * KROK_ANIMACJI:.2f}s"><title>{nazwy[i]}</title></path>'
        )
    # graf: województwo = kropka, wspólna granica = kreska; kropki kolorują się
    # w tej samej kolejności co mapa (--d), kroki sterowane z CSS fragmentami slajdu
    linie.append('<g class="graf">')
    for i, j in itertools.combinations(range(n), 2):
        if j in sasiedzi[i]:
            (x1, y1), (x2, y2) = srodki[i], srodki[j]
            linie.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
    for poz, i in enumerate(kolejnosc):
        x, y = srodki[i]
        linie.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="15" style="--c:{KOLORY_MAPY[kolor[i]]};'
                     f'--d:{poz * KROK_ANIMACJI:.2f}s"><title>{nazwy[i]}</title></circle>')
    linie.append("</g>")
    linie.append("</svg>")

    wyjscie = FIGURY / "_mapa-wojewodztw.md"
    wyjscie.write_text(
        "<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->\n\n"
        "```{=html}\n" + "\n".join(linie) + "\n```\n",
        encoding="utf-8",
    )
    krawedzie = sum(len(s) for s in sasiedzi.values()) // 2
    print(f"mapa: {n} województw, {krawedzie} par sąsiadów, "
          f"3 kolory {'wystarczą' if trzy else 'nie wystarczą'}, "
          f"{wyjscie.stat().st_size // 1024} KB -> {wyjscie}")


# --- tory pocisków ------------------------------------------------------------

G = 9.81
V0 = 300.0      # prędkość wylotowa, m/s
OPOR = 1e-4     # k w a = -k|v|v, 1/m; rząd wielkości dla pocisku ok. 75 mm
KATY = [15, 30, 45, 60, 75]
SKALA_TORU = 0.06                 # px na metr, ta sama w obu panelach i w obu osiach
TOR_W, TOR_H, TOR_X0, TOR_Y0 = 600, 300, 20, 280  # viewBox i położenie działa


def tor(kat, k, dt=0.01):
    """Tor pocisku (RK4) do upadku; zwraca listę (t, x, y)."""
    vx, vy = V0 * math.cos(math.radians(kat)), V0 * math.sin(math.radians(kat))
    t = x = y = 0.0
    punkty = [(0.0, 0.0, 0.0)]

    def a(vx, vy):
        v = math.hypot(vx, vy)
        return -k * v * vx, -G - k * v * vy

    while True:
        k1 = a(vx, vy)
        k2 = a(vx + dt / 2 * k1[0], vy + dt / 2 * k1[1])
        k3 = a(vx + dt / 2 * k2[0], vy + dt / 2 * k2[1])
        k4 = a(vx + dt * k3[0], vy + dt * k3[1])
        nvx = vx + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nvy = vy + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        nx, ny = x + dt * (vx + nvx) / 2, y + dt * (vy + nvy) / 2
        if ny < 0:
            s = y / (y - ny)
            punkty.append((t + s * dt, x + s * (nx - x), 0.0))
            return punkty
        t, x, y, vx, vy = t + dt, nx, ny, nvx, nvy
        punkty.append((t, x, y))


def najlepszy_kat():
    """Kąt (co 1°) o największym zasięgu z oporem."""
    return max(range(10, 81), key=lambda kat: tor(kat, OPOR)[-1][1])


def px(x, y):
    return TOR_X0 + x * SKALA_TORU, TOR_Y0 - y * SKALA_TORU


def sciezka(punkty, co=10):
    xy = [px(x, y) for _, x, y in punkty[::co] + [punkty[-1]]]
    return "M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in xy)


def etykieta_kata(punkty, kat, klasa):
    _, x, y = max(punkty, key=lambda p: p[2])
    a, b = px(x, y)
    return f'<text x="{a:.0f}" y="{b - 8:.0f}" class="{klasa}">{kat}°</text>'


def panel_toru(z_oporem):
    opis = ("Tory pocisku z oporem powietrza dla kątów 15–75°; w tle przerywane parabole bez oporu"
            if z_oporem else "Tory pocisku bez oporu powietrza: parabole dla kątów 15–75°")
    linie = [f'<svg viewBox="0 0 {TOR_W} {TOR_H}" class="tory" role="img" aria-label="{opis}">',
             f'<line x1="0" y1="{TOR_Y0}" x2="{TOR_W}" y2="{TOR_Y0}" class="ziemia"/>']
    for kat in KATY:
        parabola = tor(kat, 0.0)
        if z_oporem:
            linie.append(f'<path d="{sciezka(parabola)}" class="cien"/>')
        else:
            klasa = "tor bez glowny" if kat == 45 else "tor bez"
            linie.append(f'<path d="{sciezka(parabola)}" class="{klasa}"/>')
            linie.append(etykieta_kata(parabola, kat, "kat glowny" if kat == 45 else "kat"))
    if z_oporem:
        # zamiast 45° rysujemy kąt, który z oporem daje największy zasięg
        najlepszy = najlepszy_kat()
        for kat in [najlepszy if k == 45 else k for k in KATY]:
            punkty = tor(kat, OPOR)
            klasa = "tor opor glowny" if kat == najlepszy else "tor opor"
            linie.append(f'<path d="{sciezka(punkty)}" class="{klasa}"/>')
            linie.append(etykieta_kata(punkty, kat, "kat glowny" if kat == najlepszy else "kat"))
    linie.append(f'<circle cx="{TOR_X0}" cy="{TOR_Y0}" r="6" class="dzialo"/>')
    linie.append("</svg>")
    return "\n".join(linie)


def schemat_krokow():
    """Kilka kroków metody Eulera z dużym Δt: kropka (położenie), strzałka (prędkość · Δt)."""
    dt, k, skala = 6.0, OPOR, 0.035
    vx, vy = V0 * math.cos(math.radians(45)), V0 * math.sin(math.radians(45))
    x = y = 0.0
    punkty = [(x, y)]
    for _ in range(6):
        x, y = x + vx * dt, y + vy * dt
        v = math.hypot(vx, vy)
        vx, vy = vx - k * v * vx * dt, vy + (-G - k * v * vy) * dt
        punkty.append((x, y))
    xs = [p[0] for p in punkty]
    ys = [p[1] for p in punkty]
    szer = (max(xs) - min(xs)) * skala + 40
    wys = (max(ys) - min(ys)) * skala + 30
    xy = [(20 + (a - min(xs)) * skala, wys - 15 - (b - min(ys)) * skala) for a, b in punkty]
    linie = [f'<svg viewBox="0 0 {szer:.0f} {wys:.0f}" class="kroki" role="img" '
             'aria-label="Metoda krok po kroku: z położenia i prędkości liczymy nowe położenie">',
             '<defs><marker id="grot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
             'markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10Z" class="grot"/>'
             '</marker></defs>']
    for (a, b), (c, d) in zip(xy, xy[1:]):
        linie.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" '
                     'marker-end="url(#grot)"/>')
    for a, b in xy:
        linie.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="5"/>')
    linie.append("</svg>")
    return "\n".join(linie)


def tory():
    pliki = {"_tory-bez-oporu.md": panel_toru(False),
             "_tory-z-oporem.md": panel_toru(True),
             "_kroki.md": schemat_krokow()}
    for nazwa, svg in pliki.items():
        (FIGURY / nazwa).write_text(
            "<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->\n\n"
            "```{=html}\n" + svg + "\n```\n",
            encoding="utf-8",
        )
    zasieg = {kat: tor(kat, OPOR)[-1][1] for kat in range(10, 81)}
    najlepszy = najlepszy_kat()
    print(f"tory: v0 = {V0:g} m/s, k = {OPOR:g} 1/m; bez oporu 45° -> {V0 ** 2 / G:.0f} m; "
          f"z oporem najdalej {najlepszy}° -> {zasieg[najlepszy]:.0f} m, "
          f"15° -> {zasieg[15]:.0f} m, 75° -> {zasieg[75]:.0f} m, "
          f"lot 45° {tor(45, OPOR)[-1][0]:.0f} s")


# --- piramida Prony'ego ------------------------------------------------------

# piętra: (klasa, etykieta, liczby ludzików w kolejnych rzędach); liczebności poglądowe
PIETRA_PRONY = [("p1", "wzory", [3]),
                ("p2", "schemat", [7]),
                ("p3", "+ −", [9, 11, 13])]
LUDZIK_DX, LUDZIK_DY, PRZERWA_PIETER = 20, 26, 12
PRONY_W, PRONY_SRODEK, PRONY_ETYKIETA = 400, 138, 284


def piramida_prony():
    """Trzy piętra rachmistrzów: kilku matematyków, kilku planujących, kilkudziesięciu liczących."""
    linie = [None,  # nagłówek <svg> po policzeniu wysokości
             '<defs><g id="ludzik"><circle cx="0" cy="-11" r="5.2"/>'
             '<path d="M-8,9Q-8,-4.5 0,-4.5Q8,-4.5 8,9Z"/></g></defs>']
    y = 26
    for i, (klasa, etykieta, rzedy) in enumerate(PIETRA_PRONY):
        if i:
            # strop między piętrami, na szerokość niższego piętra
            strop = y + 9 + PRZERWA_PIETER / 2 + 2
            y += LUDZIK_DY + PRZERWA_PIETER
            polowa = max(rzedy) * LUDZIK_DX / 2
            linie.append(f'<line x1="{PRONY_SRODEK - polowa:.0f}" y1="{strop:.0f}" '
                         f'x2="{PRONY_SRODEK + polowa:.0f}" y2="{strop:.0f}" class="strop"/>')
        y_pietra = y
        for ile in rzedy:
            for k in range(ile):
                x = PRONY_SRODEK + (k - (ile - 1) / 2) * LUDZIK_DX
                linie.append(f'<use href="#ludzik" x="{x:.1f}" y="{y}" class="{klasa}"/>')
            y += LUDZIK_DY
        y -= LUDZIK_DY
        linie.append(f'<text x="{PRONY_ETYKIETA}" y="{(y_pietra + y) / 2 + 4:.0f}" '
                     f'class="etykieta {klasa}">{etykieta}</text>')
    wys = y + 16
    linie[0] = (f'<svg viewBox="0 0 {PRONY_W} {wys}" class="prony" role="img" aria-label='
                '"Piramida Prony\'ego: kilku matematyków dobiera wzory, kilku rachmistrzów układa '
                'schemat, kilkudziesięciu liczących tylko dodaje i odejmuje">')
    linie.append("</svg>")
    wyjscie = FIGURY / "_piramida-prony.md"
    wyjscie.write_text(
        "<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->\n\n"
        "```{=html}\n" + "\n".join(linie) + "\n```\n",
        encoding="utf-8",
    )
    print(f"piramida Prony'ego: {[sum(r) for _, _, r in PIETRA_PRONY]} ludzików -> {wyjscie}")


# --- 347 · 28 na trzy sposoby -------------------------------------------------

PANEL_W, PANEL_H = 300, 270
KRATKA = 30                 # kratka zeszytu; jedna cyfra słupka = jedna kratka
SLUPEK_KOL0 = 225           # środek kolumny jedności


def zapisz_figure(nazwa, svg):
    (FIGURY / nazwa).write_text(
        "<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->\n\n"
        "```{=html}\n" + svg + "\n```\n",
        encoding="utf-8",
    )


def slupek(a, b, blad=None):
    """Mnożenie pisemne a · b na kartce w kratkę, odręcznie.

    blad: (wiersz, kolumna, cyfra) — podmienia jedną cyfrę iloczynu częściowego
    i liczy dalej (dodawanie już poprawne), jak uczeń, który pomylił się raz."""
    jednosci, dziesiatki = b % 10, b // 10
    czesc1 = str(a * jednosci)
    if blad:
        k = len(czesc1) - 1 - blad[1]
        czesc1 = czesc1[:k] + str(blad[2]) + czesc1[k + 1:]
    czesc2 = str(a * dziesiatki)
    wynik = str(int(czesc1) + int(czesc2) * 10)
    # przeniesienia przy mnożeniu przez cyfrę jedności, nad kolumnami 1, 2, ...
    przeniesienia, p = {}, 0
    for k, cyfra in enumerate(reversed(str(a))):
        p = (int(cyfra) * jednosci + p) // 10
        if p and k + 1 < len(str(a)):
            przeniesienia[k + 1] = p

    def x(kol):
        return SLUPEK_KOL0 - KRATKA * kol

    def wiersz(tekst, r, kol0=0, klasa="reka"):
        y = KRATKA * r + 26
        return [f'<text x="{x(kol0 + k)}" y="{y}" class="{klasa}">{c}</text>'
                for k, c in enumerate(reversed(tekst))]

    linie = [f'<svg viewBox="0 0 {PANEL_W} {PANEL_H}" class="liczenie slupek" role="img" '
             f'aria-label="Mnożenie pisemne {a} razy {b} = {wynik}">']
    for i in range(0, PANEL_W + 1, KRATKA):
        linie.append(f'<line x1="{i}" y1="0" x2="{i}" y2="{PANEL_H}" class="kratka"/>')
    for j in range(0, PANEL_H + 1, KRATKA):
        linie.append(f'<line x1="0" y1="{j}" x2="{PANEL_W}" y2="{j}" class="kratka"/>')
    for kol, c in przeniesienia.items():
        linie.append(f'<text x="{x(kol) + 8}" y="{KRATKA + 22}" class="reka male">{c}</text>')  # nad cyfrą
    linie += wiersz(str(a), 2)
    linie += wiersz("×", 3, kol0=len(str(b)) + 1) + wiersz(str(b), 3)
    szer = max(len(czesc1), len(czesc2) + 1, len(wynik)) + 1
    for r in (4, 6):
        y0 = KRATKA * r - 1
        linie.append(f'<path d="M{x(szer - 1) - 14},{y0} Q{x(szer // 2)},{y0 + 3} {x(0) + 15},{y0 - 1}" '
                     'class="kreska"/>')
    linie += wiersz(czesc1, 4)
    linie += wiersz("+", 5, kol0=len(czesc2) + 1) + wiersz(czesc2, 5, kol0=1)
    linie += wiersz(wynik, 6)
    linie.append("</svg>")
    return "\n".join(linie), wynik


def w_pamieci():
    """Ludzik i dymek z rachunkiem: 347 · 30 − 347 · 2."""
    linie = [f'<svg viewBox="0 0 {PANEL_W} {PANEL_H}" class="liczenie pamiec" role="img" '
             'aria-label="Rachunek w pamięci: 347 razy 30 minus 347 razy 2 daje 9716">',
             '<rect x="18" y="12" width="264" height="150" rx="60" class="dymek"/>',
             '<circle cx="92" cy="182" r="11" class="dymek"/>',
             '<circle cx="74" cy="203" r="7" class="dymek"/>',
             '<text x="150" y="58" class="mysl">347 · 30 = 10 410</text>',
             '<text x="150" y="96" class="mysl">347 · 2 = 694</text>',
             '<text x="150" y="138" class="mysl wynik">10 410 − 694 = 9716</text>',
             '<g transform="translate(52,240) scale(2.2)" class="glowa">'
             '<circle cx="0" cy="-11" r="5.2"/><path d="M-8,9Q-8,-4.5 0,-4.5Q8,-4.5 8,9Z"/></g>',
             "</svg>"]
    return "\n".join(linie)


def kalkulator(wynik):
    klawisze = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ",", "=", "+"]
    x0, y0, w, h = 75, 8, 150, 254
    linie = [f'<svg viewBox="0 0 {PANEL_W} {PANEL_H}" class="liczenie kalkulator" role="img" '
             f'aria-label="Kalkulator z wynikiem {wynik}">',
             f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="14" class="obudowa"/>',
             f'<rect x="{x0 + 12}" y="{y0 + 14}" width="{w - 24}" height="52" rx="4" class="ekran"/>',
             f'<text x="{x0 + w - 20}" y="{y0 + 54}" class="cyfry">{wynik}</text>']
    for i, k in enumerate(klawisze):
        kx = x0 + 12 + (i % 4) * 32
        ky = y0 + 80 + (i // 4) * 41
        klasa = "klawisz dzialanie" if k in "÷×−+=" else "klawisz"
        linie.append(f'<rect x="{kx}" y="{ky}" width="28" height="34" rx="5" class="{klasa}"/>'
                     f'<text x="{kx + 14}" y="{ky + 24}" class="etykieta-klawisza">{k}</text>')
    linie.append("</svg>")
    return "\n".join(linie)


def mnozenie():
    a, b = 347, 28
    svg, wynik = slupek(a, b)
    assert wynik == str(a * b)
    svg_blad, wynik_blad = slupek(a, b, blad=(4, 1, 6))  # 2776 -> 2766
    zapisz_figure("_mnozenie-pamiec.md", w_pamieci())
    zapisz_figure("_mnozenie-slupek.md", svg)
    zapisz_figure("_mnozenie-slupek-blad.md", svg_blad)
    zapisz_figure("_mnozenie-kalkulator.md", kalkulator(wynik))
    print(f"mnożenie: {a} · {b} = {wynik}; słupek z błędem daje {wynik_blad}")


# --- Appel i Haken: dwie części dowodu -----------------------------------------

SKAN_AH = "appel-haken-tabela4-1977.png"  # część I, s. 472: Tabela 4, strona 1
KONFIGURACJE = 1936  # lista z 1976 (w publikacji z 1977: 1482); Wilson, Celebratio
AH_W, AH_H = 1150, 500
PRAWA_X, PRAWA_Y, PRAWA_SZER = 420, 40, 720  # część komputerowa: diament i podpis pod nim


def diament_birkhoffa(cx, cy):
    """Diament Birkhoffa (1913): cztery wierzchołki stopnia 5 w pierścieniu sześciu.

    Wewnątrz: u (góra), v (dół), w (lewo), x (prawo), krawędź u–v wspólna dla trójkątów
    w–u–v i x–u–v. Pierścień r1..r6 co 60°, od lewej górnej, zgodnie z ruchem wskazówek."""
    R = 125
    pierscien = {f"r{i + 1}": (cx + R * math.cos(math.radians(a)), cy - R * math.sin(math.radians(a)))
                 for i, a in enumerate([120, 60, 0, -60, -120, 180])}
    srodek = {"u": (cx, cy - 42), "v": (cx, cy + 42), "w": (cx - 58, cy), "x": (cx + 58, cy)}
    pkt = {**pierscien, **srodek}
    wnetrze = [("u", "v"), ("u", "w"), ("u", "x"), ("v", "w"), ("v", "x")]
    do_pierscienia = [("w", "r1"), ("w", "r6"), ("w", "r5"), ("u", "r1"), ("u", "r2"),
                      ("x", "r2"), ("x", "r3"), ("x", "r4"), ("v", "r4"), ("v", "r5")]
    obwod = [(f"r{i}", f"r{i % 6 + 1}") for i in range(1, 7)]
    # kontrola: każdy wierzchołek wewnętrzny ma stopień 5
    for v in srodek:
        assert sum(v in k for k in wnetrze + do_pierscienia) == 5, v
    linie = ['<g class="konfiguracja">']
    for klasa, krawedzie in (("obwod", obwod), ("do-pierscienia", do_pierscienia), ("wnetrze", wnetrze)):
        for a, b in krawedzie:
            (x1, y1), (x2, y2) = pkt[a], pkt[b]
            linie.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{klasa}"/>')
    for x, y in pierscien.values():
        linie.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="w-pierscieniu"/>')
    for x, y in srodek.values():
        linie.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" class="w-srodku"/>')
    tx = cx + R + 60
    for i, (tekst, klasa) in enumerate([("jeden przypadek:", "mocny"), ("fragment grafu", ""),
                                        ("● = 5 sąsiadów", ""),
                                        ("przykład: diament", "drobny"), ("Birkhoffa, 1913", "drobny")]):
        linie.append(f'<text x="{tx:.0f}" y="{cy - 50 + i * 30 + (8 if i > 2 else 0):.0f}" '
                     f'class="opis-konfiguracji {klasa}">{tekst}</text>')
    linie.append("</g>")
    return "\n".join(linie)


def appel_haken():
    """Stos kartek (część ręczna) i diament Birkhoffa (część komputerowa), pod spodem oś czasu.

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .blad, potem .koniec."""
    linie = [f'<svg viewBox="0 0 {AH_W} {AH_H}" class="appel-haken" role="img" aria-label='
             '"Dowód Appela i Hakena: ponad 400 stron sprawdzanych ręcznie i 1936 konfiguracji '
             'sprawdzone komputerem; błąd znaleziono w części ręcznej">']
    # część ręczna: stos kartek, na wierzchu skan prawdziwej strony (Tabela 4 z części I, 1977)
    skan = base64.b64encode((KATALOG / "img" / SKAN_AH).read_bytes()).decode()
    kx, ky, kw, kh = 80, 10, 192, 276
    for i in range(3, 0, -1):
        linie.append(f'<rect x="{kx + i * 6}" y="{ky + i * 6}" width="{kw}" height="{kh}" class="kartka"/>')
    linie.append(f'<rect x="{kx}" y="{ky}" width="{kw}" height="{kh}" class="kartka"/>')
    linie.append(f'<image x="{kx + 4}" y="{ky + 4}" width="{kw - 8}" height="{kh - 8}" '
                 f'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{skan}"/>')
    linie.append('<text x="190" y="345" class="podpis mocny">część ręczna</text>')
    linie.append('<text x="190" y="372" class="podpis">strona z dowodu · Appel, Haken 1977</text>')
    linie.append(f'<g class="blad"><path d="M{kx + 20},{ky + 40} L{kx + kw - 20},{ky + kh - 40} '
                 f'M{kx + kw - 20},{ky + 40} L{kx + 20},{ky + kh - 40}" class="krzyz"/></g>')
    # jeden przypadek: diament Birkhoffa, potem liczba wszystkich przypadków
    linie.append(diament_birkhoffa(PRAWA_X + 200, PRAWA_Y + 130))
    srodek = PRAWA_X + PRAWA_SZER / 2
    linie.append(f'<text x="{srodek:.0f}" y="345" class="podpis mocny">część komputerowa</text>')
    linie.append(f'<text x="{srodek:.0f}" y="372" class="podpis liczba-przypadkow">jeden z {KONFIGURACJE} '
                 'przypadków · wszystkie sprawdza komputer (1200 h)</text>')
    # oś czasu
    y = 430
    linie.append(f'<line x1="40" y1="{y}" x2="{AH_W - 20}" y2="{y}" class="os"/>')
    zdarzenia = [(190, "1976", "Appel i Haken: dowód", ""),
                 (480, "1981", "Schmidt: błąd w części ręcznej", "blad"),
                 (770, "1989", "poprawki w monografii", "koniec"),
                 (1010, "2005", "cały dowód w Coq", "koniec")]
    for x, rok, opis, klasa in zdarzenia:
        g = f'<g class="{klasa}">' if klasa else "<g>"
        linie.append(f'{g}<circle cx="{x}" cy="{y}" r="8" class="punkt"/>'
                     f'<text x="{x}" y="{y - 18}" class="rok">{rok}</text>'
                     f'<text x="{x}" y="{y + 32}" class="opis">{opis}</text></g>')
    linie.append("</svg>")
    zapisz_figure("_appel-haken.md", "\n".join(linie))
    print(f"Appel i Haken: {KONFIGURACJE} konfiguracji -> figury/_appel-haken.md")


# --- Appel i Haken: pętla budowania dowodu --------------------------------------

GRANAT, POMARANCZ, ZIELEN = "#1f4e79", "#a65a17", "#59a14f"
ZIELEN_TEKST = "#3f7f37"  # zieleń w napisach: #59a14f ma na bieli tylko 3,2:1


def petla_ah():
    """Pętla 1972–1976: ludzie układają reguły i przeglądają przypadki, z tego wychodzi
    lista konfiguracji, maszyna sprawdza każdą; „nie” wraca do reguł, „wszystkie tak” kończy.

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .nie (strzałka powrotu), .tak (wyjście)."""
    W, H = 1150, 500
    bloki = [  # (x, kolor, tytuł, liczba, podpis)
        (20, GRANAT, "przepis", "487", ["reguł: które miejsca", "mapy obejrzeć"]),
        (310, GRANAT, "przypadki", "≈10 000", ["miejsc", "obejrzanych ręcznie"]),
        (600, GRANAT, "lista", "1936", ["konfiguracji"]),
        (890, POMARANCZ, "da się dokolorować?", "199 291", ["kolorowań pierścienia", "dla jednej konfiguracji"]),
    ]
    bw, bh, by = 240, 185, 105
    linie = [f'<svg viewBox="0 0 {W} {H}" class="petla-ah" role="img" aria-label="Pętla budowania '
             'dowodu Appela i Hakena: ludzie układają reguły i przeglądają przypadki, maszyna sprawdza '
             'każdą konfigurację z listy; gdy któraś nie przechodzi, ludzie zmieniają reguły">']
    linie.append('<defs>' + "".join(
        f'<marker id="grot-{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{k}"/></marker>'
        for n, k in (("szary", "#666"), ("zielony", ZIELEN))) + '</defs>')
    # kto: ludzie nad trzema blokami, maszyna nad ostatnim
    linie.append(f'<text x="{(20 + 600 + bw) / 2:.0f}" y="70" class="kto" fill="{GRANAT}">ludzie</text>')
    linie.append(f'<line x1="20" y1="85" x2="{600 + bw}" y2="85" stroke="{GRANAT}" stroke-width="3"/>')
    linie.append(f'<text x="{890 + bw / 2:.0f}" y="70" class="kto" fill="{POMARANCZ}">maszyna</text>')
    linie.append(f'<line x1="890" y1="85" x2="{890 + bw}" y2="85" stroke="{POMARANCZ}" stroke-width="3"/>')
    for x, kolor, tytul, liczba, podpis in bloki:
        cx = x + bw / 2
        linie.append(f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" rx="12" class="blok" stroke="{kolor}"/>'
                     f'<text x="{cx:.0f}" y="{by + 40}" class="tytul-bloku">{tytul}</text>'
                     f'<text x="{cx:.0f}" y="{by + 100}" class="liczba" fill="{kolor}">{liczba}</text>'
                     + "".join(f'<text x="{cx:.0f}" y="{by + 137 + 24 * k}" class="podpis-bloku">{t}</text>'
                               for k, t in enumerate(podpis)))
    for x, *_ in bloki[:-1]:
        linie.append(f'<line x1="{x + bw + 6}" y1="{by + bh / 2}" x2="{x + bw + 44}" y2="{by + bh / 2}" '
                     'stroke="#666" stroke-width="4" marker-end="url(#grot-szary)"/>')
    # szkielet dowodu pod listą i pod maszyną
    linie.append(f'<text x="{600 + bw / 2:.0f}" y="{by + bh + 32}" class="szkielet">każda mapa ma coś z listy</text>')
    linie.append(f'<text x="{890 + bw / 2:.0f}" y="{by + bh + 32}" class="szkielet">kontrprzykład tego nie ma</text>')
    # powrót: „nie” z maszyny do reguł
    yd = 420
    linie.append(f'<g class="nie"><path d="M960,{by + bh + 50} V{yd} H140 V{by + bh + 8}" fill="none" stroke="#666" '
                 'stroke-width="4" marker-end="url(#grot-szary)"/>'
                 f'<text x="550" y="{yd - 14}" class="etykieta">nie przeszła? zmień reguły</text>'
                 f'<text x="550" y="{yd + 32}" class="etykieta drobna">ok. 500 poprawek · 1972–1976</text></g>')
    # wyjście: wszystkie „tak”
    linie.append(f'<g class="tak"><path d="M1070,{by + bh + 50} V{yd + 20}" fill="none" stroke="{ZIELEN}" '
                 'stroke-width="5" marker-end="url(#grot-zielony)"/>'
                 f'<text x="1140" y="{yd + 62}" class="etykieta zielona">wszystkie „tak”: VI 1976</text></g>')
    linie.append("</svg>")
    zapisz_figure("_petla-ah.md", "\n".join(linie))
    print("pętla Appela i Hakena -> figury/_petla-ah.md")


CAP_Z3_2 = [(0, 0), (1, 0), (0, 1), (1, 1)]  # 4 punkty bez prostej w ℤ₃² (więcej się nie da)
PROSTA_ZAWINIETA = [(1, 0), (0, 1), (2, 2)]  # p = (1, 0), v = (2, 1): na kartce nie prosta


def plaszczyzna_z3(x0, y0, bok=44, skala=1):
    """Wstęp do pętli FunSearch (klasa .plaszczyzna): ℤ₃² jako siatka 3×3, oś y w górę.
    Pomarańczowe pola — 4 punkty bez prostej; granatowe obwódki — prosta zawinięta, która blokuje (2, 2)."""
    def prosta(a, b, c):
        return all((i + j + k) % 3 == 0 for i, j, k in zip(a, b, c))
    punkty = list(itertools.product(range(3), repeat=2))
    assert not any(prosta(*t) for t in itertools.combinations(CAP_Z3_2, 3))
    assert all(any(prosta(p, *t) for t in itertools.combinations(CAP_Z3_2, 2))
               for p in punkty if p not in CAP_Z3_2), "da się dołożyć piąty punkt"
    assert prosta(*PROSTA_ZAWINIETA)
    linie = [f'<g class="plaszczyzna" transform="scale({skala})">']
    for x, y in punkty:
        klasa = "pole wziete" if (x, y) in CAP_Z3_2 else "pole"
        linie.append(f'<rect x="{x0 + x * bok}" y="{y0 + (2 - y) * bok}" width="{bok}" height="{bok}" class="{klasa}"/>')
    for x, y in PROSTA_ZAWINIETA:
        linie.append(f'<rect x="{x0 + x * bok + 5}" y="{y0 + (2 - y) * bok + 5}" width="{bok - 10}" height="{bok - 10}" '
                     f'class="obwodka" stroke="{GRANAT}"/>')
    for k in range(3):
        linie.append(f'<text x="{x0 + k * bok + bok / 2:.0f}" y="{y0 + 3 * bok + 26}" class="wsp">{k}</text>'
                     f'<text x="{x0 - 16}" y="{y0 + (2 - k) * bok + bok / 2 + 9:.0f}" class="wsp">{k}</text>')
    xt = x0 + 3 * bok + 30
    linie.append(f'<text x="{xt}" y="{y0 + 28}" class="opis-z3">wymiar 2: 9 punktów, najwięcej <tspan fill="{POMARANCZ}" '
                 'font-weight="700">4</tspan> bez prostej</text>'
                 f'<text x="{xt}" y="{y0 + 78}" class="opis-z3" fill="{GRANAT}">(1,0), (0,1), (2,2) — też prosta:</text>'
                 f'<text x="{xt}" y="{y0 + 114}" class="opis-z3" fill="{GRANAT}">p = (1,0), v = (2,1), '
                 'p + 2v = (5,2) = (2,2)</text>')
    linie.append('</g>')
    return linie


def petla_funsearch():
    """Pętla FunSearch (2023) w układzie pętli Appela i Hakena: w pętli same bloki maszyny
    (model językowy pisze funkcję, program buduje zbiór, oceniacz liczy), ludzie nad pętlą — ją zbudowali.

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .plaszczyzna (duża ℤ₃² na wejściu, znika,
    gdy wchodzi .petla — pas ludzi i bloki maszyny), .powrot (najlepsze wracają do modelu),
    .wynik i .ludzie-czytaja razem (512 w wymiarze 8; zewnętrzna pętla: ludzie czytają program)."""
    W, H = 1150, 520
    bloki = [  # (x, tytuł, liczba, podpis)
        (20, "model językowy", "pisze", ["jedną funkcję programu:", "który punkt wziąć?"]),
        (345, "program", "6561", ["punktów do wyboru;", "bierze, póki brak prostej"]),
        (670, "oceniacz", "ile?", ["punktów zebrał program", "sprawdza: bez prostej"]),
    ]
    bw, bh, by = 290, 185, 170
    xp = 1065  # prawa kolumna: wynik
    linie = [f'<svg viewBox="0 0 {W} {H}" class="petla-ah petla-fs" role="img" aria-label="Pętla FunSearch: '
             'ludzie wybrali problem, napisali oceniacz i przepis konstrukcji; w pętli model językowy pisze funkcję, '
             'program buduje zbiór punktów, oceniacz liczy punkty, najlepsze programy wracają do modelu">']
    linie.append('<defs>' + "".join(
        f'<marker id="grot-fs-{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{k}"/></marker>'
        for n, k in (("szary", "#666"), ("zielony", ZIELEN), ("granat", GRANAT))) + '</defs>')
    linie.append('<g class="petla">')
    # ludzie nad pętlą
    linie.append(f'<rect x="20" y="16" width="{W - 40}" height="70" rx="12" class="pas-ludzi" stroke="{GRANAT}"/>'
                 f'<text x="{W / 2:.0f}" y="61" class="pas-tekst"><tspan class="kto" fill="{GRANAT}">ludzie</tspan>'
                 '  wybrali problem · napisali oceniacz · przepis</text>')
    # maszyna nad trzema blokami
    linie.append(f'<text x="{(20 + 670 + bw) / 2:.0f}" y="135" class="kto" fill="{POMARANCZ}">maszyna</text>')
    linie.append(f'<line x1="20" y1="150" x2="{670 + bw}" y2="150" stroke="{POMARANCZ}" stroke-width="3"/>')
    for x, tytul, liczba, podpis in bloki:
        cx = x + bw / 2
        linie.append(f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" rx="12" class="blok" stroke="{POMARANCZ}"/>'
                     f'<text x="{cx:.0f}" y="{by + 40}" class="tytul-bloku">{tytul}</text>'
                     f'<text x="{cx:.0f}" y="{by + 100}" class="liczba" fill="{POMARANCZ}">{liczba}</text>'
                     + "".join(f'<text x="{cx:.0f}" y="{by + 137 + 27 * k}" class="podpis-bloku">{t}</text>'
                               for k, t in enumerate(podpis)))
    for x, *_ in bloki[:-1]:
        linie.append(f'<line x1="{x + bw + 6}" y1="{by + bh / 2}" x2="{x + bw + 39}" y2="{by + bh / 2}" '
                     'stroke="#666" stroke-width="4" marker-end="url(#grot-fs-szary)"/>')
    linie.append('</g>')
    # powrót: najlepsze programy wracają do modelu
    yd = 450
    linie.append(f'<g class="powrot"><path d="M{670 + bw / 2:.0f},{by + bh + 6} V{yd} H{20 + bw / 2:.0f} V{by + bh + 8}" '
                 'fill="none" stroke="#666" stroke-width="4" marker-end="url(#grot-fs-szary)"/>'
                 f'<text x="{(20 + 670 + bw) / 2:.0f}" y="{yd - 14}" class="etykieta">najlepsze programy wracają do modelu</text>'
                 f'<text x="{(20 + 670 + bw) / 2:.0f}" y="{yd + 32}" class="etykieta drobna">'
                 'każdy wynik sprawdzony · nie wiadomo, czy coś się znajdzie</text></g>')
    # wynik: wymiar 8
    yw = by + bh / 2
    linie.append(f'<g class="wynik"><line x1="{670 + bw + 6}" y1="{yw}" x2="{xp - 62}" y2="{yw}" stroke="{ZIELEN}" '
                 'stroke-width="5" marker-end="url(#grot-fs-zielony)"/>'
                 f'<text x="{xp}" y="{yw + 18}" class="liczba" fill="{ZIELEN_TEKST}">512</text>'
                 f'<text x="{xp}" y="{yw + 52}" class="podpis-bloku">wymiar 8</text>'
                 f'<text x="{xp}" y="{yw + 79}" class="podpis-bloku">dotąd 496</text></g>')
    # zewnętrzna pętla: ludzie czytają program
    linie.append(f'<g class="ludzie-czytaja"><path d="M{xp},{yw - 46} V{92}" fill="none" stroke="{GRANAT}" '
                 'stroke-width="4" stroke-dasharray="9 6" marker-end="url(#grot-fs-granat)"/>'
                 f'<text x="{xp - 14}" y="112" class="etykieta granat">czytają</text>'
                 f'<text x="{xp - 14}" y="138" class="etykieta granat">program</text></g>')
    linie.extend(plaszczyzna_z3(20, 45, 42, skala=1.65))
    linie.append("</svg>")
    zapisz_figure("_petla-funsearch.md", "\n".join(linie))
    print("pętla FunSearch -> figury/_petla-funsearch.md")


# --- FunSearch: funkcja startowa i znaleziona ------------------------------------

# Romera-Paredes i in., Nature 2024: rys. 2a (start) i rys. 4b (znaleziona dla n = 8), przepisane dosłownie;
# pominięte tylko adnotacje typów w nagłówku. Skrypt je uruchamia w szkielecie z rys. 2a i sprawdza wynik.
PRIORITY_START = """def priority(el, n):
  return 0.0"""
PRIORITY_512 = """def priority(el, n):
  score = n
  in_el = 0
  el_count = el.count(0)

  if el_count == 0:
    score += n**2
    if el[1] == el[-1]:
      score *= 1.5
    if el[2] == el[-2]:
      score *= 1.5
    if el[3] == el[-3]:
      score *= 1.5
  else:
    if el[1] == el[-1]:
      score *= 0.5
    if el[2] == el[-2]:
      score *= 0.5

  for e in el:
    if e == 0:
      if in_el == 0:
        score *= n * 0.5
      elif in_el == el_count - 1:
        score *= 0.5
      else:
        score *= n * 0.5 ** in_el
      in_el += 1
    else:
      score += 1

  if el[1] == el[-1]:
    score *= 1.5
  if el[2] == el[-2]:
    score *= 1.5

  return score"""
SLOWA_KLUCZOWE = {"def", "if", "elif", "else", "for", "in", "return"}


def cap_set_zachlanny(zrodlo, n=8):
    """Szkielet z rys. 2a: punkty od najwyższego priorytetu (remisy jak np.argsort(stable)[::-1]),
    punkt bierzemy, jeśli nie domyka prostej z dwoma już wziętymi (x + y + z = 0 mod 3)."""
    przestrzen = {}
    exec(zrodlo, przestrzen)
    elementy = list(itertools.product(range(3), repeat=n))
    oceny = [przestrzen["priority"](el, n) for el in elementy]
    kolejnosc = sorted(range(len(elementy)), key=oceny.__getitem__)[::-1]
    zbior, zablokowane = [], set()
    for i in kolejnosc:
        c = elementy[i]
        if c in zablokowane:
            continue
        zablokowane.update(tuple((-a - b) % 3 for a, b in zip(c, x)) for x in zbior)
        zbior.append(c)
    wziete = set(zbior)
    assert all(tuple((-a - b) % 3 for a, b in zip(x, y)) not in wziete
               for x, y in itertools.combinations(zbior, 2)), "trzy punkty na prostej"
    return len(zbior)


def wiersz_kodu(tekst):
    """Wiersz Pythona jako tspany: słowa kluczowe i nazwa funkcji wyróżnione."""
    out = []
    for kawalek in re.split(r"(\W+)", tekst):
        kawalek_xml = kawalek.replace("&", "&amp;").replace("<", "&lt;")
        if kawalek in SLOWA_KLUCZOWE:
            out.append(f'<tspan class="kw">{kawalek_xml}</tspan>')
        elif kawalek == "priority":
            out.append(f'<tspan class="fn">{kawalek_xml}</tspan>')
        else:
            out.append(kawalek_xml)
    return "".join(out)


# wiersze znalezionej funkcji pokazane na slajdzie (24px mieści ok. 12); reszta jako „⋮ N wierszy pominiętych”
WYCINEK_512 = [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 36]


def liczba_wierszy(n):
    """1 wiersz, 2–4 wiersze, 5 wierszy, 22 wiersze, 25 wierszy."""
    if n == 1:
        return "1 wiersz"
    return f"{n} wiersze" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else f"{n} wierszy"


def funsearch_kod():
    """Lewa: funkcja startowa ludzi (granat) i jej wynik; środek: wycinek funkcji znalezionej przez model
    (pomarańcz; pominięte wiersze zliczone), prawa: jej wynik i opis symetrii. Wyniki liczy skrypt.

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .znaleziona, .symetria (wiersze z el[i] == el[-i])."""
    start, znaleziona = cap_set_zachlanny(PRIORITY_START), cap_set_zachlanny(PRIORITY_512)
    assert znaleziona == 512, znaleziona
    W, H, dy, y0 = 1180, 560, 32, 166
    wiersze = PRIORITY_512.split("\n")
    niepuste = sum(1 for w in wiersze if w.strip())
    linie = [f'<svg viewBox="0 0 {W} {H}" class="funsearch-kod" role="img" aria-label="Funkcja priority: '
             f'startowa, napisana przez ludzi, zwraca zawsze 0 i daje {start} punktów; znaleziona przez model '
             f'językowy ma {liczba_wierszy(niepuste)} i daje {znaleziona} punktów">']
    linie.append(f'<text x="{W / 2:.0f}" y="34" class="szkielet-opis">przepis ludzi: bierz punkty od najwyższej oceny '
                 '<tspan class="fn">priority</tspan>, póki nie ma prostej</text>')

    def blok(x, szer, wiersze, kolor):
        out = [f'<rect x="{x}" y="{y0 - 36}" width="{szer}" height="{len(wiersze) * dy + 26}" rx="8" '
               f'class="kod-tlo" stroke="{kolor}"/>']
        for k, w in enumerate(wiersze):
            y = y0 + k * dy
            if w.startswith("⋮"):
                out.append(f'<text x="{x + 14}" y="{y}" class="pominiete">{w}</text>')
                continue
            if "el[-" in w:
                out.append(f'<rect x="{x + 4}" y="{y - 24}" width="{szer - 8}" height="{dy}" class="pasek-symetrii"/>')
            out.append(f'<text x="{x + 14}" y="{y}" class="kod" xml:space="preserve">{wiersz_kodu(w)}</text>')
        return out

    # lewa: start
    xl, szl = 10, 350
    linie.append(f'<text x="{xl + szl / 2:.0f}" y="100" class="kto" fill="{GRANAT}">start · napisali ludzie</text>')
    linie += blok(xl, szl, PRIORITY_START.split("\n"), GRANAT)
    linie.append(f'<text x="{xl + szl / 2:.0f}" y="{y0 + dy + 100}" class="wynik" fill="{GRANAT}">{start}</text>'
                 f'<text x="{xl + szl / 2:.0f}" y="{y0 + dy + 136}" class="podpis">punktów bez prostej</text>')
    # środek: wycinek znalezionej; luki w numeracji WYCINEK_512 to pominięte wiersze
    wycinek, poprz = [], -1
    for k in WYCINEK_512:
        pominiete = sum(1 for w in wiersze[poprz + 1:k] if w.strip())
        if pominiete > 1:
            wycinek.append(f"⋮ {liczba_wierszy(pominiete)} pominięte" if liczba_wierszy(pominiete).endswith("e")
                           else f"⋮ {liczba_wierszy(pominiete)} pominiętych")
        wycinek.append(wiersze[k])
        poprz = k
    xp, szp = 400, 470
    xw = (xp + szp + W) / 2  # prawa kolumna: wynik i opis
    linie.append(f'<g class="znaleziona"><text x="{xp + szp / 2:.0f}" y="100" class="kto" fill="{POMARANCZ}">'
                 'znaleziona · napisał model</text>')
    linie += blok(xp, szp, wycinek, POMARANCZ)
    linie.append(f'<text x="{xw:.0f}" y="{y0 + 40}" class="wynik" fill="{POMARANCZ}">{znaleziona}</text>'
                 f'<text x="{xw:.0f}" y="{y0 + 76}" class="podpis">punktów bez prostej</text></g>')
    ys = y0 + 6 * dy
    linie.append(f'<g class="symetria-opis"><text x="{xw:.0f}" y="{ys}" class="opis-symetrii">'
                 '<tspan class="kod">el[i] == el[-i]</tspan></text>'
                 + "".join(f'<text x="{xw:.0f}" y="{ys + 40 + 30 * k}" class="podpis">{t}</text>'
                           for k, t in enumerate(["i-ta współrzędna", "i i-ta od końca:", "widać symetrię",
                                                  "rozwiązania"]))
                 + '</g>')
    linie.append("</svg>")
    zapisz_figure("_funsearch-kod.md", "\n".join(linie))
    print(f"FunSearch: priority startowa -> {start}, znaleziona -> {znaleziona} punktów (n = 8), "
          f"na slajdzie {len(WYCINEK_512)} z {niepuste} wierszy -> figury/_funsearch-kod.md")


# --- AlphaTensor: gra na kostce i schodki 4×4 -----------------------------------

def tensor_mnozenia_2x2():
    """Komórki (wyraz A, wyraz B, wyraz wyniku) z jedynką: a_ij · b_jk trafia do c_ik."""
    return [(2 * i + j, 2 * j + k, 2 * i + k) for i in range(2) for j in range(2) for k in range(2)]


# ruchy Strassena: (litery A ze znakami, litery B ze znakami, wyrazy wyniku ze znakami), wzór do podpisu
RUCHY_STRASSENA = [
    ({"a": 1, "d": 1}, {"e": 1, "h": 1}, {0: 1, 3: 1}, "(a+d)(e+h)"),
    ({"c": 1, "d": 1}, {"e": 1}, {2: 1, 3: -1}, "(c+d)e"),
    ({"a": 1}, {"f": 1, "h": -1}, {1: 1, 3: 1}, "a(f−h)"),
    ({"d": 1}, {"g": 1, "e": -1}, {0: 1, 2: 1}, "d(g−e)"),
    ({"a": 1, "b": 1}, {"h": 1}, {0: -1, 1: 1}, "(a+b)h"),
    ({"c": 1, "a": -1}, {"e": 1, "f": 1}, {3: 1}, "(c−a)(e+f)"),
    ({"b": 1, "d": -1}, {"g": 1, "h": 1}, {0: 1}, "(b−d)(g+h)"),
]
WYRAZY_WYNIKU = ["ae+bg", "af+bh", "ce+dg", "cf+dh"]


def stany_gry():
    """Plansze po kolejnych ruchach Strassena: lista (stan, pola ruchu); stan[(A, B, wyraz)] ∈ {−1, 0, 1}."""
    stan = {c: 1 for c in tensor_mnozenia_2x2()}
    wynik = [(dict(stan), set())]
    for u, v, w, _ in RUCHY_STRASSENA:
        pola = set()
        for (x, cu), (y, cv), (z, cw) in itertools.product(u.items(), v.items(), w.items()):
            c = ("abcd".index(x), "efgh".index(y), z)
            stan[c] = stan.get(c, 0) - cu * cv * cw
            pola.add(c)
        stan = {c: x for c, x in stan.items() if x}
        assert all(x in (-1, 1) for x in stan.values())
        wynik.append((dict(stan), pola))
    assert not stan, "7 ruchów Strassena ma opróżnić plansze"
    return wynik


def alphatensor():
    """Lewa część: gra AlphaTensor dla macierzy 2×2 jako cztery plansze 4×4 (po jednej na wyraz wyniku;
    wiersze — wyrazy A, kolumny — wyrazy B; to te same 64 pola co w kostce z Fawzi i in., Nature 2022, Fig. 1a).
    Na starcie 8 pełnych pól = 8 iloczynów. Ruch = jedno mnożenie; zdejmuje z plansz wzór pól.
    Kolejne stany po ruchach Strassena aż do pustych plansz. Prawa: rekordy dla 4×4 — 64, 49 (Strassen dwa razy),
    47 (AlphaTensor, tylko modulo 2), 48 (AlphaEvolve, liczby zespolone).

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .stan-1 (ruch 1), .stan-2…7 (ruchy 2–7 same, --d),
    .r47, .r48."""
    W, H = 1300, 500
    stany = stany_gry()
    linie = [f'<svg viewBox="0 0 {W} {H}" class="alphatensor" role="img" aria-label="Mnożenie macierzy 2×2 '
             'jako cztery plansze z ośmioma pełnymi polami; ruchy Strassena czyszczą je w siedmiu mnożeniach; '
             'obok rekordy dla macierzy 4×4: 64, 49, 47, 48">']
    p, odstep, x0, y0 = 34, 26, 50, 134
    szer = 4 * p
    srodek = x0 + (4 * szer + 3 * odstep) / 2
    linie.append(f'<text x="{srodek:.0f}" y="34" class="naglowek">gra dla macierzy 2×2</text>')
    yr = y0 + 4 * p + 50

    def plansze(stan, pola):
        out = []
        for z in range(4):
            xb = x0 + z * (szer + odstep)
            for r, k in itertools.product(range(4), range(4)):
                x, y = xb + k * p, y0 + r * p
                klasa = {1: "brakuje", -1: "nadmiar", 0: "puste"}[stan.get((r, k, z), 0)]
                out.append(f'<rect x="{x}" y="{y}" width="{p}" height="{p}" class="pole {klasa}"/>')
                if (r, k, z) in pola:
                    out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{p - 6}" height="{p - 6}" class="slad"/>')
        return "".join(out)

    tlo = (f'<rect x="{x0 - 2}" y="{y0 - 2}" width="{4 * szer + 3 * odstep + 4}" height="{yr + 48 - y0}" '
           'class="tlo-stanu"/>')
    for n, (stan, pola) in enumerate(stany):
        if n == 0:
            podpis = ""
        else:
            wzor = RUCHY_STRASSENA[n - 1][3]
            podpis = (f'<text x="{srodek:.0f}" y="{yr}" class="opis ruch">ruch {n} z 7: {wzor}</text>'
                      f'<text x="{srodek:.0f}" y="{yr + 34}" class="opis {"mocny" if n == 7 else "drobny"}">'
                      + ("2 pola trafione, 6 nadmiarowych do zdjęcia" if n == 1 else
                         "plansze puste: 7 mnożeń zamiast 8" if n == 7 else
                         f"zostało pól: {len(stan)}") + "</text>")
        styl = f' style="--d: {(n - 2) * 1.6:.1f}s"' if n >= 2 else ""
        linie.append(f'<g class="stan stan-{n}"{styl}>' + (tlo if n else "") + plansze(stan, pola) + podpis + "</g>")
    # podpisy stałe: wyrazy wyniku nad planszami, litery wierszy i kolumn
    for z, wyraz in enumerate(WYRAZY_WYNIKU):
        xb = x0 + z * (szer + odstep)
        linie.append(f'<text x="{xb + szer / 2:.0f}" y="{y0 - 46}" class="wyraz">{wyraz}</text>')
        for k in range(4):
            linie.append(f'<text x="{xb + k * p + p / 2:.0f}" y="{y0 - 10}" class="litera mala">{"efgh"[k]}</text>')
    for r in range(4):
        linie.append(f'<text x="{x0 - 10}" y="{y0 + r * p + p / 2 + 7:.0f}" class="litera mala do-prawej">{"abcd"[r]}</text>')
    linie.append(f'<text x="{srodek:.0f}" y="{yr + 100}" class="opis">8 pełnych pól = 8 mnożeń ze wzoru</text>'
                 f'<text x="{srodek:.0f}" y="{yr + 134}" class="opis mocny">cel: wyczyścić plansze w jak najmniej ruchach</text>')
    # schodki dla 4×4
    def yv(v):
        return 92 + (65 - v) * 17
    xa = 710
    linie.append(f'<text x="{(xa + W) / 2:.0f}" y="34" class="naglowek">macierze 4×4: ile mnożeń?</text>')
    for v in range(45, 66, 5):
        linie.append(f'<line x1="{xa}" y1="{yv(v)}" x2="{W - 20}" y2="{yv(v)}" class="linia-siatki"/>'
                     f'<text x="{xa - 8}" y="{yv(v) + 8}" class="os-y">{v}</text>')
    px_ = {"szkola": 780, "1969": 900, "2022": 1040, "2025": 1200}
    linie.append(f'<path d="M{px_["szkola"]},{yv(64)} H{px_["1969"]} V{yv(49)} H{px_["2025"] + 40}" class="schodki"/>')
    linie.append(f'<circle cx="{px_["szkola"]}" cy="{yv(64)}" r="9" class="punkt szary"/>'
                 f'<text x="{px_["szkola"]}" y="{yv(64) - 18}" class="liczba szara">64</text>'
                 f'<text x="{px_["szkola"]}" y="{yv(64) + 32}" class="podpis">wzór</text>')
    linie.append(f'<circle cx="{px_["1969"]}" cy="{yv(49)}" r="9" class="punkt granat"/>'
                 f'<text x="{px_["1969"] - 34}" y="{yv(49) - 16}" class="liczba granat">49</text>'
                 # podpis na lewo od punktu, żeby nie wchodził pod AlphaTensor 2022
                 f'<text x="{px_["1969"] - 18}" y="{yv(49) + 40}" class="podpis koniec">Strassen 1969</text>'
                 f'<text x="{px_["1969"] - 18}" y="{yv(49) + 66}" class="podpis drobny koniec">7 · 7</text>')
    linie.append(f'<g class="r47"><path d="M{px_["2022"]},{yv(49)} V{yv(47)}" class="skok"/>'
                 f'<circle cx="{px_["2022"]}" cy="{yv(47)}" r="9" class="punkt pomarancz"/>'
                 f'<text x="{px_["2022"] - 18}" y="{yv(47) + 12}" class="liczba pomarancz koniec">47</text>'
                 f'<text x="{px_["2022"]}" y="{yv(47) + 44}" class="podpis">AlphaTensor 2022</text>'
                 f'<text x="{px_["2022"]}" y="{yv(47) + 70}" class="podpis drobny">tylko modulo 2</text></g>')
    linie.append(f'<g class="r48"><path d="M{px_["2025"]},{yv(49)} V{yv(48)}" class="skok"/>'
                 f'<circle cx="{px_["2025"]}" cy="{yv(48)}" r="9" class="punkt pomarancz"/>'
                 f'<text x="{px_["2025"]}" y="{yv(49) - 18}" class="liczba pomarancz">48</text>'
                 # podpis nad liczbą: pod punktem zderzałby się z podpisem AlphaTensor 2022
                 f'<text x="{px_["2025"] - 10}" y="{yv(49) - 90}" class="podpis">AlphaEvolve 2025</text>'
                 f'<text x="{px_["2025"] - 10}" y="{yv(49) - 64}" class="podpis drobny">liczby zespolone</text></g>')
    linie.append("</svg>")
    zapisz_figure("_alphatensor.md", "\n".join(linie))
    print("AlphaTensor: plansze 2×2, 7 ruchów Strassena do zera, schodki 64/49/47/48 -> figury/_alphatensor.md")


# --- dwie drogi programowania: quicksort i LeNet-5 ------------------------------

# 6 krótkich wierszy zamiast 4 długich: przy 24px w kolumnie mieści się ok. 38 znaków
QUICKSORT = [
    ("def", "def "), ("fn", "sortuj"), ("", "(xs):"), ("\n", ""),
    ("", "    "), ("kw", "if not"), ("", " xs: "), ("kw", "return"), ("", " []"), ("\n", ""),
    ("", "    p, *r = xs"), ("\n", ""),
    ("", "    a = [x "), ("kw", "for"), ("", " x "), ("kw", "in"), ("", " r "), ("kw", "if"), ("", " x < p]"), ("\n", ""),
    ("", "    b = [x "), ("kw", "for"), ("", " x "), ("kw", "in"), ("", " r "), ("kw", "if"), ("", " x >= p]"), ("\n", ""),
    ("", "    "), ("kw", "return"), ("", " "), ("fn", "sortuj"), ("", "(a) + [p] + "), ("fn", "sortuj"), ("", "(b)"),
]
LISTA_QS = [5, 3, 8, 1, 9, 2, 7, 4]


def drzewo_quicksort(xs, x0, y0, szer, dy):
    """Drzewo wywołań quicksorta: węzeł stoi nad kolumnami, które jego liczby zajmą w wyniku
    (kolumna = miejsce w posortowanej liście), więc rodzeństwo się nie nakłada."""
    ranga = {v: i for i, v in enumerate(sorted(xs))}
    kol = szer / len(xs)
    linie, krawedzie, glebokosci = [], [], []

    def wezel(lista, glebokosc, rodzic):
        lo, hi = min(ranga[v] for v in lista), max(ranga[v] for v in lista)
        cx, cy = x0 + (lo + hi + 1) / 2 * kol, y0 + glebokosc * dy
        glebokosci.append(glebokosc)
        if rodzic:
            krawedzie.append(f'<line x1="{rodzic[0]:.0f}" y1="{rodzic[1] + 10}" x2="{cx:.0f}" y2="{cy - 22}" class="krawedz"/>')
        p, *r = lista
        tekst = f'<tspan class="os">{p}</tspan>' + "".join(f" {v}" for v in r)
        linie.append(f'<text x="{cx:.0f}" y="{cy:.0f}" class="wezel">{tekst}</text>')
        for czesc in ([v for v in r if v < p], [v for v in r if v >= p]):
            if czesc:
                wezel(czesc, glebokosc + 1, (cx, cy))

    wezel(xs, 0, None)
    yw = y0 + (max(glebokosci) + 1) * dy + 10
    linie.append(f'<line x1="{x0}" y1="{yw - 28}" x2="{x0 + szer}" y2="{yw - 28}" class="kreska-wyniku"/>')
    for v in sorted(xs):
        linie.append(f'<text x="{x0 + (ranga[v] + 0.5) * kol:.0f}" y="{yw + 6}" class="wynik">{v}</text>')
    return krawedzie + linie


def dwie_drogi():
    """Algorytmiczny i trenowany obok siebie, w trzech wierszach: co pisze człowiek,
    co jest w środku, skąd wiemy, że działa.

    Prawa strona pochodzi z prawdziwego treningu: narzedzia/trenuj_lenet.py (PyTorch)
    zapisuje img/lenet-warstwa-*.png, img/mnist-cyfry.png i narzedzia/lenet.json."""
    opis = json.loads((KATALOG / "narzedzia" / "lenet.json").read_text(encoding="utf-8"))
    png = lambda nazwa: base64.b64encode((KATALOG / "img" / nazwa).read_bytes()).decode()
    W, H, L, P, SZ = 1180, 636, 10, 620, 550  # szerokość, wysokość, lewa i prawa kolumna, szerokość kolumny
    linie = [f'<svg viewBox="0 0 {W} {H}" class="dwie-drogi" role="img" aria-label="Po lewej quicksort '
             'w Pythonie i drzewo jego wywołań, po prawej reguła uczenia, cyfry MNIST i wszystkie '
             f'{opis["parametry"]} wag sieci LeNet-5">']
    linie.append(f'<line x1="{W / 2}" y1="10" x2="{W / 2}" y2="{H - 10}" class="podzial"/>')
    linie.append(f'<text x="{L}" y="30" class="tor" fill="{GRANAT}">ALGORYTMICZNY</text>')
    linie.append(f'<text x="{P}" y="30" class="tor" fill="{POMARANCZ}">TRENOWANY</text>')
    # wiersz 1: co pisze człowiek
    linie.append(f'<text x="{L}" y="68" class="pyta">człowiek pisze przepis</text>')
    dk = 30  # odstęp wierszy kodu
    linie.append(f'<rect x="{L}" y="82" width="{SZ}" height="{6 * dk + 22}" rx="8" class="kod-tlo"/>')
    kod, wiersz = [f'<text x="{L + 16}" y="116" class="kod">'], 0
    for klasa, t in QUICKSORT:
        if klasa == "\n":
            wiersz += 1
            kod.append(f'</text><text x="{L + 16}" y="{116 + wiersz * dk}" class="kod">')
        else:
            t = t.replace("<", "&lt;").replace(">", "&gt;").replace(" ", " ")
            kod.append(f'<tspan class="{klasa}">{t}</tspan>' if klasa else t)
    linie.append("".join(kod) + "</text>")
    linie.append(f'<text x="{P}" y="68" class="pyta">człowiek pisze regułę uczenia i dostarcza dane</text>')
    linie.append(f'<rect x="{P}" y="82" width="{SZ}" height="70" rx="8" class="kod-tlo"/>')
    linie.append(f'<text x="{P + SZ / 2}" y="129" class="wzor">w ← w − η · ∂L/∂w</text>')
    cw, ch = 8 * 28 * 1.75, 28 * 1.75
    linie.append(f'<image x="{P}" y="166" width="{cw:.0f}" height="{ch:.0f}" class="piksele" '
                 f'href="data:image/png;base64,{png("mnist-cyfry.png")}"/>')
    linie.append(f'<text x="{P + cw + 14:.0f}" y="190" class="drobny">… i tak</text>')
    linie.append(f'<text x="{P + cw + 14:.0f}" y="216" class="drobny">{opis["obrazy_uczace"]:,} cyfr'
                 .replace(",", " ") + '</text>')
    # wiersz 2: co jest w środku
    y2 = 326
    linie.append(f'<text x="{L}" y="{y2}" class="pyta">w środku: każdy krok da się prześledzić</text>')
    linie.extend(drzewo_quicksort(LISTA_QS, L, y2 + 40, SZ, 42))
    linie.append(f'<text x="{P}" y="{y2}" class="pyta">w środku: {opis["parametry"]:,} wag liczbowych'
                 .replace(",", "\u202f") + '</text>')
    (w1, h1), (w2, h2), (w3, h3), (w4, h4), (w5, h5) = opis["warstwy_png"]
    # (numer, x, y, skala, podpis); filtry u góry, macierze połączeń pod nimi. Lewa kolumna obrazów
    # (1, 3) i prawa (2, 4, 5) schodzą niezależnie; podpisy prawej wyrównane do prawej krawędzi.
    yp = y2 + 136
    warstwy = [
        (1, P, y2 + 16, 7, "1. warstwa"),
        (2, P + SZ - w2 * 2.4, y2 + 16, 2.4, "2. warstwa"),
        (3, P, y2 + 88, 1, "3. warstwa"),
        (4, P + SZ - w4, yp, 1, ""),
        (5, P + SZ - w4, yp + h4 + 8, 1, "4. i 5. warstwa"),
    ]
    for (nr, x, y, skala, podpis), (w, h) in zip(warstwy, opis["warstwy_png"]):
        linie.append(f'<image x="{x:.0f}" y="{y}" width="{w * skala:.0f}" height="{h * skala:.0f}" '
                     f'class="piksele" href="data:image/png;base64,{png(f"lenet-warstwa-{nr}.png")}"/>')
        if podpis:
            prawa = nr in (2, 5)
            linie.append(f'<text x="{P + SZ if prawa else x:.0f}" y="{y + h * skala + 24:.0f}" '
                         f'text-anchor="{"end" if prawa else "start"}" class="warstwa">{podpis}</text>')
    # wiersz 3: skąd wiemy, że działa
    ys = 618
    linie.append('<g class="skad">')
    linie.append(f'<text x="{L}" y="{ys}" class="werdykt" fill="{GRANAT}">wiemy z <tspan class="mocny">dowodu</tspan>: '
                 'zawsze sortuje</text>')
    proc = f'{opis["trafnosc_testowa"] * 100:.1f}'.replace(".", ",")
    linie.append(f'<text x="{P}" y="{ys}" class="werdykt" fill="{POMARANCZ}">wiemy z <tspan class="mocny">pomiaru</tspan>: trafia '
                 f'{proc}% z {opis["obrazy_testowe"]:,} nowych cyfr'.replace(",000", " 000") + '</text>')
    linie.append("</g></svg>")
    zapisz_figure("_dwie-drogi.md", "\n".join(linie))
    print(f"dwie drogi: quicksort {LISTA_QS}, LeNet-5 {opis['parametry']} wag, {proc}% -> figury/_dwie-drogi.md")


# --- od zadań do problemów otwartych: FrontierMath i Erdős ---------------------

# Rekordy na FrontierMath Tier 4 w wersji 2 zestawu (VI 2026, poprawione błędy w 42% zadań; 41 zadań),
# według daty udostępnienia modelu; Epoch AI, benchmark_data.zip, frontiermath_tier_4_v2.csv (pobrane 18 X 2026).
# Starsze modele Epoch przeliczył na v2 w czerwcu 2026, więc wszystkie punkty są na jednej skali.
# (data udostępnienia, procent, model)
FRONTIERMATH = [("2025-01-31", 0.0, "o3-mini"), ("2025-04-16", 4.9, "o4-mini"), ("2025-08-07", 22.0, "GPT-5"), ("2025-12-11", 46.0, "GPT-5.2 Pro"),
                ("2026-03-05", 58.5, "GPT-5.4 Pro"), ("2026-04-23", 78.0, "GPT-5.5 Pro"),
                ("2026-06-09", 90.2, "Claude Fable 5"), ("2026-09-03", 97.6, "GPT-6 Astra"),
                ("2026-09-29", 100.0, "GPT-6.1 Sol")]
MIESIACE = (["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"] * 2)[:22]  # I 2025 – X 2026

# FrontierMath Erdős (Epoch AI, 1 IX 2026; arXiv 2609.25050): 68 problemów otwartych w VIII 2026,
# wybrał Thomas Bloom; liczy się tylko dowód lub kontrprzykład, który przejdzie sprawdzenie w Lean.
# Treść w Lean: 50 problemów z projektu Formal Conjectures (Google DeepMind), 18 zapisała AI na zlecenie
# autorów; dowód sprawdza automatycznie Comparator (Lean FRO), człowiek go nie czyta.
ERDOS_PROBLEMY = 68
ERDOS_WARUNKI = ["1 próba na problem", "do 300 $ i 72 godzin", "bez pomocy człowieka",
                 "bez internetu", "dowód sprawdza program (Lean)"]
# (model, rozwiązane, miesiąc testu) w regulaminowym przebiegu; Epoch AI, benchmark_data.zip, frontiermath_erdos.csv
# (pobrane 23 X 2026), kolumna „Started at”: GPT-6.1 Sol 1 X, Astra przed premierą 28 VIII (wynik ogłoszony
# z benchmarkiem 1 IX), Opus 5.5 24 IX, Sonnet 5.5 8 X, GPT-6 Sol 30 IX. Astra: #74 obalony, #126 udowodniony;
# które problemy rozwiązały pozostałe — nie wiemy. Na slajdzie tylko modele z wynikiem > 0; zera (GPT-5.6 Sol,
# GPT-5.5, Claude Fable 5.1, Claude Fable 5, Claude Opus 5, Kimi K3, Grok 4.7, Gemini 3.8 Flash) w notatkach.
ERDOS_START = "1 IX 2026"
ERDOS_WYNIKI = [("GPT-6.1 Sol", 3, "X"), ("GPT-6 Astra", 2, "VIII"), ("Claude Opus 5.5", 2, "IX"),
                ("Claude Sonnet 5.5", 2, "X"), ("GPT-6 Sol", 1, "IX")]
# Poza regulaminem Astra rozwiązała przynajmniej raz 5 problemów (#1, #74, #126, #548, #571), ponad 220 000 $
ERDOS_POZA = 5


def miarka():
    """Rekordy FrontierMath Tier 4 (zadania ze znaną odpowiedzią) aż do nasycenia, na wersji 2 zestawu."""
    W, H = 1180, 545
    x = lambda m: 86 + m * 45
    y = lambda p: 430 - p * 3.5

    def miesiac(data):
        r, m, d = map(int, data.split("-"))
        return (r - 2025) * 12 + m - 1 + (d - 1) / 30

    proc = lambda p: f"{p:g}".replace(".", ",") + "%"
    linie = [f'<svg viewBox="0 0 {W} {H}" class="miarka" role="img" aria-label="Rekordy modeli na '
             'FrontierMath Tier 4 od 0% w styczniu 2025 do 100% we wrześniu 2026">']
    linie.append(f'<text x="{x(0)}" y="30" class="naglowek">zadania ze znaną odpowiedzią</text>')
    linie.append(f'<text x="{x(0)}" y="62" class="pod-naglowkiem">najtrudniejszy poziom; '
                 'najlepszy model dostępny w danym miesiącu</text>')
    ostatni = len(MIESIACE) - 1
    for p in (0, 50, 100):
        linie.append(f'<line x1="{x(0) - 10}" y1="{y(p)}" x2="{x(ostatni) + 10}" y2="{y(p)}" class="siatka"/>'
                     f'<text x="{x(0) - 16}" y="{y(p) + 8}" class="os-y">{p}%</text>')
    # 22 miesiące: kreska przy każdym, podpis co kwartał (sąsiednie VII i VIII by się zlały)
    for m, nazwa in enumerate(MIESIACE):
        linie.append(f'<line x1="{x(m)}" y1="{y(0) + 4}" x2="{x(m)}" y2="{y(0) + 10}" class="kreska"/>')
        if m % 3 == 0:
            linie.append(f'<text x="{x(m)}" y="{y(0) + 34}" class="os-x">{nazwa}</text>')
    linie.append(f'<text x="{(x(0) + x(11)) / 2}" y="{y(0) + 66}" class="rok">2025</text>'
                 f'<text x="{(x(12) + x(ostatni)) / 2}" y="{y(0) + 66}" class="rok">2026</text>')
    punkty = [(x(miesiac(d)), y(p), p) for d, p, _ in FRONTIERMATH]
    # (dx, dy, wyrównanie) nazwy i (dx, wyrównanie) wartości nad punktem, po kolei dla punktów.
    # Nazwa zwykle w prawo w dół (krzywa rośnie, więc tam jest miejsce); przy dwóch pierwszych w dole są
    # podpisy osi, więc nazwa nad wartością. Na stromym odcinku IV–VI wartości na lewo, żeby linia ich nie
    # przecinała. Dwa wrześniowe punkty są blisko: GPT-6 Astra z nazwą nad wartością (nad wykresem jest
    # wolne miejsce), GPT-6.1 Sol z nazwą w prawo w dół, a Claude Fable 5 niżej, pod nią.
    nazwy_poz = [(0, -50, "middle"), (0, -50, "middle"), (12, 30, "start"), (12, 30, "start"), (12, 30, "start"),
                 (12, 30, "start"), (12, 44, "start"), (-14, -50, "end"), (-10, 32, "start")]
    wartosci = [(0, "middle"), (0, "middle"), (0, "middle"), (0, "middle"), (-10, "end"), (-10, "end"),
                (0, "middle"), (-14, "end"), (14, "start")]
    nazwy = [f'<text x="{px + dx}" y="{py + dy}" class="model {k}">{m}</text>'
             for (px, py, _), (_, _, m), (dx, dy, k) in zip(punkty, FRONTIERMATH, nazwy_poz)]
    linie.append('<polyline points="' + " ".join(f"{px},{py}" for px, py, _ in punkty) + '" class="krzywa"/>')
    for (px, py, p), (dx, k) in zip(punkty, wartosci):
        linie.append(f'<circle cx="{px}" cy="{py}" r="7" class="punkt"/>'
                     f'<text x="{px + dx}" y="{py - 18}" text-anchor="{k}" class="wartosc">{proc(p)}</text>')
    linie += nazwy
    px, py, _ = punkty[-1]
    linie.append(f'<text x="{px + 10}" y="{py + 150}" class="nasycony-opis">nic już nie mierzy</text>')
    linie.append(f'<text x="{x(ostatni) + 10}" y="{y(0) + 108}" class="przypis">wyniki na poprawionym zestawie, '
                 'policzone w VI–IX 2026</text>')
    linie.append("</svg>")
    zapisz_figure("_miarka.md", "\n".join(linie))
    print(f"miarka: FrontierMath v2 {[p for _, p, _ in FRONTIERMATH]}% -> figury/_miarka.md")


def erdos():
    """FrontierMath Erdős: ściana 68 otwartych problemów, warunki benchmarku, wyniki modeli.

    Klasy sterowane z CSS kolejnymi fragmentami slajdu: .wyniki (zielone kafle i lista modeli),
    .poza (dodatkowe próby poza regulaminem)."""
    W, H = 1180, 560
    kol, kafel, odstep, x0, y0 = 10, 40, 8, 40, 100
    krok = kafel + odstep
    rozw = ERDOS_WYNIKI[0][1]
    linie = [f'<svg viewBox="0 0 {W} {H}" class="erdos" role="img" aria-label="{ERDOS_PROBLEMY} otwartych '
             f'problemów Erdősa; najlepszy model rozwiązał {rozw}">']
    linie.append(f'<text x="{x0}" y="36" class="naglowek">{ERDOS_PROBLEMY} problemów Erdősa '
                 f'<tspan class="data-erdos">· benchmark od {ERDOS_START}</tspan></text>')
    linie.append(f'<text x="{x0}" y="66" class="pod-naglowkiem">otwarte w sierpniu 2026: '
                 'odpowiedzi nie ma w żadnej książce</text>')

    def kafle(od, do, klasa):
        for n in range(od, do):
            r, k = divmod(n, kol)
            linie.append(f'<rect x="{x0 + k * krok}" y="{y0 + r * krok}" width="{kafel}" height="{kafel}" '
                         f'rx="5" class="{klasa}"/>')

    kafle(0, ERDOS_PROBLEMY, "kafel")
    linie.append('<g class="wyniki">')
    kafle(0, rozw, "kafel rozwiazany")
    yp = y0 + -(-ERDOS_PROBLEMY // kol) * krok + 44
    linie.append(f'<text x="{x0}" y="{yp}" class="wynik-erdos"><tspan class="zielony">{rozw}</tspan>'
                 f' z {ERDOS_PROBLEMY}</text>'
                 f'<text x="{x0}" y="{yp + 30}" class="pod-naglowkiem">najlepszy wynik</text></g>')
    linie.append('<g class="poza">')
    linie.append(f'<text x="{x0 + 190}" y="{yp}" class="poza-opis">Astra poza regulaminem: {ERDOS_POZA},'
                 f'</text><text x="{x0 + 190}" y="{yp + 30}" class="poza-opis">za ponad 220 000 $</text></g>')

    xp = 610
    linie.append(f'<text x="{xp}" y="{y0 + 16}" class="naglowek-maly">warunki</text>')
    for i, w in enumerate(ERDOS_WARUNKI):
        linie.append(f'<text x="{xp}" y="{y0 + 50 + i * 32}" class="warunek">{w}</text>')
    yw = y0 + 50 + len(ERDOS_WARUNKI) * 32 + 24
    linie.append(f'<g class="wyniki"><text x="{xp}" y="{yw}" class="naglowek-maly">wyniki</text>'
                 f'<text x="{xp + 230}" y="{yw}" class="naglowek-maly">test</text>')
    for i, (model, n, miesiac) in enumerate(ERDOS_WYNIKI):
        klasa = "model najlepszy" if n == rozw else "model"
        linie.append(f'<text x="{xp}" y="{yw + 34 + i * 28}" class="{klasa}">{model}</text>'
                     f'<text x="{xp + 230}" y="{yw + 34 + i * 28}" class="miesiac">{miesiac}</text>'
                     f'<text x="{xp + 330}" y="{yw + 34 + i * 28}" class="{klasa} liczba">{n}</text>')
    linie.append("</g></svg>")
    zapisz_figure("_erdos.md", "\n".join(linie))
    print(f"erdős: {[n for _, n, _ in ERDOS_WYNIKI]} z {ERDOS_PROBLEMY}, poza regulaminem {ERDOS_POZA} "
          "-> figury/_erdos.md")


# --- olimpiada: dwie olimpiady na tej samej skali --------------------------------

# AlphaGeometry (I 2024) tylko jako zdanie nad tabelką: 25 z 30 zadań geometrycznych z IMO 2000–2022 to inna
# skala niż punkty IMO; średni złoty medalista 25,9 (Trinh i in., Nature 2024). Niżej dwie olimpiady,
# każda: 6 zadań po 7 pkt. IMO 2024 (blog DeepMind 25.07.2024): AlphaProof rozwiązał 1, 2 (algebra, teoria liczb)
# i 6 (algebra; najtrudniejsze, rozwiązało je 5 zawodników), AlphaGeometry 2 — 4 (geometria); nie rozwiązał 3 i 5
# (kombinatoryka). Zadania przełożone ręcznie na Lean; jedno w kilka minut, inne do trzech dni. Progi 2024:
# złoto od 29, srebro od 22. IMO 2025: Gemini Deep Think i model OpenAI — 1–5, bez 6 (kombinatoryka), 35 pkt;
# Gemini czytał treść sam, w limicie 2 × 4,5 godziny, ocenili koordynatorzy IMO. Próg złota 2025: 35 (UKMT).
# (rok, system, rozwiązane zadania, punkty, medal, próg złota, warunki)
OLIMPIADA = [
    (2024, "AlphaProof + AlphaGeometry 2", {1, 2, 4, 6}, 28, "srebro", 29,
     ["ludzie przekładają mu zadania",
      "nad niektórymi pracuje nawet 3 dni (zawodnicy: 2 × 4,5 godziny)"]),
    (2025, "Gemini Deep Think, OpenAI", {1, 2, 3, 4, 5}, 35, "złoto", 35,
     ["zadania czyta sam, dowody pisze zwykłym językiem",
      "mieści się w czasie zawodników: 2 × 4,5 godziny"]),
]


def olimpiada():
    """Dwie olimpiady na tej samej skali: sześć kwadratów (zadania po 7 pkt), wypełniony = rozwiązany, obok
    punkty i medal, pod spodem warunki (kto przekłada treść, ile czasu). Postęp: o jedno zadanie więcej,
    a przede wszystkim bez pomocy ludzi. Nad tabelką AlphaGeometry jako tło.

    Klasa sterowana z CSS fragmentem slajdu: .rok-2025."""
    W, H = 1180, 560
    bok, odstep, x0 = 76, 12, 20
    linie = [f'<svg viewBox="0 0 {W} {H}" class="olimpiada" role="img" aria-label="Styczeń 2024: AlphaGeometry '
             'rozwiązuje 25 z 30 zadań geometrycznych z dawnych olimpiad, złoty medalista średnio 26. '
             'IMO 2024: AlphaProof rozwiązuje zadania 1, 2, 4 i 6, 28 punktów, srebro, złoto od 29; ludzie '
             'przekładają mu zadania, nad niektórymi pracuje nawet 3 dni. IMO 2025: Gemini Deep Think i OpenAI '
             'rozwiązują zadania 1–5, 35 punktów, złoto; zadania czyta sam, w czasie zawodników">',
             f'<text x="{x0}" y="30" class="wstep">Styczeń 2024: AlphaGeometry rozwiązuje 25 z 30 zadań '
             'geometrycznych</text>',
             f'<text x="{x0}" y="64" class="wstep">z dawnych olimpiad; złoty medalista rozwiązywał średnio 26.</text>',
             f'<line x1="{x0}" y1="92" x2="{W - 20}" y2="92" class="kreska"/>']
    xp = x0 + 6 * bok + 5 * odstep + 44
    for n, (rok, system, rozwiazane, pkt, medal, zloto, warunki) in enumerate(OLIMPIADA):
        g = 134 + 232 * n
        klasa = "srebro" if medal == "srebro" else "zloto"
        el = [f'<text x="{x0}" y="{g}" class="rok">IMO {rok} <tspan class="system">{system}</tspan></text>']
        for z in range(1, 7):
            x = x0 + (z - 1) * (bok + odstep)
            stan = klasa if z in rozwiazane else "brak"
            el.append(f'<rect x="{x}" y="{g + 20}" width="{bok}" height="{bok}" rx="6" class="zadanie {stan}"/>'
                      f'<text x="{x + bok / 2:.0f}" y="{g + 20 + bok / 2 + 10:.0f}" class="nr {stan}">{z}</text>')
        el += [f'<text x="{xp}" y="{g + 52}" class="punkty">{pkt} pkt · {medal}</text>',
               f'<text x="{xp}" y="{g + 88}" class="prog">złoto od {zloto} pkt</text>']
        for k, w in enumerate(warunki):
            el.append(f'<text x="{x0}" y="{g + 136 + 32 * k}" class="warunek">{w}</text>')
        linie.append(f'<g class="rok-{rok}">' + "".join(el) + "</g>")
    linie.append("</svg>")
    zapisz_figure("_olimpiada.md", "\n".join(linie))
    print("olimpiada: IMO 2024 i 2025 na tej samej skali -> figury/_olimpiada.md")


# --- zagęszczenie: blok 2021–2026 w przybliżeniu ---------------------------------

# Wyniki z tego wykładu: (miesiąc od I 2021, podpis). Daty jak w konspekcie.
ZAGESZCZENIE = [
    (11, "Davies i in."),            # Nature, XII 2021 (Wagner: IV 2021, w notatkach)
    (21, "AlphaTensor"),             # Nature, X 2022
    (35, "FunSearch"),               # Nature, XII 2023
    (36, "AlphaGeometry"),           # Nature, I 2024
    (42, "srebro IMO"),              # VII 2024
    (54, "złoto IMO"),               # VII 2025
    (59, "Erdős #1026"),             # XII 2025, Aristotle
    (63, "Erdős #1196"),             # IV 2026, GPT-5.4 Pro
    (66, "hipoteza jakobianowa"),    # 20 VII 2026
    (68, "FrontierMath 100%"),       # IX 2026
    (68, "Navier–Stokes"),           # 8 IX 2026
    (69, "722 prace"),               # 6 X 2026
]
DZIS = 69.5                          # połowa X 2026: wykład; oś nie sięga dalej
# poziom podpisu nad osią i wyrównanie: dobrane tak, żeby linie odniesienia nie przecinały napisów
POZIOMY = [(0, "middle"), (0, "middle"), (0, "end"), (1, "start"), (0, "start"), (1, "middle"),
           (2, "end"), (3, "end"), (4, "end"), (5, "end"), (6, "end"), (7, "end")]


def zageszczenie():
    """U góry mała oś 1946–2026 jak na slajdzie „Dwie drogi i matematyka” (tabele strzelnicze, algebra
    symboliczna, cztery barwy, blok 2021–2026). Klik: blok w przybliżeniu na całą szerokość, skala miesięcy, punkt = wynik z wykładu.
    Oś kończy się na „dziś”. Bez liczb wyników w latach (zdjęte 19.10.2026): liczyły punkty, które sami
    wybraliśmy, a gęstość widać na osi.

    Klasa sterowana z CSS fragmentem slajdu: .lupa."""
    W, H = 1180, 510
    xm = lambda r: 110 + (r - 1946) * 12.5
    ym = 70
    x = lambda m: 60 + m * 15
    A = 450
    linie = [f'<svg viewBox="0 0 {W} {H}" class="zageszczenie" role="img" aria-label="Oś czasu 1946–2026 '
             'z blokiem 2021–2026 w przybliżeniu: wyniki z tego wykładu po kolei od grudnia 2021 do października '
             '2026, coraz gęściej">']
    # klin przybliżenia pod małą osią, żeby nie zasłaniał jej podpisów (pojawia się razem z .lupa)
    linie.append(f'<g class="lupa"><polygon points="{xm(2021)},{ym + 18} {xm(DZIS / 12 + 2021):.1f},{ym + 18} '
                 f'{x(DZIS) + 20:.1f},{A - 320} {x(0) - 20},{A - 320}" class="stozek"/></g>')
    # mała oś
    linie.append(f'<line x1="{xm(1946)}" y1="{ym}" x2="{xm(DZIS / 12 + 2021)}" y2="{ym}" class="os-mala"/>')
    linie.append(f'<rect x="{xm(2021)}" y="{ym - 18}" width="{xm(DZIS / 12 + 2021) - xm(2021):.1f}" height="36" '
                 'rx="5" class="blok"/>')
    # 1968 i 1976 leżą blisko: podpisy rozsunięte (koniec przed punktem / początek przy punkcie)
    for r, podpis, dx, kotwica in ((1946, "tabele strzelnicze", 0, "middle"), (1968, "algebra symboliczna", 52, "end"),
                                   (1976, "cztery barwy", -15, "start")):
        linie.append(f'<circle cx="{xm(r)}" cy="{ym}" r="8" class="punkt-maly"/>'
                     f'<text x="{xm(r)}" y="{ym - 20}" class="rok-maly">{r}</text>'
                     f'<text x="{xm(r) + dx}" y="{ym + 40}" class="podpis-maly" style="text-anchor: {kotwica}">{podpis}</text>')
    linie.append(f'<text x="{(xm(2021) + xm(DZIS / 12 + 2021)) / 2:.0f}" y="{ym - 28}" class="rok-maly">2021–2026</text>')
    # przybliżenie
    el = [f'<line x1="{x(0)}" y1="{A}" x2="{x(DZIS):.1f}" y2="{A}" class="os"/>',
          f'<text x="{x(DZIS) + 10:.1f}" y="{A + 7}" class="dzis">dziś</text>']
    for k in range(6):
        el.append(f'<line x1="{x(12 * k)}" y1="{A - 10}" x2="{x(12 * k)}" y2="{A + 50}" class="granica-roku"/>'
                  f'<text x="{(x(12 * k) + x(min(12 * k + 12, DZIS))) / 2:.0f}" y="{A + 34}" class="rok">{2021 + k}</text>')
    for (m, podpis), (poz, wyr) in zip(ZAGESZCZENIE, POZIOMY):
        yt = A - 34 - 40 * poz
        xt = {"middle": x(m), "end": x(m) - 6, "start": x(m) + 6}[wyr]
        el.append(f'<line x1="{x(m)}" y1="{A}" x2="{x(m)}" y2="{yt + 6}" class="odniesienie"/>'
                  f'<circle cx="{x(m)}" cy="{A}" r="7" class="punkt"/>'
                  f'<text x="{xt}" y="{yt}" text-anchor="{wyr}" class="wynik">{podpis}</text>')
    linie.append('<g class="lupa">' + "".join(el) + "</g>")
    linie.append("</svg>")
    zapisz_figure("_zageszczenie.md", "\n".join(linie))
    print(f"zagęszczenie: {len(ZAGESZCZENIE)} wyników na osi -> figury/_zageszczenie.md")


SZCZEBLE = ["rachunek", "sprawdzanie|przypadków", "szukanie", "dowód", "pytanie"]
# (przykład, kiedy, ile szczebli od dołu przejęła maszyna, czym, krok odsłonięcia)
AUTORSTWO = [
    ("w głowie", "", 0, "", 0),
    ("pismo, tablice, maszyny", "do 1945", 1, "narzędzia", 0),
    ("tabele strzelnicze", "1946", 1, "ENIAC", 0),
    ("cztery barwy", "1976", 2, "komputery IBM", 1),
    ("AlphaTensor", "2022", 3, "AlphaTensor", 1),
    ("FunSearch", "2023", 3, "model językowy", 1),
    ("olimpiada", "2025", 4, "Gemini Deep Think", 2),
    ("hipoteza jakobianowa", "2026", 4, "Claude Fable 5", 2),
    ("Navier–Stokes", "2026", 4, "model OpenAI", 2),
    ("722 prace", "2026", 4, "model OpenAI", 2),
    ("demo", "dziś", 4, "agenci Claude", 3),
]


def autorstwo():
    """Siatka „kto co zrobił”: wiersze to przykłady z wykładu, kolumny to szczeble drabiny. Granat — człowiek,
    pomarańcz — maszyna, z nazwą narzędzia. Pomarańcz rośnie od rachunku; przez ok. 2400 lat (jeden wiersz)
    nie wychodzi poza rachunek, w ostatnich wierszach granatowe zostaje tylko pytanie.

    Klasy sterowane z CSS fragmentami slajdu: .krok1–.krok3 (kolejne grupy wierszy), .pytanie (ramka kolumny)."""
    W, H = 1180, 560
    X0, KOL, Y0, WIERSZ, PRZERWA = 400, 154, 78, 40, 4
    linie = [f'<svg viewBox="0 0 {W} {H}" class="autorstwo" role="img" aria-label="Siatka: przykłady z wykładu '
             'od liczenia w głowie do demo na żywo; maszyna przejmuje kolejne szczeble drabiny, '
             'przy człowieku zostaje pytanie">']
    for k, nazwa in enumerate(SZCZEBLE):
        xc = X0 + k * KOL + KOL / 2
        wiersze = nazwa.split("|")
        for j, w in enumerate(wiersze):
            linie.append(f'<text x="{xc:.0f}" y="{Y0 - 14 - 26 * (len(wiersze) - 1 - j)}" class="szczebel">{w}</text>')
    for i, (przyklad, kiedy, n, czym, krok) in enumerate(AUTORSTWO):
        y = Y0 + i * WIERSZ
        el = [f'<text x="0" y="{y + 28}" class="przyklad">{przyklad}</text>',
              f'<text x="{X0 - 14}" y="{y + 28}" class="kiedy">{kiedy}</text>']
        # pasek = kilka szczebli naraz, żeby napis w nim nie był przecięty; człowiek po jednej komórce na szczebel
        pasek = lambda k0, k1, klasa: (f'<rect x="{X0 + k0 * KOL + PRZERWA / 2}" y="{y + PRZERWA / 2}" '
                                       f'width="{(k1 - k0) * KOL - PRZERWA}" height="{WIERSZ - PRZERWA}" rx="4" '
                                       f'class="{klasa}"/>')
        if n:
            el += [pasek(k, k + 1, "czlowiek") for k in range(n, 5)]
            el.append(pasek(0, n, "maszyna") + f'<text x="{X0 + n * KOL / 2:.0f}" y="{y + 28}" class="czym">{czym}</text>')
        else:
            el.append(pasek(0, 5, "czlowiek") + f'<text x="{X0 + 2.5 * KOL:.0f}" y="{y + 28}" class="czym">'
                      'człowiek: wszystko</text>')
        klasa = f' class="krok{krok}"' if krok else ""
        linie.append(f'<g{klasa}>' + "".join(el) + "</g>")
    linie.append(f'<g class="pytanie"><rect x="{X0 + 4 * KOL - 4}" y="{Y0 - 70}" width="{KOL + 8}" '
                 f'height="{len(AUTORSTWO) * WIERSZ + 76}" rx="8" class="ramka"/>'
                 f'<text x="{W / 2:.0f}" y="{H - 8}" class="puenta">Nie znamy przypadku, w którym maszyna sama '
                 'postawiła ważny problem i go rozwiązała.</text></g>')
    linie.append("</svg>")
    zapisz_figure("_autorstwo.md", "\n".join(linie))
    print(f"autorstwo: {len(AUTORSTWO)} przykładów -> figury/_autorstwo.md")


def wybuch():
    """Poglądowy „wybuch”: największa prędkość w płynie rośnie jak 1/(T − t) i ucieka w nieskończoność przed T."""
    W, H = 700, 480
    x0, y0, xt, yg = 80, 410, 520, 40  # początek osi, chwila T, góra wykresu
    x = lambda t: x0 + t * (xt - x0)
    y = lambda v: y0 - v * 300
    punkty = [(x(t), y(0.08 / (1 - t))) for t in (i / 400 for i in range(400)) if y(0.08 / (1 - t)) >= yg]
    linie = [f'<svg viewBox="0 0 {W} {H}" class="wybuch" role="img" aria-label="Wykres poglądowy: '
             'największa prędkość w płynie rośnie bez ograniczeń, zanim nadejdzie chwila T">']
    linie.append(f'<line x1="{x0}" y1="{y0}" x2="{W - 30}" y2="{y0}" class="os"/>'
                 f'<polygon points="{W - 30},{y0 - 7} {W - 16},{y0} {W - 30},{y0 + 7}" class="grot"/>'
                 f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{yg - 10}" class="os"/>'
                 f'<polygon points="{x0 - 7},{yg - 10} {x0},{yg - 24} {x0 + 7},{yg - 10}" class="grot"/>')
    linie.append(f'<text x="{W - 10}" y="{y0 + 44}" class="opis-osi" text-anchor="end">czas</text>'
                 f'<text x="{x0 - 22}" y="{(y0 + yg) / 2}" class="opis-osi" text-anchor="middle" '
                 f'transform="rotate(-90 {x0 - 22} {(y0 + yg) / 2})">największa prędkość</text>')
    linie.append(f'<line x1="{xt}" y1="{yg - 10}" x2="{xt}" y2="{y0}" class="asymptota"/>'
                 f'<text x="{xt}" y="{y0 + 44}" class="opis-osi" text-anchor="middle">chwila T</text>')
    linie.append('<polyline points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in punkty) + '" class="krzywa"/>')
    linie.append("</svg>")
    zapisz_figure("_wybuch.md", "\n".join(linie))
    print("wybuch: wykres poglądowy -> figury/_wybuch.md")


# --- demo i slajd końcowy ----------------------------------------------------

ZADANIE_DEMO = KATALOG / "demo-automorfizmy" / "zadanie.json"
# adres repozytorium prezentacji (publikacja: narzedzia/publikuj.sh)
REPO_PREZENTACJI = "https://github.com/rodakt/ai-math"


def demo_zadanie():
    """Zadanie demo: punkty p_i (litery) i strzałki p_i → q_i z demo-automorfizmy/zadanie.json.

    Po wpisaniu punktów na wykład do zadanie.json wystarczy uruchomić generator ponownie."""
    dane = json.loads(ZADANIE_DEMO.read_text(encoding="utf-8"))
    P = [tuple(float(Fraction(t)) for t in p) for p in dane["punkty_p"]]
    Q = [tuple(float(Fraction(t)) for t in q) for q in dane["punkty_q"]]
    m = len(P)
    W, H, M = 560, 460, 60
    xs = [x for x, _ in P + Q]
    ys = [y for _, y in P + Q]
    skala = min((W - 2 * M) / ((max(xs) - min(xs)) or 1), (H - 2 * M) / ((max(ys) - min(ys)) or 1))
    x0 = (W - skala * (max(xs) - min(xs))) / 2
    y0 = (H - skala * (max(ys) - min(ys))) / 2
    px = lambda p: (x0 + skala * (p[0] - min(xs)), H - y0 - skala * (p[1] - min(ys)))
    litery = "ABCDEFGHIJ"
    linie = [f'<svg viewBox="0 0 {W} {H}" class="demo-zadanie" role="img" aria-label="Zadanie demo: {m} punktów '
             'i strzałki wskazujące, dokąd ma przejść każdy z nich">',
             '<defs><marker id="demo-grot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
             'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1f4e79"/></marker></defs>']
    r = 11
    for p, q in zip(P, Q):
        (ax, ay), (bx, by) = px(p), px(q)
        d = math.hypot(bx - ax, by - ay)
        if d < 1:
            continue
        ux, uy = (bx - ax) / d, (by - ay) / d
        # łuk wygięty w prawo od kierunku ruchu, żeby zamiany A↔C nie nakładały się
        wyg = 0.18 * d
        cx, cy = (ax + bx) / 2 + uy * wyg, (ay + by) / 2 - ux * wyg
        # początek i koniec skrócone o promień punktu, wzdłuż stycznych do łuku
        def skroc(sx, sy, tx, ty, o):
            dd = math.hypot(tx - sx, ty - sy)
            return sx + (tx - sx) / dd * o, sy + (ty - sy) / dd * o
        sx, sy = skroc(ax, ay, cx, cy, r + 3)
        ex, ey = skroc(bx, by, cx, cy, r + 5)
        linie.append(f'<path d="M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}" class="strzalka" '
                     'fill="none" stroke="#1f4e79" stroke-width="3" marker-end="url(#demo-grot)"/>')
    for i, p in enumerate(P):
        x, y = px(p)
        linie.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="punkt"/>'
                     f'<text x="{x - 18:.1f}" y="{y - 16:.1f}" class="litera">{litery[i]}</text>')
    for q in Q:
        if q not in P:
            x, y = px(q)
            linie.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="cel"/>')
    linie.append("</svg>")
    zapisz_figure("_demo-zadanie.md", "\n".join(linie))
    (FIGURY / "_demo-stopien.md").write_text(
        "<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->\n\n"
        f"znana konstrukcja: stopień $(m-1)^2 = {(m - 1) ** 2}$ · czy da się niżej?\n", encoding="utf-8")
    print(f"demo: {m} punktów, konstrukcja bazowa stopnia {(m - 1) ** 2} -> figury/_demo-zadanie.md, _demo-stopien.md")


def qr_repo():
    """Kod QR do repozytorium prezentacji (segno); bez biblioteki ramka zastępcza z adresem."""
    try:
        import segno
    except ImportError:
        print("qr: brak biblioteki segno (mamba install -n mad-book -c conda-forge segno), ramka zastępcza")
        if not (FIGURY / "_qr.md").exists():
            svg = ('<svg viewBox="0 0 100 100" class="qr" role="img" aria-label="Miejsce na kod QR">'
                   '<rect x="1" y="1" width="98" height="98" fill="#fff" stroke="#999" stroke-width="1" '
                   'stroke-dasharray="4 3"/><text x="50" y="54" font-size="12" fill="#999" '
                   'text-anchor="middle">kod QR</text></svg>')
            zapisz_figure("_qr.md", svg)
        return
    kod = segno.make(REPO_PREZENTACJI, error="m")
    rozmiar = kod.symbol_size(border=2)[0]
    kwadraty = [f"M{x},{y}h1v1h-1z" for y, wiersz in enumerate(kod.matrix_iter(border=2))
                for x, ciemny in enumerate(wiersz) if ciemny]
    svg = (f'<svg viewBox="0 0 {rozmiar} {rozmiar}" class="qr" role="img" aria-label="Kod QR: {REPO_PREZENTACJI}" '
           f'shape-rendering="crispEdges"><rect width="{rozmiar}" height="{rozmiar}" fill="#fff"/>'
           f'<path d="{"".join(kwadraty)}" fill="#111"/></svg>')
    zapisz_figure("_qr.md", svg)
    print(f"qr: {REPO_PREZENTACJI} -> figury/_qr.md")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit(__doc__)
    FIGURY.mkdir(exist_ok=True)
    if len(sys.argv) == 2:
        mapa(sys.argv[1])
    tory()
    piramida_prony()
    mnozenie()
    appel_haken()
    petla_ah()
    petla_funsearch()
    funsearch_kod()
    alphatensor()
    dwie_drogi()
    miarka()
    erdos()
    olimpiada()
    zageszczenie()
    autorstwo()
    wybuch()
    demo_zadanie()
    qr_repo()
