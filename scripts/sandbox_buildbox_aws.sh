#!/usr/bin/env bash
# x86_64 EC2 build/smoke box for the retort SandboxRunner (docs/sandbox-runner.md).
#
# What it is for: building the linux/amd64 sandbox images with docker buildx
# and pushing them to the retort-sandbox ECR repo, and running one-cell smokes
# of the SandboxRunner docker backend at the Fargate shape (2 vCPU / 8 GB)
# on real x86 silicon (Bun/opencode need AVX; arm64-emulating-amd64 on a Mac
# gives meaningless timings).
#
# *** THIS SCRIPT IS NOT RUN AUTOMATICALLY. `create` makes a billable EC2
# *** instance and an IAM role. Review it, then run it yourself:
#
#     scripts/sandbox_buildbox_aws.sh create    # instance + role (idempotent)
#     scripts/sandbox_buildbox_aws.sh status    # id, state, public IP, SSM readiness
#     scripts/sandbox_buildbox_aws.sh ssm       # print the start-session command
#     scripts/sandbox_buildbox_aws.sh stop      # stop billing for compute
#     scripts/sandbox_buildbox_aws.sh start     # resume (new public IP)
#     scripts/sandbox_buildbox_aws.sh destroy   # terminate + delete role/profile
#
# Creates (all named retort-sandbox-build, tagged Name=retort-sandbox-build,
# Project=retort, project=retort-sandbox):
#   * EC2 instance        t3.medium, 30 GB gp3 root, latest Amazon Linux 2023
#                         x86_64 AMI (resolved via the SSM public parameter),
#                         default VPC/subnet, public IP, NO key pair
#   * Security group      retort-sandbox-build — egress only, no inbound rules
#   * IAM role + profile  retort-sandbox-build — AmazonSSMManagedInstanceCore,
#                         AmazonEC2ContainerRegistryPowerUser, and
#                         GetSecretValue on retort/openrouter-opencode only
#
# Access is SSM Session Manager only (no SSH). User data installs docker, git,
# buildx and the AWS CLI, and arms `shutdown -h +240` so a forgotten box turns
# itself off after 4 hours (re-armed on every boot — `start` gives a fresh 4h).
#
# Costs: t3.medium ~$0.04/h while running, ~$2.40/month for the 30 GB root
# volume while stopped. Nothing else bills while idle.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
MODE="${1:-status}"
NAME=retort-sandbox-build
INSTANCE_TYPE="${BUILDBOX_INSTANCE_TYPE:-t3.medium}"
ROOT_GB="${BUILDBOX_ROOT_GB:-30}"
SHUTDOWN_MINUTES="${BUILDBOX_SHUTDOWN_MINUTES:-240}"
AMI_PARAM=/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
SECRET_NAME=retort/openrouter-opencode
TAG_SPEC="{Key=Name,Value=${NAME}},{Key=Project,Value=retort},{Key=project,Value=retort-sandbox}"

say() { echo "[$MODE] $*"; }
die() { echo "FATAL: $*" >&2; exit 1; }

ec2() { aws ec2 --region "$REGION" "$@"; }

# The live (not terminated) instance carrying our Name tag, or empty.
find_instance() {
  ec2 describe-instances \
    --filters "Name=tag:Name,Values=${NAME}" \
              "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].InstanceId' --output text | awk '{print $1}'
}

instance_field() {  # instance_field <id> <jmespath>
  ec2 describe-instances --instance-ids "$1" \
    --query "Reservations[0].Instances[0].$2" --output text
}

ssm_ping() {  # prints Online / ConnectionLost / none
  local s
  s=$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$1" \
    --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)
  if [ -z "$s" ] || [ "$s" = "None" ]; then s=none; fi
  echo "$s"
}

wait_state() {  # wait_state <id> <state> [tries]
  local id=$1 want=$2 tries=${3:-60} st=""
  for _ in $(seq 1 "$tries"); do
    st=$(instance_field "$id" State.Name)
    [ "$st" = "$want" ] && return 0
    sleep 5
  done
  die "instance $id is '$st', never reached '$want'"
}

wait_ssm() {  # wait_ssm <id> [tries]  — the SSM agent registers after boot
  local id=$1 tries=${2:-60} p=""
  for _ in $(seq 1 "$tries"); do
    p=$(ssm_ping "$id")
    [ "$p" = "Online" ] && return 0
    sleep 10
  done
  die "instance $id never reported SSM PingStatus=Online (last: $p)"
}

# ---------------------------------------------------------------------------
cmd_create() {
  say "Ensuring ${NAME} in region ${REGION}"

  # ---- IAM role + instance profile ----------------------------------------
  local assume='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  if ! aws iam get-role --role-name "$NAME" >/dev/null 2>&1; then
    say "create role $NAME"
    aws iam create-role --role-name "$NAME" --assume-role-policy-document "$assume" \
      --tags "Key=Name,Value=${NAME}" "Key=Project,Value=retort" "Key=project,Value=retort-sandbox" >/dev/null
  else say "role $NAME exists"; fi
  for pol in AmazonSSMManagedInstanceCore AmazonEC2ContainerRegistryPowerUser; do
    aws iam attach-role-policy --role-name "$NAME" \
      --policy-arn "arn:aws:iam::aws:policy/${pol}"   # idempotent
  done
  # Secret ARNs carry a random 6-char suffix; look the real one up rather than
  # guessing with a wildcard so the policy stays as narrow as possible.
  local secret_arn
  secret_arn=$(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" \
    --region "$REGION" --query ARN --output text 2>/dev/null || true)
  if [ -n "$secret_arn" ] && [ "$secret_arn" != "None" ]; then
    aws iam put-role-policy --role-name "$NAME" --policy-name secrets-read \
      --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",
        \"Action\":\"secretsmanager:GetSecretValue\",\"Resource\":\"${secret_arn}\"}]}"
  else
    say "WARNING: secret ${SECRET_NAME} not found in ${REGION}; skipping secrets-read policy"
  fi
  if ! aws iam get-instance-profile --instance-profile-name "$NAME" >/dev/null 2>&1; then
    say "create instance profile $NAME"
    aws iam create-instance-profile --instance-profile-name "$NAME" \
      --tags "Key=Name,Value=${NAME}" "Key=Project,Value=retort" >/dev/null
  else say "instance profile $NAME exists"; fi
  if ! aws iam get-instance-profile --instance-profile-name "$NAME" \
        --query 'InstanceProfile.Roles[].RoleName' --output text | grep -qw "$NAME"; then
    aws iam add-role-to-instance-profile --instance-profile-name "$NAME" --role-name "$NAME"
    say "waiting for the instance profile to propagate"
    sleep 12
  fi

  # ---- Network: default VPC, one default subnet, egress-only SG -----------
  local vpc subnet sg
  vpc=$(ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
  { [ -n "$vpc" ] && [ "$vpc" != "None" ]; } || die "no default VPC in ${REGION}"
  subnet=$(ec2 describe-subnets --filters "Name=vpc-id,Values=${vpc}" Name=default-for-az,Values=true \
    --query 'Subnets[0].SubnetId' --output text)
  sg=$(ec2 describe-security-groups --filters "Name=vpc-id,Values=${vpc}" "Name=group-name,Values=${NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
  if [ -z "$sg" ] || [ "$sg" = "None" ]; then
    say "create security group $NAME (egress only)"
    sg=$(ec2 create-security-group --group-name "$NAME" --vpc-id "$vpc" \
      --description "retort sandbox build box: SSM only, no inbound" \
      --tag-specifications "ResourceType=security-group,Tags=[${TAG_SPEC}]" \
      --query GroupId --output text)
  else say "security group $NAME exists ($sg)"; fi
  # Belt and braces: strip any inbound rule someone may have added.
  local inbound
  inbound=$(ec2 describe-security-groups --group-ids "$sg" --query 'SecurityGroups[0].IpPermissions' --output json)
  if [ "$inbound" != "[]" ]; then
    say "removing inbound rules from $sg"
    ec2 revoke-security-group-ingress --group-id "$sg" --ip-permissions "$inbound" >/dev/null
  fi

  # ---- Instance ----------------------------------------------------------
  local id
  id=$(find_instance)
  if [ -n "$id" ]; then
    say "instance $id exists ($(instance_field "$id" State.Name)); nothing to create"
  else
    local ami userdata
    ami=$(aws ssm get-parameter --region "$REGION" --name "$AMI_PARAM" --query Parameter.Value --output text)
    say "AMI ${ami} (${AMI_PARAM})"
    userdata=$(cat <<EOF
#!/bin/bash
set -eux
# Forgotten-box guard: power off ${SHUTDOWN_MINUTES} minutes after EVERY boot.
# User data itself runs only on first boot, so install the guard as a
# cloud-init per-boot script and also arm it now.
mkdir -p /var/lib/cloud/scripts/per-boot
cat > /var/lib/cloud/scripts/per-boot/retort-shutdown-guard.sh <<'GUARD'
#!/bin/bash
shutdown -h +${SHUTDOWN_MINUTES} "retort-sandbox-build auto-shutdown guard"
GUARD
chmod +x /var/lib/cloud/scripts/per-boot/retort-shutdown-guard.sh
shutdown -h +${SHUTDOWN_MINUTES} "retort-sandbox-build auto-shutdown guard"
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user
# docker buildx plugin (--platform linux/amd64 builds pushed to ECR)
BUILDX_VER=\$(curl -fsSL https://api.github.com/repos/docker/buildx/releases/latest | grep -o '"tag_name": *"[^"]*"' | cut -d'"' -f4)
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/buildx/releases/download/\${BUILDX_VER}/buildx-\${BUILDX_VER}.linux-amd64" \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
command -v aws >/dev/null || dnf install -y awscli-2
touch /var/lib/retort-buildbox-ready
EOF
)
    say "run-instances ${INSTANCE_TYPE}, ${ROOT_GB} GB gp3, subnet ${subnet}"
    id=$(ec2 run-instances --image-id "$ami" --instance-type "$INSTANCE_TYPE" \
      --subnet-id "$subnet" --security-group-ids "$sg" --associate-public-ip-address \
      --iam-instance-profile "Name=${NAME}" \
      --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":${ROOT_GB},\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
      --metadata-options HttpTokens=required,HttpEndpoint=enabled \
      --user-data "$userdata" \
      --tag-specifications "ResourceType=instance,Tags=[${TAG_SPEC}]" \
                           "ResourceType=volume,Tags=[${TAG_SPEC}]" \
      --query 'Instances[0].InstanceId' --output text)
    say "launched $id"
  fi
  say "waiting for running + SSM Online"
  wait_state "$id" running
  wait_ssm "$id"
  cmd_status
}

cmd_status() {
  local id
  id=$(find_instance)
  if [ -z "$id" ]; then echo "instance:  none (tag Name=${NAME}, region ${REGION})"; return 0; fi
  echo "instance:  $id"
  echo "region:    $REGION"
  echo "type:      $(instance_field "$id" InstanceType)"
  echo "ami:       $(instance_field "$id" ImageId)"
  echo "state:     $(instance_field "$id" State.Name)"
  echo "public ip: $(instance_field "$id" PublicIpAddress)"
  echo "ssm:       $(ssm_ping "$id")"
}

cmd_start() {
  local id; id=$(find_instance); [ -n "$id" ] || die "no instance; run create"
  ec2 start-instances --instance-ids "$id" >/dev/null
  say "starting $id (auto-shutdown re-arms for ${SHUTDOWN_MINUTES} min on boot)"
  wait_state "$id" running; wait_ssm "$id"; cmd_status
}

cmd_stop() {
  local id; id=$(find_instance); [ -n "$id" ] || die "no instance; run create"
  ec2 stop-instances --instance-ids "$id" >/dev/null
  say "stopping $id"
  wait_state "$id" stopped 120; cmd_status
}

cmd_ssm() {
  local id; id=$(find_instance); [ -n "$id" ] || die "no instance; run create"
  echo "aws ssm start-session --region ${REGION} --target ${id}"
  echo "# then: sudo su - ec2-user   (docker group membership applies to ec2-user)"
}

cmd_destroy() {
  local id; id=$(find_instance)
  echo "This TERMINATES ${id:-<no instance>} and deletes role/profile/security group ${NAME} in ${REGION}."
  read -r -p "Type 'destroy' to continue: " ans
  [ "$ans" = "destroy" ] || die "aborted"
  if [ -n "$id" ]; then
    ec2 terminate-instances --instance-ids "$id" >/dev/null
    say "terminating $id"
    ec2 wait instance-terminated --instance-ids "$id"
  fi
  aws iam remove-role-from-instance-profile --instance-profile-name "$NAME" --role-name "$NAME" 2>/dev/null || true
  aws iam delete-instance-profile --instance-profile-name "$NAME" 2>/dev/null || true
  for arn in $(aws iam list-attached-role-policies --role-name "$NAME" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
    aws iam detach-role-policy --role-name "$NAME" --policy-arn "$arn" || true
  done
  for pol in $(aws iam list-role-policies --role-name "$NAME" --query 'PolicyNames[]' --output text 2>/dev/null); do
    aws iam delete-role-policy --role-name "$NAME" --policy-name "$pol" || true
  done
  aws iam delete-role --role-name "$NAME" 2>/dev/null || true
  local sg
  sg=$(ec2 describe-security-groups --filters "Name=group-name,Values=${NAME}" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
  if [ -n "$sg" ] && [ "$sg" != "None" ]; then
    # ENIs linger briefly after termination; retry a few times.
    for _ in $(seq 1 12); do ec2 delete-security-group --group-id "$sg" 2>/dev/null && break; sleep 10; done
  fi
  say "destroy complete"
}

case "$MODE" in
  create)  cmd_create ;;
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  status)  cmd_status ;;
  ssm)     cmd_ssm ;;
  destroy) cmd_destroy ;;
  *) echo "usage: $0 {create|start|stop|status|ssm|destroy}" >&2; exit 2 ;;
esac
