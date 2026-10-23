#!/usr/bin/env bash
# Sprawdza, czy na tej maszynie jest wszystko, czego potrzebuje run.sh.
cd "$(dirname "$0")"; source ./konfiguracja.env
ok=1
spr() { if eval "$2" >/dev/null 2>&1; then echo "  ok   $1"; else echo "  BRAK $1"; ok=0; fi; }
opc() { if eval "$2" >/dev/null 2>&1; then echo "  ok   $1"; else echo "  --   $1 (nie ma, nie szkodzi)"; fi; }
echo "Tryb: $TRYB   czas: $CZAS_CALKOWITY_MIN min   GitHub: ${GH_REPO:-brak}"
echo "Środowisko: ${ENV_PREFIX:-NIE ZNALEZIONO ($SRODOWISKO) — mamba env create -f environment.yml}"
echo "Wymagane:"
spr "claude ($CLAUDE_BIN)"           "command -v $CLAUDE_BIN"
spr "python z sympy/numpy/matplotlib" "$PYTHON -c 'import sympy, numpy, matplotlib'"
spr "jq"                               "command -v jq"
spr "GNU timeout"                      "timeout --version"
spr "latexmk + pdflatex"               "command -v latexmk && command -v pdflatex"
spr "pakiety LaTeX (polski, lmodern)"  "kpsewhich polski.sty lmodern.sty | grep -c . | grep -q 2"
spr "git"                              "command -v git"
if [ "$TRYB" = wyklad ] && [ -n "$GH_REPO" ]; then spr "gh zalogowany" "gh auth status"; fi
[ "${BEZ_AGENTA:-0}" = 1 ] || spr "agent odpowiada (krótkie wywołanie)" "timeout 120 $CLAUDE_BIN -p 'Odpowiedz jednym słowem: OK' --model $MODEL --effort low"
echo "Zalecane dla agentów (algebra):"
spr "sage działa"  "timeout 120 sage -c 'R.<a,b>=QQ[]; print(R.ideal([a^2-b]).groebner_basis())'"
echo "Opcjonalne:"
for t in Singular M2 msolve magma; do opc "$t" "command -v $t"; done
opc "python-flint" "$PYTHON -c 'import flint'"
[ $ok = 1 ] && echo "Gotowe." || echo "Uzupełnij braki przed startem."
