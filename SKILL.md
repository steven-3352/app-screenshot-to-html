---
name: app-screenshot-to-html
description: Reconstruct mobile app page screenshots as high-fidelity HTML/CSS, generate or edit bitmap image assets for those reconstructions, and create/generate tasteful adult beauty short-video briefs/prompts/videos with GPT Image 2 keyframes plus configured Grok/video models. Use when the user uploads or references an iOS, Android, mini-program, mobile H5, or app-like page screenshot and asks to recreate, restore, convert, reproduce, or implement the screen as HTML, CSS, a standalone web page, or a frontend prototype; when the user asks this skill to create, redraw, edit, fuse, or replace photos, avatars, illustrations, icons, posters, product images, backgrounds, or other raster assets with GPT Image 2 image generation models; or when the user asks for a compliant attractive/sexy-but-not-vulgar adult woman short-video concept, prompt, first-frame image prompt, reference-image workflow, outfit/appearance interaction, video model prompt, or video generation using VIDEO_API_KEY/VIDEO_API_BASE_URL/VIDEO_MODEL.
---

# App Screenshot To HTML

## Goal

Recreate the supplied mobile app screenshot as a browser-rendered HTML/CSS page with high visual fidelity. Treat the task as UI reconstruction, not image description and not redesign.

## Default Output

Create a standalone HTML file unless the user explicitly asks for React, Vue, Tailwind, or another framework. Keep the rendered viewport the same size and aspect ratio as the source screenshot whenever possible.

When the user asks for image creation or image editing as part of the work, create raster image files and then use them in the HTML/CSS output when appropriate. Keep model choice internal and do not ask the user to choose between `gpt-image-2` and `gpt-image-2-all`.

When the user asks for a beauty short-video concept or generated video, produce a compliant creative brief, generation prompts, and optionally call the configured video API. Keep characters fictional and adult, attractive but non-explicit, and do not help bypass moderation or deceive viewers that AI content is real footage.

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

## Image Generation Branch

Use this branch when the task needs a new raster image, replacement asset, edited source image, or reference-image fusion.

1. Infer image intent from the user's prompt:
   - Text-to-image: no reference image is needed.
   - Image-to-image, editing, style transfer, redraw, fusion, or asset replacement: one or more reference images are needed.
2. If the user did not specify generation parameters, ask once whether they want to set them. Mention only user-facing parameters: size/aspect, quality, output count, output format, background, negative prompt, and output folder. Do not expose model names.
3. If the user leaves parameters unset or says to use defaults, use `1024x1024`, `high`, `1`, `png`, `auto` background, no negative prompt, and the current task output folder.
4. Read `references/image-generation.md` before calling image generation.
5. Select the model internally:
   - Use `gpt-image-2` for straightforward text-to-image.
   - Use `gpt-image-2-all` when any reference image, image editing, redraw, multi-image fusion, or preserve-from-input requirement is present.
6. Generate the image asset, save it as a file, inspect the result when possible, and iterate if it misses the requested visual intent.
7. When using generated assets in a reconstructed page, keep the page layout real HTML/CSS and reference the asset file; do not use a full-page generated image as a shortcut for UI reconstruction.

## Beauty Video Branch

Use this branch when the user wants an attractive adult woman short video, a GPT Image 2 first frame, a Grok/video-model prompt, a generated video, or a workflow based on reference images/videos.

1. Read `references/beauty-video.md`.
2. Ask for missing creative inputs in at most two or three short rounds:
   - reference image/video and which traits to reuse
   - fictional adult character appearance and personality
   - outfit, coverage level, scene, lighting, action, camera, duration, aspect ratio, and target model
3. If the user uses risky or crude wording, rewrite it into safe visual intent such as `attractive`, `confident`, `playful`, `tasteful`, `elegant`, or `platform-friendly`. Do not frame this as bypassing moderation.
4. Refuse or redirect minors, childlike styling, nudity, explicit sexual acts, coercion,偷拍, and real-person impersonation.
5. Use `scripts/beauty_video_brief.py questions` when you need the intake checklist.
6. Use `scripts/beauty_video_brief.py build ...` to generate:
   - `beauty-video-brief.md`
   - `beauty-video-brief.json`
   - `video-prompt-baseline.txt`
   - `gpt-image2-keyframe-prompt.txt`
   - `video-model-prompt.txt`
   - `negative-prompt.txt`
7. Choose the first-frame path based on whether a reference image is available:
   - If the user provides a reference image (a photo or an existing frame), use it directly as the first frame and skip first-frame generation.
   - If there is no reference image, generate a first frame with `scripts/generate_image.py` using the keyframe prompt, then inspect it before using it for video.
8. If the user wants to generate the video, use `scripts/generate_video.py` with the first-frame image passed as `--image`. It reads `VIDEO_API_KEY`, `VIDEO_API_BASE_URL`, and `VIDEO_MODEL` from environment files, so the key and base URL are config-only and require no code change. The helper defaults to `POST /v1/videos` and polls `GET /v1/videos/{id}`. The default `grok-video-3-10s` model requires a reference image, so always have a first frame ready.
9. If the API returns `no available platform found`, the request shape is accepted but the upstream model is unavailable; retry later or try the documented model names `grok-videos` for `--body-format openai-videos` or `grok-video-3` for `--body-format grok-json`.
10. Final prompts and videos should be sexy-but-not-vulgar: adult, beautiful first, minimal-but-covered outfits such as swimwear or lingerie are allowed, non-explicit, no underage styling, no celebrity likeness, no real-person cloning, and follow platform AI-content disclosure requirements.
11. After generating a video, if the user wants a shareable post, use `scripts/beauty_video_xhs_package.py` to create a Xiaohongshu-ready caption, publish checklist, and local watch page that plays the generated MP4.

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
python3 scripts/compare_screenshots.py source.png rendered.png --diff diff.png
```

Use the numeric result as guidance, not as the only quality signal. A low pixel difference can still hide important text or alignment mistakes.

## HTML Element Numbering Helper

Use `scripts/html_element_editor.mjs` when the user wants a product manager or non-technical reviewer to identify page elements by number and request copy/style/attribute changes.

Generate a numbered preview and mapping from a local static HTML file:

```bash
node scripts/html_element_editor.mjs scan ./index.html --name homepage
```

Open `.codex-html-editor/homepage.numbered.html` for the reviewer. The preview outlines editable elements and labels them with stable numbers for that scan. Keep `.codex-html-editor/homepage.map.json` for follow-up edits.

List the mapped elements:

```bash
node scripts/html_element_editor.mjs list .codex-html-editor/homepage.map.json
```

Apply reviewer requests by number:

```bash
node scripts/html_element_editor.mjs text .codex-html-editor/homepage.map.json 12 "立即开始"
node scripts/html_element_editor.mjs style .codex-html-editor/homepage.map.json 12 "background: #111827; color: white"
node scripts/html_element_editor.mjs attr .codex-html-editor/homepage.map.json 8 alt "产品控制台截图"
```

The helper writes a timestamped backup before changing the source HTML, then refreshes the map and preview. For React, Vue, Tailwind, or other source-driven projects, use this helper for reviewer communication, then prefer editing the component/source files instead of built HTML.

## Image Generation Helper

Use `scripts/generate_image.py` for GPT Image 2 generation/editing when API credentials are available:

```bash
python3 scripts/generate_image.py --prompt prompt.txt --out-dir generated-assets
python3 scripts/generate_image.py --prompt prompt.txt --image ref.png --out-dir generated-assets
```

The script chooses the image model from the presence of reference images and writes output files plus a JSON manifest.

## Beauty Video Brief Helper

Use `scripts/beauty_video_brief.py` to collect inputs and write prompt artifacts for tasteful adult beauty short videos:

```bash
python3 scripts/beauty_video_brief.py questions
python3 scripts/beauty_video_brief.py build --out-dir video-brief --appearance "long black hair, natural makeup" --outfit "cream-white fitted dress with a modest neckline"
```

If the helper returns `needs_human_review`, inspect its safety flags before generating images or video prompts.

Use `scripts/generate_video.py` to call the configured Grok/video model:

```bash
python3 scripts/generate_video.py --prompt video-brief/video-model-prompt.txt --image video-brief/first-frame.png --out-dir video-brief/video-output --size 9:16 --duration 10
```

For the Grok video provider, prefer `--size 9:16` for the creative brief, but `grok-video-3-10s` is normalized to `720P` for the upstream request. The default body format is `openai-videos`, which submits multipart fields `model`, `prompt`, `seconds`, `size`, and a required `input_reference` file for Grok special models. For the alternate JSON API, pass `--body-format grok-json --model grok-video-3`. For other provider-specific APIs, pass `--endpoint`, `--body-format json` or `--body-format multipart`, and, for async jobs, `--poll-endpoint`. Use `--task-id` to poll an existing task without resubmitting. Use `--dry-run` to inspect the payload without spending video credits.

To package the result for Xiaohongshu after generation:

```bash
python3 scripts/beauty_video_xhs_package.py \
  --brief-json video-brief/beauty-video-brief.json \
  --manifest video-brief/video-output/video-manifest.json \
  --video video-brief/video-output/video-001.mp4 \
  --cover video-brief/xhs-video-cover.jpg \
  --out-dir video-brief/xhs-publish
```

This writes:

- `xhs-publish-content.md`
- `xhs-caption.txt`
- `watch-effect.html`
- `xhs-package.json`

## Final Response

Report the output path, viewport size used, verification performed, generated asset paths when any, and any fidelity limitations such as unknown fonts, missing icons, unavailable image assets, or image generation parameters left at defaults. For beauty-video work, report the brief path, keyframe prompt path, video prompt path, negative prompt path, video manifest/output path when generated, reference assets used, and any safety rewrites or limitations.
