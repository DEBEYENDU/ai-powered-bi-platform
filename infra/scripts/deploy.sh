#!/bin/sh
# Unified deploy helper: compose (staging/prod) or Helm (k8s).
# Usage: ./deploy.sh <staging|prod> [--helm]  (env: REGISTRY, TAG, secrets)
set -eu

ENV="${1:?usage: deploy.sh <staging|prod> [--helm]}"
MODE="${2:-compose}"

if [ "$MODE" = "--helm" ]; then
  echo "Deploying to Kubernetes ($ENV)..."
  helm upgrade --install bi-platform ./infra/helm/bi-platform \
    -f "./infra/helm/bi-platform/values-$ENV.yaml" \
    --set "images.backend.tag=${TAG:?set TAG}" \
    --set "images.frontend.tag=${TAG}" \
    --namespace bi-platform --create-namespace
  kubectl -n bi-platform rollout status deploy/bi-platform-api --timeout=600s
else
  echo "Deploying via compose ($ENV)..."
  docker compose -f "./infra/compose/$ENV.yml" pull
  docker compose -f "./infra/compose/$ENV.yml" up -d --remove-orphans
  sleep 15
  API_BASE_URL="${API_BASE_URL:-http://localhost:8000}" python3 ./infra/scripts/smoke_test.py
fi
echo "Deploy complete."
