# NovaDeploy Platform: GitOps Administration Guide - Portfolio Cut

This Markdown sample is a concise portfolio cut of a fictional GitOps administration guide. It highlights the deployment path, safety controls, verification pattern, and rollback logic without requiring a long runbook read.

*Deploying Services to Amazon EKS with Argo CD*  
Version 1.0 | Status: Portfolio cut | Written by: Jeff Slavin

[Read the full runbook.](novadeploy-gitops-admin-guide-full-version.md)

!!! note "Portfolio Notice"
    NovaDeploy is a fictional platform created for portfolio purposes. This sample contains no proprietary employer, client, or production information.

!!! info "Positioning"
    This cut is designed for a 2-3 minute reviewer skim. It preserves the deployment path, core safety controls, architecture, verification pattern, and rollback decision logic while moving long command transcripts and full Terraform detail to the extended runbook.

## 1. Reviewer Summary

This sample demonstrates how to turn a complex EKS, GitOps, and DevSecOps workflow into clear operator guidance. The short version prioritizes signal: source-of-truth rules, zero-trust secret handling, CI guardrails, and safe rollback decisions.

| Reviewer Need | Where This Cut Shows It |
| --- | --- |
| Docs-as-Code structure | GitOps repository layout, protected main branch, CI checks, and Argo CD sync policy |
| Cloud/Kubernetes depth | Amazon EKS, IRSA, KMS, AWS Secrets Manager, ESO, Reloader, Helm, and kubectl checks |
| Operational judgment | Stop checkpoints, rotation gate, evidence rules, and rollback matrix |
| Brevity under complexity | Long transcripts and Terraform reference remain in the full runbook, not the skim version |

## 2. At-a-Glance Deployment Path

!!! success "Happy Path"
    Standard path: validate controllers and local tooling -&gt; update GitOps repo and Terraform-managed IAM/KMS metadata -&gt; open PR -&gt; pass CI and platform review -&gt; merge to protected main -&gt; sync or wait for Argo CD automation -&gt; verify health, secrets, and rollout state -&gt; roll back if needed.

!!! warning "Stop Checkpoints"
    Stop if controllers are unhealthy, CI fails, any secret-consuming workload lacks the Reloader root annotation, an ExternalSecret is not Ready, Argo CD is not Synced/Healthy, or any check would require printing a secret value.

| Step | Operator Action | Evidence |
| --- | --- | --- |
| 1 | Run local dependency checks and controller health checks. | Tool versions; Argo CD, ESO, and Reloader Running/Ready |
| 2 | Update declared state in Git and Terraform-managed cloud metadata. | PR diff contains no plaintext secrets |
| 3 | Pass CI and platform review. | lint, helm template, kubeconform, secret scan, Reloader guardrail |
| 4 | Merge to main and sync. | argocd app get shows Synced / Healthy |
| 5 | Verify release and secrets without exposing values. | rollout status, ExternalSecret Ready=True, key names present, secret-mounted |
| 6 | Close or roll back. | Git revert by default; Argo CD history only for approved SLA emergency |

## 3. Core Guardrails

These are the controls a reviewer should remember after a quick skim. The full runbook expands each item with command transcripts, Terraform snippets, and emergency procedures.

| Control | Rule | Why It Matters |
| --- | --- | --- |
| GitOps source of truth | main is protected; every change lands through PR and passing CI. | Argo CD can self-heal drift and preserve an audit trail. |
| Terraform source of truth | IAM, KMS, Secrets Manager metadata, rotation config, and Lambda permissions stay in Terraform. | Cloud permissions remain reviewable, reproducible, and importable after break-glass work. |
| No plaintext secrets | Secret values never enter Git, Terraform state, PRs, CI logs, tickets, or chats. | Reviewers can validate controls without exposing credentials. |
| IRSA separation | The workload role never reads Secrets Manager; the dedicated ESO reader role is scoped to nova/&lt;service&gt;/*. | Application pods do not receive broad secret-read permissions. |
| Reloader safety | Secret-consuming workloads carry reloader.stakater.com/auto: "true" on root workload metadata. | Secret refreshes result in controlled rolling restarts. |
| Argo CD compatibility | Application sets RespectIgnoreDifferences=true for Reloader last-reloaded annotations. | Argo CD does not undo Reloader restart patches during sync. |
| Rotation gate | Keep var.rotation_enabled=false until KMS, Lambda, ESO, Reloader, and mount checks pass. | Rotation is not enabled before workloads can safely consume refreshed secrets. |

## 4. Architecture Overview

The design separates responsibilities: Git declares cluster state, Terraform declares cloud control-plane resources, AWS Secrets Manager stores values, ESO syncs Kubernetes Secret objects, and Reloader restarts workloads through controlled pod-template changes.

```text
Developer PR
  -> CI guardrails: lint, render, kubeconform, secret scan, Reloader check
  -> protected main
  -> Argo CD reconciles desired state into Amazon EKS

Terraform
  -> IAM roles, KMS key policy, Secrets Manager metadata, rotation config

AWS Secrets Manager --(ESO reader IRSA role)--> External Secrets Operator
  -> namespaced Kubernetes Secret
  -> workload mounts or references Secret
  -> Reloader detects Secret data change and triggers rolling restart
```

!!! note "Accessible Diagram Summary"
    Text alternative: a PR updates Git-tracked cluster state; CI blocks unsafe manifests; Argo CD syncs to EKS; Terraform owns IAM/KMS/Secrets Manager controls; ESO reads the approved AWS secret path through IRSA; Reloader restarts only annotated workloads after the Kubernetes Secret changes.

## 5. Repository and Sync Policy

```text
nova-gitops/
  apps/                         # Argo CD Application manifests
  clusters/production/           # AppProject, root app, namespaces, policy baseline
  charts/<service>/              # Service Helm chart
  envs/production/values/        # Production value overrides
  secrets/external/              # ExternalSecret CRs only; no plaintext secrets
  infra/iam/<service>.tf         # IAM, KMS, Secrets Manager metadata, rotation config
  scripts/check-reloader-annotations.sh
```

Argo CD watches main. Direct pushes are blocked. Automated sync may prune deleted Git-tracked resources and self-heal manual drift. Production namespaces are pre-created by the cluster baseline; service Applications do not rely on CreateNamespace=true.

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - ServerSideApply=true
    - RespectIgnoreDifferences=true
```

## 6. Verification Pattern

After every sync, validate health, rollout state, ExternalSecret readiness, Kubernetes Secret existence, expected key names, mount success, and Reloader rollout state. Never decode, print, paste, or ticket secret values.

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

| Check | Pass Criteria | Forbidden Evidence |
| --- | --- | --- |
| Argo CD state | Synced / Healthy | Manual kubectl patch not represented in Git |
| ExternalSecret | Ready=True and SecretSynced reason | Secret value output |
| Kubernetes Secret | Object exists; expected key names are present | Decoded data or base64 payload |
| Mount check | Disposable pod prints only secret-mounted | cat/print of mounted file content |
| Reloader rollout | Pods recreated after Secret refresh; app remains healthy | Secret payload in logs, tickets, or screenshots |

## 7. Implementation Excerpts

These excerpts show the strongest technical controls without turning the portfolio cut into a full internal runbook.

### 7.1 CI Reloader Guardrail

```bash
helm template charts/<service> -f envs/production/values/<service>.yaml > "$rendered"
python3 - "$rendered" <<'PY'
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}
# For each rendered workload that references a Secret:
# require metadata.annotations["reloader.stakater.com/auto"] == "true"
# fail the PR if any secret-consuming workload is missing the root annotation
PY
```

### 7.2 ESO Reader ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <service>-eso-secret-reader
  namespace: <namespace>
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/nova-<service>-eso-read
```

The matching IAM trust policy trusts only system:serviceaccount:&lt;namespace&gt;:&lt;service&gt;-eso-secret-reader and the sts.amazonaws.com audience. The IAM policy scope is limited to arn:aws:secretsmanager:&lt;region&gt;:&lt;ACCOUNT_ID&gt;:secret:nova/&lt;service&gt;/* plus kms:Decrypt through Secrets Manager for the same KMS key.

### 7.3 Namespaced SecretStore

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
```

## 8. Rollback Matrix

!!! warning "Rollback Principle"
    Git revert is the default because it keeps Git as the source of truth and leaves a clean audit trail. Argo CD history rollback is break-glass only and must be followed by a Git revert within 24 hours.

| Scenario | Strategy | Operator Note |
| --- | --- | --- |
| Bad image tag promoted | Git revert | Revert the image-bump commit, pass CI, merge, then sync or wait for automation. |
| Wrong Helm values or Application manifest | Git revert | Revert the Git-tracked change so Git remains canonical. |
| Application unreachable and SLA at risk | Argo CD history rollback | Use only if Argo CD and Kubernetes API are reachable and Git revert cannot meet the SLA. Follow with Git revert within 24 hours. |
| GitHub or CI outage blocks revert | Argo CD history rollback | Use the last-good Argo CD revision, document evidence, and complete Git revert when Git/CI returns. |
| Secret value misconfiguration | Secrets Manager rollback + ESO re-sync | Roll back through the approved secret process. Use Git revert only for SecretStore, ExternalSecret, IAM, KMS, or rotation-config changes. |
| Cluster unreachable | Infrastructure troubleshooting | Do not use Argo CD. Troubleshoot EKS control plane, networking, IAM, and node health first. |

## 9. What the Full Runbook Adds

- Full Reloader bash + Python guardrail script with CI/pre-commit placement

- Expanded Terraform examples for workload role, ESO reader role, KMS key policy, and rotation resources

- Detailed cluster health, RBAC, KMS, and rotation-readiness checks

- Approved secret-seeding workflow and evidence checklist that avoids leaking values

- Full Argo CD sync-window override and App of Apps emergency rollback sequence

- [Access the full runbook.](novadeploy-gitops-admin-guide-full-version.md)
