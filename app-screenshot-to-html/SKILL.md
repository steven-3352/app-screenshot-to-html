---
name: app-screenshot-to-html
description: Reconstruct mobile app page screenshots as high-fidelity HTML/CSS. Use when the user uploads or references an iOS, Android, mini-program, mobile H5, or app-like page screenshot and asks to recreate, restore, convert, reproduce, or implement the screen as HTML, CSS, a standalone web page, or a frontend prototype.
---

# App Screenshot To HTML

## Goal

Recreate the supplied mobile app screenshot as a browser-rendered HTML/CSS page with high visual fidelity. Treat the task as UI reconstruction, not image description and not redesign.

## Default Output

Create a standalone HTML file unless the user explicitly asks for React, Vue, Tailwind, or another framework. Keep the rendered viewport the same size and aspect ratio as the source screenshot whenever possible.

## Workflow

1. Inspect the screenshot and record the source width, height, likely device class, and visible platform conventions.
2. Divide the screen into app regions: status bar, navigation/header, content, floating actions, bottom tab bar, and safe area.
3. Extract visible UI facts:
   - exact readable text
   - typography hierarchy
   - background, text, divider, card, button, and accent colors
   - spacing, alignment, grid rhythm, border radius, shadows, and hairlines
   - icons, images, avatars, badges, inputs, controls, and list rows
4. Implement the layout as real HTML/CSS. Use flex/grid and fixed mobile constraints before adding responsive behavior.
5. Render the page in a browser at the source screenshot dimensions.
6. Capture a screenshot and compare it with the source.
7. Iterate on spacing, sizing, color, typography, and missing elements until the result is visually close.

## Reconstruction Rules

- Match the screenshot; do not modernize, simplify, or make a marketing page.
- Preserve app-like density. Avoid oversized web landing-page spacing, decorative sections, or generic card-heavy redesigns.
- Use exact visible text when readable. If text is unreadable, preserve its visual role with a short neutral placeholder.
- Use CSS variables for repeated colors, radii, shadows, and spacing tokens.
- Include the visible status bar, navigation bar, bottom tabs, and safe-area spacing when present.
- Use native HTML elements for lists, buttons, forms, inputs, switches, and tabs when practical.
- Use icon libraries available in the target project. If none exists, use CSS shapes, inline SVG, or simple text/icon approximations.
- For screenshots containing photos, avatars, product images, maps, or complex illustrations, crop from the source image when allowed; otherwise use visually similar placeholders and state that limitation.
- Do not claim exact or 100% reconstruction when fonts, source assets, icons, or hidden states are unavailable.

## Fidelity Checklist

Before final delivery, check:

- overall canvas size and vertical content fit
- status/header heights and bottom safe area
- primary text positions, line breaks, and weights
- card/list row dimensions and alignment
- icon sizes and tappable-control positions
- color similarity for background, text, dividers, and accents
- absence of accidental overlap, clipping, or layout shift

For detailed mobile UI heuristics, read `references/mobile-ui-reconstruction.md` when the screenshot is non-trivial.

## Screenshot Comparison

Use `scripts/compare_screenshots.py` when two screenshot files are available:

```bash
python3 app-screenshot-to-html/scripts/compare_screenshots.py source.png rendered.png --diff diff.png
```

Use the numeric result as guidance, not as the only quality signal. A low pixel difference can still hide important text or alignment mistakes.

## Final Response

Report the output path, viewport size used, verification performed, and any fidelity limitations such as unknown fonts, missing icons, or unavailable image assets.
