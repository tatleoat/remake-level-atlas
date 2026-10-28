#!/bin/bash
# Download "name url" lines into the given folder, 0.7 s apart, skipping files already there.
cd "$2"
while read -r name url; do
  [ -s "$name" ] && continue
  code=$(curl -s -A "remake-level-atlas/1.0 (personal research)" -o "$name" -w "%{http_code}" "$url")
  [ "$code" = 200 ] || { echo "$code $name"; rm -f "$name"; }
  sleep 0.7
done < "$1"
echo DONE
