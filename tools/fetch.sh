#!/bin/bash
# Fetch each "relpath url" line from $1 into web/, 2 s apart, skipping files already there.
cd "$(dirname "$0")/.."
while read -r rel url; do
  [ -s "web/$rel" ] && continue
  code=$(curl -s -o "web/$rel" -w "%{http_code}" "$url")
  echo "$code $rel"
  sleep 2
done < "$1"
echo DONE
