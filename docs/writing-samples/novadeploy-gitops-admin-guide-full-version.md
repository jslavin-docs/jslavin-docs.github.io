---
description: "Full fictional NovaDeploy GitOps administration guide covering Amazon EKS, Argo CD, IAM, KMS, ESO, Reloader, CI guardrails, verification, and rollback workflows."
---

# NovaDeploy Platform: GitOps Administration Guide

*Deploying Services to Amazon EKS with Argo CD*  
Version 1.0 | Status: Full runbook | Written by: Jeff Slavin

This fictional runbook covers service deployment to Amazon Elastic Kubernetes Service (EKS) with Argo CD, including access controls, encryption, secrets, GitOps, and rollback.

[Read the portfolio cut.](novadeploy-gitops-admin-guide-portfolio-cut.md)

!!! note "Portfolio Notice"
    NovaDeploy is a fictional portfolio platform. This sample contains no proprietary employer, client, or production information.

!!! info "Document Purpose"
    This runbook demonstrates documentation leadership through clear operator guidance: one source of truth, clear stop points, auditable checks, and safe rollback paths.

!!! info "Scope and Audience"
    **Scope:** Deploy and recover NovaDeploy services on Amazon EKS with Argo CD. Covers GitOps, AWS Identity and Access Management (IAM), AWS Key Management Service (KMS), Secrets Manager, External Secrets Operator (ESO), Reloader, verification, and rollback. Excludes application-code changes, broader incident response, and service-specific business logic.

    **Audience:** Platform engineers, DevOps/SRE operators, cloud engineers, and documentation reviewers working with GitOps-managed Kubernetes services.

??? abstract page-contents "Contents"
    - [1. Quick Start and Stop Conditions](#1-quick-start-and-stop-conditions)
    - [2. Deployment Guardrails](#2-deployment-guardrails)
    - [3. Architecture Overview](#3-architecture-overview)
    - [4. Prerequisites and Tooling](#4-prerequisites-and-tooling)
    - [5. IAM, KMS, SecretStore, and ESO Setup](#5-iam-kms-secretstore-and-eso-setup)
    - [6. GitOps Repository Layout](#6-gitops-repository-layout)
    - [7. Argo CD Application and Sync Policy](#7-argo-cd-application-and-sync-policy)
    - [8. Deployment Verification](#8-deployment-verification)
    - [9. Rollback and Recovery](#9-rollback-and-recovery)
    - [10. Appendices](#10-appendices)

## 1. Quick Start and Stop Conditions

Follow this workflow for standard, non-emergency production deployments. Later sections provide the implementation details.

| Step | Action | What to Do | Stop Condition |
| --- | --- | --- | --- |
| 1 | Validate readiness | Run controller health checks, local tool checks, and the guardrail table before editing the deployment pull request (PR). | Stop if Argo CD, ESO, or Reloader is unhealthy. |
| 2 | Change declared state | Update Helm values, Argo CD Application resources, ExternalSecret custom resources (CRs), or Terraform-owned IAM/KMS metadata. | Do not commit, paste, or type plaintext secrets into Git, a PR, or a shell. |
| 3 | Open PR | Pass CI (the automated checks): lint, helm template, kubeconform, secret scan, and Reloader annotation guardrail. | Stop if any workload consumes a Secret without the root Reloader annotation. |
| 4 | Merge to main | Merge after approval. Argo CD watches main and reconciles the application. | No direct pushes and no direct kubectl edits. |
| 5 | Sync and verify | Wait for automated sync or run argocd app sync `<app-name>`; then run health, smoke, and secret-mount checks. | Do not use --force for normal deployment hotfixes. |
| 6 | Close or recover | Close the ticket only after Synced/Healthy, smoke-test success, and non-secret evidence is recorded. | Use Git revert by default; use Argo CD history only for approved service-level agreement (SLA) emergencies. |

!!! info "Zero-Trust Definition"
    No plaintext secrets in Git, ConfigMaps, literal environment variables, Terraform state, PRs, logs, chats, or tickets. Secret values live in AWS Secrets Manager. ESO syncs values into Kubernetes Secret objects. Reloader propagates changes by controlled rolling restart, not by exposing secret values.

## 2. Deployment Guardrails

These production safety rules apply throughout the guide.

| Guardrail | Required Evidence | Pass Criteria |
| --- | --- | --- |
| Git is source of truth | main branch protected; all changes through PR; CI passes before merge | Manual cluster drift is rejected or reverted through Argo CD self-heal. |
| Terraform owns cloud controls | IAM roles, policies, KMS keys, Secrets Manager metadata, rotation config, and Lambda permissions are managed in Terraform | Use the AWS CLI for read-only checks of Terraform-managed configuration. Direct CLI changes to that configuration require approved break-glass procedures and subsequent reconciliation with Terraform. |
| No plaintext secrets | Secret scan, PR review, and no aws_secretsmanager_secret_version for production values | Secret values never enter Git, Terraform state, PR comments, CI logs, chats, or tickets. |
| IRSA separation | Two IAM roles for service accounts (IRSA) per service: workload ServiceAccount has non-secret AWS permissions only; dedicated ESO reader ServiceAccount assumes `nova-<service>-eso-read` | Only ESO reads AWS Secrets Manager for service-scoped paths. |
| Namespace-scoped SecretStore | ExternalSecret uses secretStoreRef.kind: SecretStore in the workload namespace | Avoid ClusterSecretStore for app secrets unless a platform exception is approved. |
| Reloader compatibility | Root workload metadata contains `reloader.stakater.com/auto: "true"`; the Application defines `ignoreDifferences` for the Reloader annotation and sets `RespectIgnoreDifferences=true`. | Reloader can patch pod templates without Argo CD immediately removing its annotation. |
| Rotation gate | var.rotation_enabled remains false until KMS policy, Lambda role, ESO readiness, Reloader role-based access control (RBAC), and mount checks pass | Enable rotation only after every dependency is verified in staging and approved for production. |

### 2.1 Rotation Readiness Gate

Enable production rotation only after each item passes in staging and the production change is approved.

- Run the cluster health check in Section 4.2.

- Confirm ESO can reconcile the target ExternalSecret and create/update the Kubernetes Secret.

- Confirm the KMS key policy permits the ESO reader role and the rotation Lambda execution role when rotation is enabled.

- Confirm Reloader can get/list/watch Secrets and ConfigMaps and patch workloads in the workload namespace.

- Confirm every secret-consuming Deployment, StatefulSet, or DaemonSet has reloader.stakater.com/auto: "true" on root workload metadata.

- Confirm the Argo CD Application ignores Reloader last-reloaded annotations and sets RespectIgnoreDifferences=true.

- Run the secret mount check in Section 8.2.



## 3. Architecture Overview

Git defines the desired cluster state; Terraform defines cloud control-plane resources; AWS Secrets Manager stores secret values; ESO syncs them into Kubernetes Secret objects.

```mermaid
%%{init: {"theme": "base", "flowchart": {"htmlLabels": true, "nodeSpacing": 115, "rankSpacing": 85, "curve": "basis"}, "themeVariables": {"fontFamily": "Roboto, Arial, sans-serif", "fontSize": "16px", "primaryTextColor": "#111827", "secondaryTextColor": "#111827", "tertiaryTextColor": "#111827", "lineColor": "#374151", "edgeLabelBackground": "#ecfdf5"}}}%%
flowchart TD
  subgraph gitops["GitOps path"]
    direction TB
    pr["Developer PR<br/>opens change"]
    ci["CI guardrails<br/>block unsafe diff"]
    main["Protected main<br/>receives merge"]
    argocd["Argo CD sync<br/>applies desired state"]
    eks["Amazon EKS<br/>runs target state"]
    pr --> ci --> main --> argocd --> eks
  end

  subgraph cloud["Terraform-owned cloud controls"]
    direction TB
    tf["Terraform<br/>declares cloud state"]
    iam["IAM roles<br/>scope access"]
    kms["KMS policy<br/>controls decrypt"]
    smMeta["Secrets Manager<br/>metadata and rotation"]
    sm["AWS secret path<br/>stores values"]
    tf --> iam --> kms --> smMeta --> sm
  end

  subgraph runtime["Runtime secret sync and refresh"]
    direction TB
    eso["ESO<br/>syncs approved value"]
    k8sSecret["Kubernetes Secret<br/>object updated"]
    reloader["Reloader<br/>detects data change"]
    apiPatch["Kubernetes API server<br/>metadata patch"]
    rollout["Workload controller<br/>rolls pods safely"]
    eso --> k8sSecret --> reloader
    reloader -->|"Patch .spec.template<br/>metadata"| apiPatch
    apiPatch -->|"Native rolling update"| rollout
  end

  eks -. "Hosts ESO + Reloader<br/>and workloads inside EKS" .-> eso
  sm -->|"Scoped read only<br/>dedicated ESO reader<br/>IRSA role<br/>path nova/&lt;service&gt;/*"| eso

  style gitops fill:#eef2ff,stroke:#4338ca,stroke-width:2px,color:#312e81
  style cloud fill:#fffbeb,stroke:#d97706,stroke-width:2px,color:#78350f
  style runtime fill:#ecfdf5,stroke:#0d9488,stroke-width:2px,color:#134e4a
  classDef gitopsNode fill:#f5f7ff,stroke:#4338ca,color:#111827,stroke-width:2px
  classDef cloudNode fill:#fff7ed,stroke:#b45309,color:#111827,stroke-width:2px
  classDef runtimeNode fill:#f0fdfa,stroke:#0d9488,color:#111827,stroke-width:2px
  class pr,ci,main,argocd,eks gitopsNode
  class tf,iam,kms,smMeta,sm cloudNode
  class eso,k8sSecret,reloader,apiPatch,rollout runtimeNode
```

!!! note "Accessible Diagram Summary"
    The diagram shows three paths: GitOps, Terraform-owned cloud controls, and runtime secret sync. GitOps moves a reviewed PR through CI, protected main, Argo CD, and Amazon EKS. Terraform defines IAM, KMS, Secrets Manager metadata, rotation config, and the approved AWS secret path.

    Amazon EKS hosts ESO, Reloader, application pods, and other runtime controllers. Only ESO reads AWS Secrets Manager, using a dedicated IRSA role scoped to `nova/<service>/*`. Application pods do not receive broad Secrets Manager read access.

    ESO syncs the approved value into a Kubernetes Secret. Reloader detects the change and patches workload Pod template metadata through the Kubernetes API server, triggering a rolling restart by the workload controller.

## 4. Prerequisites and Tooling

The platform team pins exact versions in the infrastructure repository. Check compatibility before opening a deployment PR.

| Tool / Resource | Requirement | Purpose |
| --- | --- | --- |
| AWS CLI | v2; approved role | EKS auth, read-only validation, and break-glass evidence |
| kubectl | Compatible with cluster | Health, rollout, RBAC, and Secret-object checks |
| Helm | 3.x; platform-pinned | Chart rendering during local validation and CI |
| Argo CD CLI | Compatible with server | Application status, sync, wait, history, rollback |
| Terraform | Version pinned by infra repo | IAM, KMS, Secrets Manager metadata, rotation config |
| External Secrets Operator | Platform-pinned; custom resource definitions (CRDs) installed | Syncs AWS Secrets Manager values to Kubernetes Secret objects |
| ESO controller RBAC | `create` on `serviceaccounts/token` for ServiceAccounts referenced by `auth.jwt.serviceAccountRef` | Allows ESO to request short-lived projected tokens through the Kubernetes TokenRequest API |
| Reloader | Platform-pinned; reload strategy = annotations | Triggers rolling restarts when watched Secrets/ConfigMaps change |
| Python + PyYAML | Python 3.x and PyYAML | Fast CI guardrail for rendered workload annotations |
| jq | 1.6 or later | Safe JSON construction during approved secret seeding |
| Approved password manager or privileged access management (PAM) CLI | Platform-approved client, authenticated with multi-factor authentication (MFA) | Supplies the initial secret value to the seeding workflow without exposing it to a shell |

### 4.1 Local Tool Validation

Run these checks before editing the GitOps repository. If any command fails, fix local access or tooling before opening the PR.

```bash
aws --version
kubectl version --client=true
helm version --short
argocd version --client
terraform version
python3 -c "import yaml; print('PyYAML available')"
jq --version
```

### 4.2 Cluster Health Check

Run this before every release cycle. All controllers must be healthy before sync, rollback, or rotation work proceeds.

The RBAC checks use `kubectl auth can-i --as` to test controller ServiceAccount permissions. The operator or CI identity must be allowed to impersonate those accounts; most production operator roles should not have broad impersonation rights. If you lack permission, have a platform administrator or approved CI identity run this block and attach the non-secret results to the deployment ticket.

```bash
set -euo pipefail

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_can_i_as() {
  local subject="$1"
  local message="$2"
  shift 2

  if ! kubectl auth can-i "$@" --as "${subject}" --quiet; then
    fail "${message}"
  fi
}

kubectl wait --for=condition=Ready node --all --timeout=120s \
  || fail "One or more cluster nodes are not Ready."

kubectl wait --for=condition=Available deployment --all \
  -n argocd --timeout=120s \
  || fail "One or more Argo CD deployments are unavailable."

kubectl rollout status statefulset/argocd-application-controller \
  -n argocd --timeout=120s \
  || fail "Argo CD application controller is not ready."

kubectl wait --for=condition=Available deployment --all \
  -n <eso-controller-namespace> --timeout=120s \
  || fail "One or more ESO deployments are unavailable."

kubectl wait --for=condition=Available deployment --all \
  -n <reloader-namespace> --timeout=120s \
  || fail "Reloader is unavailable."

RELOADER_STRATEGY=$(kubectl get deploy <reloader-deployment-name> \
  -n <reloader-namespace> \
  -o jsonpath='{.spec.template.spec.containers[*].args}{" "}{.spec.template.spec.containers[*].env[?(@.name=="RELOAD_STRATEGY")].value}' \
  | tr '",[]' '    ')

printf '%s\n' "${RELOADER_STRATEGY}" \
  | grep -Eqi '(^|[[:space:]])(--)?reload-strategy[=[:space:]]+annotations([[:space:]]|$)|(^|[[:space:]])annotations([[:space:]]|$)' \
  || fail "Reloader is not configured with the required annotations reload strategy."

ESO_SA=$(kubectl get deploy <eso-controller-deployment-name> \
  -n <eso-controller-namespace> \
  -o jsonpath='{.spec.template.spec.serviceAccountName}')

RELOADER_SA=$(kubectl get deploy <reloader-deployment-name> \
  -n <reloader-namespace> \
  -o jsonpath='{.spec.template.spec.serviceAccountName}')

test -n "${ESO_SA}" \
  || fail "Could not resolve the ESO controller ServiceAccount."

test "${RELOADER_SA}" = "<reloader-sa-name>" \
  || fail "Reloader is using '${RELOADER_SA}', not the expected '<reloader-sa-name>'."

ESO_SUBJECT="system:serviceaccount:<eso-controller-namespace>:${ESO_SA}"
RELOADER_SUBJECT="system:serviceaccount:<reloader-namespace>:${RELOADER_SA}"

require_can_i_as \
  "${ESO_SUBJECT}" \
  "ESO cannot create TokenRequest objects for the referenced ServiceAccount in <namespace>." \
  create serviceaccounts/token -n <namespace>

for verb in get list watch; do
  require_can_i_as \
    "${RELOADER_SUBJECT}" \
    "Reloader cannot ${verb} Secrets in <namespace>." \
    "${verb}" secrets -n <namespace>

  require_can_i_as \
    "${RELOADER_SUBJECT}" \
    "Reloader cannot ${verb} ConfigMaps in <namespace>." \
    "${verb}" configmaps -n <namespace>
done

for workload in deployments.apps statefulsets.apps daemonsets.apps; do
  for verb in get list update patch; do
    require_can_i_as \
      "${RELOADER_SUBJECT}" \
      "Reloader cannot ${verb} ${workload} in <namespace>." \
      "${verb}" "${workload}" -n <namespace>
  done
done
```

The strategy check normalizes the `jsonpath` array for `args` to match both `--reload-strategy=annotations` and `--reload-strategy annotations`. Confirm the flag and environment-variable names against the platform-pinned Reloader chart version before relying on this check.

| Component | Pass Criteria |
| --- | --- |
| Nodes | All schedulable nodes report Ready and no unexpected NoSchedule taints. |
| Argo CD | server, repo-server, application-controller, and dex are Running. |
| ESO | Controller and webhook are Running; the controller can `create` `serviceaccounts/token` for the namespace that contains the referenced ServiceAccount; ExternalSecret status becomes Ready after apply. |
| Reloader | Live deployment uses the annotations reload strategy and can read watched Secrets/ConfigMaps and update each supported workload type. |
| EKS API-data encryption | Clusters below Kubernetes 1.28 must have explicit Secrets envelope encryption configured; EKS clusters running 1.28 or later receive default envelope encryption for all Kubernetes API data. See the [AWS default envelope encryption documentation](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html). |

## 5. IAM, KMS, SecretStore, and ESO Setup

!!! info "Section Summary"
    Create two narrowly scoped IRSA roles per service: a workload role for non-secret AWS access, and an ESO reader role for service-scoped Secrets Manager reads and KMS decryption through Secrets Manager. Terraform manages the cloud resources; Kubernetes manifests bind the matching ServiceAccounts.

### 5.1 Role Model

| Role / Account | Used By | Allowed Access | Explicitly Not Allowed |
| --- | --- | --- | --- |
| `nova-<service>-prod` | Workload ServiceAccount `<workload-sa-name>` | Only the non-secret AWS APIs the application needs, such as S3 or DynamoDB | No Secrets Manager read permissions |
| `nova-<service>-eso-read` | ServiceAccount `<service>-eso-secret-reader` | `secretsmanager:GetSecretValue`, `DescribeSecret`, and `ListSecretVersionIds` for `nova/<service>/*`, plus KMS decrypt through Secrets Manager | No wildcard paths; no trust for other service accounts |
| rotation Lambda role | Approved Secrets Manager rotation Lambda | Rotation-only actions and KMS use through Secrets Manager when rotation is enabled | Not present in KMS policy while var.rotation_enabled=false |

### 5.2 Terraform Pattern

Confirm the EKS OpenID Connect (OIDC) issuer before provisioning IRSA. This check is read-only; create IAM resources through Terraform.

```bash
aws eks describe-cluster \
  --name <cluster-name> \
  --region <region> \
  --query "cluster.identity.oidc.issuer" \
  --output text
```

Create or update service IAM resources through `infra/iam/<service>.tf`. This example restricts the ESO reader role to the dedicated ESO secret-reader ServiceAccount.

```hcl
locals {
  oidc_provider = replace(var.oidc_provider_url, "https://", "")
  eso_sa_sub    = "system:serviceaccount:${var.namespace}:${var.service}-eso-secret-reader"
}

data "aws_iam_policy_document" "eso_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${var.account_id}:oidc-provider/${local.oidc_provider}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider}:sub"
      values   = [local.eso_sa_sub]
    }
  }
}

resource "aws_iam_role" "eso_read" {
  name               = "nova-${var.service}-eso-read"
  assume_role_policy = data.aws_iam_policy_document.eso_assume_role.json
}
```

Attach the secret-read policy only to `nova-<service>-eso-read`, never to the workload role. Pass the Amazon Resource Name (ARN) of the KMS key that encrypts the service secret through the typed `secrets_kms_key_arn` input.

```hcl
variable "secrets_kms_key_arn" {
  description = "ARN of the KMS key that encrypts this service's Secrets Manager secrets"
  type        = string
}

data "aws_iam_policy_document" "eso_read" {
  statement {
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecretVersionIds"
    ]
    resources = [
      "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:nova/${var.service}/*"
    ]
  }

  statement {
    actions   = ["kms:Decrypt"]
    resources = [var.secrets_kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "eso_read" {
  name   = "nova-${var.service}-eso-read"
  role   = aws_iam_role.eso_read.id
  policy = data.aws_iam_policy_document.eso_read.json
}
```

!!! info "KMS Source of Truth"
    The same KMS key ARN must be used by the Secrets Manager secret, the `nova-<service>-eso-read` IAM policy, the KMS key policy, and the rotation Lambda role policy. If the platform uses a shared externally managed key, verify the key policy before merge.

### 5.3 ServiceAccount and SecretStore Manifests

Prefer keeping ServiceAccount manifests in charts/ to version-control IAM bindings. Keep the workload and ESO reader ServiceAccounts separate.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <service>-eso-secret-reader
  namespace: <namespace>
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/nova-<service>-eso-read
```

Define each service's SecretStore in its workload namespace. Use ClusterSecretStore for application secrets only with a platform-approved cross-namespace exception.

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secrets-manager-<service>
  namespace: <namespace>
spec:
  provider:
    aws:
      service: SecretsManager
      region: <region>
      auth:
        jwt:
          serviceAccountRef:
            name: <service>-eso-secret-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: <service>-app-secrets
  namespace: <namespace>
spec:
  refreshInterval: 5m
  secretStoreRef:
    name: aws-secrets-manager-<service>
    kind: SecretStore
  target:
    name: <service>-app-secrets
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_PASSWORD
      remoteRef:
        key: nova/<service>/db
        property: password
```

remoteRef.key must match the Terraform-managed Secrets Manager name pattern: `nova/<service>/<secret_name>`. Do not use kubectl, Git, or Terraform to set production secret values.

### 5.4 Approved Secret-Seeding Workflow

Seeding sets the initial secret value and is the only approved human write path for production secrets. Terraform manages Secrets Manager metadata, KMS policy, and rotation config; Section 2 forbids `aws_secretsmanager_secret_version` for production values. An approved administrator creates the first AWSCURRENT version once, using this procedure.

!!! warning "Where seeding is allowed to happen"
    If your organization forbids production secrets on workstations, seed through the PAM session broker, an approved bastion or jump host, or a CI job. The CI job must assume the seeding role through OIDC and read the value from the approved secret broker. The commands are the same; only the host and identity change. Record the path used in the deployment ticket.

1. A platform administrator retrieves the initial value from the approved password manager or PAM workflow.

2. The administrator opens a private session with MFA. **The secret value is never typed, pasted, echoed, or interpolated into a shell.** It flows from the password manager through the input stream to AWS and appears nowhere else.

    !!! danger "Do not disable session controls"
        Keep shell history and terminal recording enabled. PAM session capture is required, and step 7 relies on its audit trail. Both forms below keep the value out of process arguments (`argv`) and shell history without disabling these controls.

3. Use one of these approved forms. Both read directly from the password-manager CLI, keeping the value out of the shell prompt, `argv`, and history.

    **Form A, no file on disk (preferred).** Process substitution passes a file descriptor to the AWS CLI without writing a plaintext copy to the filesystem.

    ```bash
    # Requires bash or zsh. Use Form B in a POSIX shell.
    aws secretsmanager put-secret-value \
      --secret-id nova/<service>/<secret_name> \
      --secret-string file://<(<password-manager-cli> read "<pm-item-reference>" \
        | jq -Rn '{password: input}')
    ```

    **Form B, temporary file with restricted permissions.** Set the umask *before* creating the file; applying `chmod` afterward leaves a window in which it is world-readable.

    ```bash
    umask 077                                   # every file created in this shell is 0600
    SECURE_DIR="$(mktemp -d)"                   # encrypted local storage, or /dev/shm
    SECRET_FILE="${SECURE_DIR}/<service>-secret.json"

    <password-manager-cli> read "<pm-item-reference>" \
      | jq -Rn '{password: input}' > "${SECRET_FILE}"

    ls -l "${SECRET_FILE}"                      # confirm 0600 before continuing
    ```

    !!! danger "Never place the value in argv"
        Do not use `--secret-string "$(<password-manager-cli> read ...)"` or hand-write the JSON in a heredoc. Command substitution exposes plaintext in process arguments to `ps` and local processes while the command runs. A heredoc requires pasting the value into the terminal, which step 2 forbids.

    !!! note "If no password-manager CLI is available"
        Export the value from the password manager directly to the pre-created 0600 path using the manager's own save-to-file function. Do not route it through the terminal, the clipboard, or an editor buffer.

    `jq -Rn '{password: input}'` reads one line from stdin and JSON-escapes it. Do not build the JSON by hand: a value containing `"`, `\`, or a newline produces a malformed document or a silently truncated secret.

4. Create the first AWSCURRENT version with `put-secret-value` and a file reference. Form A already does this; for Form B, use the file from step 3.

    ```bash
    aws secretsmanager put-secret-value \
      --secret-id nova/<service>/<secret_name> \
      --secret-string "file://${SECRET_FILE}"
    ```

5. Verify with `describe-secret` only. Do not use `get-secret-value` during deployment verification.

    ```bash
    aws secretsmanager describe-secret \
      --secret-id nova/<service>/<secret_name> \
      --query "{Name:Name,VersionIdsToStages:VersionIdsToStages,KmsKeyId:KmsKeyId}"
    ```

6. Form B only: remove the temporary file and directory immediately after seeding.

    ```bash
    shred -u "${SECRET_FILE}" 2>/dev/null || rm -f "${SECRET_FILE}"
    rmdir "${SECURE_DIR}"
    unset SECRET_FILE SECURE_DIR
    ```

    !!! note "shred is not a guarantee"
        On copy-on-write filesystems and SSDs with wear leveling, `shred` cannot reliably overwrite the original blocks. Prefer Form A, or place `SECURE_DIR` on a memory-backed path such as `/dev/shm` so no block reaches persistent storage.

7. Record only non-secret evidence in the deployment ticket: secret ARN/name, KMS key ID, AWSCURRENT version ID, seeding path used (workstation, PAM, bastion, or CI), approver, timestamp, and rotation-readiness status.

## 6. GitOps Repository Layout

One GitOps repository defines NovaDeploy cluster state: manifests, Helm overrides, ExternalSecret resources, cluster baselines, and infrastructure modules. Application source code lives in separate repositories.

```text
nova-gitops/
  apps/                          # Argo CD Application manifests
  clusters/production/           # AppProject, root app, namespaces, policy baseline
  charts/<service>/              # Service Helm chart
  envs/production/values/        # Production value overrides
  secrets/external/              # ExternalSecret CRs only; no plaintext secrets
  infra/iam/<service>.tf         # IAM, KMS, Secrets Manager metadata, rotation config
  scripts/check-reloader-annotations.sh
  .github/workflows/             # lint, render, kubeconform, secret scan, guardrails
```

| Path | Owner | Review Focus |
| --- | --- | --- |
| `apps/` | Platform engineering | Application project, destination, sync policy, `ignoreDifferences` |
| `clusters/production/` | Platform engineering | AppProject, sync windows, namespace baseline |
| `charts/<service>/` | Service team + platform reviewer | Workload metadata annotations, probes, resources, service accounts |
| `envs/production/values/` | Service team | Image tag, config values, environment-specific overrides |
| `secrets/external/` | Platform engineering | ExternalSecret references only; no secret values |
| `infra/iam/<service>.tf` | Platform engineering | IAM trust boundaries, KMS policy, Secrets Manager metadata, rotation gates |
| `scripts/` | Platform engineering | Guardrail correctness, fail-closed behavior, and portability |
| `.github/workflows/` | Platform engineering | Required checks, pinned actions, and least-privilege workflow permissions |

## 7. Argo CD Application and Sync Policy

This Application manifest combines automated sync, server-side apply, and Reloader compatibility. Create production namespaces through clusters/production/ so NetworkPolicy, ResourceQuota, LimitRange, labels, and admission policies exist before workload sync.

!!! warning "Auto-Prune Boundary"
    Enable `prune: true` in production only when the production AppProject and sync windows constrain the Application. Without these controls, a bad merge, path mistake, or unauthorized destination can trigger automatic deletion.

Configure both settings: `ignoreDifferences` excludes the Reloader-managed annotation when Argo CD compares live and desired state; `RespectIgnoreDifferences=true` also applies that exclusion during sync.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: api-gateway
  namespace: argocd
spec:
  project: novadeploy-production
  source:
    repoURL: https://github.com/novadeploy/nova-gitops
    targetRevision: main
    path: charts/api-gateway
    helm:
      valueFiles:
        - ../../envs/production/values/api-gateway.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: api-gateway
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
      - RespectIgnoreDifferences=true
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/template/metadata/annotations/reloader.stakater.com~1last-reloaded-from
    - group: apps
      kind: StatefulSet
      jsonPointers:
        - /spec/template/metadata/annotations/reloader.stakater.com~1last-reloaded-from
    - group: apps
      kind: DaemonSet
      jsonPointers:
        - /spec/template/metadata/annotations/reloader.stakater.com~1last-reloaded-from
```

| Setting | Meaning | Operational Note |
| --- | --- | --- |
| prune: true | Resources removed from Git are removed from the cluster on sync. | Treat deletions as production changes; require review. |
| selfHeal: true | Manual drift is reverted to Git state. | Do not hotfix production with direct kubectl edits. |
| ServerSideApply=true | Kubernetes tracks field ownership during apply. | Preferred for shared resources and conflict detection. |
| RespectIgnoreDifferences=true | Argo CD respects ignoreDifferences during sync. | Prevents sync from removing Reloader last-reloaded annotations. |
| No CreateNamespace=true | Production namespaces are not created ad hoc by service apps. | Cluster baseline creates namespaces with required policy first. |

### 7.1 Sync Windows

Sync windows are defined in the AppProject. This project has a matching `allow` window, so automated and manual syncs are blocked outside that schedule. An optional `deny` window can block shorter periods within the allowed schedule; it is not needed for nights or weekends.

| Window / State | Effect | Operator Action |
| --- | --- | --- |
| Monday-Friday 09:00-17:00 UTC; matching allow window active | Routine automated or manual sync is permitted after PR approval. | Sync normally, then complete Section 8 verification. |
| All other times; no matching allow window active | Routine sync is blocked by default, including Monday-Thursday overnight. | Wait for the next allow window unless an approved incident requires a manual override. |
| Approved emergency manual override | `manualSync` is temporarily enabled on the matching allow window. | Enable the override by window ID, perform one manual sync, verify, and disable the override immediately. |

## 8. Deployment Verification

Close the deployment ticket only after all checks pass and the evidence contains no secret values. Validate object state, expected key names, mount success, rollout state, and recent pod creation time only.

### 8.1 Health and Secret Checks

```bash
argocd app get <app-name> --refresh
argocd app wait <app-name> --health
kubectl rollout status deployment/<service> -n <namespace>

kubectl get externalsecret <service>-app-secrets -n <namespace>
kubectl describe externalsecret <service>-app-secrets -n <namespace>
kubectl get secret <service>-app-secrets -n <namespace>
kubectl get secret <service>-app-secrets -n <namespace> \
  -o go-template='{{range $k, $_ := .data}}{{printf "%s\n" $k}}{{end}}'
# Expected: ExternalSecret Ready=True and expected key names are present.
# Never print or decode values.
```

### 8.2 Secret Mount Check

This disposable pod checks that the Secret mounts and is readable without exposing values. It prints only `secret-mounted` on success.

The manifest meets the restricted Pod Security profile and namespace resource controls in `clusters/production/` (Section 7). These namespaces reject pods without a `securityContext` or `resources` block before attempting a mount. Run this check in the Secret's workload namespace; mounts cannot be checked across namespaces.

```bash
cat <<'EOF' | kubectl apply -n <namespace> -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-mount-check
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: secret-mount-check
      image: busybox:1.36
      command: ["sh", "-ec", "test -s /mnt/secrets/DATABASE_PASSWORD && test -r /mnt/secrets/DATABASE_PASSWORD && echo secret-mounted"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 50m
          memory: 32Mi
      volumeMounts:
        - name: app-secrets
          mountPath: /mnt/secrets
          readOnly: true
  volumes:
    - name: app-secrets
      secret:
        secretName: <service>-app-secrets
        defaultMode: 0440
EOF
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/secret-mount-check \
  -n <namespace> --timeout=60s
kubectl logs secret-mount-check -n <namespace>
kubectl delete pod secret-mount-check -n <namespace> --ignore-not-found
```

| Field | Why it is required |
| --- | --- |
| `runAsNonRoot: true` plus `runAsUser` | Restricted Pod Security requires a non-root user. With `busybox:1.36`, `runAsNonRoot` alone causes `CreateContainerConfigError` because the image defaults to root. An explicit user ID (UID) is required. |
| `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault` | Remaining restricted-profile requirements. Omitting any one rejects the pod at admission. |
| `resources` requests and limits | The namespace baseline applies ResourceQuota and LimitRange. A pod with no resources block is rejected by a quota covering requests or limits unless a LimitRange supplies defaults. |
| `automountServiceAccountToken: false` | A disposable debug pod in a namespace built on IRSA separation must not receive a projected ServiceAccount token. |
| `fsGroup: 1000` with `defaultMode: 0440` | Kubernetes sets the mounted Secret's group ownership to `fsGroup`, allowing the non-root UID to read it regardless of cluster defaults. |

!!! warning "Mount mode and UID are coupled"
    The default Secret mode, 0644, allows any UID to read the file. With mode 0400 and no `fsGroup`, a non-root container cannot read it: `test -s` passes because the file exists and is not empty, but `test -r` fails. This permissions problem can look like a failed mount. Set `defaultMode` and `fsGroup` explicitly, as above, to avoid that ambiguity.

!!! note "kubectl compatibility"
    `--for=jsonpath` requires kubectl 1.23 or later. The pod exits immediately after the check, so `--for=condition=Ready` can miss it and time out even after success. On older clients, poll instead: `kubectl get pod secret-mount-check -n <namespace> -o jsonpath='{.status.phase}'`.

**Pass criteria.** The pod reaches Succeeded, the log contains exactly `secret-mounted`, and the pod is deleted. If admission rejects the pod, first align the manifest with the namespace's Pod Security level and resource controls. That rejection does not establish a problem with the Secret.

### 8.3 Reloader Confirmation

```bash
kubectl rollout status deployment/<service> -n <namespace>
kubectl get deploy <service> -n <namespace> \
  -o go-template='{{ index .spec.template.metadata.annotations "reloader.stakater.com/last-reloaded-from" }}{{ "\n" }}'
kubectl get pods -n <namespace> -l app=<service> \
  --sort-by=.metadata.creationTimestamp
argocd app get <app-name> --refresh
# Expected: pods were recreated after the Secret refresh; app remains Synced / Healthy.
```

## 9. Rollback and Recovery

!!! warning "Rollback Principle"
    Use Git revert by default to preserve the source of truth and audit trail. Argo CD history rollback requires an approved emergency exception (break-glass). The matching Git revert must then merge to bring Git back in line with the cluster.

| Scenario | Strategy | Operator Note |
| --- | --- | --- |
| Bad image tag promoted | Git revert | Revert the image-bump commit, pass CI, merge, then sync or wait for automation. |
| Wrong Helm values or Application manifest | Git revert | Revert the change in Git so it continues to define the desired state. |
| Application unreachable and SLA at risk | Argo CD history rollback | Use only if Argo CD and the Kubernetes API are reachable and Git revert cannot meet the SLA. Follow Section 9.2. |
| GitHub or CI outage blocks revert | Argo CD history rollback | Roll back to the last-good revision while Git or CI is unavailable, and record non-secret evidence. Follow Section 9.2. |
| Secret value misconfiguration | Secrets Manager rollback + ESO re-sync | Roll back through the approved secret process. Use Git revert only for SecretStore, ExternalSecret, IAM, KMS, or rotation-config changes. |
| Cluster unreachable | Infrastructure troubleshooting | Do not use Argo CD. Troubleshoot EKS control plane, networking, IAM, and node health first. |

### 9.1 Git Revert

1. Identify the bad commit SHA and the last-good commit in nova-gitops.

2. Create a revert branch from protected main.

3. Check whether the bad commit is single-parent or a merge commit.

4. Open a PR, require emergency approval, merge, then sync or wait for automation.

5. Run the full Section 8 verification path before closing the incident.

```bash
git checkout main && git pull
git checkout -b revert/<bad-sha>

git show -s --format=%P <bad-sha>
# If one parent SHA is returned:
git revert <bad-sha> --no-edit
# If two or more parent SHAs are returned, keep main as parent 1:
git revert -m 1 <bad-sha> --no-edit

git push origin revert/<bad-sha>
```

If the allow schedule blocks an approved emergency sync, use this manual-sync override. Automated sync remains blocked outside the allow window.

```bash
argocd proj windows list <project>
argocd proj windows enable-manual-sync <project> <allow-window-id>
argocd app sync <app-name>
argocd app wait <app-name> --health
argocd proj windows disable-manual-sync <project> <allow-window-id>
```

### 9.2 Argo CD History Rollback

Use only when a Git revert cannot meet the SLA deadline. If an App-of-Apps root app manages child Application CRs, suspend it during the approved incident window; otherwise, it may re-enable the child app and re-sync the broken commit.

Run the break-glass sequence in this order:

1. Confirm Argo CD and the Kubernetes API are reachable.

2. Record the root and target Applications' current sync-policy settings in the incident ticket. Do not export and re-apply the full live Application object: it includes server-managed fields and may bypass the Git-managed definition.

3. Suspend the App-of-Apps root app, then disable auto-sync on the target Application.

4. Roll back the target Application to the last-good revision and wait for health.

5. Keep both suspended until the matching Git revert merges.

```bash
argocd app get <root-app-name> --refresh
argocd app get <app-name> --refresh
argocd app list --selector app.kubernetes.io/part-of=<root-app-name>
argocd app set <root-app-name> --sync-policy none
argocd app set <app-name> --sync-policy none
argocd app history <app-name>
argocd app rollback <app-name> <revision-number>
argocd app wait <app-name> --health
# Leave target auto-sync disabled until the mandatory Git revert merges.
```

Restore Git and cluster consistency after the incident:

1. Open a Jira ticket tagged [gitops-debt].

2. Complete the matching Git revert within 24 hours.

3. After the revert PR merges, restore the target and root Applications with `argocd app set` using their exact pre-incident, Git-declared policies.

4. Refresh both Applications and confirm they return to their pre-incident sync policies and the reverted Git revision.

The example below assumes both Applications normally use automated sync, prune, and self-heal. Remove any flag that was not enabled in the Git-managed definition.

```bash
argocd app set <app-name> \
  --sync-policy automated \
  --auto-prune \
  --self-heal

argocd app set <root-app-name> \
  --sync-policy automated \
  --auto-prune \
  --self-heal

argocd app get <app-name> --refresh
argocd app get <root-app-name> --refresh
```

## 10. Appendices

### 10.1 CI Reloader Annotation Guardrail

This guardrail checks each rendered workload, so one correct Deployment annotation cannot hide a missing root annotation on another workload that uses secrets. Match the Helm release name to `Application.metadata.name` and `--namespace` to `Application.spec.destination.namespace`. If `source.helm.releaseName` is set, use that override.

```bash
#!/usr/bin/env bash
set -euo pipefail

rendered="$(mktemp)"
trap 'rm -f "$rendered"' EXIT

release_name="<app-name>"          # Application.metadata.name
target_namespace="<namespace>"     # Application.spec.destination.namespace

helm template "${release_name}" charts/<service> \
  --namespace "${target_namespace}" \
  -f envs/production/values/<service>.yaml \
  > "$rendered"

python3 - "$rendered" <<'PY'
import sys
import yaml

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet"}
SECRET_KEYS = {"secretKeyRef", "secretRef", "secretName", "secret"}  # "secret": projected volume sources


def uses_secret(node):
    if isinstance(node, dict):
        return bool(SECRET_KEYS & node.keys()) or any(
            uses_secret(value) for value in node.values()
        )
    if isinstance(node, list):
        return any(uses_secret(value) for value in node)
    return False


missing = []

with open(sys.argv[1], encoding="utf-8") as rendered:
    for obj in yaml.safe_load_all(rendered):
        if not isinstance(obj, dict) or obj.get("kind") not in WORKLOADS:
            continue

        meta = obj.get("metadata") or {}
        pod = obj.get("spec", {}).get("template", {}).get("spec", {})
        annotations = meta.get("annotations") or {}

        if (
            uses_secret(pod)
            and annotations.get("reloader.stakater.com/auto") != "true"
        ):
            missing.append(
                f'{obj["kind"]}/{meta.get("name", "<unknown>")}'
            )

if missing:
    print(
        'ERROR: secret-consuming workloads missing '
        'reloader.stakater.com/auto="true":',
        file=sys.stderr,
    )
    print(
        "\n".join(f"  - {item}" for item in missing),
        file=sys.stderr,
    )
    sys.exit(1)
PY
```

With the temporary file and `set -euo pipefail`, a failed `helm template` stops the job before Python runs. The script checks Deployment, StatefulSet, and DaemonSet pod specs; Ingress `tls.secretName` values do not cause false positives. Use kubeconform and admission policy for broader structural checks.

### 10.2 Evidence Checklist

| Evidence Item | Acceptable Example | Forbidden Evidence |
| --- | --- | --- |
| Argo CD state | Screenshot or text showing Synced / Healthy | None |
| ExternalSecret state | Ready=True, SecretSynced reason, recent refresh time | Secret value output |
| Kubernetes Secret | Object exists and expected key names are present | Decoded data or base64 content |
| Mount check | Disposable pod reached Succeeded; log shows only secret-mounted | cat/print of mounted file content |
| Reloader rollout | Rollout status and pod creation times after Secret refresh | Secret payload |
| Rollback | Revert PR link, approval, commit SHA, app health after sync | Manual kubectl patch not represented in Git |

### 10.3 Common Placeholders

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `<ACCOUNT_ID>` | AWS account ID | `123456789012` |
| `<region>` | AWS region for EKS, Secrets Manager, and KMS | `us-east-1` |
| `<namespace>` | Kubernetes namespace for the workload | `api-gateway` |
| `<service>` | NovaDeploy service name | `api-gateway` |
| `<cluster-name>` | EKS cluster name | `nova-prod` |
| `<app-name>` | Argo CD Application name | `api-gateway` |
| `<project>` | Argo CD AppProject name | `novadeploy-production` |
| `<bad-sha>` | Git commit SHA being reverted | `9f28b6c` |
| `<revision-number>` | Argo CD history revision number | `42` |
| `<root-app-name>` | App-of-Apps root Application name | `novadeploy-production-root` |
| `<secret_name>` | Service-scoped Secrets Manager secret suffix | `db` |
| `<password-manager-cli>` | Approved password manager or PAM command-line client | `op` |
| `<pm-item-reference>` | Item reference within the approved password manager | `op://Platform/nova-api-gateway-db/password` |
| `<allow-window-id>` | Argo CD sync-window ID | `7` |
| `<workload-sa-name>` | Workload Kubernetes ServiceAccount | `api-gateway-sa` |
| `<eso-controller-namespace>` | Namespace where ESO runs | `external-secrets` |
| `<eso-controller-deployment-name>` | ESO controller Deployment name | `external-secrets` |
| `<reloader-namespace>` | Namespace where Reloader runs | `reloader` |
| `<reloader-deployment-name>` | Reloader Deployment name | `reloader` |
| `<reloader-sa-name>` | Expected Reloader ServiceAccount name | `reloader` |
