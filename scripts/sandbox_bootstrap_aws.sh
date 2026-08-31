#!/usr/bin/env bash
# One-time AWS bootstrap for the retort SandboxRunner (docs/future-experiments.md §0c).
#
# *** THIS SCRIPT IS NOT RUN AUTOMATICALLY. It creates billable resources and
# *** IAM roles in the target account — review it, then run it yourself:
# ***     scripts/sandbox_bootstrap_aws.sh --dry-run     # print the plan
# ***     scripts/sandbox_bootstrap_aws.sh               # create (idempotent)
# ***     scripts/sandbox_bootstrap_aws.sh --delete      # tear everything down
#
# Creates (all named retort-sandbox*, all tagged project=retort-sandbox):
#   * ECR repository      retort-sandbox
#   * S3 bucket           retort-sandbox-artifacts-<account-id>   (private)
#   * IAM roles           retort-sandbox-execution (pull image, read the
#                         retort/* secret, write logs)
#                         retort-sandbox-task (S3 rw on the bucket's runs/*
#                         prefix ONLY — the agent's blast radius)
#   * Batch               Fargate compute environment + job queue retort-sandbox,
#                         job definition retort-sandbox-python (2 vCPU / 8 GB —
#                         override per experiment via containerOverrides)
#   * Secrets Manager     retort/openrouter-opencode (PLACEHOLDER, no value:
#                         set it yourself, the key never lives in a repo)
#
# Costs while idle: ~$0 (Fargate bills per task-second; ECR/S3 pennies for
# storage; the empty secret is $0.40/month).
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
BUCKET_ARG="${2:-}"
MODE="${1:-create}"

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="${BUCKET_ARG:-retort-sandbox-artifacts-${ACCOUNT}}"
TAGS="Key=project,Value=retort-sandbox"
NAME=retort-sandbox

say() { echo "[$MODE] $*"; }
run() { if [ "$MODE" = "--dry-run" ]; then say "WOULD: $*"; else say "$*"; "$@"; fi; }

if [ "$MODE" = "--delete" ]; then
  say "Tearing down ${NAME} in ${ACCOUNT}/${REGION} (bucket ${BUCKET})"
  aws batch update-job-queue --job-queue "$NAME" --state DISABLED --region "$REGION" || true
  sleep 5
  aws batch delete-job-queue --job-queue "$NAME" --region "$REGION" || true
  aws batch update-compute-environment --compute-environment "$NAME" --state DISABLED --region "$REGION" || true
  sleep 5
  aws batch delete-compute-environment --compute-environment "$NAME" --region "$REGION" || true
  aws batch deregister-job-definition --job-definition "${NAME}-python:1" --region "$REGION" || true
  aws ecr delete-repository --repository-name "$NAME" --force --region "$REGION" || true
  aws s3 rb "s3://${BUCKET}" --force || true
  aws secretsmanager delete-secret --secret-id retort/openrouter-opencode --force-delete-without-recovery --region "$REGION" || true
  for role in ${NAME}-execution ${NAME}-task; do
    for arn in $(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
      aws iam detach-role-policy --role-name "$role" --policy-arn "$arn" || true
    done
    for pol in $(aws iam list-role-policies --role-name "$role" --query 'PolicyNames[]' --output text 2>/dev/null); do
      aws iam delete-role-policy --role-name "$role" --policy-name "$pol" || true
    done
    aws iam delete-role --role-name "$role" || true
  done
  say "Teardown complete."
  exit 0
fi

say "Bootstrapping ${NAME} in account ${ACCOUNT}, region ${REGION}"
say "Artifacts bucket: ${BUCKET}"

# ---- ECR -------------------------------------------------------------------
if ! aws ecr describe-repositories --repository-names "$NAME" --region "$REGION" >/dev/null 2>&1; then
  run aws ecr create-repository --repository-name "$NAME" \
    --image-tag-mutability IMMUTABLE --region "$REGION" --tags "$TAGS"
else say "ECR repo $NAME exists"; fi

# ---- S3 --------------------------------------------------------------------
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [ "$REGION" = "us-east-1" ]; then
    run aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
  else
    run aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=${REGION}"
  fi
  run aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  run aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" \
    --lifecycle-configuration '{"Rules":[{"ID":"expire-runs","Status":"Enabled","Filter":{"Prefix":"runs/"},"Expiration":{"Days":30}}]}'
else say "S3 bucket $BUCKET exists"; fi

# ---- Secrets Manager placeholder -------------------------------------------
if ! aws secretsmanager describe-secret --secret-id retort/openrouter-opencode --region "$REGION" >/dev/null 2>&1; then
  run aws secretsmanager create-secret --name retort/openrouter-opencode \
    --description "OpenRouter key for retort sandbox opencode runs (set the value yourself)" \
    --region "$REGION"
  say "NOTE: secret created WITHOUT a value. Set it with:"
  say "  aws secretsmanager put-secret-value --secret-id retort/openrouter-opencode --secret-string '<key>'"
else say "Secret retort/openrouter-opencode exists"; fi

# ---- IAM -------------------------------------------------------------------
ASSUME='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

if ! aws iam get-role --role-name "${NAME}-execution" >/dev/null 2>&1; then
  run aws iam create-role --role-name "${NAME}-execution" \
    --assume-role-policy-document "$ASSUME" --tags "$TAGS"
  run aws iam attach-role-policy --role-name "${NAME}-execution" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  run aws iam put-role-policy --role-name "${NAME}-execution" \
    --policy-name secrets-read --policy-document "{
      \"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",
      \"Action\":\"secretsmanager:GetSecretValue\",
      \"Resource\":\"arn:aws:secretsmanager:${REGION}:${ACCOUNT}:secret:retort/*\"}]}"
else say "Role ${NAME}-execution exists"; fi

if ! aws iam get-role --role-name "${NAME}-task" >/dev/null 2>&1; then
  run aws iam create-role --role-name "${NAME}-task" \
    --assume-role-policy-document "$ASSUME" --tags "$TAGS"
  run aws iam put-role-policy --role-name "${NAME}-task" \
    --policy-name s3-runs-rw --policy-document "{
      \"Version\":\"2012-10-17\",\"Statement\":[
        {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],
         \"Resource\":\"arn:aws:s3:::${BUCKET}/runs/*\"}]}"
else say "Role ${NAME}-task exists"; fi

# ---- Batch -----------------------------------------------------------------
# Default VPC + subnets; adjust if the account has no default VPC.
if ! aws batch describe-compute-environments --compute-environments "$NAME" --region "$REGION" \
     --query 'computeEnvironments[0].computeEnvironmentName' --output text 2>/dev/null | grep -q "$NAME"; then
  SUBNETS=$(aws ec2 describe-subnets --region "$REGION" \
    --filters Name=default-for-az,Values=true --query 'Subnets[].SubnetId' --output json)
  SG=$(aws ec2 describe-security-groups --region "$REGION" \
    --filters Name=group-name,Values=default --query 'SecurityGroups[0].GroupId' --output text)
  run aws batch create-compute-environment --compute-environment-name "$NAME" \
    --type MANAGED --state ENABLED --region "$REGION" \
    --compute-resources "{\"type\":\"FARGATE\",\"maxvCpus\":32,\"subnets\":${SUBNETS},\"securityGroupIds\":[\"${SG}\"]}"
  say "Waiting for compute environment to become VALID..."
  [ "$MODE" = "--dry-run" ] || sleep 15
else say "Compute environment $NAME exists"; fi

if ! aws batch describe-job-queues --job-queues "$NAME" --region "$REGION" \
     --query 'jobQueues[0].jobQueueName' --output text 2>/dev/null | grep -q "$NAME"; then
  run aws batch create-job-queue --job-queue-name "$NAME" --state ENABLED \
    --priority 1 --region "$REGION" \
    --compute-environment-order "order=1,computeEnvironment=${NAME}"
else say "Job queue $NAME exists"; fi

# Job definition: registering a new revision is harmless (revisions are
# immutable); the runner always uses the latest.
IMAGE="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${NAME}:python"
run aws batch register-job-definition --job-definition-name "${NAME}-python" \
  --type container --region "$REGION" \
  --platform-capabilities FARGATE \
  --timeout "attemptDurationSeconds=5400" \
  --container-properties "{
    \"image\":\"${IMAGE}\",
    \"resourceRequirements\":[
      {\"type\":\"VCPU\",\"value\":\"2\"},
      {\"type\":\"MEMORY\",\"value\":\"8192\"}],
    \"executionRoleArn\":\"arn:aws:iam::${ACCOUNT}:role/${NAME}-execution\",
    \"jobRoleArn\":\"arn:aws:iam::${ACCOUNT}:role/${NAME}-task\",
    \"networkConfiguration\":{\"assignPublicIp\":\"ENABLED\"},
    \"secrets\":[{\"name\":\"OPENROUTER_API_KEY\",
      \"valueFrom\":\"arn:aws:secretsmanager:${REGION}:${ACCOUNT}:secret:retort/openrouter-opencode\"}],
    \"logConfiguration\":{\"logDriver\":\"awslogs\"}}"

say "Bootstrap complete. Next: docker build + push to ${IMAGE}, record the"
say "pushed DIGEST in the experiment's SandboxRunner(image_digests=...), and"
say "set the secret value. Then run the §0c smokes."
