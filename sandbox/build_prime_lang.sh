#!/usr/bin/env bash
# Build + push retort-sandbox:{go,typescript}-v3 (v2 bases + prime-agent
# v0.7.2), staging the LOCAL prime-agent dist bundle exactly as
# build_python_v4.sh does (13MB, never committed). Prints each pushed digest.
# Job-definition registration is left to the caller (needs the digest).
#
# Usage: sandbox/build_prime_lang.sh go typescript
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

for LANG in "$@"; do
  TAG="${LANG}-${TAG_VERSION:-v3}"
  docker build --platform linux/amd64 --provenance=false --sbom=false \
    -f "sandbox/Dockerfile.${LANG}-v3" -t "$ECR:$TAG" .
  docker push "$ECR:$TAG"
  DIGEST=$(aws ecr describe-images --repository-name retort-sandbox --region us-east-1 \
    --query "imageDetails[?imageTags[0]=='$TAG'].imageDigest" --output text)
  echo "PUSHED $TAG $DIGEST"
done
rm -rf sandbox/prime-pkg
