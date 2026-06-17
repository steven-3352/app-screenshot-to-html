#!/usr/bin/env python3
"""Generate or edit images with GPT Image 2 models.

The script chooses the model internally:
- text-to-image: gpt-image-2
- reference/edit workflows: gpt-image-2-all
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


TEXT_MODEL = "gpt-image-2"
EDIT_MODEL = "gpt-image-2-all"
VALID_QUALITIES = {"low", "medium", "high", "auto"}
VALID_FORMATS = {"png", "webp", "jpeg"}
DOTENV_LOADED = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate text-to-image or image-to-image assets with GPT Image 2 models."
    )
    parser.add_argument("--prompt", required=True, help="Prompt text or path to a prompt file.")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Reference image path or URL. Repeat for multi-reference edits.",
    )
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for outputs.")
    parser.add_argument("--size", default="1024x1024", help="Output size, e.g. 1024x1024.")
    parser.add_argument(
        "--quality",
        default="high",
        choices=sorted(VALID_QUALITIES),
        help="Rendering quality.",
    )
    parser.add_argument(
        "--count",
        default=1,
        type=int,
        help="Number of output images. Clamped to 1..8.",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=sorted(VALID_FORMATS),
        help="Output file format.",
    )
    parser.add_argument(
        "--background",
        default="auto",
        choices=["auto", "opaque"],
        help="Background mode. Transparent is intentionally not exposed for gpt-image-2.",
    )
    parser.add_argument(
        "--negative-prompt",
        default="",
        help="Things the image should avoid; appended to the prompt.",
    )
    parser.add_argument(
        "--timeout",
        default=300,
        type=float,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def read_prompt(value: str) -> str:
    path = Path(value).expanduser()
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return value.strip()


def final_prompt(prompt: str, negative_prompt: str, size: str) -> str:
    parts = [prompt.strip(), f"Size/aspect: {size}"]
    if negative_prompt.strip():
        parts.append(f"Avoid: {negative_prompt.strip()}")
    return "\n\n".join(part for part in parts if part)


def env_first(names: list[str], default: str = "") -> str:
    load_codex_dotenv()
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def load_codex_dotenv() -> None:
    global DOTENV_LOADED
    if DOTENV_LOADED:
        return
    DOTENV_LOADED = True

    codex_home_raw = os.environ.get("CODEX_HOME", "").strip()
    paths: list[Path] = []
    if codex_home_raw:
        paths.append(Path(codex_home_raw).expanduser() / ".env")
    paths.append(Path.home() / ".codex" / ".env")

    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        load_env_file(path)


def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(raw_line)
        if not parsed:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].strip()
    key, separator, value = line.partition("=")
    if not separator:
        return None
    key = key.strip()
    if not is_env_key(key):
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    return key, value


def is_env_key(key: str) -> bool:
    if not key or not (key[0].isalpha() or key[0] == "_"):
        return False
    return all(char.isalnum() or char == "_" for char in key)


def auth_for_model(model: str) -> tuple[str, str]:
    if model == EDIT_MODEL:
        api_key = env_first(
            [
                "GPT_IMAGE_2_ALL_API_KEY",
                "GUI_SORA2_KEY",
                "GPT_IMAGE_2_API_KEY",
                "OPENAI_API_KEY",
            ]
        )
        base_url = env_first(
            [
                "GPT_IMAGE_2_ALL_BASE_URL",
                "SORA2_API_BASE_URL",
                "GPT_IMAGE_2_BASE_URL",
                "OPENAI_BASE_URL",
                "BASE_URL",
                "base_url",
            ]
        )
    else:
        api_key = env_first(["GPT_IMAGE_2_API_KEY", "OPENAI_API_KEY"])
        base_url = env_first(
            ["GPT_IMAGE_2_BASE_URL", "OPENAI_BASE_URL", "BASE_URL", "base_url"],
            "https://api.openai.com",
        )

    if not api_key:
        if model == EDIT_MODEL:
            needed = "GPT_IMAGE_2_ALL_API_KEY or GUI_SORA2_KEY"
        else:
            needed = "GPT_IMAGE_2_API_KEY or OPENAI_API_KEY"
        raise RuntimeError(f"Missing API key for {model}; set {needed}.")

    if not base_url:
        raise RuntimeError(
            f"Missing base URL for {model}; set GPT_IMAGE_2_ALL_BASE_URL or GPT_IMAGE_2_BASE_URL."
        )

    base_url = normalize_base_url(base_url)
    return api_key, base_url


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url.lstrip('/')}"
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    return base_url


def request_json(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1200]
        raise RuntimeError(f"HTTP {exc.code} from image API: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Image API request failed: {exc}") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        preview = raw[:1200].decode("utf-8", "replace")
        raise RuntimeError(f"Image API returned non-JSON response: {preview}") from exc


def post_json(
    base_url: str,
    api_key: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return request_json(f"{base_url}{endpoint}", headers, body, timeout)


def content_type_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def read_image_part(value: str) -> tuple[str, bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(value, timeout=120) as response:
            data = response.read()
            content_type = response.headers.get_content_type() or "image/png"
        name = Path(parsed.path).name or f"reference-{uuid.uuid4().hex}.png"
        return name, data, content_type

    path = Path(value).expanduser()
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Reference image not found: {value}")
    return path.name, path.read_bytes(), content_type_for_path(path)


def multipart_body(
    fields: dict[str, str],
    images: list[str],
) -> tuple[bytes, str]:
    boundary = f"----gpt-image-2-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add(value: bytes | str) -> None:
        chunks.append(value.encode("utf-8") if isinstance(value, str) else value)

    for name, value in fields.items():
        add(f"--{boundary}\r\n")
        add(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        add(str(value))
        add("\r\n")

    for image in images:
        filename, data, content_type = read_image_part(image)
        safe_name = filename.replace('"', "")
        add(f"--{boundary}\r\n")
        add(
            'Content-Disposition: form-data; name="image"; '
            f'filename="{safe_name}"\r\n'
        )
        add(f"Content-Type: {content_type}\r\n\r\n")
        add(data)
        add("\r\n")

    add(f"--{boundary}--\r\n")
    return b"".join(chunks), boundary


def post_multipart(
    base_url: str,
    api_key: str,
    endpoint: str,
    fields: dict[str, str],
    images: list[str],
    timeout: float,
) -> dict[str, Any]:
    body, boundary = multipart_body(fields, images)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    return request_json(f"{base_url}{endpoint}", headers, body, timeout)


def download_url(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def extract_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items = data.get("data")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if isinstance(data, dict) and ("b64_json" in data or "url" in data):
        return [data]
    return []


def write_outputs(
    items: list[dict[str, Any]],
    out_dir: Path,
    output_format: str,
    timeout: float,
) -> list[str]:
    paths: list[str] = []
    extension = "jpg" if output_format == "jpeg" else output_format
    for index, item in enumerate(items, start=1):
        target = out_dir / f"image-{index:03d}.{extension}"
        if item.get("b64_json"):
            target.write_bytes(base64.b64decode(str(item["b64_json"])))
        elif item.get("url"):
            target.write_bytes(download_url(str(item["url"]), timeout=timeout))
        else:
            continue
        paths.append(str(target))
    return paths


def main() -> int:
    args = parse_args()
    count = max(1, min(int(args.count or 1), 8))
    prompt = final_prompt(read_prompt(args.prompt), args.negative_prompt, args.size)
    if not prompt.strip():
        print("Prompt is required.", file=sys.stderr)
        return 2

    operation = "edit" if args.image else "generation"
    model = EDIT_MODEL if args.image else TEXT_MODEL
    api_key, base_url = auth_for_model(model)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if operation == "generation":
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": count,
            "size": args.size,
            "quality": args.quality,
            "output_format": args.format,
            "background": args.background,
        }
        data = post_json(
            base_url,
            api_key,
            "/v1/images/generations",
            payload,
            args.timeout,
        )
    else:
        fields = {
            "model": model,
            "prompt": prompt,
            "n": str(count),
            "size": args.size,
            "quality": args.quality,
            "output_format": args.format,
            "background": args.background,
        }
        data = post_multipart(
            base_url,
            api_key,
            "/v1/images/edits",
            fields,
            args.image,
            args.timeout,
        )

    items = extract_items(data)
    paths = write_outputs(items, args.out_dir, args.format, args.timeout)
    if not paths:
        raise RuntimeError(f"No image data found in API response: {json.dumps(data)[:1200]}")

    manifest = {
        "created_at": int(time.time()),
        "operation": operation,
        "model": model,
        "size": args.size,
        "quality": args.quality,
        "count": count,
        "format": args.format,
        "background": args.background,
        "reference_images": args.image,
        "outputs": paths,
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({**manifest, "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"generate_image.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
