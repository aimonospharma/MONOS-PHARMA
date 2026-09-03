#!/usr/bin/env bash
# lab.coremind.mn руу байршуулах ZIP бэлдэнэ.
# Файлууд ZIP-ийн үндэс дээр орно (нэмэлт дэд фолдергүй), .venv болон
# ажлын өгөгдөл (app/data, app/storage) хасагдана.
set -euo pipefail

cd "$(dirname "$0")"
OUT="dist/mp-team.zip"
mkdir -p dist
rm -f "$OUT"

zip -r -q "$OUT" . \
  -x '.venv/*' \
     'dist/*' \
     'app/data/*' \
     'app/storage/*' \
     '*/__pycache__/*' \
     '*.pyc' \
     '.git/*' \
     '.DS_Store' \
     '*/.DS_Store'

echo "✅ $OUT  ($(du -h "$OUT" | cut -f1))"
echo
echo "ZIP-ийн үндэс дэх файлууд:"
unzip -Z1 "$OUT" | awk -F/ 'NF<=1 || (NF==2 && $2=="")' | sort
