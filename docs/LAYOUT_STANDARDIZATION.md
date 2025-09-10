# Layout Standardization Proposal

This doc outlines a path to standardize page layouts and body classes.

## Goals
- Unify spacing below the sticky header across pages.
- Reduce one-off CSS by introducing reusable layout components.
- Provide a shared, extensible base for chat-like pages.

## Changes Implemented
 Introduced a global CSS variable `--header-height` in `templates/base.html`.
 The platform now uses a fixed header (`.phoenix-header`) and reserves space globally by applying `padding-top: var(--header-height)` to the `body` (and `scroll-padding-top` on `html` for anchor jumps). This ensures every page starts below the header.
 A small script in `base.html` measures the actual header height on load/resize and syncs `--header-height` dynamically. This keeps offsets correct if the header content or font sizes change.
- Added `templates/_layouts/chat_base.html` reusable layout for chat pages with consistent slots: `chat_sidebar`, `chat_header`, `chat_messages`, `chat_input`.
 3) If a page needs a custom layout (like full-bleed or fixed panels), consider applying a page-specific body class and adjust internal containers, not the global `body` offset. For sticky elements under the header, use the utility class `.sticky-after-header { top: var(--header-height); }`.

 5) For chat-like pages, prefer extending `_layouts/chat_base.html` which already accounts for `--header-height` (e.g., `height: calc(100vh - var(--header-height))`).
- New chat-like pages should extend `templates/_layouts/chat_base.html`.
- Gradually refactor `derplexity_v2.html` to use `chat_base.html` by mapping its regions to the provided blocks.
- Align other long-scroll content pages to rely on the default `main` padding, removing ad-hoc top margins where possible.

## Next Steps
- Identify duplicated chat/sidebar patterns across derplexity/robin and converge on shared components.
- Extract message bubble styles and actions into shared CSS partials.
- Add tests (snapshot or Percy) to catch layout regressions around the sticky header.
