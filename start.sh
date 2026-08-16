#!/usr/bin/env bash
# Digital Wellness AI - start the app (macOS / Linux).
#
# Runs run.py, which starts the API (the API also serves the web pages)
# and opens the browser at the right address. Do NOT serve the frontend
# folder with a separate static server: it will serve the pages but
# cannot answer a sign-in, and you get 501 on the login button.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 run.py
elif command -v python >/dev/null 2>&1; then
  exec python run.py
else
  echo "Python 3 was not found. Install it and try again." >&2
  exit 1
fi
