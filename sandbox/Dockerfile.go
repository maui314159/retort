# retort sandbox image — go cells.
#
# Same pinning contract as Dockerfile.python: push a NEW immutable tag per
# rebuild (go-v1, go-v2, ...), register a new job-definition revision, and
# record the pushed DIGEST in SandboxRunner(image_digests={"go": ...}).
#
# Build (REPO ROOT as context):
#   docker build -f sandbox/Dockerfile.go --platform linux/amd64 \
#     --provenance=false --sbom=false -t retort-sandbox:go-v1 .
#
# Scoring toolchain: the go scorers shell out to `go test -count=1
# -coverpkg=./... -coverprofile=...` and `go vet` (gofmt ships with the
# toolchain). Go comes from the official tarball, PINNED — Debian's packaged
# go is too old for current agent output.
ARG OPENCODE_VERSION=1.18.20
ARG GO_VERSION=1.22.12

FROM python:3.12-slim AS wheel
WORKDIR /src
COPY pyproject.toml README.md* ./
COPY src ./src
RUN pip wheel --no-deps --no-build-isolation -w /wheels . \
    || (pip install hatchling && pip wheel --no-deps -w /wheels .)

FROM python:3.12-slim

ARG OPENCODE_VERSION
ARG GO_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git tar unzip build-essential \
    && rm -rf /var/lib/apt/lists/*

# awscli v2 from the official installer — the Debian package's postinst is
# broken against the floating python:3.12-slim base (python3-distro dpkg
# error, hit 2026-09-01); the zip install is AWS's supported path anyway.
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install --bin-dir /usr/local/bin \
    && rm -rf /tmp/aws /tmp/awscliv2.zip \
    && aws --version

RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
      | tar -C /usr/local -xz \
    && ln -s /usr/local/go/bin/go /usr/local/bin/go \
    && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt \
    && go version

# retort scorer suite (same minimal-deps contract as Dockerfile.python; the
# build-time import check fails the BUILD if the dep set stops sufficing).
COPY --from=wheel /wheels /wheels
RUN pip install --no-cache-dir --no-deps /wheels/retort-*.whl \
    && pip install --no-cache-dir pluggy pydantic pyyaml click \
    && python -c "from retort.scoring.collector import ScoreCollector; \
from retort.scoring.registry import create_default_registry; \
create_default_registry()" \
    && rm -rf /wheels

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && npm install -g "opencode-ai@${OPENCODE_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && opencode --version

RUN useradd --create-home --shell /bin/bash retort \
    && mkdir -p /workspace && chown retort:retort /workspace
COPY sandbox/entrypoint.sh /entrypoint.sh
COPY sandbox/score_gate.py /score_gate.py
COPY sandbox/score_full.py /score_full.py
RUN chmod +x /entrypoint.sh
USER retort
ENV HOME=/home/retort
# go needs writable caches as the non-root user.
ENV GOPATH=/home/retort/go GOCACHE=/home/retort/.cache/go-build

ENTRYPOINT ["/entrypoint.sh"]
