# Beauty Short Video Reference

Use this reference when the user wants a tasteful short video featuring an attractive adult woman, especially for GPT Image 2 keyframes and Grok/video-model generation.

## Fixed Creative Baseline

This project primarily produces **beautiful woman short videos**. Keep this baseline fixed in every keyframe prompt and video prompt unless the user explicitly overrides it:

```text
Primary goal: a genuinely beautiful adult woman.
Sexy but never vulgar: minimal tasteful outfits such as swimwear, lingerie, bodysuit, off-shoulder tops, or short skirts are allowed; show subtle skin and silhouette with an implied allure rather than explicit exposure.
Allure should feel elegant, confident, and platform-friendly.
```

Creative rules:

- **Beauty first**: the subject must read as genuinely beautiful before adding motion or styling.
- **Less clothing, not exposed**: prefer minimal outfits with clear coverage boundaries and implied allure.
- **Sexy ≠ vulgar**: sensual confidence, silhouette, and subtle reveal are good; explicit posing is not.
- **Allowed outfit directions**: swimwear, lingerie, bodysuit, off-shoulder tops, short skirts, fitted dresses.
- **Still refuse**: nudity, explicit sexual content, minors, childlike styling, coercion, real-person impersonation.

## Safety Positioning

- Create fictional adult characters only. State adult age clearly, usually `25 years old`.
- Keep the tone attractive, confident, charming, elegant, and tasteful.
- Do not optimize for bypassing moderation, evading platform review, or making AI content deceptively appear real.
- Rewrite unsafe or crude wording into platform-friendly creative direction.
- Refuse or redirect requests involving minors, childlike styling, nudity, explicit sexual acts, coercion,偷拍, or real-person impersonation.
- Follow platform AI-content disclosure requirements when publishing.

## User Intake

Ask only the missing questions needed to build the brief. Prefer two or three rounds at most.

Core questions:

1. Reference assets: image/video path, and which parts to reference: hair, outfit, lighting, scene, pose, rhythm, or composition.
2. Character: adult age, ethnicity/style direction, face impression, hair, makeup, personality.
3. Outfit: color, fabric, silhouette, coverage level, accessories.
4. Scene and lighting: room type, background, time of day, light temperature.
5. Motion: gesture, dance intensity, facial expression, camera distance, loop ending.
6. Output: aspect ratio, duration, first-frame generation with GPT Image 2, target video model, and whether to call the video API.

When the user is vague, default to:

- 9:16, 8-10 seconds
- fictional adult woman, 25 years old, strikingly beautiful face and figure
- stylish minimal swimwear or tasteful lingerie-inspired outfit with clear coverage
- poolside, hotel room, or warm indoor scene with flattering light
- fixed camera, medium close-up that highlights beauty and silhouette
- slow hair flip, gentle hip sway, soft smile, subtle shoulder turn

## Wording Rewrite

Map risky wording to safer visual intent:

- `少女/萝莉/学生妹/幼态/teen` -> `成年女性、成熟气质`
- `裸/露点/走光` -> `不暴露、边界清晰的服装`
- `透明/透视/真空` -> `有质感、边界清晰且不透明的时装`
- `擦边/过审/躲审核` -> `平台友好、合规表达`
- `撩人/勾引/挑逗` -> `有吸引力的镜头互动`
- `火辣/欲/低俗/艳俗` -> `性感但有品味、克制高级`
- `事业线/胸部特写` -> `适度曲线与若隐若现，但不特写敏感部位`
- `脱衣/掀衣/舔/抚摸` -> `自然手部动作和轻微律动`
- `像真人/看不出AI/伪装真人` -> `自然质感，并按平台要求标注 AI 生成`

Do **not** rewrite valid outfit requests such as `泳装`, `内衣`, `比基尼`, `吊带`, `露肩` unless they also imply nudity, minors, or explicit acts.

## Prompt Structure

For GPT Image 2 keyframe prompts, include:

- the fixed creative baseline above
- vertical aspect ratio
- fictional adult identity with clear beauty cues
- appearance and outfit
- scene and lighting
- camera framing
- realistic phone-camera texture
- sexy-but-not-vulgar constraints

For video model prompts and API generation, include:

- the fixed creative baseline above
- duration and aspect ratio
- same character and outfit
- simple stable camera
- three-part motion: opening gesture, main subtle movement, loop-friendly ending
- realistic hair/cloth movement
- explicit safety constraints

Negative prompt baseline:

```text
underage, teen, childlike, school uniform, nudity, explicit sexual content, transparent clothing, wardrobe malfunction, coercion, intoxication, 偷拍, celebrity likeness, real person impersonation, extra fingers, distorted hands, warped face, uncanny eyes, plastic skin, text, watermark, logo
```

## Brief Helper

Use `scripts/beauty_video_brief.py` to ask intake questions or generate reusable prompt artifacts.

Print intake questions:

```bash
python3 scripts/beauty_video_brief.py questions
```

Build a brief:

```bash
python3 scripts/beauty_video_brief.py build \
  --out-dir video-brief \
  --title poolside-sexy-beauty \
  --reference ref.png \
  --appearance "long dark hair, refined makeup, luminous skin, alluring eyes, photogenic beauty" \
  --outfit "stylish minimal black one-piece swimsuit, tasteful coverage, subtle skin reveal without exposure" \
  --scene "poolside at golden hour with soft backlight" \
  --mood "confident, sensual, elegant, playful charm" \
  --action "slow hair flip, gentle hip sway, soft smile, subtle shoulder turn, loop-friendly ending" \
  --model "Grok video"
```

Outputs:

- `beauty-video-brief.md`
- `beauty-video-brief.json`
- `video-prompt-baseline.txt`
- `gpt-image2-keyframe-prompt.txt`
- `video-model-prompt.txt`
- `negative-prompt.txt`

If the helper returns `needs_human_review`, inspect `safety_flags` and rewrite or refuse before generating.

## Reference Image vs. No Reference Image

Decide the path before calling the video helper:

- **A reference image is available** (user-supplied photo, or a frame they point to): use it directly as the first frame. Skip first-frame generation and call `scripts/generate_video.py --image <path>`.
- **No reference image**: generate a first frame first. Build the keyframe prompt, run `scripts/generate_image.py` to create a first frame, inspect it, then pass that file to `scripts/generate_video.py --image <generated-frame>`.

The default `grok-video-3-10s` model requires a reference image (`input_reference`), so the no-reference path must always produce a first frame before video generation.

## Video API Helper

Use `scripts/generate_video.py` when the user wants to call the configured video model. The helper reads credentials from process environment, `./.env`, `$CODEX_HOME/.env`, or `~/.codex/.env`.

Expected environment variables:

```bash
VIDEO_API_KEY="sk-..."
VIDEO_API_BASE_URL="https://your-video-api-base-url"
VIDEO_MODEL="grok-video-3-10s"
```

The video API key and base URL are read only from these environment variables, so swapping providers is a config change with no code edit.

For the Grok video provider, the documented OpenAI-style endpoint is `POST /v1/videos` with `multipart/form-data` fields:

- `model`
- `prompt`
- `seconds`
- `input_reference` for the reference image file
- `size`, usually `720P` for `grok-video-3-10s`

The helper defaults to that endpoint (`--body-format openai-videos`) and automatically polls `GET /v1/videos/{id}`. The provider also exposes `grok-videos` for the OpenAI-style video model and `grok-video-3` for the JSON `/v1/video/create` format. If the configured `VIDEO_MODEL` returns `no available platform found`, retry later or pass one of those model names explicitly.

Image-to-video with a first-frame image (a user-supplied reference or a generated first frame):

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --image video-brief/first-frame.png \
  --out-dir video-brief/video-output \
  --size 9:16 \
  --duration 10
```

If an image reference is a local file, the helper sends it as the `input_reference` multipart file field. For `grok-video-3-10s`, local file input is the expected path. If you only have a URL, download it first or use a helper that uploads bytes.

Alternative Grok JSON format:

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --out-dir video-brief/video-output \
  --body-format grok-json \
  --model grok-video-3 \
  --size 9:16 \
  --quality 720P
```

Poll an existing task without resubmitting:

```bash
python3 scripts/generate_video.py \
  --task-id "grok:..." \
  --out-dir video-brief/video-output
```

For other provider APIs, pass `--endpoint`, `--body-format json` or `--body-format multipart`, and, for async jobs, `--poll-endpoint`, using `{id}` as the task id placeholder when needed.

Dry-run without calling the API:

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --out-dir video-brief/video-output \
  --dry-run
```

Outputs:

- `video-request-payload.json`
- `video-api-response.json`
- `video-api-final-response.json` when polling is used
- `video-manifest.json`
- `video-001.mp4` when the API returns a downloadable video URL

## Xiaohongshu Publish Package

After the MP4 is generated, use `scripts/beauty_video_xhs_package.py` when the user wants content that can be posted directly to Xiaohongshu or a page where viewers can watch the result.

```bash
python3 scripts/beauty_video_xhs_package.py \
  --brief-json video-brief/beauty-video-brief.json \
  --manifest video-brief/video-output/video-manifest.json \
  --video video-brief/video-output/video-001.mp4 \
  --cover video-brief/xhs-video-cover.jpg \
  --out-dir video-brief/xhs-publish
```

Outputs:

- `xhs-publish-content.md`: structured Xiaohongshu title, body, tags, checklist, and asset paths
- `xhs-caption.txt`: copy-paste caption
- `watch-effect.html`: local HTML page with the generated video player and publish copy
- `xhs-package.json`: machine-readable package manifest

Keep the publishing copy focused on process, tooling, and creative workflow. Include an AI-generated disclosure. Do not claim the person or footage is real.
