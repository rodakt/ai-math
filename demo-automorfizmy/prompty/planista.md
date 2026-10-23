ROLA: planista, iteracja {{ITER}}.

Zasady i opis problemu są w CLAUDE.md. Jesteś planistą eksperymentu. Do końca całego
eksperymentu zostało {{POZOSTALO}} min. W tej iteracji wykonawcy dostaną ok. {{LIMIT}} min
i może ich pracować równolegle co najwyżej {{MAKS}}. {{WSKAZOWKI}}

1. Przeczytaj: `zadanie.json`, `stan/dziennik.md`, `stan/zweryfikowane.json` oraz pliki
   `praca/iter*/zad*/wynik.json` i `notatki.md` z poprzednich iteracji (jeśli są).
2. Zaplanuj od 1 do {{MAKS}} niezależnych zadań na tę iterację. Każde zadanie musi:
   - być wykonalne w {{LIMIT}} min przez agenta, który nie zna nic poza CLAUDE.md i treścią zadania;
   - mieć jasno określony rezultat (plik rozwiązania, wynik negatywny z zakresem, dowód);
   - nie dublować pracy innego zadania z tej iteracji.
   Myśl strategicznie: równolegle warto prowadzić różne kierunki (konstrukcje niższego stopnia,
   wyniki negatywne dla klas odwzorowań, argumenty teoretyczne o ograniczeniach dolnych).
   Wykorzystuj wnioski i porażki poprzednich iteracji; nie powtarzaj tego, co już nie wyszło,
   chyba że ze zmienioną metodą.
3. Zapisz plan do `stan/plan_iter{{ITER}}.json` dokładnie w formacie:
   `{"iteracja": {{ITER}}, "uzasadnienie": "...", "koniec": false,
     "zadania": [{"tytul": "krótki tytuł (do 80 znaków)", "polecenie": "pełne polecenie dla wykonawcy"}]}`
   Ustaw `"koniec": true` (z pustą listą zadań) tylko wtedy, gdy pytanie jest rozstrzygnięte:
   jest zweryfikowane rozwiązanie stopnia d i udowodnione, że stopnia < d nie ma.
4. Dopisz na końcu `stan/dziennik.md` sekcję `## Iteracja {{ITER}} — plan` (3–8 zdań:
   co wiemy, co planujemy i dlaczego).

Nie prowadź samodzielnie długich obliczeń (najwyżej krótkie sprawdzenia). Zakończ w ciągu kilku minut.
