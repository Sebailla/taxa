/**
 * Typed design-token surface for the `design-system` capability module.
 *
 * Mirrors the Tailwind 4 `@theme` block in `src/app/globals.css` (the
 * CSS custom-property names are the source of truth). Each binding is a
 * `string` typed `const` whose value is the `var(--<name>)` reference —
 * feature components import these symbols for type-safe design-token
 * access without scattering CSS-variable string literals across the
 * codebase.
 *
 * Phase 1 scope (per `odd/tasks/design-system-extract.md`):
 *   - Surface family: 4 tokens (low, container, high, highest).
 *     `surface-container-lowest` is intentionally NOT exported — the
 *     `@theme` block in `globals.css` does not declare it, and Phase 1
 *     mirrors the existing CSS rather than inventing new tokens.
 *   - Primary surface + on-surface variants: 5 tokens (surface,
 *     on-surface, on-surface-variant, outline, outline-variant).
 *   - Brand: 2 tokens (`primary`, `accent`). `on-primary` is NOT
 *     exported — the `@theme` block has no `--on-primary` declaration.
 *   - Other: 1 token (`elevated`).
 *   - Realm palette: 8 tokens (bacteria, archaea, viruses, animalia,
 *     fungi, plantae, chromista, other).
 *
 * Total: 20 tokens.
 *
 * Adding the missing tokens (`surface-container-lowest`, `on-primary`,
 * or any other) is Phase 2+ work — it requires extending the `@theme`
 * block + the dark-palette override block in `globals.css`.
 */

// ---------------------------------------------------------------------------
// Surface family — neutral container tones.
// ---------------------------------------------------------------------------

export const surfaceContainerLow: string = "var(--surface-container-low)";
export const surfaceContainer: string = "var(--surface-container)";
export const surfaceContainerHigh: string = "var(--surface-container-high)";
export const surfaceContainerHighest: string = "var(--surface-container-highest)";

// ---------------------------------------------------------------------------
// Primary surface + on-surface variants — base canvas + foreground text.
// ---------------------------------------------------------------------------

export const surface: string = "var(--surface)";
export const onSurface: string = "var(--on-surface)";
export const onSurfaceVariant: string = "var(--on-surface-variant)";
export const outline: string = "var(--outline)";
export const outlineVariant: string = "var(--outline-variant)";

// ---------------------------------------------------------------------------
// Brand — saturated accents used for CTAs, links, focused rows.
// ---------------------------------------------------------------------------

export const primary: string = "var(--primary)";
export const accent: string = "var(--accent)";

// ---------------------------------------------------------------------------
// Other — elevated surface used for floating chrome / shadows.
// ---------------------------------------------------------------------------

export const elevated: string = "var(--elevated)";

// ---------------------------------------------------------------------------
// Realm palette — saturated pastels that stay identical in light +
// dark mode. Used by `TreeRow` rank badges + the detail panel header.
// ---------------------------------------------------------------------------

export const realmBacteria: string = "var(--realm-bacteria)";
export const realmArchaea: string = "var(--realm-archaea)";
export const realmViruses: string = "var(--realm-viruses)";
export const realmAnimalia: string = "var(--realm-animalia)";
export const realmFungi: string = "var(--realm-fungi)";
export const realmPlantae: string = "var(--realm-plantae)";
export const realmChromista: string = "var(--realm-chromista)";
export const realmOther: string = "var(--realm-other)";