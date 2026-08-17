#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-order-fulfillment-conversational-agent:1.0.0}"
TAR="${TAR:-/tmp/order-fulfillment-conversational-agent-image.tar}"

echo "Building ${IMAGE}..."
docker build -t "${IMAGE}" .

echo "Saving image to ${TAR}..."
docker save "${IMAGE}" -o "${TAR}"

echo "Importing into Kubernetes containerd namespace..."
sudo ctr -n k8s.io images import "${TAR}"

echo "Imported image:"
sudo ctr -n k8s.io images list | grep 'order-fulfillment-conversational-agent' || true

echo "Done."
