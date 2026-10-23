#!/usr/bin/env bash
# Publikacja migawki prezentacji na GitHubie: repo z plikami (bez plików roboczych)
# i GitHub Pages ze slajdami. Historia nie jest publikowana: każde uruchomienie
# zastępuje poprzednią migawkę jednym commitem.
#
#   narzedzia/publikuj.sh          pokazuje, co zostanie opublikowane, i pyta o zgodę
#
# Wymaga: czystego drzewa (publikowany jest HEAD), świeżego renderu w _output/,
# gh zalogowanego z dostępem gita (gh auth setup-git).
set -euo pipefail
KAT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KAT"

REPO=rodakt/ai-math
STRONA=https://rodakt.github.io/ai-math/
REPO_DEMO=https://github.com/rodakt/demo-automorfizmy
POMIJANE=(konspekt.md zasady-slajdow.md przygotowania-demo.md)

blad() { echo "BŁĄD: $*" >&2; exit 1; }

[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || blad "niezacommitowane zmiany; publikowany jest HEAD, więc najpierw commit"
[ -f _output/slajdy.html ] || blad "brak _output/slajdy.html; najpierw render"
[ -z "$(find slajdy.qmd styles.scss figury img -newer _output/slajdy.html -print -quit)" ] \
  || blad "_output/slajdy.html starszy niż źródła; najpierw render"
grep -q "UZUPELNIC" _output/slajdy.html && blad "w slajdach zastępczy adres (UZUPELNIC)"
grep -q "$REPO" figury/_qr.md || blad "kod QR nie wskazuje $REPO (narzedzia/generuj_figury.py)"
gh api user >/dev/null 2>&1 || blad "gh niezalogowany: gh auth login"
printf 'protocol=https\nhost=github.com\n\n' | GIT_TERMINAL_PROMPT=0 git credential fill >/dev/null 2>&1 \
  || blad "git nie ma dostępu do GitHuba: gh auth setup-git"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/repo" "$TMP/strona"
git archive HEAD | tar -x -C "$TMP/repo"
for p in "${POMIJANE[@]}"; do rm -rf "$TMP/repo/$p"; done
WERSJA=$(git rev-parse --short HEAD)
DATA=$(date +%d.%m.%Y)

cat > "$TMP/repo/README.md" <<EOF
# Kto udowodnił to twierdzenie?

Matematyka w epoce sztucznej inteligencji — slajdy wykładu.

- **Slajdy online:** $STRONA (klawisz S — notatki prelegenta ze źródłami i szczegółami)
- **Demo z wykładu:** $REPO_DEMO — agenci Claude Code szukają w tle automorfizmu
  wielomianowego niskiego stopnia; raport PDF w repozytorium

## Zawartość

- \`slajdy.qmd\` — źródło slajdów (Quarto, reveal.js); render: \`quarto render\`
  (dzięki \`_freeze/\` bez Pythona)
- \`figury/\`, \`narzedzia/generuj_figury.py\` — figury generowane skryptem
- \`img/\` — obrazy; źródła i licencje podane na slajdach i w notatkach
- \`demo-automorfizmy/\` — kod demo (zarządca, prompty agentów, weryfikator)

Cudze artykuły, z których korzystałem, nie są tu publikowane; odnośniki są w notatkach.

Migawka z $DATA.
EOF

cp _output/slajdy.html "$TMP/strona/index.html"
touch "$TMP/strona/.nojekyll"

echo "Repozytorium: https://github.com/$REPO (publiczne), migawka HEAD $WERSJA"
echo "Pominięte:    ${POMIJANE[*]}"
echo "Strona:       $STRONA"
echo "Pliki:"
(cd "$TMP/repo" && find . -type f | sed 's|^\./||' | sed 's|/.*|/|' | sort | uniq -c)
read -rp "Enter = publikuj, Ctrl-C = rezygnacja " _

if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --public \
    --description "Kto udowodnił to twierdzenie? Matematyka w epoce sztucznej inteligencji — slajdy" \
    --homepage "$STRONA" >/dev/null
fi

publikuj_galaz() {  # $1 katalog, $2 gałąź, $3 opis
  git -C "$1" init -q -b "$2"
  git -C "$1" add -A
  git -C "$1" -c user.name="$(git config user.name)" -c user.email="$(git config user.email)" \
    commit -q -m "$3"
  GIT_TERMINAL_PROMPT=0 git -C "$1" push -q --force "https://github.com/$REPO.git" "$2"
}
publikuj_galaz "$TMP/repo" main "Migawka prezentacji ($DATA, $WERSJA)"
publikuj_galaz "$TMP/strona" gh-pages "Slajdy ($DATA, $WERSJA)"

gh api "repos/$REPO/pages" >/dev/null 2>&1 \
  || gh api -X POST "repos/$REPO/pages" -f "source[branch]=gh-pages" -f "source[path]=/" >/dev/null

echo "Gotowe: https://github.com/$REPO"
echo "Slajdy: $STRONA (pierwsza publikacja Pages trwa do kilku minut)"
