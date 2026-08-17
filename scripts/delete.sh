#!/usr/bin/env bash
set -euo pipefail
kubectl delete namespace conversational-layer --ignore-not-found=true
