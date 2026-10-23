#!/usr/bin/env python3
"""Generuje deterministyczne części raportu (raport/gen/*.tex) z plików stanu.

Liczby w tych częściach pochodzą wyłącznie z weryfikatora i z zapisów zarządcy,
nie z tekstów pisanych przez agentów.
"""
import argparse
import csv
import json
import os
import time

import sympy as sp

from verify import odwzorowanie, wczytaj_zadanie, wymierna, wyrazenie, x, y

ZNAKI = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
         "#": r"\#", "^": r"\^{}", "_": r"\_", "%": r"\%", "~": r"\~{}"}
# Znaki matematyczne z tekstów agentów (tytuły zadań, opisy); bez tego pdflatex się wywraca.
MATEMATYCZNE = {"≤": r"\le", "≥": r"\ge", "≠": r"\ne", "→": r"\to", "↦": r"\mapsto",
                "⇒": r"\Rightarrow", "∘": r"\circ", "∈": r"\in", "∉": r"\notin", "∩": r"\cap",
                "∪": r"\cup", "∖": r"\setminus", "√": r"\surd", "·": r"\cdot", "×": r"\times",
                "⋯": r"\cdots", "−": "-", "±": r"\pm", "≈": r"\approx", "∞": r"\infty",
                "²": "^2", "³": "^3", "¹": "^1", "⁻": "^-", "σ": r"\sigma", "τ": r"\tau",
                "φ": r"\varphi", "ω": r"\omega", "α": r"\alpha", "β": r"\beta", "γ": r"\gamma",
                "δ": r"\delta", "λ": r"\lambda", "π": r"\pi", "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}"}
TEKSTOWE = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ–—„”“’…§äöüéÄÖÜ")


def znak(c):
    if c in ZNAKI:
        return ZNAKI[c]
    if c in MATEMATYCZNE:
        return rf"\ensuremath{{{MATEMATYCZNE[c]}}}"
    return c if c.isascii() or c in TEKSTOWE else "?"


def tex(s):
    return "".join(znak(c) for c in str(s))


def L(e):
    return sp.latex(e)


def czynnik_tex(c):
    if c["typ"] == "afiniczne":
        A = [[wymierna(v) for v in w] for w in c["A"]]
        t = [wymierna(v) for v in c.get("t", [0, 0])]
        u = A[0][0] * x + A[0][1] * y + t[0]
        v = A[1][0] * x + A[1][1] * y + t[1]
        return rf"(x,y)\mapsto\left({L(u)},\ {L(v)}\right)"
    if c["zmienia"] == "y":
        f = wyrazenie(c["f"], (x,))
        return rf"(x,y)\mapsto\left(x,\ y + \left({L(f)}\right)\right)"
    f = wyrazenie(c["f"], (y,))
    return rf"(x,y)\mapsto\left(x + \left({L(f)}\right),\ y\right)"


def gen_zadanie(p, q):
    m = len(p)
    w = [r"\subsection*{Dane eksperymentu}",
         rf"Liczba punktów $m={m}$; znane ograniczenie górne na minimalny stopień: $(m-1)^2={(m - 1) ** 2}$.",
         r"\begin{center}\begin{tabular}{ccc}\toprule $i$ & $p_i$ & $q_i$\\\midrule"]
    for i, (a, b) in enumerate(zip(p, q), start=1):
        w.append(rf"{i} & $({L(a[0])},\ {L(a[1])})$ & $({L(b[0])},\ {L(b[1])})$\\")
    w.append(r"\bottomrule\end{tabular}\end{center}")
    w.append(r"\IfFileExists{gen/bijekcja.pdf}{\begin{figure}[h!]\centering"
             r"\includegraphics[width=0.55\textwidth]{gen/bijekcja.pdf}"
             r"\caption{Zadana bijekcja $p_i\mapsto q_i$.}\end{figure}}{}")
    return "\n".join(w)


def gen_wyniki(k, stan):
    if not stan or not stan.get("najlepszy_plik"):
        return "Na tym etapie nie ma jeszcze zweryfikowanych rozwiązań.\n"
    dobre = [r for r in stan["rozwiazania"] if r["ok"]]
    zle = [r for r in stan["rozwiazania"] if not r["ok"]]
    d = stan["najlepszy_stopien"]
    w = [rf"Najniższy stopień automorfizmu przyjętego przez niezależny weryfikator: \textbf{{{d}}} "
         rf"(znane ograniczenie górne: ${stan['ograniczenie_znane']}$). "
         r"Weryfikator sprawdza dokładnie, w arytmetyce liczb wymiernych, warunki $F(p_i)=q_i$, "
         r"odwracalność (odwrotność wielomianowa o współczynnikach wymiernych) oraz stopień. "
         r"Stopień ten jest ograniczeniem \emph{górnym}; o ograniczeniach dolnych mówią "
         r"wyłącznie twierdzenia opisane w dalszych częściach raportu.",
         "",
         rf"Przyjęte rozwiązania: {len(dobre)}; odrzucone: {len(zle)}.",
         r"\begin{center}\small\begin{tabular}{rlp{5.2cm}p{5.6cm}}\toprule Stopień & Czynniki & Autor & Plik\\\midrule"]
    for r in dobre[:12]:
        st = r"$\cdot$".join(map(str, r.get("stopnie_czynnikow", []))) or "--"
        w.append(rf"{r['stopien']} & {st} & {tex(r.get('autor', '')[:70])} & \texttt{{{tex(r['plik']).replace('/', '/' + chr(92) + 'allowbreak{}')}}}\\")
    w.append(r"\bottomrule\end{tabular}\end{center}")
    if zle:
        w.append(r"\paragraph{Odrzucone zgłoszenia.} Weryfikator odrzucił następujące pliki:")
        w.append(r"\begin{itemize}\small")
        for r in zle[:10]:
            w.append(rf"\item \texttt{{{tex(r['plik'])}}}: {tex('; '.join(r['bledy'])[:220])}")
        w.append(r"\end{itemize}")

    with open(os.path.join(k, stan["najlepszy_plik"])) as f:
        rozw = json.load(f)
    w.append(r"\subsection*{Najlepsze znalezione odwzorowanie}")
    if rozw.get("opis"):
        w.append(tex(rozw["opis"]))
    if rozw.get("postac", "slowo") == "slowo":
        w.append(r"\noindent $F = \varphi_n\circ\dots\circ\varphi_1$, gdzie (w kolejności działania):")
        w.append(r"\begin{align*}")
        w.append(r"\\".join(rf"\varphi_{{{i}}}&\colon {czynnik_tex(c)}" for i, c in enumerate(rozw["czynniki"], 1)))
        w.append(r"\end{align*}")
    P, Q, _ = odwzorowanie(rozw)
    if len(P.terms()) + len(Q.terms()) <= 120:
        w.append(r"Postać rozwinięta:")
        w.append(r"\begin{flushleft}\small")
        w.append(rf"$F_1(x,y) = {L(P.as_expr())}$\par\medskip")
        w.append(rf"$F_2(x,y) = {L(Q.as_expr())}$")
        w.append(r"\end{flushleft}")
    else:
        w.append(rf"Postać rozwinięta ma {len(P.terms()) + len(Q.terms())} wyrazów; "
                 r"podajemy ją tylko w pliku źródłowym rozwiązania.")
    w.append(r"\IfFileExists{gen/najlepsze.pdf}{\begin{figure}[h!]\centering"
             r"\includegraphics[width=\textwidth]{gen/najlepsze.pdf}"
             r"\caption{Łamana $p_1\to\dots\to p_m$ (lewa) i jej obraz przez najlepsze znalezione $F$ "
             r"(prawa); barwa wskazuje położenie wzdłuż łamanej.}\end{figure}}{}")
    w.append(r"\IfFileExists{gen/czynniki.pdf}{\begin{figure}[h!]\centering"
             r"\includegraphics[width=\textwidth]{gen/czynniki.pdf}"
             r"\caption{Działanie kolejnych czynników $\varphi_k$ najlepszego $F$ na punkty i łamaną. "
             r"Czynnik trójkątny przesuwa punkty tylko pionowo albo tylko poziomo; "
             r"każdy panel ma własny kadr.}\end{figure}}{}")
    w.append(r"\IfFileExists{gen/postep.pdf}{\begin{figure}[h!]\centering"
             r"\includegraphics[width=0.7\textwidth]{gen/postep.pdf}"
             r"\caption{Najniższy zweryfikowany stopień w kolejnych minutach eksperymentu.}\end{figure}}{}")
    return "\n".join(w) + "\n"


def gen_kulisy(k):
    wiersze = []
    sciezka = os.path.join(k, "stan", "agenci.tsv")
    if os.path.exists(sciezka):
        with open(sciezka) as f:
            wiersze = list(csv.reader(f, delimiter="\t"))
    w = [r"\section{Kulisy eksperymentu}",
         r"Raport powstał bez udziału człowieka w trakcie pracy. Skrypt-zarządca pilnował czasu "
         r"i w każdej iteracji uruchamiał: agenta-planistę (wybór kierunków), kilku niezależnych "
         r"agentów-wykonawców (każdy w osobnym katalogu, z twardym limitem czasu), niezależny "
         r"weryfikator (program przygotowany przed startem, którego agenci nie mogli zmienić) "
         r"oraz agenta-redaktora tekstu. Po każdej iteracji raport był składany i publikowany.",
         ""]
    if not wiersze:
        return "\n".join(w) + "\n"
    opis_kodu = {"0": "zakończył", "124": "limit czasu", "137": "limit czasu"}
    w.append(r"\begin{center}\small\begin{longtable}{rlp{6.2cm}rlr}\toprule "
             r"Iter. & Rola & Zadanie & Min. & Koniec & Koszt [USD]\\\midrule\endhead")
    suma = 0.0
    for r in wiersze:
        if len(r) < 9:
            continue
        nazwa, rola, it, start, koniec, kod, koszt, tury, tytul = r[:9]
        try:
            minuty = (int(koniec) - int(start)) / 60
            suma += float(koszt)
        except ValueError:
            minuty = 0
        w.append(rf"{tex(it)} & {tex(rola)} & {tex(tytul[:120])} & {minuty:.1f} & "
                 rf"{opis_kodu.get(kod, 'kod ' + tex(kod))} & {float(koszt or 0):.2f}\\")
    w.append(r"\bottomrule\end{longtable}\end{center}")
    w.append(rf"Łączny koszt obliczeń modelu (według raportów narzędzia): {suma:.2f} USD. "
             r"Skrót SHA-256 weryfikatora: \texttt{\hashWeryfikatora}.")
    return "\n".join(w) + "\n"


def gen_meta(k, stan_raportu, stan):
    start = os.path.join(k, "stan", "start_epoch")
    t0 = int(open(start).read()) if os.path.exists(start) else int(time.time())
    minuty = (int(time.time()) - t0) // 60
    hashw = open(os.path.join(k, "stan", "hash_weryfikatora")).read().strip() \
        if os.path.exists(os.path.join(k, "stan", "hash_weryfikatora")) else "?"
    najl = stan.get("najlepszy_stopien") if stan else None
    autor = os.environ.get("AUTOR", "")
    return "\n".join([
        rf"\newcommand{{\stanRaportu}}{{{tex(stan_raportu)}}}",
        rf"\newcommand{{\dataEksperymentu}}{{{time.strftime('%d.%m.%Y, %H:%M', time.localtime(t0))}}}",
        rf"\newcommand{{\czasEksperymentu}}{{{minuty}}}",
        rf"\newcommand{{\najlepszyStopien}}{{{najl if najl is not None else '--'}}}",
        rf"\newcommand{{\autorEksperymentu}}{{{tex(autor)}}}",
        rf"\newcommand{{\hashWeryfikatora}}{{{tex(hashw)}}}",
    ]) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--katalog", default=".")
    ap.add_argument("--stan", default="wersja robocza")
    args = ap.parse_args()
    k = args.katalog
    gen = os.path.join(k, "raport", "gen")
    os.makedirs(gen, exist_ok=True)
    p, q = wczytaj_zadanie(os.path.join(k, "zadanie.json"))
    stan = None
    sz = os.path.join(k, "stan", "zweryfikowane.json")
    if os.path.exists(sz):
        with open(sz) as f:
            stan = json.load(f)
    pliki = {
        "meta.tex": gen_meta(k, args.stan, stan),
        "zadanie.tex": gen_zadanie(p, q),
        "wyniki.tex": gen_wyniki(k, stan),
        "kulisy.tex": gen_kulisy(k),
    }
    for nazwa, tresc in pliki.items():
        with open(os.path.join(gen, nazwa), "w") as f:
            f.write(tresc)


if __name__ == "__main__":
    main()
