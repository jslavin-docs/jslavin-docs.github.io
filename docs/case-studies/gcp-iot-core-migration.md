---
description: How the ClearBlade IoT Core quick start was designed to prevent silent migration failures during Google's shutdown of Cloud IoT Core.
---

# Case Study: Designing a Quick Start So Migrations Don't Fail Silently

*Lead Technical Writer, ClearBlade (Oct 2022 – Nov 2024)*

**TL;DR:** When Google shut down Cloud IoT Core, every connected fleet had to move by a hard deadline. I wrote the quick start that became the front door to the replacement, designed so a migration couldn't *look* finished when it wasn't.

## The problem

In August 2022, Google announced it would retire Cloud IoT Core. On Aug 16, 2023 the service shut down: MQTT and HTTP bridges closed and Google's own docs went offline with it. Every connected fleet had to move, whether they wanted to or not.

ClearBlade built ClearBlade IoT Core as a direct replacement. More than 250 Google Cloud customers ultimately migrated. That number is the company's, for the whole program. It's what the docs had to support: production fleets, a fixed external deadline, and operators who didn't choose to migrate.

## The constraint

The product goal was to minimize customer changes. Customers keep their Google Cloud project, their Pub/Sub topics (Google's message pipeline), and their device credentials. The device-side change is pointing to ClearBlade's MQTT endpoint (MQTT is the messaging protocol used by the devices).

That dictates the onboarding order: provisioning runs through Google Cloud Marketplace, a GCP service account authorizes the connection, and Pub/Sub permissions carry telemetry. The guide has to start in GCP because that's how the product works. I also called out that the temporary IAM permissions role used for migration could be removed when done.

## The risk to design against

In a forced migration, the dangerous failure is silent success. A migration tool can report "complete" even when:

* the device registry doesn't exist yet
* a credential is expired or mismatched
* Pub/Sub wiring was never verified

The fleet looks migrated and isn't. This happened: a user of the open-source migration tool [publicly reported](https://github.com/ClearBlade/clearblade-iot-core-migration/issues/2) a run that completed against an empty registry and did nothing, and asked for the docs to address it.

## What I wrote

I authored the step-by-step quick start that is the front door to ClearBlade IoT Core. I built in code samples and live telemetry testing. The sequence is deliberate:

* **Create the registry first** so devices can't migrate into a void
* **Generate the device keypair in-flow** so you don't assume it exists
* **Make Pub/Sub wiring explicit** so it isn't inherited invisibly from the old service
* **End on proof, not config** so the guide is done when you see real device data arrive at the other end, not when a command returns success

Each step blocks a specific way a migration could look finished without being finished.

## Result

The quick start remains the published entry point: [Read the published quick start](https://docs.clearblade.com/iotcore/quick-start). It's one page in a larger set of quick starts, how-tos, reference, and migration tooling that supported 250+ customers off a discontinued service.
