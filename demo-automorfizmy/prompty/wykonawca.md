ROLA: wykonawca, iteracja {{ITER}}, katalog `{{KATALOG}}`.

Zasady i opis problemu są w CLAUDE.md. Twoje zadanie: **{{TYTUL}}**. Pełna treść jest
w `{{KATALOG}}/zadanie.md`. {{WSKAZOWKI}}

Masz twardy limit czasu: o godzinie **{{KONIEC_GODZ}}** (sprawdzaj `date +%H:%M`) proces
zostanie zabity bez ostrzeżenia. Wszystko, czego nie zapiszesz na dysku, przepadnie.

Zasady pracy:
- Piszesz tylko w `{{KATALOG}}/` (skrypty w `skrypty/`, duże pliki pośrednie w `tmp/`).
  Możesz czytać wszystko, w tym wyniki innych iteracji.
- Od razu utwórz `{{KATALOG}}/wynik.json` ze statusem `"w_toku"` i aktualizuj go co kilka
  minut oraz po każdym istotnym ustaleniu. Format:
  `{"status": "rozwiazanie|wynik_negatywny|bez_rozstrzygniecia|w_toku",
    "podsumowanie": "2–5 zdań po polsku",
    "najlepszy_stopien": liczba albo null,
    "twierdzenia": [{"tresc": "...", "etykieta": "UDOWODNIONE|OBLICZENIOWE|HIPOTEZA",
                     "uzasadnienie": "...", "pliki": ["skrypty/..."]}]}`
- Prowadź `{{KATALOG}}/notatki.md`: co sprawdzono, jaką metodą, z jakim wynikiem, czego nie
  zdążono. Ma z niego skorzystać następny agent i redaktor raportu.
- Każde znalezione odwzorowanie zapisz jako `{{KATALOG}}/rozwiazanie_*.json` i sprawdź
  weryfikatorem. Nie zgłaszaj plików, których weryfikator nie przyjmuje.
- Obliczenia ciężkie uruchamiaj z `timeout` krótszym niż czas, który ci został, w tle z
  zapisem postępu do pliku. Ok. 3 minuty przed końcem przerwij obliczenia i uporządkuj
  `wynik.json` oraz `notatki.md`.
- Wynik negatywny jest wartościowy, jeśli dokładnie opisuje przeszukaną klasę i daje
  odtwarzalny skrypt. Nie przypisuj mu większej ogólności, niż ma.
