#!/usr/bin/env bash
# Start eksperymentu jednym poleceniem: świeża kopia tego folderu, run.sh w tmux, podgląd obok.
#   ./start.sh wyklad      push na GitHub, pełny czas z konfiguracja.env
#   ./start.sh test        jak wyklad, ale 15 min i repozytorium demo-test-…
#   ./start.sh proba       bez GitHuba, pełny czas
# Opcjonalnie liczba minut na końcu, np.  ./start.sh test 20
set -euo pipefail
ZRODLO="$(cd "$(dirname "$0")" && pwd)"
TRYB_STARTU=${1:-}
STEMPEL=$(date +%m%d-%H%M%S)

case "$TRYB_STARTU" in
  wyklad|test|proba) ;;
  *) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac

source "$ZRODLO/konfiguracja.env"
MINUTY=${2:-$CZAS_CALKOWITY_MIN}
[ "$TRYB_STARTU" = test ] && MINUTY=${2:-15}

if tmux has-session -t demo 2>/dev/null; then
  echo "Sesja tmux 'demo' już działa. Podłącz się: tmux attach -t demo"
  echo "(albo zakończ ją: tmux kill-session -t demo)"
  exit 1
fi

if [ "$TRYB_STARTU" = proba ]; then
  TRYB=proba; GH_REPO=""
else
  TRYB=wyklad
  LOGIN=$(gh api user -q .login 2>/dev/null) || { echo "gh niezalogowany: gh auth login"; exit 1; }
  # gh może być zalogowany, a git push i tak pyta o hasło (brak „Authenticate Git”)
  printf 'protocol=https\nhost=github.com\n\n' | GIT_TERMINAL_PROMPT=0 git credential fill >/dev/null 2>&1 \
    || { echo "git nie ma dostępu do GitHuba (push zapyta o hasło): gh auth setup-git"; exit 1; }
  if [ "$TRYB_STARTU" = test ]; then GH_REPO="$LOGIN/demo-test-$STEMPEL"
  else GH_REPO=${GH_REPO:-$LOGIN/demo-automorfizmy-$STEMPEL}; fi
  # repo wykładu ma być nowe; istniejące zwykle zostało po próbie
  if [ "$TRYB_STARTU" = wyklad ] && gh repo view "$GH_REPO" >/dev/null 2>&1; then
    echo "UWAGA: repozytorium $GH_REPO już istnieje (pozostałość po próbie?)."
    echo "Przebieg dopisze się do niego. Usunięcie: gh repo delete $GH_REPO"
    read -rp "Wpisz 'tak', żeby mimo to kontynuować: " ODP
    [ "$ODP" = tak ] || exit 1
  fi
fi

CEL=~/demo-przebiegi/$STEMPEL-$TRYB_STARTU
mkdir -p ~/demo-przebiegi
[ -e "$CEL" ] && { echo "$CEL już istnieje"; exit 1; }
cp -r "$ZRODLO" "$CEL"
rm -rf "$CEL"/{.git,stan,praca,logi,raport/build,raport.pdf}   # gdyby źródło nosiło ślady przebiegu

# limity tylko tam, gdzie jest systemd --user (WSL tak; MX Linux z sysvinit nie)
OGRANICZ=""
if systemd-run --user --scope -q true 2>/dev/null; then
  OGRANICZ="systemd-run --user --scope -q -p MemoryMax=5G -p CPUQuota=600%"
fi

echo "Tryb:     $TRYB_STARTU ($MINUTY min)"
echo "GitHub:   ${GH_REPO:-brak} ${GH_REPO:+($GH_WIDOCZNOSC)}"
echo "Folder:   $CEL"
echo "Limity:   ${OGRANICZ:-brak (bez systemd), tylko nice}"
read -rp "Enter = start, Ctrl-C = rezygnacja " _

tmux new-session -d -s demo -n eksperyment -c "$CEL" \
  "TRYB=$TRYB GH_REPO=$GH_REPO CZAS_CALKOWITY_MIN=$MINUTY $OGRANICZ nice -n 10 ./run.sh; echo; read -rp 'Koniec. Enter zamyka okno. '"
tmux new-window -t demo -n podglad -c "$CEL" "./podglad.sh"
tmux select-window -t demo:eksperyment
echo "Ctrl-b n: następne okno (podgląd)   Ctrl-b d: odłącz (eksperyment liczy dalej)"
sleep 2
exec tmux attach -t demo
