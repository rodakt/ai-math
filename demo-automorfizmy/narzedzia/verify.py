#!/usr/bin/env python3
"""Niezależny weryfikator rozwiązań.

Zarządca (run.sh) uruchamia kopię tego pliku zrobioną przed startem
eksperymentu, więc agenci nie mogą zmienić tego, co sprawdza.

Sprawdzane jest, że:
  * wszystkie współczynniki są wymierne, a składowe są wielomianami od x, y;
  * odwzorowanie jest odwracalne z odwrotnością wielomianową
    (postać "slowo": każdy czynnik jest afiniczny z wyznacznikiem != 0 albo
    trójkątny, więc odwrotność istnieje z konstrukcji; postać "jawna":
    sprawdzane G(F) = id oraz F(G) = id);
  * F(p_i) = q_i dokładnie, dla każdego i;
  * stopień F = maksimum stopni całkowitych składowych.

Użycie:
  verify.py sprawdz --zadanie zadanie.json PLIK.json
  verify.py zbierz  --zadanie zadanie.json --praca praca --wyjscie stan/zweryfikowane.json
"""
import argparse
import glob
import hashlib
import json
import os
import signal
import sys
import time

import sympy as sp
from sympy import QQ, Poly

x, y = sp.symbols("x y")
LIMIT_SEKUND = 180


def wymierna(v):
    w = sp.Rational(str(v).strip())
    if not w.is_Rational:
        raise ValueError(f"to nie jest liczba wymierna: {v!r}")
    return w


def wyrazenie(s, dozwolone):
    e = sp.sympify(str(s), locals={"x": x, "y": y}, rational=True)
    nadmiar = e.free_symbols - set(dozwolone)
    if nadmiar:
        raise ValueError(f"niedozwolone zmienne {sorted(map(str, nadmiar))} w {s!r}")
    return e


def wielomian2(s):
    return Poly(wyrazenie(s, (x, y)), x, y, domain=QQ)


def horner(wsp, P):
    """f(P) dla f o współczynnikach wsp (od najwyższej potęgi)."""
    wynik = Poly(0, x, y, domain=QQ)
    for c in wsp:
        wynik = wynik * P + c
    return wynik


def podstaw(H, P, Q):
    """H(P, Q) dla H, P, Q wielomianów od x, y."""
    wynik = Poly(0, x, y, domain=QQ)
    if H.is_zero:
        return wynik
    st_y = max(j for (_, j) in H.monoms())
    potegi_Q = [Poly(1, x, y, domain=QQ)]
    for _ in range(st_y):
        potegi_Q.append(potegi_Q[-1] * Q)
    st_x = max(i for (i, _) in H.monoms())
    wsp_x = [Poly(0, x, y, domain=QQ) for _ in range(st_x + 1)]
    for (i, j), c in H.terms():
        wsp_x[i] = wsp_x[i] + potegi_Q[j] * c
    for i in range(st_x, -1, -1):
        wynik = wynik * P + wsp_x[i]
    return wynik


def zastosuj(czynnik, P, Q):
    """Zwraca (czynnik)(P, Q) oraz stopień czynnika."""
    typ = czynnik.get("typ")
    if typ == "afiniczne":
        A = [[wymierna(v) for v in wiersz] for wiersz in czynnik["A"]]
        t = [wymierna(v) for v in czynnik.get("t", [0, 0])]
        if len(A) != 2 or any(len(w) != 2 for w in A) or len(t) != 2:
            raise ValueError("czynnik afiniczny: A musi być 2x2, t długości 2")
        if A[0][0] * A[1][1] - A[0][1] * A[1][0] == 0:
            raise ValueError("czynnik afiniczny ma wyznacznik 0 (nieodwracalny)")
        return P * A[0][0] + Q * A[0][1] + t[0], P * A[1][0] + Q * A[1][1] + t[1], 1
    if typ == "trojkatne":
        zm = czynnik.get("zmienia")
        if zm == "y":  # (x, y) -> (x, y + f(x))
            f = Poly(wyrazenie(czynnik["f"], (x,)), x, domain=QQ)
            return P, Q + horner(f.all_coeffs(), P), max(f.degree(), 1)
        if zm == "x":  # (x, y) -> (x + f(y), y)
            f = Poly(wyrazenie(czynnik["f"], (y,)), y, domain=QQ)
            return P + horner(f.all_coeffs(), Q), Q, max(f.degree(), 1)
        raise ValueError('czynnik trójkątny: pole "zmienia" musi być "x" albo "y"')
    raise ValueError(f"nieznany typ czynnika: {typ!r}")


def wczytaj_zadanie(sciezka):
    with open(sciezka) as f:
        z = json.load(f)
    p = [tuple(wymierna(v) for v in pt) for pt in z["punkty_p"]]
    q = [tuple(wymierna(v) for v in pt) for pt in z["punkty_q"]]
    if len(p) != len(q) or len(set(p)) != len(p) or len(set(q)) != len(q):
        raise ValueError("zadanie.json: punkty muszą być parami różne, po tyle samo")
    return p, q


def odwzorowanie(rozw):
    """Zwraca (P, Q, stopnie_czynnikow) z pliku rozwiązania; rzuca ValueError przy błędzie."""
    postac = rozw.get("postac", "slowo")
    if postac == "slowo":
        P = Poly(x, x, y, domain=QQ)
        Q = Poly(y, x, y, domain=QQ)
        stopnie = []
        czynniki = rozw.get("czynniki")
        if not czynniki:
            raise ValueError("postać 'slowo' wymaga niepustej listy 'czynniki'")
        for c in czynniki:  # pierwszy czynnik działa pierwszy
            P, Q, st = zastosuj(c, P, Q)
            if c.get("typ") == "trojkatne" and st >= 2:
                stopnie.append(st)
        return P, Q, stopnie
    if postac == "jawna":
        F = [wielomian2(s) for s in rozw["F"]]
        G = [wielomian2(s) for s in rozw["G"]]
        if len(F) != 2 or len(G) != 2:
            raise ValueError("F i G muszą mieć po dwie składowe")
        X = Poly(x, x, y, domain=QQ)
        Y = Poly(y, x, y, domain=QQ)
        if [podstaw(g, *F) for g in G] != [X, Y]:
            raise ValueError("G(F(x,y)) != (x,y): G nie jest odwrotnością F")
        if [podstaw(f, *G) for f in F] != [X, Y]:
            raise ValueError("F(G(x,y)) != (x,y): G nie jest odwrotnością F")
        return F[0], F[1], []
    raise ValueError(f"nieznana postać: {postac!r}")


class Przekroczono(Exception):
    pass


def _alarm(*_):
    raise Przekroczono()


def sprawdz(sciezka_zad, sciezka_rozw):
    t0 = time.time()
    wynik = {"plik": sciezka_rozw, "ok": False, "stopien": None, "bledy": []}
    try:
        with open(sciezka_rozw) as f:
            rozw = json.load(f)
        wynik["autor"] = str(rozw.get("autor", ""))
        wynik["opis"] = str(rozw.get("opis", ""))[:500]
        p, q = wczytaj_zadanie(sciezka_zad)
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(LIMIT_SEKUND)
        try:
            P, Q, stopnie = odwzorowanie(rozw)
        finally:
            signal.alarm(0)
        wynik["stopien"] = max(P.total_degree(), Q.total_degree())
        wynik["stopnie_czynnikow"] = stopnie
        for i, (pi, qi) in enumerate(zip(p, q), start=1):
            obraz = (P(*pi), Q(*pi))
            if obraz != qi:
                wynik["bledy"].append(f"F(p{i}) = ({obraz[0]}, {obraz[1]}), a powinno być ({qi[0]}, {qi[1]})")
        wynik["ok"] = not wynik["bledy"]
        if wynik["ok"]:
            wynik["F"] = [str(P.as_expr()), str(Q.as_expr())]
            wynik["liczba_wyrazow"] = len(P.terms()) + len(Q.terms())
    except Przekroczono:
        wynik["bledy"].append(f"weryfikacja przekroczyła {LIMIT_SEKUND} s")
    except Exception as e:  # każdy błąd danych = odrzucenie
        wynik["bledy"].append(f"{type(e).__name__}: {e}")
    wynik["czas_weryfikacji_s"] = round(time.time() - t0, 2)
    return wynik


def zbierz(sciezka_zad, katalog_praca, wyjscie):
    poprzednie = {}
    if os.path.exists(wyjscie):
        try:
            with open(wyjscie) as f:
                for r in json.load(f).get("rozwiazania", []):
                    poprzednie[r["sha256"]] = r
        except Exception:
            pass
    pliki = sorted(glob.glob(os.path.join(katalog_praca, "**", "rozwiazanie*.json"), recursive=True))
    pliki = [p for p in pliki if "tmp" not in os.path.relpath(p, katalog_praca).split(os.sep)]
    wyniki = []
    for plik in pliki:
        with open(plik, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        if sha in poprzednie and poprzednie[sha]["plik"] == plik:
            wyniki.append(poprzednie[sha])
            continue
        r = sprawdz(sciezka_zad, plik)
        r["sha256"] = sha
        r["zauwazono"] = time.strftime("%H:%M:%S")
        print(f"{'OK ' if r['ok'] else 'ODRZUCONE'} {plik} stopień={r['stopien']} {'; '.join(r['bledy'])[:200]}")
        wyniki.append(r)
    dobre = [r for r in wyniki if r["ok"]]
    dobre.sort(key=lambda r: (r["stopien"], r.get("liczba_wyrazow", 0)))
    p, _ = wczytaj_zadanie(sciezka_zad)
    m = len(p)
    stan = {
        "m": m,
        "ograniczenie_znane": (m - 1) ** 2,
        "najlepszy_stopien": dobre[0]["stopien"] if dobre else None,
        "najlepszy_plik": dobre[0]["plik"] if dobre else None,
        "liczba_zaakceptowanych": len(dobre),
        "liczba_odrzuconych": len(wyniki) - len(dobre),
        "rozwiazania": dobre + [r for r in wyniki if not r["ok"]],
    }
    os.makedirs(os.path.dirname(wyjscie) or ".", exist_ok=True)
    tmp = wyjscie + ".tmp"
    with open(tmp, "w") as f:
        json.dump(stan, f, ensure_ascii=False, indent=1)
    os.replace(tmp, wyjscie)
    print(f"Zaakceptowane: {len(dobre)}, odrzucone: {len(wyniki) - len(dobre)}, "
          f"najlepszy stopień: {stan['najlepszy_stopien']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sprawdz")
    a.add_argument("--zadanie", default="zadanie.json")
    a.add_argument("plik")
    b = sub.add_parser("zbierz")
    b.add_argument("--zadanie", default="zadanie.json")
    b.add_argument("--praca", default="praca")
    b.add_argument("--wyjscie", default="stan/zweryfikowane.json")
    args = ap.parse_args()
    if args.cmd == "sprawdz":
        r = sprawdz(args.zadanie, args.plik)
        r.pop("F", None)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r["ok"] else 1)
    zbierz(args.zadanie, args.praca, args.wyjscie)


if __name__ == "__main__":
    main()
