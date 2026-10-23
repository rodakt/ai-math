#!/usr/bin/env bash
# Zarządca eksperymentu: pilnuje czasu, uruchamia agentów, weryfikuje, składa raport, publikuje.
# Zatrzymanie z zachowaniem raportu końcowego: Ctrl-C albo  touch stan/STOP
set -uo pipefail
KAT="$(cd "$(dirname "$0")" && pwd)"
cd "$KAT"
source ./konfiguracja.env
export GIT_TERMINAL_PROMPT=0   # push bez dostępu ma się nie udać od razu, a nie czekać na login

case "$TRYB" in
  proba) GH_REPO=""; ETYKIETA="PRÓBA — " ;;
  wyklad) ETYKIETA="" ;;
  *) echo "TRYB musi być 'proba' albo 'wyklad'"; exit 1 ;;
esac
mkdir -p stan praca logi raport/gen
START=$(date +%s)
KONIEC=$((START + CZAS_CALKOWITY_MIN * 60))
echo "$START" > stan/start_epoch
echo "$KONIEC" > stan/koniec_epoch

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a stan/przebieg.log; }
faza() { echo "$*" > stan/faza.txt; log "== $*"; }
pozostalo_min() { echo $(( (KONIEC - $(date +%s)) / 60 )); }
minuta() { echo $(( ($(date +%s) - START) / 60 )); }

# --- środowisko: bez niego nie ma rysunków ani Sage, więc nie startujemy ---
if ! "$PYTHON" -c 'import sympy, numpy, matplotlib' 2>/dev/null || ! command -v sage >/dev/null; then
  echo "Brak środowiska '$SRODOWISKO' (python z matplotlib i sage). Uruchom ./sprawdz_srodowisko.sh;"
  echo "utwórz je (mamba env create -f environment.yml) albo wskaż inne: SRODOWISKO=nazwa ./run.sh"
  exit 1
fi

# --- zaufane narzędzia: kopia sprzed startu, poza katalogiem agentów ---
ZAUFANE=$(mktemp -d)
cp narzedzia/*.py "$ZAUFANE/"
chmod -R a-w "$ZAUFANE"
trap 'chmod -R u+w "$ZAUFANE"; rm -rf "$ZAUFANE"' EXIT
sha256sum narzedzia/verify.py | cut -c1-16 > stan/hash_weryfikatora

if [ "$WSKAZOWKI" = 1 ]; then cp wskazowki_opcjonalne.md wskazowki.md; else rm -f wskazowki.md; fi
TEKST_WSK=""
[ "$WSKAZOWKI" = 1 ] && TEKST_WSK="Przeczytaj też wskazowki.md (hipotezy do sprawdzenia)."

# --- przerwanie ---
PRZERWANO=0
declare -a AKTYWNE=()
przerwij() {
  PRZERWANO=1
  log "Przerwanie: kończę bieżących agentów i przechodzę do raportu końcowego"
  for p in "${AKTYWNE[@]}"; do kill -TERM "$p" 2>/dev/null; done
}
trap przerwij INT TERM
koniec_zadany() { [ "$PRZERWANO" = 1 ] || [ -f stan/STOP ]; }

# --- git i GitHub ---
[ -d .git ] || git init -q -b main
git config user.name >/dev/null || git config user.name "eksperyment-autonomiczny"
git config user.email >/dev/null || git config user.email "eksperyment@localhost"

publikuj() {
  [ -n "$GH_REPO" ] || return 0
  timeout 120 git push -q -u origin main >/dev/null 2>&1 || log "push nieudany (kontynuuję)"
}
zapisz() {  # $1 opis, $2=wymus -> push niezależnie od PUSH_PO_ETAPIE
  git add -A >/dev/null 2>&1
  git commit -q -m "$1" >/dev/null 2>&1 || true
  if [ "$PUSH_PO_ETAPIE" = 1 ] || [ "${2:-}" = wymus ]; then publikuj; fi
}

if [ -n "$GH_REPO" ] && ! git remote get-url origin >/dev/null 2>&1; then
  if gh repo view "$GH_REPO" >/dev/null 2>&1; then
    git remote add origin "$(gh repo view "$GH_REPO" --json url -q .url).git"
  else
    gh repo create "$GH_REPO" "--$GH_WIDOCZNOSC" --source . --remote origin \
      --description "Autonomiczny eksperyment: rozszerzanie bijekcji do automorfizmu wielomianowego" \
      >/dev/null || log "Nie udało się utworzyć repozytorium $GH_REPO"
  fi
fi

cat > README.md <<EOF
# Autonomiczny eksperyment: bijekcja → automorfizm wielomianowy Q²

Ten katalog powstał w trakcie eksperymentu prowadzonego przez agentów Claude Code bez udziału
człowieka (start: $(date '+%d.%m.%Y %H:%M'), budżet czasu: ${CZAS_CALKOWITY_MIN} min${ETYKIETA:+, próba generalna}).

- **Raport:** [raport.pdf](raport.pdf) — aktualizowany po każdym etapie
- Dane: [zadanie.json](zadanie.json); zasady dla agentów: [CLAUDE.md](CLAUDE.md)
- Dziennik: [stan/dziennik.md](stan/dziennik.md); wyniki weryfikatora: [stan/zweryfikowane.json](stan/zweryfikowane.json)
- Praca agentów: [praca/](praca/); zapisy sesji: [logi/](logi/)
- Zarządca: [run.sh](run.sh); weryfikator: [narzedzia/verify.py](narzedzia/verify.py)
EOF

# --- agenci ---
wypelnij() {  # szablon wyjście KLUCZ=wartość...
  local tekst; tekst=$(<"$1"); local out=$2; shift 2
  local kv k v
  for kv in "$@"; do k=${kv%%=*}; v=${kv#*=}; tekst=${tekst//"{{$k}}"/"$v"}; done
  printf '%s\n' "$tekst" > "$out"
}

uruchom_agenta() {  # nazwa limit_min plik_promptu wysiłek  -> PID w OSTATNI_PID
  local nazwa=$1 lim=$2 prompt=$3 wys=$4
  timeout -k 30 "${lim}m" "$CLAUDE_BIN" -p "$(<"$prompt")" \
    --model "$MODEL" --effort "$wys" --dangerously-skip-permissions \
    --output-format stream-json --verbose \
    > "logi/$nazwa.jsonl" 2> "logi/$nazwa.err" < /dev/null &
  OSTATNI_PID=$!
  AKTYWNE+=("$OSTATNI_PID")
}

czekaj() {  # pid -> kod wyjścia
  local pid=$1 kod
  while :; do
    wait "$pid"; kod=$?
    kill -0 "$pid" 2>/dev/null || return "$kod"
  done
}

zanotuj_agenta() {  # nazwa rola iter start kod tytuł
  local wynik koszt tury
  wynik=$(jq -s -r 'map(select(.type=="result")) | last | "\(.total_cost_usd // 0)\t\(.num_turns // 0)"' \
    "logi/$1.jsonl" 2>/dev/null) || wynik=$'0\t0'
  [ -n "$wynik" ] && [ "$wynik" != "null" ] || wynik=$'0\t0'
  koszt=${wynik%%$'\t'*}; tury=${wynik#*$'\t'}
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$(date +%s)" "$5" "$koszt" "$tury" \
    "$(echo "$6" | tr '\t\n' '  ')" >> stan/agenci.tsv
  log "agent $1 zakończony (kod $5, koszt ${koszt} USD)"
}

agent_sekwencyjny() {  # nazwa rola iter limit prompt wysiłek tytuł
  local start; start=$(date +%s)
  uruchom_agenta "$1" "$4" "$5" "$6"
  czekaj "$OSTATNI_PID"; local kod=$?
  AKTYWNE=()
  zanotuj_agenta "$1" "$2" "$3" "$start" "$kod" "$7"
}

# --- weryfikacja i raport ---
weryfikuj() {
  timeout 900 "$PYTHON" "$ZAUFANE/verify.py" zbierz --zadanie zadanie.json --praca praca \
    --wyjscie stan/zweryfikowane.json >> stan/przebieg.log 2>&1 || log "weryfikator zgłosił problem"
  local d; d=$(jq -r '.najlepszy_stopien // "brak"' stan/zweryfikowane.json 2>/dev/null || echo brak)
  echo "$(minuta),$d" >> stan/historia.csv
  log "najlepszy zweryfikowany stopień: $d"
}

kompiluj() {
  mkdir -p raport/build
  ( cd raport && timeout 180 latexmk -pdf -interaction=nonstopmode -halt-on-error \
      -outdir=build raport.tex > build/latexmk.log 2>&1 )
}

skladaj() {  # $1 opis stanu raportu
  "$PYTHON" "$ZAUFANE/rysunki.py" --katalog . >> stan/przebieg.log 2>&1 || log "rysunki: błąd"
  "$PYTHON" "$ZAUFANE/raport_gen.py" --katalog . --stan "$ETYKIETA$1" >> stan/przebieg.log 2>&1 || log "raport_gen: błąd"
  if kompiluj; then
    cp raport/build/raport.pdf raport.pdf
  else
    log "LaTeX nie przeszedł; przywracam sekcje z poprzedniego etapu"
    git checkout HEAD -- raport/sekcje 2>/dev/null
    git clean -fdq raport/sekcje 2>/dev/null
    if kompiluj; then cp raport/build/raport.pdf raport.pdf; else log "raport nadal się nie kompiluje"; fi
  fi
}

# ================= etap 0 =================
faza "etap 0: dane i konstrukcja bazowa"
touch stan/dziennik.md
grep -q '^# Dziennik' stan/dziennik.md || printf '# Dziennik eksperymentu\n\nStart: %s\n\n' "$(date '+%d.%m.%Y %H:%M')" >> stan/dziennik.md
if [ "$KONSTRUKCJA_BAZOWA" = 1 ]; then
  "$PYTHON" "$ZAUFANE/konstrukcja_bazowa.py" --zadanie zadanie.json \
    --wyjscie praca/iter00/baza/rozwiazanie_bazowe.json >> stan/przebieg.log 2>&1 \
    && printf '## Etap 0\n\nZnana konstrukcja (dwa odwzorowania trójkątne z interpolacji) zapisana w praca/iter00/baza/.\n\n' >> stan/dziennik.md \
    || log "konstrukcja bazowa nie powiodła się"
fi
weryfikuj
skladaj "wersja robocza: etap 0"
zapisz "Etap 0: dane i konstrukcja bazowa" wymus

# ================= iteracje =================
ITER=0
while ! koniec_zadany; do
  ITER=$((ITER + 1)); I=$(printf %02d "$ITER")
  RED=0; [ "$REDAKCJA_POSREDNIA" = 1 ] && RED=$LIMIT_REDAKTORA_MIN
  if (( $(pozostalo_min) < LIMIT_PLANISTY_MIN + MIN_WYKONAWCY_MIN + RED + REZERWA_KONCOWA_MIN )); then
    log "Za mało czasu na kolejną iterację"; break
  fi

  faza "iteracja $I: planowanie"
  WLIM=$(( $(pozostalo_min) - LIMIT_PLANISTY_MIN - RED - REZERWA_KONCOWA_MIN ))
  (( WLIM > LIMIT_WYKONAWCY_MIN )) && WLIM=$LIMIT_WYKONAWCY_MIN
  wypelnij prompty/planista.md "logi/iter${I}_planista.prompt" ITER="$I" POZOSTALO="$(pozostalo_min)" \
    LIMIT="$WLIM" MAKS="$MAKS_WYKONAWCOW" WSKAZOWKI="$TEKST_WSK"
  agent_sekwencyjny "iter${I}_planista" planista "$I" "$LIMIT_PLANISTY_MIN" "logi/iter${I}_planista.prompt" "$WYSILEK_PLANISTY" "planowanie"
  koniec_zadany && break

  PLAN=stan/plan_iter$I.json
  if ! jq -e '.zadania | type == "array"' "$PLAN" >/dev/null 2>&1; then
    log "Planista nie zostawił poprawnego planu; używam planu zastępczego"
    jq -n --argjson it "$ITER" '{iteracja: $it, uzasadnienie: "plan zastępczy zarządcy", koniec: false,
      zadania: [{tytul: "Kontynuacja najbardziej obiecującego kierunku",
                 polecenie: "Przeczytaj stan/dziennik.md, stan/zweryfikowane.json i notatki z praca/. Wybierz najbardziej obiecujący kierunek: albo znalezienie automorfizmu o stopniu niższym niż najlepszy zweryfikowany, albo uzasadnienie ograniczenia dolnego. Zrealizuj go."}]}' > "$PLAN"
  fi
  if jq -e '.koniec == true' "$PLAN" >/dev/null 2>&1; then
    log "Planista uznał pytanie za rozstrzygnięte"; break
  fi

  WLIM=$(( $(pozostalo_min) - RED - REZERWA_KONCOWA_MIN ))
  (( WLIM > LIMIT_WYKONAWCY_MIN )) && WLIM=$LIMIT_WYKONAWCY_MIN
  (( WLIM < MIN_WYKONAWCY_MIN )) && { log "Za mało czasu dla wykonawców"; break; }
  N=$(jq '.zadania | length' "$PLAN"); (( N > MAKS_WYKONAWCOW )) && N=$MAKS_WYKONAWCOW
  faza "iteracja $I: $N wykonawców po $WLIM min"
  KONIEC_GODZ=$(date -d "+$WLIM min" +%H:%M)
  declare -a PIDY=() NAZWY=() TYTULY=()
  STARTW=$(date +%s)
  for ((k = 1; k <= N; k++)); do
    KZ="praca/iter$I/zad$k"; mkdir -p "$KZ"
    TYTUL=$(jq -r ".zadania[$((k - 1))].tytul // \"zadanie $k\"" "$PLAN")
    { echo "# $TYTUL"; echo; jq -r ".zadania[$((k - 1))].polecenie // \"\"" "$PLAN"; } > "$KZ/zadanie.md"
    wypelnij prompty/wykonawca.md "logi/iter${I}_zad$k.prompt" ITER="$I" KATALOG="$KZ" TYTUL="$TYTUL" \
      KONIEC_GODZ="$KONIEC_GODZ" WSKAZOWKI="$TEKST_WSK"
    uruchom_agenta "iter${I}_zad$k" "$WLIM" "logi/iter${I}_zad$k.prompt" "$WYSILEK_WYKONAWCY"
    PIDY+=("$OSTATNI_PID"); NAZWY+=("iter${I}_zad$k"); TYTULY+=("$TYTUL")
    log "start iter${I}_zad$k: $TYTUL"
  done
  for ((k = 0; k < N; k++)); do
    czekaj "${PIDY[$k]}"; kod=$?
    zanotuj_agenta "${NAZWY[$k]}" wykonawca "$I" "$STARTW" "$kod" "${TYTULY[$k]}"
  done
  AKTYWNE=(); unset PIDY NAZWY TYTULY

  faza "iteracja $I: weryfikacja"
  weryfikuj
  skladaj "wersja robocza po iteracji $I"
  zapisz "Iteracja $I: wyniki wykonawców"
  koniec_zadany && break
  [ "$REDAKCJA_POSREDNIA" = 1 ] || continue

  faza "iteracja $I: redakcja raportu"
  wypelnij prompty/redaktor.md "logi/iter${I}_redaktor.prompt" ITER="po iteracji $I" STAN="wersja robocza" KONCOWA=""
  agent_sekwencyjny "iter${I}_redaktor" redaktor "$I" "$LIMIT_REDAKTORA_MIN" "logi/iter${I}_redaktor.prompt" "$WYSILEK_REDAKTORA" "redakcja raportu"
  skladaj "wersja robocza po iteracji $I"
  zapisz "Iteracja $I: raport"
done

# ================= raport końcowy =================
PRZERWANO=0; rm -f stan/STOP
faza "raport końcowy"
weryfikuj
skladaj "wersja końcowa (przed redakcją)"
zapisz "Wyniki końcowe przed redakcją" wymus
LIM=$(( $(pozostalo_min) - 2 )); (( LIM < 3 )) && LIM=3; (( LIM > 8 )) && LIM=8
wypelnij prompty/redaktor.md logi/final_redaktor.prompt ITER="wersja końcowa" STAN="wersja końcowa" \
  KONCOWA=". To redakcja KOŃCOWA: przejrzyj cały raport pod kątem spójności i ścisłości, napisz \`raport/sekcje/streszczenie.tex\` (bez nagłówka, 5–8 zdań: problem, najlepszy zweryfikowany stopień, co udowodniono, co pozostaje otwarte) i zakończ wnioski listą pytań otwartych"
agent_sekwencyjny final_redaktor redaktor koniec "$LIM" logi/final_redaktor.prompt "$WYSILEK_REDAKTORA" "redakcja końcowa"
skladaj "wersja końcowa"
zapisz "Raport końcowy" wymus
if [ -n "$GH_REPO" ] && [ -f raport.pdf ]; then
  TAG="raport-$(date +%Y%m%d-%H%M)"
  gh release create "$TAG" raport.pdf --repo "$GH_REPO" --title "Raport końcowy" \
    --notes "Najniższy zweryfikowany stopień: $(jq -r '.najlepszy_stopien // "brak"' stan/zweryfikowane.json)" \
    >/dev/null 2>&1 && log "Opublikowano wydanie $TAG" || log "Nie udało się utworzyć wydania"
fi
faza "zakończono"
log "Raport: $KAT/raport.pdf"
