---
title: "GCP IoT Core Migration Case Study"
description: How the ClearBlade IoT Core quick start was designed to prevent silent migration failures during Google's shutdown of Cloud IoT Core.
social:
  cards_layout_options:
    title: "Case Study: GCP IoT Core Migration"
---

# Case Study: Designing a Quick Start So Migrations Don't Fail Silently

*Lead Technical Writer, ClearBlade (Oct 2022 – Nov 2024)*

I wrote ClearBlade IoT Core's quick start to help customers verify the full migration path on a sample device before moving their fleets.

## The problem

Google announced Cloud IoT Core's retirement in August 2022 and shut it down on August 16, 2023, closing its MQTT and HTTP bridges and taking its documentation offline. Production fleets faced a fixed migration deadline.

ClearBlade IoT Core was a direct replacement. [ClearBlade reports](https://www.clearblade.com/press/clearblade-unleashes-scalability-in-iot-and-ai-with-google-cloud) that more than 250 Google Cloud customers migrated across the program.

## The constraint

To minimize customer changes, ClearBlade lets customers keep their Google Cloud project, Pub/Sub topics (Google's message pipeline), and device credentials. The device-side change is switching to ClearBlade's MQTT endpoint (MQTT is the devices' messaging protocol).

The guide therefore starts in GCP: provision through Google Cloud Marketplace, authorize the connection with a service account, and grant Pub/Sub permissions for telemetry.

## When migrations only look complete

In a forced migration, the dangerous failure is silent success. A migration tool can report "complete" even when:

* the device registry doesn't exist yet
* a credential is expired or mismatched
* Pub/Sub wiring was never verified

A user of the open-source migration tool [reported a real example](https://github.com/ClearBlade/clearblade-iot-core-migration/issues/2): a run completed against an empty registry, did nothing, and prompted a request for clearer documentation.

## What I wrote

I built in code samples and live telemetry testing. The steps follow the Google quick start customers already knew:

* **Create the registry first** so devices have a destination
* **Generate the device keypair** rather than assume it exists
* **Make Pub/Sub wiring explicit** rather than assume the old service's setup carries over
* **End on proof, not config**: finish when the sample device's messages arrive in Pub/Sub, not when a command reports success

I also explained that customers could remove the temporary IAM role after migration.

## Result

The [quick start](https://docs.clearblade.com/iotcore/quick-start) remains the published entry point, part of the quick starts, how-tos, reference, and migration tooling that supported the program. The migration guides in that set cut support tickets by 30%.

