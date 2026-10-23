#!/usr/bin/env python3
"""Znana konstrukcja ze stopniem <= (m-1)^2 (siatka bezpieczeństwa, bez udziału agentów).

F = A ∘ T2 ∘ T1 ∘ B, gdzie
  B  = (x + k y, y)        dobrane tak, by pierwsze współrzędne B(p_i) były różne,
  A⁻¹ = (x, y + k' x)      dobrane tak, by drugie współrzędne A⁻¹(q_i) były różne,
  T1 = (x, y + a(x))       a interpoluje różnice drugich współrzędnych (deg a <= m-1),
  T2 = (x + b(y), y)       b interpoluje różnice pierwszych współrzędnych (deg b <= m-1).
"""
import argparse
import json
import os

import sympy as sp

from verify import wczytaj_zadanie

x, y = sp.symbols("x y")


def pierwsze_k(punkty, wsp):
    for k in range(0, 1000):
        if len({wsp(pt, k) for pt in punkty}) == len(punkty):
            return k
    raise RuntimeError("nie znaleziono ścinania")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zadanie", default="zadanie.json")
    ap.add_argument("--wyjscie", required=True)
    args = ap.parse_args()
    p, q = wczytaj_zadanie(args.zadanie)
    m = len(p)

    k = pierwsze_k(p, lambda pt, k: pt[0] + k * pt[1])
    pB = [(a + k * b, b) for a, b in p]
    k2 = pierwsze_k(q, lambda pt, k: pt[1] + k * pt[0])
    qA = [(a, b + k2 * a) for a, b in q]

    a_x = sp.expand(sp.interpolate([(pB[i][0], qA[i][1] - pB[i][1]) for i in range(m)], x))
    b_y = sp.expand(sp.interpolate([(qA[i][1], qA[i][0] - pB[i][0]) for i in range(m)], y))

    rozw = {
        "autor": "konstrukcja bazowa (skrypt przygotowany przed eksperymentem)",
        "opis": f"Złożenie dwóch odwzorowań trójkątnych stopni {sp.degree(a_x, x)} i {sp.degree(b_y, y)} "
                f"z interpolacji Lagrange'a, otoczone ścinaniami; stopień nie przekracza (m-1)^2 = {(m - 1) ** 2}.",
        "postac": "slowo",
        "czynniki": [
            {"typ": "afiniczne", "A": [[1, k], [0, 1]], "t": [0, 0]},
            {"typ": "trojkatne", "zmienia": "y", "f": str(a_x)},
            {"typ": "trojkatne", "zmienia": "x", "f": str(b_y)},
            {"typ": "afiniczne", "A": [[1, 0], [-k2, 1]], "t": [0, 0]},
        ],
    }
    rozw["czynniki"] = [c for c in rozw["czynniki"]
                        if not (c["typ"] == "afiniczne" and c["A"] == [[1, 0], [0, 1]])]
    os.makedirs(os.path.dirname(args.wyjscie), exist_ok=True)
    with open(args.wyjscie, "w") as f:
        json.dump(rozw, f, ensure_ascii=False, indent=1)
    with open(os.path.join(os.path.dirname(args.wyjscie), "wynik.json"), "w") as f:
        json.dump({"status": "rozwiazanie",
                   "podsumowanie": rozw["opis"],
                   "twierdzenia": [],
                   "najlepszy_stopien": None}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
