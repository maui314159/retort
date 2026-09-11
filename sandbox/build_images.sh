#!/usr/bin/env bash
# Build (and push) the retort sandbox images reproducibly.
#
#   sandbox/build_images.sh stage                 # stage the prime-agent bundle only
#   sandbox/build_images.sh build v5 python go    # local tags retort-sandbox:<lang>-v5
#   sandbox/build_images.sh push  v5 python go typescript   # build + push to ECR
#
# One Dockerfile per language (sandbox/Dockerfile.<lang>) carries the whole
# recipe; this script supplies what a Dockerfile cannot know:
#   * the prime-agent DIST BUNDLE, staged from the local source build into
#     sandbox/prime-pkg/ (never committed; its tree sha256 is recorded),
#   * provenance build-args (retort commit + dirty flag, prime version/sha),
#   * the ECR registry, derived from the caller's account at run time,
#   * the pushed DIGEST, appended to sandbox/images.lock.json together with
#     everything needed to rebuild it. The lock file is the committed record
#     of "which digest came from which inputs" (docs/sandbox-runner.md §4).
#
# Env: PRIME_AGENT_REPO (default ~/dve/github/prime-agent), AWS_REGION
# (default us-east-1), ECR_REGISTRY (default <account>.dkr.ecr.<region>.amazonaws.com),
# PRIME_PKG_STAGED=1 to trust an already-staged sandbox/prime-pkg/ and
# RETORT_COMMIT / RETORT_DIRTY to label a build from a tarball without .git
# (remote builds on the x86_64 box, scripts/sandbox_buildbox_aws.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
REGION="${AWS_REGION:-us-east-1}"
REPO_NAME=retort-sandbox
LOCK=sandbox/images.lock.json
PKG=sandbox/prime-pkg

say() { echo "[build_images] $*" >&2; }
die() { say "ERROR: $*"; exit 1; }

stage_prime() {
  local repo="${PRIME_AGENT_REPO:-$HOME/dve/github/prime-agent}"
  local bundle="$repo/packages/coding-agent/dist/bundle"
  test -f "$bundle/cli.js" || die "no prime-agent dist bundle at $bundle (set PRIME_AGENT_REPO)"
  local ver commit
  ver=$(git -C "$repo" describe --tags 2>/dev/null || echo unknown)
  commit=$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)
  rm -rf "$PKG"; mkdir -p "$PKG"
  cp "$repo/packages/coding-agent/package.json" "$PKG/package.json"
  rsync -a --exclude "*.map" --exclude "*.d.ts" "$repo/packages/coding-agent/dist/" "$PKG/dist/"
  rsync -a --exclude test "$repo/prime-agent-runtime/" "$PKG/runtime-src/"
  local sha
  sha=$(find "$PKG" -type f -not -name .staged.json -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d' ' -f1)
  printf '{"prime_agent_version":"%s","prime_agent_commit":"%s","tree_sha256":"%s"}\n' \
    "$ver" "$commit" "$sha" > "$PKG/.staged.json"
  say "staged prime-agent $ver ($commit), tree sha256 $sha"
}

need_staged() {
  if [ "${PRIME_PKG_STAGED:-0}" = "1" ]; then
    test -f "$PKG/.staged.json" || die "PRIME_PKG_STAGED=1 but $PKG/.staged.json is missing"
  else
    stage_prime
  fi
}

json_field() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$1" "$2"; }

build_one() {  # gen lang push?
  local gen="$1" lang="$2" push="$3"
  local df="sandbox/Dockerfile.${lang}"
  test -f "$df" || die "no $df"
  local commit dirty pver psha tag
  # Remote builds run from a tarball without .git: the packer passes these in.
  commit="${RETORT_COMMIT:-$(git rev-parse --short=10 HEAD 2>/dev/null || echo unknown)}"
  dirty="${RETORT_DIRTY:-$(git status --porcelain --untracked-files=no 2>/dev/null | grep -q . && echo true || echo false)}"
  pver=$(json_field "$PKG/.staged.json" prime_agent_version)
  psha=$(json_field "$PKG/.staged.json" tree_sha256)
  tag="${lang}-${gen}"
  local ref="${REPO_NAME}:${tag}"
  if [ "$push" = "1" ]; then ref="${ECR}/${REPO_NAME}:${tag}"; fi
  say "build $ref (retort $commit dirty=$dirty, prime $pver)"
  docker build --platform linux/amd64 --provenance=false --sbom=false \
    -f "$df" -t "$ref" \
    --build-arg "RETORT_COMMIT=${commit}" --build-arg "RETORT_DIRTY=${dirty}" \
    --build-arg "PRIME_AGENT_VERSION=${pver}" --build-arg "PRIME_BUNDLE_SHA256=${psha}" \
    "$ROOT"
  local digest="" image_id
  image_id=$(docker image inspect "$ref" --format '{{.Id}}')
  if [ "$push" = "1" ]; then
    docker push "$ref"
    digest=$(aws ecr describe-images --repository-name "$REPO_NAME" --region "$REGION" \
      --image-ids "imageTag=${tag}" --query 'imageDetails[0].imageDigest' --output text)
    [ -n "$digest" ] && [ "$digest" != "None" ] || die "pushed $tag but ECR reports no digest"
    say "PUSHED $tag $digest"
  fi
  python3 - "$LOCK" "$tag" "$lang" "$gen" "$digest" "$image_id" "$commit" "$dirty" "$pver" "$psha" "$df" <<'PY'
import json, sys, datetime, hashlib, pathlib
lock, tag, lang, gen, digest, image_id, commit, dirty, pver, psha, df = sys.argv[1:]
p = pathlib.Path(lock)
entries = json.loads(p.read_text()) if p.exists() else []
entries = [e for e in entries if not (e["tag"] == tag and e.get("digest") == digest)]
entries.append({
    "tag": tag, "language": lang, "generation": gen,
    "digest": digest or None, "image_id": image_id,
    "retort_commit": commit, "retort_dirty": dirty == "true",
    "prime_agent_version": pver, "prime_bundle_sha256": psha,
    "dockerfile_sha256": hashlib.sha256(pathlib.Path(df).read_bytes()).hexdigest(),
    "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "pushed": bool(digest),
})
p.write_text(json.dumps(entries, indent=2) + "\n")
PY
  say "recorded $tag in $LOCK"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  stage) stage_prime ;;
  build|push)
    gen="${1:-}"; shift || true
    [ -n "$gen" ] && [ $# -gt 0 ] || die "usage: $0 $cmd <generation> <lang>..."
    push=0
    if [ "$cmd" = "push" ]; then
      push=1
      ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
      ECR="${ECR_REGISTRY:-${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com}"
      aws ecr get-login-password --region "$REGION" \
        | docker login --username AWS --password-stdin "$ECR" >/dev/null
    fi
    need_staged
    for lang in "$@"; do build_one "$gen" "$lang" "$push"; done
    ;;
  *) echo "usage: $0 {stage|build <gen> <lang>...|push <gen> <lang>...}" >&2; exit 2 ;;
esac
