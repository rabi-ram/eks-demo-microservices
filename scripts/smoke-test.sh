#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "Checking backend health..."
curl --fail --silent --show-error \
  "$BASE_URL/health" | grep -q '"status":"healthy"'

echo "Checking backend API..."
curl --fail --silent --show-error \
  "$BASE_URL/api" | grep -q 'Hello from FastAPI running on Amazon EKS!'

echo "Checking Prometheus metrics..."
curl --fail --silent --show-error \
  "$BASE_URL/metrics" | grep -q 'http_requests_total'

echo "All smoke tests passed."
