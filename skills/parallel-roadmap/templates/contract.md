---
name: <contract name>
version: 1
status: draft           # draft | frozen
defined_by: <node id that freezes it>
---

# Contract: <name>

## Purpose

<What this interface connects, and which nodes use it.>

## Interface

<Exact types, signatures, schema, event names or file format. Code blocks, not prose. Link to the source file once it exists.>

## Behavior

- <Rules both sides must follow: ordering, errors, limits, idempotency.>

## Stub

<Where the stub or fake lives and what it returns, so consumers can build before the real thing exists.>

## Contract tests

<Where the tests are that every implementation must pass.>

## Changes

- v1: initial.
