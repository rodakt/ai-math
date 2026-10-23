ROLA: redaktor raportu ({{ITER}}). Stan raportu: {{STAN}}.

Zasady i opis problemu są w CLAUDE.md. Raport (`raport/raport.tex`) składa się z części
generowanych automatycznie (`raport/gen/*.tex`: dane, tabela wyników z weryfikatora, rysunki,
kulisy — tylko ich nie edytuj, ale przeczytaj) oraz z sekcji, które piszesz ty:
`raport/sekcje/wstep.tex` (już istnieje; popraw tylko w razie potrzeby), `metoda.tex`,
`przebieg.tex`, `wnioski.tex`, opcjonalnie `literatura.tex` (środowisko thebibliography){{KONCOWA}}.

Źródła: `stan/dziennik.md`, `stan/zweryfikowane.json`, `stan/plan_iter*.json`,
`praca/iter*/zad*/{wynik.json,notatki.md}`.

Wymagania:
- Styl profesjonalnej notatki matematycznej po polsku: definicje, stwierdzenia, dowody lub
  szkice dowodów (środowiska `twierdzenie`, `lemat`, `stwierdzenie`, `uwaga`, `hipoteza`,
  `proof`), opis metod obliczeniowych na tyle dokładny, by dało się je powtórzyć.
- `metoda.tex` zaczyna się od `\section{Metoda}`, `przebieg.tex` od `\section{Przebieg
  eksperymentu}`, `wnioski.tex` od `\section{Wnioski i pytania otwarte}`.
- Każde twierdzenie opatrz statusem zgodnie z CLAUDE.md (ZWERYFIKOWANE / UDOWODNIONE /
  OBLICZENIOWE / HIPOTEZA) — w tekście wprost, np. „(wynik obliczeniowy, zob. …)”. Stopnie
  osiągnięte podawaj wyłącznie zgodnie ze `stan/zweryfikowane.json`.
- Nie wymyślaj wyników. Jeśli coś jest niejasne albo niesprawdzone, napisz to.
- Sekcje mają być spójne z aktualnym stanem: przepisuj je, a nie tylko dopisuj.
- Sprawdź kompilację: `cd raport && latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=tmp_red raport.tex`
  i popraw błędy; potem usuń katalog `raport/tmp_red`.
- Dopisz na końcu `stan/dziennik.md` jedno-dwuzdaniowy wpis `## Raport — {{ITER}}`.
