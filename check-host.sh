#!/bin/sh
# Read-only capability probe. No environment dumps, secrets, installations or service changes.
printf "%s\n" "JARVIS LAB: kontrola serveru"
for tool in python3 docker podman timeout; do
 if command -v "$tool" >/dev/null 2>&1; then printf "%s: dostupny\n" "$tool"; else printf "%s: nedostupny\n" "$tool"; fi
done
if command -v docker >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
 if timeout 10 docker info >/dev/null 2>&1; then printf "%s\n" "Docker daemon: pristup overen"; else printf "%s\n" "Docker daemon: pristup nepotvrzen"; fi
fi
printf "%s\n" "JARVIS LAB: kontrola dokoncena; zadne sluzby nebyly spusteny"
