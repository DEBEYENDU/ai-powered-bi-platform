#!/bin/sh
# Self-signed TLS for staging/dev only. Production uses cert-manager/ACMc.
# Usage: ./generate-certs.sh <domain> [out_dir]
set -eu

DOMAIN="${1:?usage: generate-certs.sh <domain> [out_dir]}"
OUT="${2:-infra/nginx/certs}"
mkdir -p "$OUT"

openssl req -x509 -newkey rsa:4096 -sha256 -days 90 -nodes \
  -keyout "$OUT/privkey.pem" -out "$OUT/fullchain.pem" \
  -subj "/CN=$DOMAIN" -addext "subjectAltName=DNS:$DOMAIN"
chmod 600 "$OUT/privkey.pem"
echo "Self-signed cert for $DOMAIN written to $OUT (staging/dev only)"
