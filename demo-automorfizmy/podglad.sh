#!/usr/bin/env bash
# Podgląd na żywo (np. na drugim terminalu albo przez ssh): ./podglad.sh
cd "$(dirname "$0")"
ostatnia_akcja() {
  tail -n 200 "$1" 2>/dev/null | jq -r 'select(.type=="assistant") | .message.content[]?
    | select(.type=="tool_use") | .name + ": " + ((.input.description // .input.command // .input.file_path // .input.pattern // "") | tostring | gsub("\n"; " ") | .[0:100])' 2>/dev/null | tail -n 1
}
while :; do
  clear
  teraz=$(date +%s)
  start=$(cat stan/start_epoch 2>/dev/null || echo "$teraz"); koniec=$(cat stan/koniec_epoch 2>/dev/null || echo "$teraz")
  printf 'Minuta %d   |   zostało %d min   |   %s\n' $(( (teraz - start) / 60 )) $(( (koniec - teraz) / 60 )) "$(cat stan/faza.txt 2>/dev/null)"
  printf 'Najniższy zweryfikowany stopień: %s   (znane ograniczenie: %s)\n\n' \
    "$(jq -r '.najlepszy_stopien // "—"' stan/zweryfikowane.json 2>/dev/null)" \
    "$(jq -r '.ograniczenie_znane // "—"' stan/zweryfikowane.json 2>/dev/null)"
  for f in $(ls -t logi/*.jsonl 2>/dev/null | head -n 4); do
    n=$(basename "$f" .jsonl)
    if [ -f "praca/${n/_zad//zad}/zadanie.md" ]; then tytul=$(head -n 1 "praca/${n/_zad//zad}/zadanie.md" | sed 's/^# //'); else tytul=""; fi
    printf '%-18s %s\n    └ %s\n' "$n" "$tytul" "$(ostatnia_akcja "$f")"
  done
  echo; tail -n 8 stan/przebieg.log 2>/dev/null
  sleep 10
done
