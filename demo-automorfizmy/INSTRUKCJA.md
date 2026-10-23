# Demo na wykład: autonomiczny eksperyment w tle

Agenci Claude Code przez ~38 minut szukają automorfizmu wielomianowego Q² o możliwie niskim
stopniu, rozszerzającego zadaną bijekcję 5 punktów. Po każdym etapie powstaje PDF i trafia
na GitHub. Nikt nie ingeruje w trakcie.

## Jak to działa

```
run.sh (zarządca, zwykły skrypt bash — pilnuje czasu)
 ├─ etap 0: konstrukcja bazowa stopnia ≤ (m−1)² (skrypt, bez agentów) → pierwszy PDF
 ├─ iteracja N (przy 38 min: dwie):
 │   ├─ planista (claude -p, ≤3 min): czyta dziennik, planuje 1–3 zadania
 │   ├─ wykonawcy (claude -p, równolegle, ≤12 min każdy, osobne katalogi)
 │   ├─ weryfikator (Python/sympy, kopia sprzed startu — agenci nie mogą go zmienić)
 │   └─ PDF (tabele i rysunki generowane skryptem) + commit + push
 │      [opcjonalnie REDAKCJA_POSREDNIA=1: redaktor przepisuje tekst po każdej iteracji]
 └─ redakcja końcowa (≤5–8 min, ile zostało) → PDF → push → GitHub Release z raportem
```

Liczby w tabeli wyników i rysunki pochodzą wyłącznie z weryfikatora, nie z tekstów agentów.
Twierdzenia w tekście mają etykiety ZWERYFIKOWANE / UDOWODNIONE / OBLICZENIOWE / HIPOTEZA
(zasady w `CLAUDE.md`).

| Plik | Rola |
|---|---|
| `zadanie.json` | punkty p_i, q_i — **wpisz własne przed wykładem** |
| `konfiguracja.env` | tryb (proba/wyklad), czasy, model, wysiłek, równoległość, GitHub |
| `CLAUDE.md` | zasady wspólne dla wszystkich agentów (czytane automatycznie) |
| `prompty/` | polecenia dla ról: planista, wykonawca, redaktor |
| `narzedzia/verify.py` | weryfikator (dokładna arytmetyka nad Q) |
| `wskazowki_opcjonalne.md` | moje wskazówki matematyczne; domyślnie wyłączone (`WSKAZOWKI=0`) |
| `podglad.sh` | podgląd na żywo: faza, najlepszy stopień, co robi każdy agent |
| `start.sh` | start jednym poleceniem: świeża kopia, `run.sh` w tmux z limitami, podgląd obok |

## Przygotowanie maszyny (raz)

Wszystko musi być zainstalowane wcześniej — agenci mają zakaz instalowania czegokolwiek.

1. Systemowo: `claude` (zalogowany), `git`, `latexmk` + pdflatex z pakietami `polski`
   i `lmodern`, GNU `timeout`.
2. Reszta w jednym środowisku mamba (Sage z Singularem, sympy, numpy, matplotlib, jq, gh):
   ```bash
   mamba env create -f environment.yml      # jednorazowo, kilka–kilkanaście minut
   ```
   Nie trzeba go aktywować: `konfiguracja.env` znajduje je po nazwie (`SRODOWISKO`) i dodaje
   do PATH zarządcy oraz agentów. Weryfikator celowo liczy na sympy, a agenci na Sage —
   wynik sprawdza inna biblioteka niż ta, którą go znaleziono.
3. W `konfiguracja.env` sprawdź `GH_REPO` i `AUTOR` (domyślne wartości są już wpisane); zaloguj gh raz:
   `mamba run -n demo-automorfizmy gh auth login` — protokół **HTTPS** (przy SSH push
   wymaga klucza na GitHubie), „Authenticate Git” → Yes, logowanie przez przeglądarkę.
   Jeśli gh jest już zalogowany bez tego (git push pyta o „Username”): `gh auth setup-git`.
   `start.sh` sprawdza oba logowania przed startem.
   W WSL przeglądarka się nie otworzy: kod `XXXX-XXXX` z linijki „One-time code” wpisz
   ręcznie na github.com/login/device.
4. `./sprawdz_srodowisko.sh` — na tej maszynie, na której naprawdę będzie liczone.

## Tryby: próba i wykład

`TRYB=proba` (domyślny): commity lokalne w kopii, **bez pusha** (GH_REPO jest ignorowane),
PDF i README oznaczone jako próba. `TRYB=wyklad`: push po etapach i Release na końcu.
Agenci nie wiedzą, który to tryb — zachowują się tak samo, więc próba jest miarodajna.

## Start: `start.sh`

```bash
./start.sh test        # 15 min, push do nowego repozytorium <login>/demo-test-<czas>
./start.sh wyklad      # pełny czas, push do GH_REPO (puste: <login>/demo-automorfizmy-<czas>);
                       # gdy repo już istnieje — ostrzeżenie i potwierdzenie słowem „tak”
./start.sh proba       # pełny czas, bez GitHuba
./start.sh test 20     # opcjonalnie liczba minut
```

Skrypt kopiuje ten folder do nowego `~/demo-przebiegi/<MMDD-HHMMSS>-<tryb>` (źródło zostaje
czyste, kopie nie mogą się zagnieździć), pokazuje tryb, repozytorium i folder, czeka na Enter
i uruchamia w sesji tmux `demo` okno `eksperyment` (`run.sh`) i okno `podglad`
(`podglad.sh`). Ctrl-b n — następne okno, Ctrl-b d — odłączenie (liczy dalej),
`tmux attach -t demo` — powrót. Gdzie działa `systemd --user` (WSL), `run.sh` dostaje limit
5 GB pamięci i 6 wątków; zawsze `nice -n 10`, żeby prezentacja na tej samej maszynie
nie zwalniała. Zmiany w `zadanie.json` czy `konfiguracja.env` wprowadzaj w źródle **przed**
startem — kopia powstaje w chwili uruchomienia.

## Próba generalna (co najmniej jedna, pełnej długości)

`./start.sh proba` albo `./start.sh test 38` (wtedy sprawdzisz też publikację) — **nie**
`./start.sh wyklad`, bo ten zająłby docelowe repo `GH_REPO`; w `zadanie.json`
najlepiej INNE punkty niż na wykład. Repozytoria testowe usuwa się ręcznie (Settings →
Delete) albo `gh repo delete` po `gh auth refresh -s delete_repo`.

Sprawdź: ile trwają etapy, czy wykonawcy kończą przed limitem (w tabeli „Kulisy”:
„zakończył” vs „limit czasu”), czy zostawiają sensowne `wynik.json`, ile kosztuje przebieg,
czy PDF wygląda dobrze. Kalibracja: czasy, `MAKS_WYKONAWCOW` i wysiłek (domyślnie medium
dla planisty i wykonawców, low dla redaktora). Wyższy wysiłek to dłuższe myślenie w każdym
kroku, a więc mniej kroków w limicie; czasy kroków widać w `logi/*.jsonl`.

## Na wykładzie

1. Docelowe punkty w `zadanie.json` źródła.
2. Na slajdzie 1: `./start.sh wyklad`, Enter — na komputerze **innym niż ten, który wyświetla
   slajdy** (usypianie, Wi-Fi, obciążenie).
3. Podgląd w trakcie: okno `podglad` w tmux albo strona repozytorium (README → raport.pdf);
   repozytorium jest domyślnie prywatne (`GH_WIDOCZNOSC`), więc w przeglądarce trzeba być
   zalogowanym do GitHuba.
4. Koniec przychodzi sam po `CZAS_CALKOWITY_MIN`. Wcześniejsze zakończenie z raportem
   końcowym: `touch ~/demo-przebiegi/<folder>/stan/STOP` (po bieżącym etapie) albo Ctrl-C
   w oknie `eksperyment` (od razu przerywa agentów i przechodzi do redakcji końcowej,
   ok. 5–8 min).

## Izolacja i pamięć agentów

- **Model nie uczy się z sesji.** Nie ma pamięci między rozmowami w chmurze: każde
  `claude -p` zaczyna od zera i wie tylko to, co dostanie w poleceniu i przeczyta z dysku.
- **Claude Code pamięta lokalnie**, w `~/.claude/`: zapisy sesji (`projects/<ścieżka>/*.jsonl`,
  służą do `--resume`), automatyczną pamięć projektu (`projects/<ścieżka>/memory/`, klucz to
  ścieżka katalogu) oraz globalne instrukcje `~/.claude/CLAUDE.md`, które dostaje **każda**
  sesja na tym koncie.
- Dla czystego eksperymentu uruchamiaj z osobnym katalogiem konfiguracji:
  ```bash
  export CLAUDE_CONFIG_DIR=~/.claude-demo    # pusty: brak pamięci, brak globalnego CLAUDE.md
  claude                                      # jednorazowo: zaloguj się w tej konfiguracji
  ```
  albo z osobnego konta systemowego czy kontenera.
- Najłatwiej o przeciek przez **pliki**: wyniki prób generalnych zostają w folderze,
  a agenci czytają wszystko w `praca/` i `stan/`. Dlatego na wykład zawsze świeża kopia.
- Po stronie Anthropic dane są przechowywane zgodnie z polityką konta, a przy włączonej opcji
  „pomóż ulepszać Claude” (konta Pro/Max) mogą trafić do treningu *przyszłych* modeli. To
  jednak nie jest pamięć działająca w trakcie: nie wpływa na eksperyment za tydzień.

## Bezpieczeństwo

Agenci działają z `--dangerously-skip-permissions`, czyli wykonują polecenia bez pytania.
Uruchamiaj to w kontenerze, maszynie wirtualnej albo na osobnym koncie systemowym, bez
dostępu do prywatnych plików. Token `gh` najlepiej ograniczyć do jednego repozytorium.
Jeśli `claude` odmówi pracy w tym trybie jako root, użyj zwykłego użytkownika.

## Koszt

Iteracja to 1 + `MAKS_WYKONAWCOW` sesji agenta; przy 38 minutach: 2 iteracje + redakcja
końcowa, czyli ok. 9 sesji. Rzeczywisty koszt zobaczysz w próbie generalnej (tabela
w PDF). Przy subskrypcji liczy się zużycie limitu, nie dolary.
