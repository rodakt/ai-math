#!/usr/bin/env python3
"""Rysunki do raportu: bijekcja, obraz łamanej przez najlepsze F, jego czynniki, postęp w czasie."""
import argparse
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
import numpy as np  # noqa: E402
import sympy as sp  # noqa: E402

from verify import odwzorowanie, wczytaj_zadanie, wymierna, wyrazenie, x, y  # noqa: E402

KOLOR_P = "#2a6fdb"
KOLOR_Q = "#d1495b"


def ramka(pts, margines):
    a = np.array(pts, dtype=float)
    lo, hi = a.min(axis=0), a.max(axis=0)
    r = max(float((hi - lo).max()), 1.0)
    return lo - margines * r, hi + margines * r


def punkty(ax, pts, kolor, znacznik, podpis):
    a = np.array(pts, dtype=float)
    ax.scatter(a[:, 0], a[:, 1], s=60, c=kolor, marker=znacznik, zorder=5, label=podpis)
    for i, (u, v) in enumerate(a, start=1):
        ax.annotate(str(i), (u, v), textcoords="offset points", xytext=(6, 6), fontsize=10, color=kolor)


def rys_bijekcja(p, q, plik):
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for (a, b), (c, d) in zip(p, q):
        ax.annotate("", (float(c), float(d)), (float(a), float(b)),
                    arrowprops=dict(arrowstyle="->", color="0.55", lw=1.2))
    punkty(ax, p, KOLOR_P, "o", "$p_i$")
    punkty(ax, q, KOLOR_Q, "s", "$q_i$")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(plik)
    plt.close(fig)


def lamana(p, gestosc=400):
    """Punkty łamanej p_1 -> ... -> p_m i parametr t w [0, 1] wzdłuż niej."""
    a = np.array(p, dtype=float)
    s = np.linspace(0, 1, gestosc, endpoint=False)
    xy = [a[i] + (a[i + 1] - a[i]) * s[:, None] for i in range(len(a) - 1)] + [a[-1:]]
    xy = np.vstack(xy)
    return xy[:, 0], xy[:, 1], np.linspace(0, 1, len(xy))


def krzywa(ax, X, Y, t, lo, hi):
    """Krzywa barwiona parametrem t, przycięta do kadru; zwraca True, jeśli z niego wychodzi."""
    poza = (X < lo[0]) | (X > hi[0]) | (Y < lo[1]) | (Y > hi[1]) | ~np.isfinite(X) | ~np.isfinite(Y)
    X, Y = np.where(poza, np.nan, X), np.where(poza, np.nan, Y)
    odc = np.stack([np.column_stack([X[:-1], Y[:-1]]), np.column_stack([X[1:], Y[1:]])], axis=1)
    lc = LineCollection(odc, cmap="viridis", norm=plt.Normalize(0, 1), lw=2, zorder=3)
    lc.set_array(t[:-1])
    ax.add_collection(lc)
    return bool(poza.any())


def kadr(ax, lo, hi):
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    szer, wys = hi - lo
    if max(szer, wys) < 5 * min(szer, wys):
        ax.set_aspect("equal")
    ax.grid(alpha=0.3)


def rys_lamana(p, q, P, Q, stopien, plik):
    """Łamana p_1 -> ... -> p_m i jej obraz przez F (krzywa przez q_1, ..., q_m)."""
    f1 = sp.lambdify((x, y), P.as_expr(), "numpy")
    f2 = sp.lambdify((x, y), Q.as_expr(), "numpy")
    X, Y, t = lamana(p)
    with np.errstate(all="ignore"):
        U = np.asarray(f1(X, Y), dtype=float) + 0 * t
        V = np.asarray(f2(X, Y), dtype=float) + 0 * t
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.6))
    lo, hi = ramka(p, 0.15)
    krzywa(a1, X, Y, t, lo, hi)
    punkty(a1, p, KOLOR_P, "o", "$p_i$")
    kadr(a1, lo, hi)
    vlo, vhi = ramka(q, 0.6)
    if krzywa(a2, U, V, t, vlo, vhi):
        a2.text(0.02, 0.02, "krzywa wychodzi poza kadr", transform=a2.transAxes, fontsize=8, color="0.4")
    punkty(a2, q, KOLOR_Q, "s", "$q_i = F(p_i)$")
    kadr(a2, vlo, vhi)
    a1.set_title("przed: łamana $p_1\\to p_2\\to\\dots$")
    a2.set_title(f"po: jej obraz przez $F$ (stopień {stopien})")
    for a in (a1, a2):
        a.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(plik)
    plt.close(fig)


def czynnik_num(c):
    """Czynnik słowa jako funkcja numeryczna (X, Y) -> (X', Y') i krótki opis."""
    if c["typ"] == "afiniczne":
        A = np.array([[float(wymierna(v)) for v in w] for w in c["A"]])
        t = np.array([float(wymierna(v)) for v in c.get("t", [0, 0])])
        return (lambda X, Y: (A[0, 0] * X + A[0, 1] * Y + t[0], A[1, 0] * X + A[1, 1] * Y + t[1]),
                "afiniczne")
    if c["zmienia"] == "y":
        f = sp.lambdify(x, wyrazenie(c["f"], (x,)), "numpy")
        st = sp.degree(wyrazenie(c["f"], (x,)), x)
        return (lambda X, Y: (X, Y + f(X) + 0 * X)), f"$(x,\\ y+f(x))$, st. {st}"
    f = sp.lambdify(y, wyrazenie(c["f"], (y,)), "numpy")
    st = sp.degree(wyrazenie(c["f"], (y,)), y)
    return (lambda X, Y: (X + f(Y) + 0 * Y, Y)), f"$(x+f(y),\\ y)$, st. {st}"


def zmiany(numery):
    return ", ".join(f"$\\varphi_{{{k}}}$" for k in numery)


def rys_czynniki(p, q, rozw, plik):
    """Kolejne czynniki trójkątne słowa: jak punkty i łamana przechodzą przez każde ścinanie.

    Czynniki afiniczne to tylko zmiana układu współrzędnych: stosujemy je bez osobnego panelu,
    więc strzałki w każdym panelu są pionowe albo poziome."""
    X, Y, t = lamana(p)
    pts = np.array(p, dtype=float)
    stan = (X, Y, pts[:, 0], pts[:, 1])
    panele = [(stan, None, "start: $p_i$")]  # (stan, położenia przed krokiem, tytuł)
    afiniczne = []
    with np.errstate(all="ignore"):
        for k, c in enumerate(rozw["czynniki"], start=1):
            fun, opis = czynnik_num(c)
            nowy = tuple(np.asarray(v, float) for v in (*fun(stan[0], stan[1]), *fun(stan[2], stan[3])))
            if c["typ"] == "afiniczne":
                afiniczne.append(k)
            else:
                po = f" (po zmianie układu {zmiany(afiniczne)})" if afiniczne else ""
                panele.append((nowy, (stan[2], stan[3]), f"$\\varphi_{{{k}}}$: {opis}{po}"))
                afiniczne = []
            stan = nowy
    if afiniczne:
        panele.append((stan, None, f"zmiana układu {zmiany(afiniczne)}"))
    n = len(panele)
    kol = min(n, 4)
    wier = (n + kol - 1) // kol
    fig, osie = plt.subplots(wier, kol, figsize=(3.3 * kol, 3.5 * wier), squeeze=False)
    for idx, a in enumerate(osie.flat):
        if idx >= n:
            a.axis("off")
            continue
        (X, Y, px, py), przed, tytul = panele[idx]
        teraz = list(zip(px, py))
        lo, hi = ramka(teraz + (list(zip(*przed)) if przed else []), 0.25)
        if przed:
            for u, v, u2, v2 in zip(*przed, px, py):
                a.scatter([u], [v], s=40, facecolors="none", edgecolors="0.6", zorder=4)
                a.annotate("", (u2, v2), (u, v), arrowprops=dict(arrowstyle="->", color="0.45", lw=1))
        if krzywa(a, X, Y, t, lo, hi):
            a.text(0.02, 0.02, "poza kadrem", transform=a.transAxes, fontsize=7, color="0.4")
        ostatni = idx == n - 1
        punkty(a, teraz, KOLOR_Q if ostatni else KOLOR_P, "s" if ostatni else "o", None)
        a.set_xlim(lo[0], hi[0])
        a.set_ylim(lo[1], hi[1])
        a.set_box_aspect(1)
        a.grid(alpha=0.3)
        a.set_title(tytul + (": $q_i$" if ostatni else ""), fontsize=8.5, wrap=True)
        a.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(plik)
    plt.close(fig)


def rys_postep(historia, ograniczenie, plik):
    pts = []
    with open(historia) as f:
        for wiersz in csv.reader(f):
            if len(wiersz) == 2 and wiersz[1].strip().isdigit():
                pts.append((int(wiersz[0]), int(wiersz[1])))
    if not pts:
        return
    fig, ax = plt.subplots(figsize=(6, 3.2))
    t, d = zip(*pts)
    ax.step(t, d, where="post", color=KOLOR_Q, lw=2, marker="o")
    ax.axhline(ograniczenie, ls="--", color="0.5", label=f"znane ograniczenie $(m-1)^2={ograniczenie}$")
    ax.set_xlabel("minuta eksperymentu")
    ax.set_ylabel("najniższy zweryfikowany stopień")
    ax.set_ylim(0, ograniczenie + 2)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    fig.savefig(plik)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--katalog", default=".")
    args = ap.parse_args()
    k = args.katalog
    gen = os.path.join(k, "raport", "gen")
    os.makedirs(gen, exist_ok=True)
    p, q = wczytaj_zadanie(os.path.join(k, "zadanie.json"))
    rys_bijekcja(p, q, os.path.join(gen, "bijekcja.pdf"))
    sciezka = os.path.join(k, "stan", "zweryfikowane.json")
    if not os.path.exists(sciezka):
        return
    with open(sciezka) as f:
        stan = json.load(f)
    if stan.get("najlepszy_plik"):
        with open(os.path.join(k, stan["najlepszy_plik"])) as f:
            rozw = json.load(f)
        P, Q, _ = odwzorowanie(rozw)
        rys_lamana(p, q, P, Q, stan["najlepszy_stopien"], os.path.join(gen, "najlepsze.pdf"))
        if rozw.get("postac", "slowo") == "slowo":
            try:
                rys_czynniki(p, q, rozw, os.path.join(gen, "czynniki.pdf"))
            except Exception as e:  # rysunek pomocniczy nie może zatrzymać pozostałych
                print("rysunek czynników pominięty:", e)
    historia = os.path.join(k, "stan", "historia.csv")
    if os.path.exists(historia):
        rys_postep(historia, stan["ograniczenie_znane"], os.path.join(gen, "postep.pdf"))


if __name__ == "__main__":
    main()
