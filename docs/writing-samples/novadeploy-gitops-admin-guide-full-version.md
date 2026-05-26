# NovaDeploy Platform: GitOps Administration Guide

This writing sample is the full fictional operator runbook for deploying services to Amazon EKS with Argo CD. It shows how complex EKS, IAM, KMS, secrets, GitOps, and rollback workflows can be turned into prescriptive production guidance.

*Deploying Services to Amazon EKS with Argo CD*  
Version 1.0 | Status: Full runbook | Written by: Jeff Slavin

[Read the portfolio cut.](novadeploy-gitops-admin-guide-portfolio-cut.md)

!!! note "Portfolio Notice"
    NovaDeploy is a fictional platform created for portfolio purposes. This sample contains no proprietary employer, client, or production information.

!!! info "Document Purpose"
    This full runbook shows how a documentation lead can turn a complex EKS/GitOps/DevSecOps workflow into prescriptive operator guidance: one source of truth, clear stop points, auditable checks, and safe rollback paths.

!!! info "Scope and Audience"
    **Scope:** Provides an operator runbook for deploying and recovering fictional NovaDeploy services on Amazon EKS with Argo CD. It covers GitOps workflow, IAM/KMS/Secrets Manager controls, External Secrets Operator, Reloader, verification, and rollback. It excludes application-code changes, broader incident response, and service-specific business logic.

    **Audience:** Platform engineers, DevOps/SRE operators, cloud engineers, and technical documentation reviewers who need prescriptive production guidance for GitOps-managed Kubernetes services.

## 1. Quick Start and Stop Conditions

Use this path for standard, non-emergency production deployments. It gives operators one visible workflow before the guide expands into implementation detail.

| Step | Action | What to Do | Stop Condition |
| --- | --- | --- | --- |
| 1 | Validate readiness | Run controller health checks, local tool checks, and the guardrail table before editing the deployment PR. | Stop if Argo CD, ESO, or Reloader is unhealthy. |
| 2 | Change declared state | Update Helm values, Argo CD Application resources, ExternalSecret CRs, or Terraform-owned IAM/KMS metadata. | Do not commit or paste plaintext secrets. |
| 3 | Open PR | Require lint, helm template, kubeconform, secret scan, and Reloader annotation guardrail to pass. | Stop if any workload consumes a Secret without the root Reloader annotation. |
| 4 | Merge to main | Merge after approval. Argo CD watches main and reconciles the application. | No direct pushes and no direct kubectl edits. |
| 5 | Sync and verify | Wait for automated sync or run argocd app sync &lt;app-name&gt;; then run health, smoke, and secret-mount checks. | Do not use --force for normal deployment hotfixes. |
| 6 | Close or recover | Close the ticket only after Synced/Healthy, smoke-test success, and non-secret evidence is recorded. | Use Git revert by default; use Argo CD history only for approved SLA emergencies. |

!!! info "Zero-Trust Definition"
    No plaintext secrets in Git, ConfigMaps, literal environment variables, Terraform state, PRs, logs, chats, or tickets. Secret values live in AWS Secrets Manager. ESO syncs values into Kubernetes Secret objects. Reloader propagates changes by controlled rolling restart, not by exposing secret values.

## 2. Deployment Guardrails

This section is the single source of truth for production safety rules. Later procedures cross-reference these rules instead of restating them in slightly different wording.

| Guardrail | Required Evidence | Pass Criteria |
| --- | --- | --- |
| Git is source of truth | main branch protected; all changes through PR; CI passes before merge | Manual cluster drift is rejected or reverted through Argo CD self-heal. |
| Terraform owns cloud controls | IAM roles, policies, KMS keys, Secrets Manager metadata, rotation config, and Lambda permissions are managed in Terraform | AWS CLI create/update commands are read-only validation only unless approved break-glass work is later imported. |
| No plaintext secrets | Secret scan, PR review, and no aws_secretsmanager_secret_version for production values | Secret values never enter Git, Terraform state, PR comments, CI logs, chats, or tickets. |
| IRSA separation | Workload ServiceAccount has non-secret AWS permissions only; dedicated ESO reader ServiceAccount assumes nova-&lt;service&gt;-eso-read | Only ESO reads AWS Secrets Manager for service-scoped paths. |
| Namespace-scoped SecretStore | ExternalSecret uses secretStoreRef.kind: SecretStore in the workload namespace | Avoid ClusterSecretStore for app secrets unless a platform exception is approved. |
| Reloader compatibility | Root workload metadata contains reloader.stakater.com/auto: "true"; Argo CD sets RespectIgnoreDifferences=true | Reloader can patch pod templates without Argo CD immediately applying the annotation away. |
| Rotation gate | var.rotation_enabled remains false until KMS policy, Lambda role, ESO readiness, Reloader RBAC, and mount checks pass | Enable rotation only after every dependency is verified in staging and approved for production. |

### 2.1 Rotation Readiness Gate

Enable production rotation only after each item passes in staging and the production change is approved.

- Run the cluster health check in Section 3.2.

- Confirm ESO can reconcile the target ExternalSecret and create/update the Kubernetes Secret.

- Confirm the KMS key policy permits the ESO reader role and the rotation Lambda execution role when rotation is enabled.

- Confirm Reloader can get/list/watch Secrets and ConfigMaps and patch workloads in the workload namespace.

- Confirm every secret-consuming Deployment, StatefulSet, or DaemonSet has reloader.stakater.com/auto: "true" on root workload metadata.

- Confirm the Argo CD Application ignores Reloader last-reloaded annotations and sets RespectIgnoreDifferences=true.

- Enable var.rotation_enabled only after these checks pass in staging and the production change is approved.

## 3. Prerequisites and Tooling

The platform team pins exact versions in the infrastructure repository. Operators validate compatibility before opening a deployment PR.

| Tool / Resource | Requirement | Purpose |
| --- | --- | --- |
| AWS CLI | v2; approved role | EKS auth, read-only validation, and break-glass evidence |
| Kubectl | Compatible with cluster | Health, rollout, RBAC, and Secret-object checks |
| Helm | 3.x; platform-pinned | Chart rendering during local validation and CI |
| Argo CD CLI | Compatible with server | Application status, sync, wait, history, rollback |
| Terraform | Version pinned by infra repo | IAM, KMS, Secrets Manager metadata, rotation config |
| External Secrets Operator | Platform-pinned; CRDs installed | Syncs AWS Secrets Manager values to Kubernetes Secret objects |
| Reloader | Platform-pinned; reload strategy = annotations | Triggers rolling restarts when watched Secrets/ConfigMaps change |
| Python + PyYAML | Python 3.x and PyYAML | Fast CI guardrail for rendered workload annotations |

### 3.1 Local Tool Validation

Run these checks before editing the GitOps repository. If any command fails, fix local access or tooling before opening the PR.

```bash
aws --version
kubectl version --client=true
helm version --short
argocd version --client
terraform version
python3 -c "import yaml; print('PyYAML available')"
```

### 3.2 Cluster Health Check

Run this before every release cycle. All controllers must be healthy before sync, rollback, or rotation work proceeds.

```bash
kubectl get nodes -o wide                         # All nodes Ready
kubectl get pods -n argocd                       # Argo CD pods Running
kubectl get pods -n <eso-controller-namespace>   # ESO pods Running
kubectl get deploy,pods -n <reloader-namespace>  # Reloader Running

kubectl get deploy <reloader-deployment-name> -n <reloader-namespace> \
  -o yaml | grep -Ei "RELOAD_STRATEGY|reloadStrategy|reload-strategy|annotations"

RELOADER_SA=$(kubectl get deploy <reloader-deployment-name> \
  -n <reloader-namespace> \
  -o jsonpath='{.spec.template.spec.serviceAccountName}')
test "${RELOADER_SA}" = "<reloader-sa-name>"

for verb in get list watch; do
  kubectl auth can-i "${verb}" secrets \
    --as system:serviceaccount:<reloader-namespace>:${RELOADER_SA} \
    -n <namespace>
  kubectl auth can-i "${verb}" configmaps \
    --as system:serviceaccount:<reloader-namespace>:${RELOADER_SA} \
    -n <namespace>
done

kubectl auth can-i patch deployments.apps \
  --as system:serviceaccount:<reloader-namespace>:${RELOADER_SA} \
  -n <namespace>
```

| Component | Pass Criteria |
| --- | --- |
| Nodes | All schedulable nodes report Ready and no unexpected NoSchedule taints. |
| Argo CD | server, repo-server, application-controller, and dex are Running. |
| ESO | controller and webhook are Running, and ExternalSecret status becomes Ready after apply. |
| Reloader | live deployment uses the annotations reload strategy and has RBAC to patch workloads. |
| EKS Secrets encryption | Clusters earlier than 1.28 show explicit Kubernetes Secrets encryption before zero-trust checklist passes. |

## 4. IAM, KMS, SecretStore, and ESO Setup

!!! info "Section Summary"
    Create two tightly scoped IRSA roles per service. The workload role receives only non-secret AWS access. The ESO reader role receives service-scoped Secrets Manager read access plus KMS decrypt through Secrets Manager. Terraform owns the cloud resources; Kubernetes manifests only bind the matching ServiceAccounts.

### 4.1 Role Model

| Role / Account | Used By | Allowed Access | Explicitly Not Allowed |
| --- | --- | --- | --- |
| nova-&lt;service&gt;-prod | Workload ServiceAccount &lt;workload-sa-name&gt; | Only the non-secret AWS APIs the application needs, such as S3 or DynamoDB | No Secrets Manager read permissions |
| nova-&lt;service&gt;-eso-read | ServiceAccount &lt;service&gt;-eso-secret-reader | secretsmanager:GetSecretValue and DescribeSecret for nova/&lt;service&gt;/* plus KMS decrypt through Secrets Manager | No wildcard paths; no trust for other service accounts |
| rotation Lambda role | Approved Secrets Manager rotation Lambda | Rotation-only actions and KMS use through Secrets Manager when rotation is enabled | Not present in KMS policy while var.rotation_enabled=false |

### 4.2 Terraform Pattern

Confirm the EKS OIDC issuer before provisioning IRSA. This is read-only validation, not an instruction to create IAM resources with ad hoc CLI commands.

```bash
aws eks describe-cluster \
  --name <cluster-name> \
  --region <region> \
  --query "cluster.identity.oidc.issuer" \
  --output text
```

Create or update service IAM resources through infra/iam/&lt;service&gt;.tf. The excerpt below shows the trust boundary that matters most: only the dedicated ESO secret-reader ServiceAccount can assume the ESO reader role.

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

Attach the secret-read policy only to nova-&lt;service&gt;-eso-read, never to the workload role.

```hcl
data "aws_iam_policy_document" "eso_read" {
  statement {
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecretVersionIds"
    ]
    resources = [
      "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:nova/${local.service}/*"
    ]
  }

  statement {
    actions   = ["kms:Decrypt"]
    resources = [local.secrets_kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.region}.amazonaws.com"]
    }
  }
}
```

!!! info "KMS Source of Truth"
    The same KMS key ARN must be used by the Secrets Manager secret, the nova-&lt;service&gt;-eso-read IAM policy, the KMS key policy, and the rotation Lambda role policy. If the platform uses a shared externally managed key, verify the key policy before merge.

### 4.3 ServiceAccount and SecretStore Manifests

Prefer declarative ServiceAccount manifests in charts/ so IAM bindings stay version-controlled. The workload ServiceAccount and the ESO reader ServiceAccount are intentionally separate.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <service>-eso-secret-reader
  namespace: <namespace>
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/nova-<service>-eso-read
```

Each service defines a namespaced SecretStore in its workload namespace. Use SecretStore rather than ClusterSecretStore for application secrets unless the platform team approves a cross-namespace exception.

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

remoteRef.key must match the Terraform-managed Secrets Manager name pattern: nova/&lt;service&gt;/&lt;secret_name&gt;. Do not use kubectl, Git, or Terraform to set production secret values.

### 4.4 Approved Secret-Seeding Workflow

1. A platform administrator retrieves the initial value from the approved password manager or PAM workflow.

2. The administrator opens a private workstation session with MFA, shell history disabled, and no terminal recording.

3. A temporary JSON input file is created only on encrypted local storage with 0600 permissions.

4. The first AWSCURRENT version is seeded with aws secretsmanager put-secret-value and a file reference.

5. Verification uses describe-secret only; get-secret-value is not used during deployment verification.

6. The temporary file is deleted immediately after seeding.

7. The deployment ticket records only non-secret evidence: secret ARN/name, KMS key ID, AWSCURRENT version ID, approver, timestamp, and rotation-readiness status.

```bash
aws secretsmanager put-secret-value \
  --secret-id nova/<service>/<secret_name> \
  --secret-string file:///<secure-temp-path>/<service>-secret.json

aws secretsmanager describe-secret \
  --secret-id nova/<service>/<secret_name> \
  --query "{Name:Name,VersionIdsToStages:VersionIdsToStages,KmsKeyId:KmsKeyId}"
```

## 5. GitOps Repository Layout

NovaDeploy uses one control-plane GitOps repository as the source of truth for cluster state. Application source code lives in separate repositories; GitOps contains manifests, Helm overrides, ExternalSecret resources, cluster baselines, and infrastructure modules.

```text
nova-gitops/
  apps/                         # Argo CD Application manifests
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
| apps/ | Platform engineering | Application project, destination, sync policy, ignoreDifferences |
| charts/&lt;service&gt;/ | Service team + platform reviewer | Workload metadata annotations, probes, resources, service accounts |
| envs/production/values/ | Service team | Image tag, config values, environment-specific overrides |
| secrets/external/ | Platform engineering | ExternalSecret references only; no secret values |
| infra/iam/&lt;service&gt;.tf | Platform engineering | IAM trust boundaries, KMS policy, Secrets Manager metadata, rotation gates |

## 6. Argo CD Application and Sync Policy

The Application manifest below combines automated sync, server-side apply, and Reloader compatibility. Production namespaces are pre-created through clusters/production/ so NetworkPolicy, ResourceQuota, LimitRange, labels, and admission policies exist before workload sync.

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
| RespectIgnoreDifferences=true | Argo CD respects ignoreDifferences during sync. | Prevents Reloader last-reloaded annotations from being applied away during sync. |
| No CreateNamespace=true | Production namespaces are not created ad hoc by service apps. | Cluster baseline creates namespaces with required policy first. |

### 6.1 Sync Windows

Sync windows live in the AppProject. Routine production syncs are allowed only in approved windows; denied windows block new syncs unless an approved manual-sync override is enabled.

| Window | Policy | Operator Action |
| --- | --- | --- |
| Monday-Friday 09:00-17:00 UTC | Allowed | Normal automated or manual sync permitted after PR approval. |
| Friday 17:00-Monday 09:00 UTC | Denied | Use the emergency manual-sync path only for approved incidents. |
| Emergency override | Manual sync enabled per window ID | Enable, sync, wait, verify, and disable in one procedure; do not leave the override open. |

## 7. Deployment Verification

Close the deployment ticket only after all checks pass and the evidence contains no secret values. Validate object state, expected key names, mount success, rollout state, and recent pod creation time only.

### 7.1 Health and Secret Checks

```bash
argocd app get <app-name> --refresh
argocd app wait <app-name> --health
kubectl rollout status deployment/<name> -n <namespace>

kubectl get externalsecret <name> -n <namespace>
kubectl describe externalsecret <name> -n <namespace>
kubectl get secret <service>-app-secrets -n <namespace>
kubectl get secret <service>-app-secrets -n <namespace> \
  -o go-template='{{range $k, $_ := .data}}{{printf "%s\n" $k}}{{end}}'
# Expected: ExternalSecret Ready=True and expected key names are present.
# Never print or decode values.
```

### 7.2 Secret Mount Check

The disposable pod confirms the Secret can be mounted without exposing values. The command prints only the non-secret success string secret-mounted.

```yaml
cat <<'EOF' | kubectl apply -n <namespace> -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-mount-check
spec:
  restartPolicy: Never
  containers:
    - name: secret-mount-check
      image: busybox:1.36
      command: ["sh", "-ec", "test -s /mnt/secrets/DATABASE_PASSWORD && echo secret-mounted && sleep 30"]
      volumeMounts:
        - name: app-secrets
          mountPath: /mnt/secrets
          readOnly: true
  volumes:
    - name: app-secrets
      secret:
        secretName: <service>-app-secrets
EOF
kubectl wait --for=condition=Ready pod/secret-mount-check \
  -n <namespace> --timeout=60s
kubectl logs secret-mount-check -n <namespace>
kubectl delete pod secret-mount-check -n <namespace>
```

### 7.3 Reloader Confirmation

```bash
kubectl rollout status deployment/<name> -n <namespace>
kubectl get deploy <name> -n <namespace> \
  -o go-template='{{ index .spec.template.metadata.annotations "reloader.stakater.com/last-reloaded-from" }}{{ "\n" }}'
kubectl get pods -n <namespace> -l app=<service> \
  --sort-by=.metadata.creationTimestamp
argocd app get <app-name> --refresh
# Expected: pods were recreated after the Secret refresh; app remains Synced / Healthy.
```

## 8. Rollback and Recovery

!!! warning "Rollback Principle"
    Git revert is the default because it preserves Git as the source of truth and keeps the audit trail clean. Argo CD history rollback is break-glass only and creates mandatory GitOps debt until the matching Git revert merges.

| Scenario | Strategy | Operator Note |
| --- | --- | --- |
| Bad image tag promoted | Git revert | Revert the image-bump commit, pass CI, merge, then sync or wait for automation. |
| Wrong Helm values or Application manifest | Git revert | Revert the Git-tracked change so Git remains the canonical desired state. |
| Application unreachable and SLA at risk | Argo CD history rollback | Use only if Argo CD and the Kubernetes API are reachable and Git revert cannot meet the SLA. Follow with Git revert within 24 hours. |
| GitHub or CI outage blocks revert | Argo CD history rollback | Use the last-good Argo CD revision, document evidence, and complete Git revert when Git/CI returns. |
| Secret value misconfiguration | Secrets Manager rollback + ESO re-sync | Roll back through the approved secret process. Use Git revert only for SecretStore, ExternalSecret, IAM, KMS, or rotation-config changes. |
| Cluster unreachable | Infrastructure troubleshooting | Do not use Argo CD. Troubleshoot EKS control plane, networking, IAM, and node health first. |

### 8.1 Strategy 1: Git Revert

1. Identify the bad commit SHA and the last-good commit in nova-gitops.

2. Create a revert branch from protected main.

3. Check whether the bad commit is single-parent or a merge commit.

4. Open a PR, require emergency approval, merge, then sync or wait for automation.

5. Run the full Section 7 verification path before closing the incident.

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

If the change freeze blocks sync, use the canonical emergency manual-sync path below. The override grants permission for the manual sync only; it does not broadly re-enable automated sync during the denied window.

```bash
argocd proj windows list <project>
argocd proj windows enable-manual-sync <project> <window-id>
argocd app sync <app-name>
argocd app wait <app-name> --health
argocd proj windows disable-manual-sync <project> <window-id>
```

### 8.2 Strategy 2: Argo CD History Rollback

Use only when a Git revert cannot meet the SLA window. Confirm Argo CD and the Kubernetes API are reachable first. If the App of Apps root app manages child Application CRs, suspend the root app during the approved incident window or it may re-enable the child app and re-sync the broken commit.

```bash
argocd app get <root-app-name> -o yaml > root-app-sync-policy.before.yaml
argocd app list --selector app.kubernetes.io/part-of=<root-app-name>
argocd app set <root-app-name> --sync-policy none
argocd app set <app-name> --sync-policy none
argocd app history <app-name>
argocd app rollback <app-name> <revision-number>
argocd app wait <app-name> --health
# Leave target auto-sync disabled until the mandatory Git revert merges.
```

1. Open a Jira ticket tagged [gitops-debt].

2. Complete the matching Git revert within 24 hours.

3. After the revert PR merges, re-enable target app auto-sync and restore the captured root app manifest.

4. Refresh the root app and confirm it returns to its pre-incident sync policy.

```bash
argocd app set <app-name> --sync-policy automated --auto-prune --self-heal
kubectl apply -n argocd -f root-app-sync-policy.before.yaml
argocd app get <root-app-name> --refresh
```

## 9. Appendices

### 9.1 CI Reloader Annotation Guardrail

This guardrail checks rendered workloads individually, so one correctly annotated Deployment cannot mask another secret-consuming workload that lacks the root annotation.

```bash
#!/usr/bin/env bash
set -euo pipefail

python3 - <(helm template charts/<service> -f envs/production/values/<service>.yaml) <<'PY'
import sys, yaml

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet"}
SECRET_KEYS = {"secretKeyRef", "secretRef", "secretName"}
missing = []

def uses_secret(x):
    if isinstance(x, dict):
        return bool(SECRET_KEYS & x.keys()) or any(uses_secret(v) for v in x.values())
    if isinstance(x, list):
        return any(uses_secret(v) for v in x)
    return False

for obj in yaml.safe_load_all(open(sys.argv[1], encoding="utf-8")):
    if not isinstance(obj, dict) or obj.get("kind") not in WORKLOADS:
        continue

    meta = obj.get("metadata") or {}
    pod = obj.get("spec", {}).get("template", {}).get("spec", {})
    annotations = meta.get("annotations") or {}

    if uses_secret(pod) and annotations.get("reloader.stakater.com/auto") != "true":
        missing.append(f'{obj["kind"]}/{meta.get("name", "<unknown>")}')

if missing:
    print('ERROR: secret-consuming workloads missing reloader.stakater.com/auto="true":', file=sys.stderr)
    print("\n".join(f"  - {x}" for x in missing), file=sys.stderr)
    sys.exit(1)
PY
```

The script intentionally checks Deployment, StatefulSet, and DaemonSet pod specs. Ingress tls.secretName values do not create false positives. Use kubeconform and admission policy for broader structural enforcement beyond this fast PR check.

### 9.2 Evidence Checklist

| Evidence Item | Acceptable Example | Forbidden Evidence |
| --- | --- | --- |
| Argo CD state | Screenshot or text showing Synced / Healthy | None |
| ExternalSecret state | Ready=True, SecretSynced reason, recent refresh time | Secret value output |
| Kubernetes Secret | Object exists and expected key names are present | Decoded data or base64 content |
| Mount check | secret-mounted log line from disposable pod | cat/print of mounted file content |
| Reloader rollout | Rollout status and pod creation times after Secret refresh | Secret payload |
| Rollback | Revert PR link, approval, commit SHA, app health after sync | Manual kubectl patch not represented in Git |

### 9.3 Placeholder Conventions

| Placeholder | Meaning | Example |
| --- | --- | --- |
| &lt;ACCOUNT_ID&gt; | AWS account ID | 123456789012 |
| &lt;region&gt; | AWS region for EKS, Secrets Manager, and KMS | us-east-1 |
| &lt;namespace&gt; | Kubernetes namespace for the workload | api-gateway |
| &lt;service&gt; | NovaDeploy service name | api-gateway |
| &lt;cluster-name&gt; | EKS cluster name | nova-prod |
| &lt;workload-sa-name&gt; | Workload Kubernetes ServiceAccount | api-gateway-sa |
| &lt;eso-controller-namespace&gt; | Namespace where ESO controller runs | external-secrets |
| &lt;reloader-namespace&gt; | Namespace where Reloader runs | reloader |
