# Mobile UI Reconstruction Reference

Use this reference when an app screenshot has enough complexity that a short visual pass is likely to miss important layout details.

## App Screen Anatomy

- Status bar: time, signal, Wi-Fi, battery, dynamic island/notch area, or Android system icons.
- Navigation area: back button, title, subtitle, search entry, right-side actions, or segmented tabs.
- Content area: scrolling feed, form, detail panel, dashboard, message list, webview, or empty state.
- Persistent controls: floating action button, sticky submit bar, mini player, cart bar, or bottom sheet.
- Bottom area: tab bar, home indicator, gesture safe area, keyboard, or system navigation bar.

## Measurement Heuristics

- Start from the source image dimensions. Use the exact image width as the CSS page width when feasible.
- Common screenshot widths include 375, 390, 393, 414, and 430 CSS-like pixels, but do not force these if the source clearly differs.
- Estimate repeated list item heights before fine-tuning individual elements.
- Measure from stable anchors: top edge, nav title baseline, card edges, tab bar top, and bottom safe area.
- Build coarse layout first, then tune text, icons, and shadows.

## Typography

- Use system fonts first: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- Match hierarchy by relative size and weight before chasing exact font identity.
- Preserve visible line breaks and truncation.
- Keep letter spacing at normal unless the screenshot clearly uses spaced uppercase labels.
- Check Chinese, English, and numeric text separately because their apparent height can differ.

## Color And Surfaces

- Sample visually from large flat regions first: page background, cards, nav bars, and tab bars.
- Use hairline dividers for iOS-like lists, often `1px` with low alpha.
- Shadows in app UI are usually subtle. Prefer small blur and low opacity unless the screenshot clearly uses strong elevation.
- Match disabled, secondary, danger, success, and accent colors separately.

## Native Pattern Cues

- iOS pages often have larger safe-area top spacing, centered titles, rounded grouped cards, thin dividers, and a home indicator.
- Android pages often use top app bars, left-aligned titles, material-like elevation, floating action buttons, and system navigation bars.
- Mini-program pages may include capsule menu controls, page-level nav styling, and denser content spacing.

## Images And Icons

- Use the source screenshot for cropped photos or avatars only when the user supplied the screenshot and the output is a reconstruction of that screenshot.
- Keep icon stroke width, visual size, and alignment close to the source.
- If using lucide or another icon library, tune size and stroke width instead of accepting defaults blindly.
- Do not replace an app-specific logo with a random generic icon without noting the approximation.

## Verification Pass

Run at least one visual verification when feasible:

1. Render the HTML at the source screenshot dimensions.
2. Capture the rendered page.
3. Compare global layout first: screen edges, bars, cards, and major blocks.
4. Compare text second: position, size, weight, line breaks, and color.
5. Compare details last: icons, shadows, dividers, badges, and control states.

If using a pixel comparison script, investigate large-difference regions first, then do a human visual pass for text and perceived polish.
