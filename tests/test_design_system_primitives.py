"""Design-system primitive contract tests for Phase 1 of ODD-DSE.

Pins the source-level contract of the Phase 1 design-system extract:

  * `src/modules/design-system/domain/tokens.ts` — typed design-token
    surface mirroring the Tailwind 4 `@theme` block in
    `src/app/globals.css` (CSS custom-property names are the source of
    truth — Phase 1 mirrors what already exists, no new tokens).
  * Eight Server-Component primitives in
    `src/modules/design-system/presentation/` (Spinner is the only
    `"use client"` component — it owns the `aria-live` announcement
    region via `useEffect`).
  * The public barrel `src/modules/design-system/index.ts` re-exports
    the tokens surface + every primitive.

Pure source-level regex assertions, consistent with the existing
`tests/test_app_shell_render.py` style. NO rendering, NO build
dependency — every assertion runs against the source bytes on disk so
the test stays in the RED gate without spinning up `next build`.

Strict TDD discipline (per `odd/tasks/design-system-extract.md`):

  1. RED  — every test in this file MUST fail on a fresh branch where
           the primitive + tokens + barrel do not exist yet. The
           existence/source/regex witnesses below are the RED gate.
  2. GREEN — every test passes once Phase 1 ships the primitive file
           + the barrel re-export.

No consumer is touched (Phase 2 work) and `src/app/globals.css` stays
byte-identical (the design tokens are already there; Phase 1 only
gives them a typed surface + a primitive component layer that uses
existing Tailwind utilities).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DS_DIR = REPO_ROOT / "src" / "modules" / "design-system"
BARREL = DS_DIR / "index.ts"
TOKENS_FILE = DS_DIR / "domain" / "tokens.ts"
PRESENTATION = DS_DIR / "presentation"

BUTTON = PRESENTATION / "Button.tsx"
ICON_BUTTON = PRESENTATION / "IconButton.tsx"
BADGE = PRESENTATION / "Badge.tsx"
CARD = PRESENTATION / "Card.tsx"
EMPTY_STATE = PRESENTATION / "EmptyState.tsx"
SPINNER = PRESENTATION / "Spinner.tsx"
INLINE_MESSAGE = PRESENTATION / "InlineMessage.tsx"
TEXT = PRESENTATION / "Text.tsx"

ALL_PRIMITIVE_FILES = (
    BUTTON,
    ICON_BUTTON,
    BADGE,
    CARD,
    EMPTY_STATE,
    SPINNER,
    INLINE_MESSAGE,
    TEXT,
)


# ---------------------------------------------------------------------------
# Source-level read helpers (consistent with the rest of tests/).
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def _assert_contains(path: Path, pattern: str, msg: str) -> None:
    """Regex must match the source at least once. ``pattern`` is a
    raw regex; callers escape literals with ``re.escape`` where needed.
    """
    text = _read(path)
    assert re.search(pattern, text), (
        f"{path.relative_to(REPO_ROOT)}: {msg} (pattern={pattern!r})"
    )


def _assert_not_contains(path: Path, pattern: str, msg: str) -> None:
    text = _read(path)
    assert not re.search(pattern, text), (
        f"{path.relative_to(REPO_ROOT)}: {msg} (pattern={pattern!r})"
    )


# ---------------------------------------------------------------------------
# Tokens surface — `src/modules/design-system/domain/tokens.ts`
# ---------------------------------------------------------------------------


class TestTokensSurface:
    """Pins the typed design-token surface.

    Token list mirrors the Tailwind 4 `@theme` block in
    `src/app/globals.css` (lines ~25-60). The CSS custom-property names
    are the source of truth — Phase 1 does NOT add new tokens.

    Surface family: 4 tokens (the @theme block has low, container,
    high, highest — NO `surface-container-lowest`).
    Primary surface + on-surface variants: 5 tokens.
    Brand: 2 tokens (`primary`, `accent` — NO `on-primary`; the @theme
    block does not declare it).
    Other: 1 token (`elevated`).
    Realm palette: 8 tokens.
    Total: 20 tokens.
    """

    def test_tokens_file_exists(self):
        assert TOKENS_FILE.is_file(), (
            f"missing {TOKENS_FILE.relative_to(REPO_ROOT)} — "
            "ODD-DSE-001 must author the typed design-token surface"
        )

    def test_tokens_file_is_a_module(self):
        text = _read(TOKENS_FILE)
        assert re.search(r"\bexport\s+(?:const|interface|type|function)\b", text), (
            f"{TOKENS_FILE.relative_to(REPO_ROOT)} must export at least "
            "one binding — typed token surface is the Phase 1 contract"
        )

    @pytest.mark.parametrize(
        "name, css_var",
        [
            # Surface family (4 — `surfaceContainerLowest` is NOT in
            # the @theme block so Phase 1 omits it).
            ("surfaceContainerLow", "--surface-container-low"),
            ("surfaceContainer", "--surface-container"),
            ("surfaceContainerHigh", "--surface-container-high"),
            ("surfaceContainerHighest", "--surface-container-highest"),
            # Primary surface + on-surface variants (5).
            ("surface", "--surface"),
            ("onSurface", "--on-surface"),
            ("onSurfaceVariant", "--on-surface-variant"),
            ("outline", "--outline"),
            ("outlineVariant", "--outline-variant"),
            # Brand (2 — `onPrimary` is NOT in the @theme block).
            ("primary", "--primary"),
            ("accent", "--accent"),
            # Other (1).
            ("elevated", "--elevated"),
            # Realm palette (8).
            ("realmBacteria", "--realm-bacteria"),
            ("realmArchaea", "--realm-archaea"),
            ("realmViruses", "--realm-viruses"),
            ("realmAnimalia", "--realm-animalia"),
            ("realmFungi", "--realm-fungi"),
            ("realmPlantae", "--realm-plantae"),
            ("realmChromista", "--realm-chromista"),
            ("realmOther", "--realm-other"),
        ],
    )
    def test_token_is_typed_with_css_var_reference(self, name: str, css_var: str):
        """Each token MUST be a string literal `var(<css-var-name>)`.

        The CSS custom-property name is the source of truth — the
        typed surface mirrors the `@theme` block byte-for-byte.
        """
        text = _read(TOKENS_FILE)
        pattern = (
            r"\bexport\s+const\s+" + re.escape(name) +
            r"\s*:\s*string\s*=\s*[\"']var\(" + re.escape(css_var) +
            r"\)[\"']"
        )
        assert re.search(pattern, text), (
            f"{TOKENS_FILE.relative_to(REPO_ROOT)} must export "
            f"`const {name}: string = \"var({css_var})\"` — "
            "typed design-token surface mirrors the @theme block"
        )

    def test_tokens_do_not_invent_missing_css_variables(self):
        """Phase 1 mirrors the @theme block — it MUST NOT introduce
        `surface-container-lowest` or `on-primary` (neither exists in
        `globals.css:25-60`). Adding them is Phase 2+ work.
        """
        text = _read(TOKENS_FILE)
        for forbidden in ("surfaceContainerLowest", "onPrimary"):
            assert forbidden not in text, (
                f"{TOKENS_FILE.relative_to(REPO_ROOT)} exports "
                f"`{forbidden}` but the @theme block has no matching "
                "CSS custom property — Phase 1 must mirror, not invent"
            )
            assert f"--{forbidden.replace('C', '-c').lower()}" not in text, (
                f"{TOKENS_FILE.relative_to(REPO_ROOT)} references "
                f"--{forbidden.lower()} but the @theme block has no "
                "matching CSS custom property — Phase 1 must mirror, not invent"
            )


# ---------------------------------------------------------------------------
# Button — `src/modules/design-system/presentation/Button.tsx`
# ---------------------------------------------------------------------------


class TestButton:
    def test_file_exists(self):
        assert BUTTON.is_file(), (
            f"missing {BUTTON.relative_to(REPO_ROOT)} — ODD-DSE-002 must ship Button"
        )

    def test_exports_button_props_interface(self):
        text = _read(BUTTON)
        assert re.search(r"\bexport\s+interface\s+ButtonProps\b", text), (
            f"{BUTTON.relative_to(REPO_ROOT)} must export an `ButtonProps` "
            "interface — barrel re-export depends on the named export"
        )

    def test_exports_default_component(self):
        text = _read(BUTTON)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{BUTTON.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(BUTTON)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{BUTTON.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"` — "
            "Button is a Server Component (no interactivity)"
        )

    def test_default_classes_include_shape_and_transition(self):
        text = _read(BUTTON)
        for cls in ("rounded-md", "font-medium", "transition-colors",
                    "disabled:opacity-50", "disabled:cursor-not-allowed"):
            assert cls in text, (
                f"{BUTTON.relative_to(REPO_ROOT)} must include `{cls}` "
                "in the default class chain"
            )

    @pytest.mark.parametrize(
        "variant, classes",
        [
            ("primary", ("bg-primary", "text-on-primary", "hover:bg-accent")),
            ("secondary", ("border", "border-outline-variant", "bg-surface",
                           "text-on-surface", "hover:bg-surface-container-low")),
            ("ghost", ("text-on-surface", "hover:bg-surface-container-low")),
        ],
    )
    def test_variant_classes(self, variant, classes):
        text = _read(BUTTON)
        # Each variant MUST map to its variant case + all expected classes.
        for cls in classes:
            assert cls in text, (
                f"{BUTTON.relative_to(REPO_ROOT)} variant `{variant}` must use `{cls}`"
            )

    @pytest.mark.parametrize(
        "size, classes",
        [
            ("sm", ("text-xs", "px-3", "py-1.5")),
            ("md", ("text-sm", "px-4", "py-2")),
        ],
    )
    def test_size_classes(self, size, classes):
        text = _read(BUTTON)
        for cls in classes:
            assert cls in text, (
                f"{BUTTON.relative_to(REPO_ROOT)} size `{size}` must use `{cls}`"
            )

    def test_default_variant_is_secondary(self):
        text = _read(BUTTON)
        assert re.search(r"\bvariant\s*=\s*[\"']secondary[\"']", text), (
            f"{BUTTON.relative_to(REPO_ROOT)} must default `variant` to `\"secondary\"`"
        )

    def test_default_size_is_md(self):
        text = _read(BUTTON)
        assert re.search(r"\bsize\s*=\s*[\"']md[\"']", text), (
            f"{BUTTON.relative_to(REPO_ROOT)} must default `size` to `\"md\"`"
        )


# ---------------------------------------------------------------------------
# IconButton — `src/modules/design-system/presentation/IconButton.tsx`
# ---------------------------------------------------------------------------


class TestIconButton:
    def test_file_exists(self):
        assert ICON_BUTTON.is_file(), (
            f"missing {ICON_BUTTON.relative_to(REPO_ROOT)} — ODD-DSE-002 must ship IconButton"
        )

    def test_exports_icon_button_props_interface(self):
        text = _read(ICON_BUTTON)
        assert re.search(r"\bexport\s+interface\s+IconButtonProps\b", text), (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} must export `IconButtonProps`"
        )

    def test_exports_default_component(self):
        text = _read(ICON_BUTTON)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(ICON_BUTTON)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    def test_default_shape_classes(self):
        text = _read(ICON_BUTTON)
        for cls in ("inline-flex", "items-center", "justify-center",
                    "p-1", "rounded", "transition-colors",
                    "disabled:opacity-50", "disabled:cursor-not-allowed"):
            assert cls in text, (
                f"{ICON_BUTTON.relative_to(REPO_ROOT)} default class chain must include `{cls}`"
            )

    def test_default_variant_uses_hover_text_primary(self):
        text = _read(ICON_BUTTON)
        assert "text-on-surface-variant" in text, (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} must include `text-on-surface-variant`"
        )
        assert "hover:text-primary" in text, (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} default variant must `hover:text-primary`"
        )

    def test_subtle_variant_uses_hover_bg(self):
        text = _read(ICON_BUTTON)
        assert "hover:bg-surface-container-low" in text, (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} subtle variant must "
            "`hover:bg-surface-container-low`"
        )

    def test_aria_label_required(self):
        text = _read(ICON_BUTTON)
        # `aria-label` MUST appear in the props interface (required for a11y).
        assert re.search(r"[\"\']aria-label[\"\']\s*:\s*string", text), (
            f"{ICON_BUTTON.relative_to(REPO_ROOT)} `aria-label` MUST be a "
            "required string prop"
        )


# ---------------------------------------------------------------------------
# Badge — `src/modules/design-system/presentation/Badge.tsx`
# ---------------------------------------------------------------------------


class TestBadge:
    def test_file_exists(self):
        assert BADGE.is_file(), (
            f"missing {BADGE.relative_to(REPO_ROOT)} — ODD-DSE-002 must ship Badge"
        )

    def test_exports_badge_props_interface(self):
        text = _read(BADGE)
        assert re.search(r"\bexport\s+interface\s+BadgeProps\b", text), (
            f"{BADGE.relative_to(REPO_ROOT)} must export `BadgeProps`"
        )

    def test_exports_default_component(self):
        text = _read(BADGE)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{BADGE.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(BADGE)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{BADGE.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    @pytest.mark.parametrize(
        "variant, classes",
        [
            ("default", ("bg-surface-container-highest", "text-on-surface-variant")),
            ("primary", ("bg-primary/10", "text-primary")),
            ("warning", ("bg-red-50", "text-red-700")),
            ("subtle", ("bg-surface", "text-on-surface-variant",
                        "border", "border-outline-variant")),
        ],
    )
    def test_variant_classes(self, variant, classes):
        text = _read(BADGE)
        for cls in classes:
            assert cls in text, (
                f"{BADGE.relative_to(REPO_ROOT)} variant `{variant}` must use `{cls}`"
            )

    def test_default_class_chain(self):
        text = _read(BADGE)
        for cls in ("inline-flex", "items-center", "uppercase",
                    "tracking-[0.1em]", "text-[11px]", "font-semibold",
                    "px-2", "py-0.5", "rounded"):
            assert cls in text, (
                f"{BADGE.relative_to(REPO_ROOT)} default class chain must include `{cls}`"
            )

    def test_uppercase_flag(self):
        text = _read(BADGE)
        assert re.search(r"\buppercase\s*\?\s*:\s*boolean\b", text), (
            f"{BADGE.relative_to(REPO_ROOT)} must expose `uppercase?: boolean` "
            "to disable the rank-badge styling"
        )


# ---------------------------------------------------------------------------
# Card — `src/modules/design-system/presentation/Card.tsx`
# ---------------------------------------------------------------------------


class TestCard:
    def test_file_exists(self):
        assert CARD.is_file(), (
            f"missing {CARD.relative_to(REPO_ROOT)} — ODD-DSE-002 must ship Card"
        )

    def test_exports_card_props_interface(self):
        text = _read(CARD)
        assert re.search(r"\bexport\s+interface\s+CardProps\b", text), (
            f"{CARD.relative_to(REPO_ROOT)} must export `CardProps`"
        )

    def test_exports_default_component(self):
        text = _read(CARD)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{CARD.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(CARD)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{CARD.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    def test_default_variant_uses_border_and_rounded(self):
        text = _read(CARD)
        for cls in ("bg-surface", "border", "border-outline-variant", "rounded-md"):
            assert cls in text, (
                f"{CARD.relative_to(REPO_ROOT)} default variant must include `{cls}`"
            )

    def test_elevated_variant_includes_arbitrary_shadow(self):
        text = _read(CARD)
        assert re.search(r"shadow-\[\s*0_1px_2px_rgba", text), (
            f"{CARD.relative_to(REPO_ROOT)} elevated variant must use the "
            "documented Tailwind arbitrary shadow cascade"
        )

    def test_subtle_variant_uses_surface_container_low(self):
        text = _read(CARD)
        assert "bg-surface-container-low" in text, (
            f"{CARD.relative_to(REPO_ROOT)} subtle variant must use "
            "`bg-surface-container-low`"
        )


# ---------------------------------------------------------------------------
# EmptyState — `src/modules/design-system/presentation/EmptyState.tsx`
# ---------------------------------------------------------------------------


class TestEmptyState:
    def test_file_exists(self):
        assert EMPTY_STATE.is_file(), (
            f"missing {EMPTY_STATE.relative_to(REPO_ROOT)} — ODD-DSE-003 must ship EmptyState"
        )

    def test_exports_empty_state_props_interface(self):
        text = _read(EMPTY_STATE)
        assert re.search(r"\bexport\s+interface\s+EmptyStateProps\b", text), (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} must export `EmptyStateProps`"
        )

    def test_exports_default_component(self):
        text = _read(EMPTY_STATE)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(EMPTY_STATE)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    @pytest.mark.parametrize(
        "size, classes",
        [
            ("sm", ("p-4", "gap-2")),
            ("md", ("p-6", "gap-3")),
            ("lg", ("p-8", "gap-4")),
        ],
    )
    def test_size_padding_and_gap(self, size, classes):
        text = _read(EMPTY_STATE)
        for cls in classes:
            assert cls in text, (
                f"{EMPTY_STATE.relative_to(REPO_ROOT)} size `{size}` must use `{cls}`"
            )

    @pytest.mark.parametrize(
        "size, title_class",
        [
            ("sm", "text-base"),
            ("md", "text-lg"),
            ("lg", "text-xl"),
        ],
    )
    def test_title_typography(self, size, title_class):
        text = _read(EMPTY_STATE)
        assert title_class in text, (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} size `{size}` title must use `{title_class}`"
        )

    def test_layout_classes(self):
        text = _read(EMPTY_STATE)
        for cls in ("flex", "flex-col", "items-center",
                    "justify-center", "text-center"):
            assert cls in text, (
                f"{EMPTY_STATE.relative_to(REPO_ROOT)} must use `{cls}` for layout"
            )

    def test_description_typography(self):
        text = _read(EMPTY_STATE)
        assert "text-sm" in text, (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} description must use `text-sm`"
        )
        assert "text-on-surface-variant" in text, (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} description must use `text-on-surface-variant`"
        )

    def test_title_typography_includes_font_semibold_and_color(self):
        text = _read(EMPTY_STATE)
        assert "font-semibold" in text, (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} title must use `font-semibold`"
        )
        assert "text-on-surface" in text, (
            f"{EMPTY_STATE.relative_to(REPO_ROOT)} title must use `text-on-surface`"
        )


# ---------------------------------------------------------------------------
# Spinner — `src/modules/design-system/presentation/Spinner.tsx`
# ---------------------------------------------------------------------------


class TestSpinner:
    def test_file_exists(self):
        assert SPINNER.is_file(), (
            f"missing {SPINNER.relative_to(REPO_ROOT)} — ODD-DSE-003 must ship Spinner"
        )

    def test_exports_spinner_props_interface(self):
        text = _read(SPINNER)
        assert re.search(r"\bexport\s+interface\s+SpinnerProps\b", text), (
            f"{SPINNER.relative_to(REPO_ROOT)} must export `SpinnerProps`"
        )

    def test_exports_default_component(self):
        text = _read(SPINNER)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{SPINNER.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_client_component(self):
        text = _read(SPINNER)
        assert re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{SPINNER.relative_to(REPO_ROOT)} MUST declare `\"use client\"` — "
            "Spinner owns the aria-live announcement region via useEffect"
        )

    def test_uses_use_effect_for_announcement(self):
        text = _read(SPINNER)
        assert re.search(r"\buseEffect\b", text), (
            f"{SPINNER.relative_to(REPO_ROOT)} must use `useEffect` for the "
            "aria-live accessibility announcement"
        )

    def test_default_classes(self):
        text = _read(SPINNER)
        for cls in ("text-on-surface-variant", "animate-spin", "material-symbols-outlined"):
            assert cls in text, (
                f"{SPINNER.relative_to(REPO_ROOT)} default class chain must include `{cls}`"
            )

    def test_glyph_is_progress_activity(self):
        text = _read(SPINNER)
        assert "progress_activity" in text, (
            f"{SPINNER.relative_to(REPO_ROOT)} must use the `progress_activity` glyph"
        )

    @pytest.mark.parametrize(
        "size, cls",
        [
            ("sm", "text-[16px]"),
            ("md", "text-[20px]"),
        ],
    )
    def test_size_classes(self, size, cls):
        text = _read(SPINNER)
        assert cls in text, (
            f"{SPINNER.relative_to(REPO_ROOT)} size `{size}` must use `{cls}`"
        )

    def test_status_region_for_screen_readers(self):
        text = _read(SPINNER)
        assert 'role="status"' in text, (
            f"{SPINNER.relative_to(REPO_ROOT)} must render `role=\"status\"` "
            "for the polite announcement region"
        )
        assert 'aria-live="polite"' in text, (
            f"{SPINNER.relative_to(REPO_ROOT)} must render `aria-live=\"polite\"`"
        )


# ---------------------------------------------------------------------------
# InlineMessage — `src/modules/design-system/presentation/InlineMessage.tsx`
# ---------------------------------------------------------------------------


class TestInlineMessage:
    def test_file_exists(self):
        assert INLINE_MESSAGE.is_file(), (
            f"missing {INLINE_MESSAGE.relative_to(REPO_ROOT)} — ODD-DSE-003 must ship InlineMessage"
        )

    def test_exports_inline_message_props_interface(self):
        text = _read(INLINE_MESSAGE)
        assert re.search(r"\bexport\s+interface\s+InlineMessageProps\b", text), (
            f"{INLINE_MESSAGE.relative_to(REPO_ROOT)} must export `InlineMessageProps`"
        )

    def test_exports_default_component(self):
        text = _read(INLINE_MESSAGE)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{INLINE_MESSAGE.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(INLINE_MESSAGE)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{INLINE_MESSAGE.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    def test_default_class_chain(self):
        text = _read(INLINE_MESSAGE)
        for cls in ("rounded-md", "border", "px-3", "py-2", "text-sm"):
            assert cls in text, (
                f"{INLINE_MESSAGE.relative_to(REPO_ROOT)} default class chain must include `{cls}`"
            )

    @pytest.mark.parametrize(
        "variant, classes",
        [
            ("info", ("bg-surface-container-low", "border-outline-variant",
                      "text-on-surface-variant")),
            ("error", ("bg-red-50", "border-red-200", "text-red-700")),
            ("success", ("bg-green-50", "border-green-200", "text-green-700")),
        ],
    )
    def test_variant_classes(self, variant, classes):
        text = _read(INLINE_MESSAGE)
        for cls in classes:
            assert cls in text, (
                f"{INLINE_MESSAGE.relative_to(REPO_ROOT)} variant `{variant}` "
                f"must use `{cls}`"
            )


# ---------------------------------------------------------------------------
# Text — `src/modules/design-system/presentation/Text.tsx`
# ---------------------------------------------------------------------------


class TestText:
    def test_file_exists(self):
        assert TEXT.is_file(), (
            f"missing {TEXT.relative_to(REPO_ROOT)} — ODD-DSE-003 must ship Text"
        )

    def test_exports_text_props_interface(self):
        text = _read(TEXT)
        assert re.search(r"\bexport\s+interface\s+TextProps\b", text), (
            f"{TEXT.relative_to(REPO_ROOT)} must export `TextProps`"
        )

    def test_exports_default_component(self):
        text = _read(TEXT)
        assert re.search(r"\bexport\s+default\s+\w", text), (
            f"{TEXT.relative_to(REPO_ROOT)} must export a default component"
        )

    def test_is_server_component(self):
        text = _read(TEXT)
        assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
            f"{TEXT.relative_to(REPO_ROOT)} MUST NOT declare `\"use client\"`"
        )

    @pytest.mark.parametrize(
        "variant, classes",
        [
            ("body", ("text-base", "text-on-surface")),
            ("body-sm", ("text-sm", "text-on-surface")),
            ("mono", ("font-mono-data", "text-on-surface")),
            ("caption", ("text-xs", "text-on-surface-variant")),
            ("label", ("font-semibold", "text-on-surface")),
        ],
    )
    def test_variant_classes(self, variant, classes):
        text = _read(TEXT)
        for cls in classes:
            assert cls in text, (
                f"{TEXT.relative_to(REPO_ROOT)} variant `{variant}` must use `{cls}`"
            )

    def test_as_polymorphic_p_default(self):
        text = _read(TEXT)
        # Accept either the inline union or a named type alias (e.g.
        # `as?: TextAs`). The functional contract is identical — the
        # alias is the more idiomatic TypeScript style and pins the
        # same union. Both are acceptable.
        inline_union = (
            r"\bas\s*\?\s*:\s*[\"\']p[\"\']\s*\|\s*[\"\']span[\"\']\s*\|"
            r"\s*[\"\']div[\"\']"
        )
        named_alias = r"\bas\s*\?\s*:\s*\w+As\b"
        assert re.search(f"(?:{inline_union})|(?:{named_alias})", text), (
            f"{TEXT.relative_to(REPO_ROOT)} must declare `as?: \"p\" | "
            "\"span\" | \"div\"` (inline union) or `as?: TextAs` (named "
            "alias)"
        )
        assert re.search(r"\bas\s*=\s*[\"\']p[\"\']", text), (
            f"{TEXT.relative_to(REPO_ROOT)} must default `as` to `\"p\"`"
        )


# ---------------------------------------------------------------------------
# Public barrel — `src/modules/design-system/index.ts`
# ---------------------------------------------------------------------------


class TestPublicBarrel:
    def test_preserves_existing_comment_block_and_export_line(self):
        """The Phase 1 contract adds re-exports BELOW the existing
        `export {}` line. The placeholder comment block documenting
        PR 2a / PR 3 deferrals stays intact.
        """
        text = _read(BARREL)
        assert "PR 2a" in text, (
            f"{BARREL.relative_to(REPO_ROOT)} must preserve the PR 2a "
            "placeholder comment block"
        )
        assert "export {};" in text, (
            f"{BARREL.relative_to(REPO_ROOT)} must preserve the `export "
            "{{}};` line (placeholder); Phase 1 adds re-exports BELOW it"
        )

    @pytest.mark.parametrize(
        "primitive_name",
        [
            "Button", "IconButton", "Badge", "Card",
            "EmptyState", "Spinner", "InlineMessage", "Text",
        ],
    )
    def test_barrel_re_exports_default_component(self, primitive_name):
        """Each primitive default export MUST be re-exported from the
        public barrel via `export { default as <Name> } from "..."`.
        Accepts either the `@taxa/design-system/presentation/<Name>`
        path-alias form or the relative `./presentation/<Name>` form.
        """
        text = _read(BARREL)
        alias_path = (
            r"(?:@taxa/design-system/presentation/" + re.escape(primitive_name) +
            r"|\.{1,2}/presentation/" + re.escape(primitive_name) + r")"
        )
        pattern = (
            r"\bexport\s*\{[^}]*\bdefault\s+as\s+" + re.escape(primitive_name) +
            r"\b[^}]*\}\s+from\s+[\"']" + alias_path + r"[\"']"
        )
        assert re.search(pattern, text, re.DOTALL), (
            f"{BARREL.relative_to(REPO_ROOT)} must re-export the default "
            f"component `{primitive_name}` from "
            f"`@taxa/design-system/presentation/{primitive_name}` "
            "(or the relative `./presentation/<Name>` form)"
        )

    def test_barrel_re_exports_tokens(self):
        text = _read(BARREL)
        alias_path = (
            r"(?:@taxa/design-system/domain/tokens|\.{1,2}/domain/tokens)"
        )
        assert re.search(
            r"\bexport\s*\*\s+from\s+[\"']" + alias_path + r"[\"']",
            text,
        ), (
            f"{BARREL.relative_to(REPO_ROOT)} must re-export the tokens surface "
            "via `export * from \".../domain/tokens\"` "
            "(path-alias or relative form)"
        )

    @pytest.mark.parametrize(
        "primitive_file",
        [p.name for p in ALL_PRIMITIVE_FILES],
    )
    def test_no_primitive_is_imported_via_a_layer_folder(self, primitive_file):
        """ESLint blocks deep imports into a module's layer folders.
        Cross-module consumers MUST use the public barrel. The
        primitive files must therefore NOT import siblings via a
        layer-folder path (they live IN that folder).
        """
        text = _read(BARREL)
        # Barrel itself imports the primitive via the presentation layer
        # path — that's the only legitimate deep import here. Any other
        # layer-folder path inside the barrel is a violation.
        forbidden_layers = ("domain", "application", "infrastructure")
        for layer in forbidden_layers:
            pattern = (
                r"\bfrom\s+[\"']@taxa/design-system/" + re.escape(layer) + r"/"
            )
            assert not re.search(pattern, text), (
                f"{BARREL.relative_to(REPO_ROOT)} MUST NOT deep-import "
                f"`@taxa/design-system/{layer}/*` — primitives are the only "
                "deep-import owners (presentation/*). Re-export tokens via "
                "`export * from \".../domain/tokens\"` instead."
            )
