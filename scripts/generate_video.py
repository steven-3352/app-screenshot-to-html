#!/usr/bin/env python3
"""Generate short videos with the configured video API.

The script reads VIDEO_API_KEY, VIDEO_API_BASE_URL, and VIDEO_MODEL from the
environment, ./.env, $CODEX_HOME/.env, or ~/.codex/.env.
"""

from __future__ import annotations

import argparse
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


DOTENV_LOADED = False
DEFAULT_ENDPOINT = "/v1/videos"
DEFAULT_GROK_JSON_ENDPOINT = "/v1/video/create"
DEFAULT_VIDEOS_POLL_ENDPOINT = "/v1/videos/{id}"
DEFAULT_BODY_FORMAT = "openai-videos"
GROK_SPECIAL_MODELS = {"grok-video-3", "grok-video-3-10s", "grok-video-3-15s"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a short video from a prompt and optional first-frame image."
    )
    parser.add_argument("--prompt", help="Prompt text or path to a prompt file.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for outputs.")
    parser.add_argument("--image", help="Optional first-frame/reference image path or URL.")
    parser.add_argument("--task-id", help="Poll and download an existing video task without submitting a new one.")
    parser.add_argument("--model", help="Model name. Defaults to VIDEO_MODEL from env.")
    parser.add_argument("--size", default="9:16", help="Video size/aspect, e.g. 9:16 or 720x1280.")
    parser.add_argument("--duration", default="10", help="Duration in seconds, e.g. 10.")
    parser.add_argument("--quality", default="high", help="Quality hint passed through to the API.")
    parser.add_argument("--format", default="mp4", choices=["mp4", "webm", "mov"])
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="API endpoint path.")
    parser.add_argument(
        "--body-format",
        default=DEFAULT_BODY_FORMAT,
        choices=["openai-videos", "grok-json", "json", "multipart"],
        help="Request body shape. Default matches the OpenAI-style POST /v1/videos.",
    )
    parser.add_argument(
        "--image-field",
        default="input_reference",
        help="Field name for an image URL in multipart/openai-videos mode.",
    )
    parser.add_argument(
        "--file-field",
        default="input_reference",
        help="Field name for a local image file in multipart/openai-videos mode.",
    )
    parser.add_argument("--poll-endpoint", default="", help="Optional status endpoint for async tasks.")
    parser.add_argument("--poll-interval", default=5.0, type=float)
    parser.add_argument("--poll-timeout", default=600.0, type=float)
    parser.add_argument("--timeout", default=300.0, type=float)
    parser.add_argument("--extra", action="append", default=[], help="Extra JSON field as key=value.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write payload and manifest without calling the video API.",
    )
    return parser.parse_args()


def read_prompt(value: str) -> str:
    path = Path(value).expanduser()
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return value.strip()


def env_first(names: list[str], default: str = "") -> str:
    load_dotenvs()
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def load_dotenvs() -> None:
    global DOTENV_LOADED
    if DOTENV_LOADED:
        return
    DOTENV_LOADED = True

    paths = [Path.cwd() / ".env"]
    codex_home_raw = os.environ.get("CODEX_HOME", "").strip()
    if codex_home_raw:
        paths.append(Path(codex_home_raw).expanduser() / ".env")
    paths.append(Path.home() / ".codex" / ".env")

    seen: set[Path] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
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


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        raise RuntimeError("Missing VIDEO_API_BASE_URL.")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url.lstrip('/')}"
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    return base_url


def auth() -> tuple[str, str, str]:
    api_key = env_first(["VIDEO_API_KEY", "GROK_API_KEY", "XAI_API_KEY"])
    base_url = env_first(["VIDEO_API_BASE_URL", "GROK_API_BASE_URL", "XAI_API_BASE_URL"])
    model = env_first(["VIDEO_MODEL"], "grok-video-3-10s")

    if not api_key:
        raise RuntimeError("Missing VIDEO_API_KEY.")
    return api_key, normalize_base_url(base_url), model


def content_type_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def read_binary_part(value: str) -> tuple[str, bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(value, timeout=120) as response:
            data = response.read()
            content_type = response.headers.get_content_type() or "application/octet-stream"
        name = Path(parsed.path).name or f"reference-{uuid.uuid4().hex}.png"
        return name, data, content_type

    path = Path(value).expanduser()
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Reference image not found: {value}")
    return path.name, path.read_bytes(), content_type_for_path(path)


def parse_extra(values: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key.strip():
            raise RuntimeError(f"Invalid --extra value: {value}. Use key=value.")
        result[key.strip()] = parse_jsonish(raw.strip())
    return result


def parse_jsonish(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none"}:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def request_json(url: str, headers: dict[str, str], body: bytes, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1600]
        if exc.code == 429 and "no available platform found" in detail:
            detail += (
                "\nHint: the provider accepted the request shape, but the selected upstream model "
                "has no available platform. Retry later or try --model grok-videos, or "
                "--body-format grok-json --model grok-video-3."
            )
        raise RuntimeError(f"HTTP {exc.code} from video API: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Video API request failed: {exc}") from exc

    return parse_json_response(raw)


def request_get_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1600]
        raise RuntimeError(f"HTTP {exc.code} from video API status endpoint: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Video API status request failed: {exc}") from exc

    return parse_json_response(raw)


def parse_json_response(raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        preview = raw[:1600].decode("utf-8", "replace")
        raise RuntimeError(f"Video API returned non-JSON response: {preview}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Video API returned non-object JSON: {data!r}")
    return data


def post_json(base_url: str, api_key: str, endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return request_json(f"{base_url}{normalize_endpoint(endpoint)}", headers, body, timeout)


def is_url(value: str) -> bool:
    return urllib.parse.urlparse(value).scheme in {"http", "https"}


def multipart_body(
    fields: dict[str, str],
    file_value: str = "",
    file_field: str = "image",
) -> tuple[bytes, str]:
    boundary = f"----video-api-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add(value: bytes | str) -> None:
        chunks.append(value.encode("utf-8") if isinstance(value, str) else value)

    for name, value in fields.items():
        add(f"--{boundary}\r\n")
        add(f'Content-Disposition: form-data; name="{name}"\r\n')
        add("Content-Type: text/plain\r\n\r\n")
        add(str(value))
        add("\r\n")

    if file_value:
        filename, data, content_type = read_binary_part(file_value)
        safe_name = filename.replace('"', "")
        safe_field = file_field.replace('"', "")
        add(f"--{boundary}\r\n")
        add(f'Content-Disposition: form-data; name="{safe_field}"; filename="{safe_name}"\r\n')
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
    file_value: str,
    file_field: str,
    timeout: float,
) -> dict[str, Any]:
    body, boundary = multipart_body(fields, file_value=file_value, file_field=file_field)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    return request_json(f"{base_url}{normalize_endpoint(endpoint)}", headers, body, timeout)


def normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip() or DEFAULT_ENDPOINT
    return endpoint if endpoint.startswith("/") else f"/{endpoint}"


def extract_task_id(data: dict[str, Any]) -> str:
    for key in ["id", "task_id", "job_id", "request_id", "video_id"]:
        value = data.get(key)
        if value:
            return str(value)
    nested = data.get("data")
    if isinstance(nested, dict):
        for key in ["id", "task_id", "job_id", "request_id", "video_id"]:
            value = nested.get(key)
            if value:
                return str(value)
    return ""


def extract_video_url(data: dict[str, Any]) -> str:
    for key in ["url", "video_url", "output_url", "download_url"]:
        value = data.get(key)
        if value:
            return str(value)

    nested = data.get("data")
    if isinstance(nested, dict):
        for key in ["url", "video_url", "output_url", "download_url"]:
            value = nested.get(key)
            if value:
                return str(value)
        result = nested.get("result")
        if isinstance(result, dict):
            for key in ["url", "video_url", "output_url", "download_url"]:
                value = result.get(key)
                if value:
                    return str(value)
        videos = nested.get("videos")
        if isinstance(videos, list) and videos:
            first = videos[0]
            if isinstance(first, dict):
                return str(first.get("url") or first.get("video_url") or first.get("download_url") or "")
            return str(first)

    outputs = data.get("outputs") or data.get("output")
    if isinstance(outputs, list) and outputs:
        first = outputs[0]
        if isinstance(first, dict):
            return str(first.get("url") or first.get("video_url") or "")
        return str(first)

    return ""


def extract_video_content(data: bytes, content_type: str) -> bytes:
    lower = (content_type or "").lower()
    if lower.startswith("video/") or lower in {"application/octet-stream", "binary/octet-stream"}:
        return data
    return b""


def response_status(data: dict[str, Any]) -> str:
    for key in ["status", "state"]:
        value = data.get(key)
        if value:
            return str(value).lower()
    nested = data.get("data")
    if isinstance(nested, dict):
        for key in ["status", "state"]:
            value = nested.get(key)
            if value:
                return str(value).lower()
    return ""


def poll_for_result(
    base_url: str,
    api_key: str,
    poll_endpoint: str,
    task_id: str,
    interval: float,
    timeout: float,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    if not task_id:
        raise RuntimeError("Cannot poll without a task id.")

    headers = {"Authorization": f"Bearer {api_key}", "API-KEY": api_key, "Accept": "application/json"}
    deadline = time.monotonic() + timeout
    endpoint = normalize_endpoint(poll_endpoint).replace("{id}", urllib.parse.quote(task_id, safe=""))

    while time.monotonic() < deadline:
        data = request_get_json(f"{base_url}{endpoint}", headers, timeout=min(60.0, interval + 30.0))
        status = response_status(data)
        if out_dir:
            (out_dir / "video-api-final-response.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if extract_video_url(data):
            return data
        if status in {"succeeded", "success", "completed", "complete", "done"}:
            return data
        if status in {"failed", "error", "cancelled", "canceled", "fail"}:
            raise RuntimeError(f"Video task failed: {json.dumps(data, ensure_ascii=False)[:1600]}")
        time.sleep(max(1.0, interval))

    raise RuntimeError(f"Timed out waiting for video task {task_id}.")


def download_task_content_if_available(
    base_url: str,
    api_key: str,
    task_id: str,
    out_dir: Path,
    output_format: str,
    timeout: float,
) -> str:
    if not task_id:
        return ""
    endpoint = f"/v1/videos/{urllib.parse.quote(task_id, safe='')}/content"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "video/*,application/octet-stream"}
    req = urllib.request.Request(f"{base_url}{endpoint}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get_content_type() or ""
    except (urllib.error.HTTPError, urllib.error.URLError):
        return ""
    content = extract_video_content(raw, content_type)
    if not content:
        return ""
    extension = "mp4" if output_format == "mp4" else output_format
    target = out_dir / f"video-001.{extension}"
    target.write_bytes(content)
    return str(target)


def download_url(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def write_video_if_available(data: dict[str, Any], out_dir: Path, output_format: str, timeout: float) -> str:
    video_url = extract_video_url(data)
    if not video_url:
        return ""
    extension = "mp4" if output_format == "mp4" else output_format
    target = out_dir / f"video-001.{extension}"
    target.write_bytes(download_url(video_url, timeout=timeout))
    return str(target)


def duration_seconds(value: str) -> int | str:
    cleaned = str(value).strip().lower().removesuffix("s").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def is_grok_special_model(model: str) -> bool:
    return model in GROK_SPECIAL_MODELS


def build_payload(args: argparse.Namespace, model: str, prompt: str) -> dict[str, Any]:
    if args.body_format == "openai-videos":
        seconds = duration_seconds(args.duration)
        if (args.model or model) == "grok-video-3-10s":
            try:
                seconds = min(int(seconds), 10)
            except (TypeError, ValueError):
                seconds = 10
        elif (args.model or model) == "grok-video-3-15s":
            try:
                seconds = min(int(seconds), 15)
            except (TypeError, ValueError):
                seconds = 15
        payload: dict[str, Any] = {
            "model": args.model or model,
            "prompt": prompt,
            "seconds": seconds,
            "size": normalize_video_size_for_model(args.size, args.model or model),
        }
        payload.update(parse_extra(args.extra))
        return payload

    if args.body_format == "grok-json":
        payload = {
            "model": args.model or model,
            "prompt": prompt,
            "aspect_ratio": normalize_size(args.size),
            "size": quality_to_grok_size(args.quality),
            "images": [args.image] if args.image and is_url(args.image) else [],
        }
        payload.update(parse_extra(args.extra))
        return payload

    payload: dict[str, Any] = {
        "model": args.model or model,
        "prompt": prompt,
        "size": args.size,
        "duration": args.duration,
        "quality": args.quality,
        "response_format": "url",
    }
    payload.update(parse_extra(args.extra))
    return payload


def normalize_size(value: str) -> str:
    value = str(value).strip()
    aliases = {
        "720x1280": "9:16",
        "1080x1920": "9:16",
        "1280x720": "16:9",
        "1920x1080": "16:9",
    }
    return aliases.get(value, value)


def normalize_video_size_for_model(value: str, model: str) -> str:
    value = str(value).strip()
    if model in GROK_SPECIAL_MODELS and value in {"9:16", "16:9", "720x1280", "1280x720", "2:3", "3:2", "1:1"}:
        return "720P"
    return normalize_size(value)


def quality_to_grok_size(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized in {"720P", "1080P"}:
        return normalized
    if normalized in {"HIGH", "HD"}:
        return "1080P"
    return "720P"


def stringify_fields(payload: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        fields[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return fields


def request_video(args: argparse.Namespace, base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = effective_endpoint(args)

    if args.body_format in {"json", "grok-json"}:
        return post_json(base_url, api_key, endpoint, payload, args.timeout)

    fields = stringify_fields(payload)
    file_value = ""
    if args.image:
        if is_grok_special_model(str(payload.get("model") or "")):
            file_value = args.image
        elif is_url(args.image):
            fields[args.image_field] = args.image
        else:
            file_value = args.image

    return post_multipart(
        base_url,
        api_key,
        endpoint,
        fields,
        file_value,
        args.file_field,
        args.timeout,
    )


def validate_request_args(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    model = str(payload.get("model") or "")
    if is_grok_special_model(model) and not args.image:
        raise RuntimeError(
            f"{model} requires --image. The Grok special-video path sends a reference image as multipart input_reference."
        )
    if args.body_format == "grok-json" and is_grok_special_model(model) and args.image and not is_url(args.image):
        raise RuntimeError(
            "The grok-json /v1/video/create format only supports image URLs in the images array. "
            "Use the default openai-videos multipart format for local reference images."
        )


def effective_endpoint(args: argparse.Namespace) -> str:
    if args.body_format == "grok-json" and args.endpoint == DEFAULT_ENDPOINT:
        return DEFAULT_GROK_JSON_ENDPOINT
    return args.endpoint


def poll_endpoint_for(args: argparse.Namespace) -> str:
    if args.poll_endpoint:
        return args.poll_endpoint
    if args.body_format == "openai-videos":
        return DEFAULT_VIDEOS_POLL_ENDPOINT
    return ""


def main() -> int:
    args = parse_args()
    if not args.prompt and not args.task_id:
        print("Prompt is required unless --task-id is provided.", file=sys.stderr)
        return 2

    api_key, base_url, env_model = auth()
    model = args.model or env_model
    args.out_dir.mkdir(parents=True, exist_ok=True)
    poll_endpoint = poll_endpoint_for(args)

    if args.task_id:
        if not poll_endpoint:
            raise RuntimeError("--poll-endpoint is required when using --task-id with this body format.")
        final_data = poll_for_result(
            base_url,
            api_key,
            poll_endpoint,
            args.task_id,
            args.poll_interval,
            args.poll_timeout,
            args.out_dir,
        )
        response_path = args.out_dir / "video-api-final-response.json"
        response_path.write_text(json.dumps(final_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        video_path = write_video_if_available(final_data, args.out_dir, args.format, args.timeout)
        if not video_path:
            video_path = download_task_content_if_available(
                base_url,
                api_key,
                args.task_id,
                args.out_dir,
                args.format,
                args.timeout,
            )
        manifest = {
            "created_at": int(time.time()),
            "dry_run": False,
            "poll_only": True,
            "base_url": base_url,
            "endpoint": "",
            "poll_endpoint": poll_endpoint,
            "model": model,
            "task_id": args.task_id,
            "response": str(response_path),
            "video": video_path,
            "video_url": extract_video_url(final_data),
        }
        manifest_path = args.out_dir / "video-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({**manifest, "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
        if not video_path and not manifest["video_url"]:
            print("generate_video.py: no video URL found in API response; inspect response JSON.", file=sys.stderr)
        return 0

    prompt = read_prompt(args.prompt or "")
    if not prompt:
        print("Prompt is required.", file=sys.stderr)
        return 2

    payload = build_payload(args, model, prompt)
    validate_request_args(args, payload)
    payload_path = args.out_dir / "video-request-payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.dry_run:
        manifest = {
            "created_at": int(time.time()),
            "dry_run": True,
            "base_url": base_url,
            "endpoint": effective_endpoint(args),
            "poll_endpoint": poll_endpoint,
            "body_format": args.body_format,
            "model": model,
            "image": args.image or "",
            "file_field": args.file_field,
            "payload": str(payload_path),
        }
        manifest_path = args.out_dir / "video-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({**manifest, "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
        return 0

    data = request_video(args, base_url, api_key, payload)

    response_path = args.out_dir / "video-api-response.json"
    response_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    final_data = data
    if poll_endpoint and not extract_video_url(data):
        final_data = poll_for_result(
            base_url,
            api_key,
            poll_endpoint,
            extract_task_id(data),
            args.poll_interval,
            args.poll_timeout,
            args.out_dir,
        )
        (args.out_dir / "video-api-final-response.json").write_text(
            json.dumps(final_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    video_path = write_video_if_available(final_data, args.out_dir, args.format, args.timeout)
    if not video_path:
        video_path = download_task_content_if_available(
            base_url,
            api_key,
            extract_task_id(data),
            args.out_dir,
            args.format,
            args.timeout,
        )
    manifest = {
        "created_at": int(time.time()),
        "dry_run": False,
        "base_url": base_url,
        "endpoint": effective_endpoint(args),
        "poll_endpoint": poll_endpoint,
        "model": model,
        "size": args.size,
        "duration": args.duration,
        "quality": args.quality,
        "image": args.image or "",
        "payload": str(payload_path),
        "response": str(response_path),
        "video": video_path,
        "video_url": extract_video_url(final_data),
        "task_id": extract_task_id(data),
    }
    manifest_path = args.out_dir / "video-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({**manifest, "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
    if not video_path and not manifest["video_url"]:
        print("generate_video.py: no video URL found in API response; inspect response JSON.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"generate_video.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
