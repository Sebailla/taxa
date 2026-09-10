#!/usr/bin/env node
// Test-only override for check-runtime.mjs. Loaded via `node --import` so the
// version patch lands before the production floor check runs. process.versions.node
// is read-only on Node 22+, so we redefine the slot via Object.defineProperty.
const override = process.env.TAXA_TEST_NODE_VERSION_OVERRIDE;
if (override) {
  Object.defineProperty(process.versions, "node", { value: override, writable: true, configurable: true });
}