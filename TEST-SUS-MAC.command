#!/bin/zsh
set -u
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"
python3 "$SCRIPT_DIR/synthetic_students/visible.py" --repo "$SCRIPT_DIR"
read -k 1 '?Zum Schließen eine Taste drücken.'
