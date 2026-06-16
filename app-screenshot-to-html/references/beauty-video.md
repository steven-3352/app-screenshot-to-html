# Beauty Short Video Reference

Use this reference when the user wants a tasteful short video featuring an attractive adult woman, especially for GPT Image 2 keyframes and Grok/video-model generation.

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
- fictional adult woman, 25 years old
- tasteful fitted dress with a modest neckline
- warm indoor smartphone selfie
- fixed camera, medium close-up
- hair adjustment, gentle sway, soft smile, confident eye contact

## Wording Rewrite

Map risky wording to safer visual intent:

- `少女/萝莉/学生妹/幼态/teen` -> `成年女性、成熟气质`
- `裸/露点/走光` -> `不暴露、平台友好的服装`
- `透明/透视/真空/情趣` -> `有设计感但不透明的时装`
- `擦边/过审/躲审核` -> `平台友好、合规表达`
- `撩人/勾引/挑逗` -> `有吸引力的镜头互动`
- `火辣/欲/性感爆棚` -> `吸睛、优雅克制、有张力`
- `深V/低胸/事业线/胸部特写` -> `修身但领口得体`
- `脱衣/掀衣/舔/抚摸` -> `自然手部动作和轻微律动`
- `像真人/看不出AI/伪装真人` -> `自然质感，并按平台要求标注 AI 生成`

## Prompt Structure

For GPT Image 2 keyframe prompts, include:

- vertical aspect ratio
- fictional adult identity
- appearance and outfit
- scene and lighting
- camera framing
- realistic phone-camera texture
- non-explicit and tasteful constraints

For video model prompts and API generation, include:

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
python3 app-screenshot-to-html/scripts/beauty_video_brief.py questions
```

Build a brief:

```bash
python3 app-screenshot-to-html/scripts/beauty_video_brief.py build \
  --out-dir video-brief \
  --title warm-indoor-beauty \
  --reference ref.png \
  --appearance "long black hair, natural makeup, confident eye contact" \
  --outfit "cream-white fitted knit dress with a modest neckline" \
  --scene "modern hotel-style room, warm ceiling light" \
  --mood "confident, playful, charming, elegant" \
  --action "brushes hair back, gently sways, smiles softly, loop-friendly ending" \
  --model "Grok video"
```

Outputs:

- `beauty-video-brief.md`
- `beauty-video-brief.json`
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
python3 app-screenshot-to-html/scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --image video-brief/first-frame.png \
  --out-dir video-brief/video-output \
  --size 9:16 \
  --duration 10
```

If an image reference is a local file, the helper sends it as the `input_reference` multipart file field. For `grok-video-3-10s`, local file input is the expected path. If you only have a URL, download it first or use a helper that uploads bytes.

Alternative Grok JSON format:

```bash
python3 app-screenshot-to-html/scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --out-dir video-brief/video-output \
  --body-format grok-json \
  --model grok-video-3 \
  --size 9:16 \
  --quality 720P
```

Poll an existing task without resubmitting:

```bash
python3 app-screenshot-to-html/scripts/generate_video.py \
  --task-id "grok:..." \
  --out-dir video-brief/video-output
```

For other provider APIs, pass `--endpoint`, `--body-format json` or `--body-format multipart`, and, for async jobs, `--poll-endpoint`, using `{id}` as the task id placeholder when needed.

Dry-run without calling the API:

```bash
python3 app-screenshot-to-html/scripts/generate_video.py \
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
python3 app-screenshot-to-html/scripts/beauty_video_xhs_package.py \
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
