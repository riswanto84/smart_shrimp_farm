#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js/npm belum terpasang."
  if command -v brew >/dev/null 2>&1; then
    echo "Menginstal Node.js melalui Homebrew..."
    brew install node
  else
    echo "Homebrew belum tersedia. Instal Node.js LTS dari https://nodejs.org lalu jalankan file ini lagi."
    read -r -p "Tekan Enter untuk keluar..."
    exit 1
  fi
fi

if [ ! -f .env ]; then
  cp .env.example .env
  TOKEN=$(openssl rand -hex 32)
  sed -i '' "s/GANTI_DENGAN_TOKEN_RAHASIA/$TOKEN/" .env
  echo "File .env dibuat otomatis. API key: $TOKEN"
fi

npm install
npm start
