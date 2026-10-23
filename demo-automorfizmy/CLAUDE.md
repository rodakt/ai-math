# Eksperyment autonomiczny: rozszerzanie bijekcji do automorfizmu wielomianowego

Pracujesz w eksperymencie prowadzonym **bez udziału człowieka**. Nikt nie odpowie na pytania
— podejmuj decyzje sam i zapisuj ich uzasadnienie. Eksperyment trwa w tle podczas wykładu,
a jego wynikiem jest raport PDF opublikowany na GitHubie. Wszystkie notatki i teksty piszesz
po polsku.

## Problem

Automorfizm wielomianowy płaszczyzny Q² to odwzorowanie F = (F₁, F₂): Q² → Q², którego
składowe są wielomianami od x, y o współczynnikach **wymiernych**, mające odwrotność tej samej
postaci. Stopień: deg F = max(deg F₁, deg F₂) (stopień całkowity).

Dane (plik `zadanie.json`): parami różne punkty p₁,…,p_m i parami różne q₁,…,q_m w Q².
Szukamy automorfizmu F z F(pᵢ) = qᵢ dla wszystkich i, o **możliwie najmniejszym stopniu**.
Wiadomo, że stopień (m−1)² zawsze wystarcza (konstrukcja: dwa odwzorowania trójkątne
z interpolacji Lagrange'a, otoczone zmianami afinicznymi — patrz `narzedzia/konstrukcja_bazowa.py`).

Pytania badawcze, w kolejności ważności:
1. Jaki najniższy stopień udaje się osiągnąć dla tej bijekcji? (ograniczenie górne)
2. Czy da się **udowodnić**, że niższego stopnia nie ma? (ograniczenie dolne — w całej klasie
   automorfizmów albo jasno opisanej podklasie)

## Uczciwość twierdzeń — zasada nadrzędna

Każde twierdzenie w notatkach i raporcie ma jedną z etykiet:
- **ZWERYFIKOWANE** — rozwiązanie przyjęte przez weryfikator (tylko on nadaje tę etykietę);
- **UDOWODNIONE** — z zapisanym, sprawdzonym rozumowaniem matematycznym;
- **OBLICZENIOWE** — wynik obliczenia (np. „układ równań nie ma rozwiązań wymiernych”), z
  odtwarzalnym skryptem i dokładnie opisanym zakresem (jaką klasę odwzorowań przeszukano);
- **HIPOTEZA** — wszystko inne.

Nigdy nie pisz „minimalny stopień” bez dowodu ograniczenia dolnego; pisz „najniższy znaleziony”.
Wynik negatywny dla podklasy (np. „brak złożeń dwóch odwzorowań trójkątnych stopnia 2”) nie
jest ograniczeniem dolnym dla wszystkich automorfizmów, chyba że wykażesz, że podklasa je
wyczerpuje. Lepszy skromny prawdziwy wniosek niż efektowny fałszywy.

## Format rozwiązania

Plik `rozwiazanie*.json` (nazwa musi zaczynać się od `rozwiazanie`) w swoim katalogu roboczym.
Zalecana postać „slowo” — złożenie czynników, **pierwszy na liście działa pierwszy**:

```json
{
  "autor": "iter02/zad1",
  "opis": "krótki opis konstrukcji",
  "postac": "slowo",
  "czynniki": [
    {"typ": "afiniczne", "A": [["1", "2"], ["0", "1"]], "t": ["0", "-1/3"]},
    {"typ": "trojkatne", "zmienia": "y", "f": "x**2 - 3/2*x"},
    {"typ": "trojkatne", "zmienia": "x", "f": "5*y**3 + y"}
  ]
}
```

- `afiniczne`: (x, y) ↦ A·(x, y) + t, det A ≠ 0;
- `trojkatne`, `"zmienia": "y"`: (x, y) ↦ (x, y + f(x)), f tylko od x;
- `trojkatne`, `"zmienia": "x"`: (x, y) ↦ (x + f(y), y), f tylko od y.

Liczby i współczynniki zapisuj dokładnie (ułamki `"a/b"`), nigdy jako przybliżenia
dziesiętne. Dopuszczalna jest też postać `"postac": "jawna"` z polami `"F": [F1, F2]` i
`"G": [G1, G2]` (odwrotność) jako napisy z wielomianami od x, y.

Sprawdzenie (zrób to, zanim zgłosisz rozwiązanie):
`$PYTHON narzedzia/verify.py sprawdz --zadanie zadanie.json ŚCIEŻKA/rozwiazanie.json`

Po każdej iteracji zarządca uruchamia **własną kopię** weryfikatora na wszystkich plikach
`rozwiazanie*.json`. Do raportu jako wynik trafia tylko to, co ona przyjmie.

## Pliki

- `zadanie.json` — dane (nie zmieniaj);
- `narzedzia/` — weryfikator i generatory raportu (nie zmieniaj);
- `stan/dziennik.md` — wspólny dziennik eksperymentu (dopisuj, nie kasuj);
- `stan/zweryfikowane.json` — wynik weryfikatora (tylko do odczytu);
- `stan/plan_iterNN.json` — plany kolejnych iteracji;
- `praca/iterNN/zadK/` — katalogi wykonawców: `zadanie.md`, `notatki.md`, `wynik.json`,
  `skrypty/`, `rozwiazanie*.json`; duże pliki tymczasowe tylko w `tmp/` (nie są publikowane);
- `raport/sekcje/*.tex` — tekst raportu pisany przez redaktora; `raport/gen/` jest generowane
  automatycznie (nie edytuj).
- `wskazowki.md` — jeśli istnieje, zawiera wskazówki przygotowane przed eksperymentem; traktuj
  je jako hipotezy do sprawdzenia, nie jako fakty.

Nie wykonuj `git commit` ani `git push` — robi to zarządca. **Niczego nie instaluj**
(ani pakietów systemowych, ani Pythona) — korzystaj z tego, co jest dostępne.

## Narzędzia obliczeniowe

Do algebry używaj przede wszystkim **Sage** (`sage skrypt.sage` albo `sage -python`), jeśli jest
dostępny: bazy Gröbnera nad Q (Singular), eliminacja, rozkład ideałów, punkty wymierne.
Sprawdź na początku, co jest (`which sage Singular M2 msolve magma`). Interpreter `$PYTHON`
ma sympy — wystarczy do prostych rachunków i do weryfikatora, ale nie do ciężkiej eliminacji.
Rachunki prowadź dokładnie nad Q. Długie obliczenia uruchamiaj z `timeout` i z zapisem
częściowych wyników do pliku, nigdy w sposób, który zablokuje cię do końca limitu.
