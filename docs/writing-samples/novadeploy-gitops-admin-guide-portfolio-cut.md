---
description: "Concise portfolio cut of a fictional NovaDeploy GitOps administration guide for Amazon EKS, Argo CD, ESO, secrets, verification, and rollback workflows."
---

# NovaDeploy Platform: GitOps Administration Guide - Portfolio Cut

This portfolio cut highlights the deployment path, safety controls, verification pattern, and rollback logic without requiring a long runbook read.

*Deploying Services to Amazon EKS with Argo CD*  
Version 1.0 | Status: Portfolio cut | Written by: Jeff Slavin

[Read the full runbook.](novadeploy-gitops-admin-guide-full-version.md)

!!! note "Portfolio Notice"
    NovaDeploy is a fictional platform created for portfolio purposes. This sample contains no proprietary employer, client, or production information.

!!! info "Positioning"
    Designed for a 5–7-minute review, this cut preserves the deployment path, core safety controls, architecture, verification pattern, and rollback logic while moving command transcripts and full Terraform detail to the extended runbook.

!!! info "Scope and Audience"
    **Scope:** Shows a reviewer-oriented deployment path for a fictional production service on Amazon EKS using Argo CD, Terraform-managed IAM/KMS/Secrets Manager metadata, External Secrets Operator, and Reloader. It summarizes guardrails, verification, and rollback logic without full command transcripts or complete Terraform examples.

    **Audience:** Technical writing reviewers, engineering managers, platform engineers, and DevOps/SRE reviewers evaluating GitOps, cloud, Kubernetes, and DevSecOps documentation depth in a short read.

## 1. Case Frame: What This Sample Proves

This portfolio cut is not a full internal runbook. It is a proof-of-judgment sample: how to explain a risky GitOps secret-refresh workflow so reviewers can see the problem, tradeoffs, controls, and recovery logic in 5–7 minutes.

| Case Question | 5-Minute Answer |
| --- | --- |
| **Problem** | Secret refresh can appear successful while production risk remains. |
| **Audience Need** | Show judgment: what to check, when to stop, what evidence is safe, and how rollback is chosen. |
| **Decision** | Lead with decision points; move transcripts and Terraform detail to the full runbook. |
| **Impact** | Reviewers can quickly evaluate secret safety, restart control, GitOps auditability, and recovery logic. |

!!! note "Problem Risks Preserved"
    A safe-looking refresh can still fail if workloads do not restart, verification exposes secret values, or rollback bypasses Git. This cut shows the controls for those risks.

### Judgment Shown in This Cut

| Judgment Area | What the Sample Demonstrates |
| --- | --- |
| **Risk reduction** | Blocks plaintext secrets, missing Reloader annotations, unhealthy controllers, and unsafe rollback paths before production. |
| **Tradeoff management** | Keeps the portfolio version short while preserving the deployment path, safety gates, verification pattern, and rollback logic. |
| **Operator empathy** | Gives operators concrete pass/fail evidence without asking them to expose secret values or infer rollback strategy under pressure. |
| **GitOps discipline** | Treats Git revert as the default recovery path and limits Argo CD history rollback to approved SLA emergencies. |

---

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

---

## 3. Decision Walkthrough: API Gateway Secret Refresh

This walkthrough shows the judgment behind one production-style change: prove the refresh is safe without exposing secret values, skipping workload restarts, or breaking GitOps source-of-truth rules.

!!! example "PR Evidence Snapshot"
    - `PR #1842` updates chart, production values, and ExternalSecret.
    - Adds root `reloader.stakater.com/auto: "true"`.
    - Keeps the external reference at `nova/api-gateway/db`.
    - Contains no plaintext values.

| Stage | Evidence Snapshot | What It Proves |
| --- | --- | --- |
| PR opened | PR is reviewable, Reloader-ready, and secret-safe. | The change is Git-tracked and safe to inspect. |
| CI completed | `lint`, `helm template`, `kubeconform`, `secret scan`, and Reloader guardrail pass. | The workload has the required restart control before merge. |
| Argo CD before sync | `api-gateway` is `Synced / Healthy` at commit `7c4e91a`. | The starting state is stable. |
| Argo CD after sync | `api-gateway` syncs to `9f28b6c` and returns `Synced / Healthy`. | The merged Git state reconciles successfully. |
| ExternalSecret verified | `Ready=True` and `SecretSynced`. | ESO created or updated the Kubernetes Secret object. |
| Secret checked safely | Secret object exists; key-name output shows `DATABASE_PASSWORD`. | Operators verify structure without printing or decoding values. |
| Reloader rollout confirmed | Rollout succeeds; pods are newer than the Secret refresh; last-reloaded annotation is present. | The refresh triggered a controlled rolling restart, not a manual pod delete. |
| Rollback decision | No rollback: Argo CD is Healthy, ExternalSecret is Ready, mount prints only `secret-mounted`, and smoke tests pass. | Git remains the source of truth. Failed checks would trigger a Git revert; Argo CD history rollback remains break-glass only. |

---

## 4. Core Guardrails

These are the controls a reviewer should remember. The full runbook expands them with command transcripts, Terraform snippets, and emergency procedures.

| Control | Rule | Why It Matters |
| --- | --- | --- |
| GitOps source of truth | main is protected; every change lands through PR and passing CI. | Argo CD can self-heal drift and preserve an audit trail. |
| Terraform source of truth | IAM, KMS, Secrets Manager metadata, rotation config, and Lambda permissions stay in Terraform. | Cloud permissions remain reviewable, reproducible, and importable after break-glass work. |
| No plaintext secrets | Secret values never enter Git, Terraform state, PRs, CI logs, tickets, or chats. | Reviewers can validate controls without exposing credentials. |
| IRSA separation | The workload role never reads Secrets Manager; the dedicated ESO reader role is scoped to nova/&lt;service&gt;/*. | Application pods do not receive broad secret-read permissions. |
| Reloader safety | Secret-consuming workloads carry reloader.stakater.com/auto: "true" on root workload metadata. | Secret refreshes result in controlled rolling restarts. |
| Argo CD compatibility | Application sets RespectIgnoreDifferences=true for Reloader last-reloaded annotations. | Argo CD does not undo Reloader restart patches during sync. |
| Rotation gate | Keep var.rotation_enabled=false until KMS, Lambda, ESO, Reloader, and mount checks pass. | Rotation is not enabled before workloads can safely consume refreshed secrets. |

---

## 5. Architecture Overview

The design separates responsibilities: Git declares cluster state, Terraform declares cloud control-plane resources, AWS Secrets Manager stores values, and ESO syncs Kubernetes Secret objects. Reloader detects Secret changes and patches workload Pod template metadata through the EKS API so native workload controllers perform the rolling restart.

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
    apiPatch["EKS API<br/>metadata patch"]
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
    The diagram has three sections: GitOps path, Terraform-owned cloud controls, and runtime secret sync and refresh. GitOps moves a reviewed PR through CI, protected main, Argo CD, and Amazon EKS. Terraform declares IAM, KMS, Secrets Manager metadata, rotation config, and the approved AWS secret path.

    Amazon EKS hosts ESO, Reloader, application pods, and other runtime controllers. AWS Secrets Manager is read only by ESO through the dedicated ESO reader IRSA role, scoped to `nova/<service>/*`; application pods do not receive broad Secrets Manager read access.

    ESO syncs the approved value into a Kubernetes Secret. Reloader detects the Secret data change and patches workload Pod template metadata so the native workload controller performs the rolling restart.

---

## 6. Repository and Sync Policy

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

Argo CD watches protected `main`, but automated prune and self-heal are not standalone production defaults. Enable them only for service Applications bound to the restricted `novadeploy-production` AppProject and production sync windows. The AppProject must limit trusted Git repositories, approved destination clusters and namespaces, and allowed resource kinds. Sync windows must block routine production syncs outside approved change windows unless an incident-approved manual-sync override is enabled.

Treat Git deletions as production deletion changes: the PR must show the resource removal, pass CI, receive platform approval, and merge through protected `main` before Argo CD can prune. Production namespaces are pre-created by the cluster baseline; service Applications do not rely on `CreateNamespace=true`.

!!! warning "Auto-Prune Boundary"
    Do not copy `prune: true` into a production Application unless the Application is constrained by the production AppProject and sync windows. Without those controls, auto-prune can turn a bad merge, path mistake, or unauthorized destination into automated deletion.

Configure both `ignoreDifferences` rules and `RespectIgnoreDifferences=true`: the rules tell Argo CD which Reloader-managed field to ignore, and `RespectIgnoreDifferences=true` makes those rules apply during sync. The example below assumes the surrounding AppProject and sync-window controls are already enforced in `clusters/production/`.

```yaml
# Required surrounding control: this Application belongs to the restricted
# production AppProject, which limits source repos, destinations, resource
# kinds, and sync windows.
project: novadeploy-production

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

syncPolicy:
  automated:
    prune: true      # Allowed only inside the restricted AppProject + sync windows.
    selfHeal: true   # Reverts manual drift back to reviewed Git state.
  syncOptions:
    - ServerSideApply=true
    - RespectIgnoreDifferences=true
```

---

## 7. Verification Pattern

After every sync, validate health, rollout state, ExternalSecret readiness, Kubernetes Secret existence, expected key names, mount success, and Reloader state. Never decode, print, paste, or ticket secret values.

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

---

## 8. Implementation Excerpt: CI Reloader Guardrail

This excerpt is the strongest technical control to preserve: it turns a platform rule into an automated PR failure. The full runbook includes the longer ServiceAccount, SecretStore, IAM, KMS, and rotation examples.

```bash
set -euo pipefail

rendered="$(mktemp)"
trap 'rm -f "$rendered"' EXIT

helm template charts/<service> -f envs/production/values/<service>.yaml > "$rendered"

python3 - "$rendered" <<'PY'
import sys, yaml

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet"}
SECRET_KEYS = {"secretKeyRef", "secretRef", "secretName"}

def uses_secret(node):
    if isinstance(node, dict):
        return bool(SECRET_KEYS & node.keys()) or any(uses_secret(v) for v in node.values())
    if isinstance(node, list):
        return any(uses_secret(v) for v in node)
    return False

missing = []

with open(sys.argv[1], encoding="utf-8") as rendered:
    for obj in yaml.safe_load_all(rendered):
        if not isinstance(obj, dict) or obj.get("kind") not in WORKLOADS:
            continue

        meta = obj.get("metadata") or {}
        pod = obj.get("spec", {}).get("template", {}).get("spec", {})
        annotations = meta.get("annotations") or {}

        if uses_secret(pod) and annotations.get("reloader.stakater.com/auto") != "true":
            missing.append(f'{obj["kind"]}/{meta.get("name", "<unknown>")}')

if missing:
    print('ERROR: secret-consuming workloads missing reloader.stakater.com/auto="true":', file=sys.stderr)
    print("\n".join(f"  - {item}" for item in missing), file=sys.stderr)
    sys.exit(1)
PY
```

The guardrail is intentionally narrow: it checks rendered Deployments, StatefulSets, and DaemonSets for secret references and fails the build when root workload metadata lacks `reloader.stakater.com/auto: "true"`. That keeps the cut focused on judgment while showing executable depth.

---

## 9. Rollback Matrix

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

---

## 10. What the Full Runbook Adds

- Full Reloader bash + Python guardrail script with CI/pre-commit placement

- Expanded Terraform examples for workload role, ESO reader role, KMS key policy, and rotation resources

- Detailed cluster health, RBAC, KMS, and rotation-readiness checks

- Approved secret-seeding workflow and non-secret evidence checklist

- Full Argo CD sync-window override and App of Apps emergency rollback sequence

- [Access the full runbook](novadeploy-gitops-admin-guide-full-version.md)
