# Image Generation Reference

Use this reference when the skill needs to create or edit raster image assets with GPT Image 2 models.

## Model Selection

Keep model selection transparent to the user.

- Use `gpt-image-2` for text-to-image requests with no reference image.
- Use `gpt-image-2-all` for image-to-image, image editing, redraws, style transfer, multi-reference fusion, product/avatar/photo replacement, or any request that needs the output to preserve details from an input image.
- Do not ask the user which model to use. Ask only about visible output parameters.

## Parameter Reminder

If the user did not provide generation parameters, ask once:

```text
你要不要设置图片参数？可以指定尺寸/比例、质量、数量、格式、背景、负面提示词和输出目录；不设置我就用默认参数继续。
```

Defaults after the reminder, or when the user says to proceed:

- size: `1024x1024`
- quality: `high`
- count: `1`
- output format: `png`
- background: `auto`
- negative prompt: empty
- output directory: the current task's asset/output folder

When the user provides parameters in natural language, convert them before calling the helper. Examples:

- "竖图", "手机海报", "portrait" -> prefer `1024x1536`
- "横图", "banner", "landscape" -> prefer `1536x1024`
- "方图", "头像", "icon" -> prefer `1024x1024`
- "两张/4 variants" -> `--count 2` / `--count 4`
- "低/中/高质量" -> `--quality low|medium|high`
- "webp/jpeg/png" -> `--format webp|jpeg|png`

## Helper Script

Call `scripts/generate_image.py` from the skill parent directory.

Text-to-image:

```bash
python3 scripts/generate_image.py \
  --prompt prompt.txt \
  --out-dir generated-assets \
  --size 1024x1024 \
  --quality high \
  --count 1 \
  --format png
```

Image-to-image or edit:

```bash
python3 scripts/generate_image.py \
  --prompt prompt.txt \
  --image ref.png \
  --image ref2.png \
  --out-dir generated-assets \
  --size 1024x1536 \
  --quality high \
  --count 1 \
  --format png
```

Pass the user's actual visual requirements in the prompt file. If a negative prompt is supplied, pass `--negative-prompt "..."`; the helper appends it to the final prompt as an avoidance instruction.

## Environment

The helper reads credentials from process environment variables and then from `$CODEX_HOME/.env` or `~/.codex/.env`. Values already exported in the shell take precedence over `.env` values.

Example `~/.codex/.env`:

```bash
GPT_IMAGE_2_BASE_URL="https://your-image-api-base-url/v1"
GPT_IMAGE_2_API_KEY="xxxxx"
```

For `gpt-image-2`:

- API key: `GPT_IMAGE_2_API_KEY`, falling back to `OPENAI_API_KEY`
- Base URL: `GPT_IMAGE_2_BASE_URL`, `OPENAI_BASE_URL`, `BASE_URL`, `base_url`, then `https://api.openai.com`. Prefer `GPT_IMAGE_2_BASE_URL` in `~/.codex/.env`; `BASE_URL` and `base_url` are legacy aliases.

For `gpt-image-2-all`:

- API key: `GPT_IMAGE_2_ALL_API_KEY`, `GUI_SORA2_KEY`, `GPT_IMAGE_2_API_KEY`, then `OPENAI_API_KEY`
- Base URL: `GPT_IMAGE_2_ALL_BASE_URL`, `SORA2_API_BASE_URL`, `GPT_IMAGE_2_BASE_URL`, `OPENAI_BASE_URL`, `BASE_URL`, then `base_url`. This model has no default base URL, so one of these must be set. Prefer `GPT_IMAGE_2_ALL_BASE_URL` for a dedicated edit/fusion endpoint, or `GPT_IMAGE_2_BASE_URL` when both models share the same endpoint.

If credentials are missing, stop and tell the user which environment variable is needed. Do not invent a key or silently fall back to an unrelated provider.

## API Behavior

The helper uses:

- `POST /v1/images/generations` for text-to-image
- `POST /v1/images/edits` with multipart image fields for image-to-image/editing

It accepts either `b64_json` image data or `url` responses and writes:

- generated images named `image-001.<format>`, `image-002.<format>`, etc.
- `manifest.json` with prompt, selected operation, parameters, and output paths

## Quality Checks

After generation:

1. Inspect the output image when possible.
2. Check whether it matches the requested subject, style, aspect, text/logo constraints, and reference-image preservation.
3. Regenerate with a refined prompt if the main subject, layout, or asset utility is clearly wrong.
4. For UI reconstruction, crop or place generated assets inside real HTML/CSS rather than replacing the whole screen with a raster image.
