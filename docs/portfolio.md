---
description: "Selected technical writing samples by Jeff Slavin covering GitOps, DevSecOps, APIs, developer onboarding, IoT platform migration, and edge computing."
---

# Portfolio { .portfolio-page-title }

Selected technical writing samples covering GitOps, DevSecOps, APIs, developer onboarding, IoT platform migration, and edge computing. The ClearBlade samples link to the company's live site, which may have changed since they were written.

## GitOps & DevSecOps Documentation

<div class="portfolio-grid">
  <a class="portfolio-card" href="../writing-samples/novadeploy-gitops-admin-guide-portfolio-cut/">
    <span class="card-tag">Amazon EKS · Argo CD · GitOps · DevSecOps</span>
    <h3>NovaDeploy GitOps Administration Guide – Portfolio Cut</h3>
    <p>A 5–7-minute cut of a fictional operator runbook: architecture, deployment steps, stop checkpoints, verification, and rollback. Covers source-of-truth rules for GitOps and Terraform, as well as keeping plaintext secrets out of Git, PRs, logs, and tickets. Includes a worked secret-refresh walkthrough and the CI check that enforces the Reloader restart guardrail.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>

  <a class="portfolio-card" href="../writing-samples/novadeploy-gitops-admin-guide-full-version/">
    <span class="card-tag">Amazon EKS · IRSA · KMS · ESO · Reloader</span>
    <h3>NovaDeploy GitOps Administration Guide – Full Runbook</h3>
    <p>The complete fictional operator runbook: SecretStore and External Secrets Operator (ESO) setup, as well as Terraform patterns for IAM, KMS, and Secrets Manager. Includes a rotation readiness gate, CI guardrails, verification commands, break-glass rollback (an approved emergency procedure), and an evidence checklist. Start with the portfolio cut for a shorter read.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>
</div>

## API & Developer Documentation

<div class="portfolio-grid">
  <a class="portfolio-card" href="https://docs.clearblade.com/iotenterprise/apis" target="_blank" rel="noopener">
    <span class="card-tag">OpenAPI 3.0 · Spec descriptions</span>
    <h3>OpenAPI 3.0 Interactive API Reference – ClearBlade IoT Enterprise</h3>
    <p>Wrote the OpenAPI 3.0 spec descriptions used to generate the interactive API reference and SDKs for ClearBlade IoT Enterprise, reducing partner integration time from weeks to days.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>

  <a class="portfolio-card" href="https://docs.clearblade.com/iotenterprise/rest-api-query-schema" target="_blank" rel="noopener">
    <span class="card-tag">REST API · Query schema</span>
    <h3>REST API Query Schema Technical Reference</h3>
    <p>Detailed ClearBlade's REST API query schema, including SQL-to-JSON translation, filter-condition logic, and TypeScript interfaces for developers querying collections through the platform.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>

  <a class="portfolio-card" href="https://docs.clearblade.com/iotenterprise/webhooks" target="_blank" rel="noopener">
    <span class="card-tag">Webhooks · Payloads · cURL</span>
    <h3>Webhooks Configuration & Payload Guide</h3>
    <p>Created webhook documentation covering authentication methods, cURL examples, JSON payload structures, path wildcards, and programmatic webhook configuration via the REST API.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>
</div>

## End-User & Onboarding Documentation

<div class="portfolio-grid single-row">
  <div class="portfolio-card">
    <span class="card-tag">Quick start · GCP IoT Core migration</span>
    <h3>Quick Start Guide – ClearBlade IoT Core</h3>
    <p>Authored a step-by-step quick start with code samples and telemetry testing as part of the migration guides for 250+ GCP IoT Core customers who moved to ClearBlade, cutting support tickets by 30%.</p>
    <a class="card-link" href="https://docs.clearblade.com/iotcore/quick-start" target="_blank" rel="noopener">Read sample <span class="inline-arrow" aria-hidden="true"></span></a>
    <a class="card-link" href="../case-studies/gcp-iot-core-migration/">Read case study <span class="inline-arrow" aria-hidden="true"></span></a>
  </div>
</div>

## Edge Computing Documentation

<div class="portfolio-grid">
  <a class="portfolio-card" href="https://docs.clearblade.com/iotenterprise/edge" target="_blank" rel="noopener">
    <span class="card-tag">Platform overview · Configuration</span>
    <h3>Edge Computing Platform Overview & Configuration</h3>
    <p>Developed ClearBlade Edge documentation for installation, configuration, and synchronization, helping teams independently deploy and manage edge environments.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>

  <a class="portfolio-card" href="https://docs.clearblade.com/iotenterprise/edge-tutorial" target="_blank" rel="noopener">
    <span class="card-tag">Hands-on tutorial · Deployment</span>
    <h3>Hands-On Edge Deployment Tutorial</h3>
    <p>Created a tutorial for deploying, installing, starting, remotely accessing, and upgrading ClearBlade IoT Enterprise edge instances.</p>
    <span class="card-link">Read sample <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>
</div>

## Public Contributions

<div class="portfolio-grid">
  <a class="portfolio-card" href="https://github.com/jslavin-clearblade?tab=overview&amp;from=2023-01-01&amp;to=2023-12-31" target="_blank" rel="noopener">
    <span class="card-tag">GitHub · Contribution activity</span>
    <h3>ClearBlade Contribution Activity</h3>
    <p>Maintained documentation across 23 ClearBlade repositories in 2023, with 135 public contributions covering the native code library reference, SDK READMEs, and developer kit documentation.</p>
    <span class="card-link">View activity <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>

  <a class="portfolio-card" href="https://github.com/ClearBlade/native-libraries/commits/master/?author=jslavin-clearblade" target="_blank" rel="noopener">
    <span class="card-tag">Git · Docs as Code</span>
    <h3>Native Code Library Commits – ClearBlade</h3>
    <p>Authored 28 commits to ClearBlade's public native-libraries documentation repository, each with a reviewable diff of the changes.</p>
    <span class="card-link">View commit history <span class="inline-arrow" aria-hidden="true"></span></span>
  </a>
</div>

## Built for AI Retrieval

Machine-readable files help AI assistants give accurate answers about this work:

- **[skill.md](https://jslavin-docs.github.io/skill.md)** — an instruction file that keeps AI answers grounded in the published content.
- **[llms.txt](https://jslavin-docs.github.io/llms.txt)** — index of the site's pages.
- **[llms-full.txt](https://jslavin-docs.github.io/llms-full.txt)** — the site's complete Markdown content in one file.
- Every page is also available as plain Markdown.
