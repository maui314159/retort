#!/usr/bin/env bash
# Build + push retort-sandbox:python-v4c (python-v3 + prime-agent v0.7.2).
# Stages the LOCAL prime-agent dist bundle into the build context (13MB,
# never committed), records its sha256, builds for linux/amd64, pushes the
# IMMUTABLE tag, and registers a new job-definition revision is left to the
# caller (needs the pushed digest).
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${PRIME_AGENT_REPO:-$HOME/dve/github/prime-agent}"
BUNDLE="$REPO/packages/coding-agent/dist/bundle"
ECR=047719634604.dkr.ecr.us-east-1.amazonaws.com/retort-sandbox

test -f "$BUNDLE/cli.js" || { echo "no dist bundle at $BUNDLE" >&2; exit 1; }
echo "prime-agent source: $(git -C "$REPO" describe --tags) ($(git -C "$REPO" rev-parse --short HEAD))"

rm -rf sandbox/prime-pkg
mkdir -p sandbox/prime-pkg
cp "$REPO/packages/coding-agent/package.json" sandbox/prime-pkg/package.json
rsync -a --exclude "*.map" --exclude "*.d.ts" "$REPO/packages/coding-agent/dist/" sandbox/prime-pkg/dist/
rsync -a --exclude test "$REPO/prime-agent-runtime/" sandbox/prime-pkg/runtime-src/
BSHA=$(find sandbox/prime-pkg -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d' ' -f1)
echo "staged bundle tree-sha256: $BSHA"

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "${ECR%%/*}" >/dev/null
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -f sandbox/Dockerfile.python-v4 -t "$ECR:python-v4c" .
docker push "$ECR:python-v4c"
rm -rf sandbox/prime-pkg
aws ecr describe-images --repository-name retort-sandbox --region us-east-1 \
  --query "imageDetails[?imageTags[0]=='python-v4c'].imageDigest" --output text
