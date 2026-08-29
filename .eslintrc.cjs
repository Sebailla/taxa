/**
 * ESLint config for the modular-monolith barrel guard.
 *
 * spec.md rule 5: cross-module deep imports are rejected at build time
 * via path-alias config or equivalent lint guard. This file is the lint
 * guard. The `no-restricted-imports` rule rejects any import whose
 * target resolves to a path under one of the four layer folders of any
 * capability module, under BOTH path spellings (literal
 * `src/modules/<cap>/<layer>/*` AND alias `@taxa/<cap>/<layer>/*`).
 * Legitimate cross-module access through the public barrel
 * (`src/modules/<cap>` or `@taxa/<cap>`) is unaffected.
 *
 * Patterns are derived from CAPABILITIES × LAYERS so the rule tracks
 * `tests/test_module_layers.py::CAPABILITIES / ::LAYERS` without a
 * manual edit. Adding a new capability is one entry; adding a new
 * layer is one entry.
 *
 * @type {import("eslint").LinterConfig}
 */
"use strict";

const CAPABILITIES = [
  "taxonomy",
  "research",
  "design-system",
  "browser-state",
  "app-shell",
];
const LAYERS = [
  "presentation",
  "application",
  "domain",
  "infrastructure",
];

const deepImportPatterns = CAPABILITIES.flatMap((capability) =>
  LAYERS.flatMap((layer) => [
    `src/modules/${capability}/${layer}/*`,
    `@taxa/${capability}/${layer}/*`,
  ]),
);

module.exports = {
  root: true,
  // ESLint 9 flat-config is the modern default, but the project predates
  // ESLint 9 and uses the legacy `.eslintrc.cjs` form. CommonJS module
  // format keeps `node --check` validation trivial.
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    // JSX / TSX parsing is added in PR 3 once React is installed.
  },
  rules: {
    "no-restricted-imports": [
      "error",
      {
        patterns: deepImportPatterns,
      },
    ],
  },
};
