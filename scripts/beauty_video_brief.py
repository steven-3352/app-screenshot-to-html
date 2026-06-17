#!/usr/bin/env python3
"""Build a compliant beauty short-video creative brief and generation prompts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


FIXED_CREATIVE_BASELINE = (
    "Primary goal: a genuinely beautiful adult woman. "
    "Sexy but never vulgar: minimal tasteful outfits such as swimwear, lingerie, bodysuit, "
    "off-shoulder tops, or short skirts are allowed; show subtle skin and silhouette with "
    "an implied allure rather than explicit exposure. "
    "Allure should feel elegant, confident, and platform-friendly."
)

DEFAULTS = {
    "title": "sexy-beauty-short",
    "duration": "10s",
    "aspect": "9:16",
    "style": "Douyin-style sensual smartphone short video, sexy but not vulgar",
    "persona": "fictional adult woman, 25 years old, strikingly beautiful face and figure",
    "appearance": "long dark hair, refined makeup, luminous skin, alluring eyes, photogenic beauty",
    "outfit": "stylish minimal black one-piece swimsuit, tasteful coverage, subtle skin reveal without exposure",
    "scene": "poolside at golden hour with soft backlight and clean background",
    "mood": "confident, sensual, elegant, playful charm",
    "action": "slow hair flip, gentle hip sway, soft smile, subtle shoulder turn, loop-friendly ending",
    "camera": "fixed smartphone camera, medium close-up framing that highlights beauty and silhouette",
}

QUESTION_SET = [
    "有没有参考图片或参考视频？如果有，说明只参考哪些部分：脸型/发型/服装/光线/场景/动作。",
    "人物外貌怎么设定？请明确是成年虚构角色，且首先要好看，例如年龄段、发型、妆容、气质。",
    "服装要什么方向？例如泳装、精致内衣、吊带短裙、露肩上衣；可少穿但要边界清晰、若隐若现，性感不等于低俗。",
    "场景在哪里？例如泳池边、酒店房间、卧室、化妆台、夜景窗边。",
    "人物性格和镜头感是什么？例如自信、温柔、俏皮、清冷、性感但有品味。",
    "动作节奏是什么？例如拨头发、轻微转身、靠近镜头、微笑定格；自然有张力，避免露骨动作。",
    "输出参数是什么？例如 9:16、8-12 秒、Grok/其他视频模型、是否先用 GPT Image 2 生成首帧。",
]

REWRITE_RULES = [
    (r"少女感|幼态感|童颜感", "清新但成熟的成人气质"),
    (r"(?i)\bteen\b|未成年|少女|萝莉|高中生|学生妹|幼态|童颜", "成年女性、成熟气质"),
    (r"(?i)\bnude\b|裸|全裸|露点|走光", "不暴露、边界清晰的服装"),
    (r"透明|透视|真空", "有质感、边界清晰且不透明的时装"),
    (r"擦边|过审|绕过审核|规避审核|躲审核", "平台友好、合规表达"),
    (r"撩人|勾引|挑逗", "有吸引力的镜头互动"),
    (r"火辣|欲|低俗|艳俗", "性感但有品味、克制高级"),
    (r"事业线|胸部特写|露点|走光", "适度曲线与若隐若现，但不特写敏感部位"),
    (r"下体|私密部位|性行为", "自然体态和整体造型"),
    (r"脱衣|掀衣|舔|抚摸|性暗示", "自然手部动作和轻微律动"),
    (r"像真人|看不出AI|伪装真人", "自然质感，并按平台要求标注 AI 生成"),
]

BLOCK_PATTERNS = [
    r"未成年|萝莉|幼女|小学生|初中生|高中生",
    r"强迫|迷奸|偷拍|无同意|醉酒",
    r"露点|性行为|自慰|口交|性交",
]

POST_REWRITE_CLEANUPS = [
    (r"成熟气质感", "成熟气质"),
    (r"有点有吸引力的镜头互动", "有吸引力的镜头互动"),
    (r"有吸引力的镜头互动眼神", "有吸引力的眼神互动"),
    (r"性感但不低俗，有吸引力的镜头互动", "性感但不低俗，镜头互动有吸引力"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a tasteful adult beauty short-video brief and prompts."
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("questions", help="Print the recommended user questions.")

    build = subparsers.add_parser("build", help="Write a brief and generation prompts.")
    build.add_argument("--out-dir", type=Path, required=True, help="Output directory.")
    build.add_argument("--title", default=DEFAULTS["title"])
    build.add_argument("--reference", action="append", default=[], help="Reference image/video path.")
    build.add_argument("--persona", default=DEFAULTS["persona"])
    build.add_argument("--appearance", default=DEFAULTS["appearance"])
    build.add_argument("--outfit", default=DEFAULTS["outfit"])
    build.add_argument("--scene", default=DEFAULTS["scene"])
    build.add_argument("--mood", default=DEFAULTS["mood"])
    build.add_argument("--action", default=DEFAULTS["action"])
    build.add_argument("--camera", default=DEFAULTS["camera"])
    build.add_argument("--style", default=DEFAULTS["style"])
    build.add_argument("--duration", default=DEFAULTS["duration"])
    build.add_argument("--aspect", default=DEFAULTS["aspect"])
    build.add_argument("--model", default="video model")
    build.add_argument("--notes", default="", help="Extra user requirements.")
    build.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        help="Optional JSON input. CLI values override omitted fields only.",
    )

    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_rewrite(value: str) -> tuple[str, list[str]]:
    original = normalize_text(value)
    rewritten = original
    changes: list[str] = []

    for pattern, replacement in REWRITE_RULES:
        next_value = re.sub(pattern, replacement, rewritten)
        if next_value != rewritten:
            changes.append(f"{pattern} -> {replacement}")
            rewritten = next_value

    for pattern, replacement in POST_REWRITE_CLEANUPS:
        rewritten = re.sub(pattern, replacement, rewritten)

    rewritten = re.sub(r"\s+", " ", rewritten).strip(" ,，")
    return rewritten, changes


def safety_flags(text: str) -> list[str]:
    flags = []
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            flags.append(pattern)
    return flags


def load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("JSON input must be an object.")
    return data


def value_for(args: argparse.Namespace, data: dict[str, Any], key: str) -> Any:
    value = getattr(args, key, None)
    default = DEFAULTS.get(key)
    if value != default and value not in (None, [], ""):
        return value
    return data.get(key, value)


def build_brief(args: argparse.Namespace) -> dict[str, Any]:
    data = load_json(args.json_path)
    fields = {
        "title": value_for(args, data, "title"),
        "reference": value_for(args, data, "reference") or [],
        "persona": value_for(args, data, "persona"),
        "appearance": value_for(args, data, "appearance"),
        "outfit": value_for(args, data, "outfit"),
        "scene": value_for(args, data, "scene"),
        "mood": value_for(args, data, "mood"),
        "action": value_for(args, data, "action"),
        "camera": value_for(args, data, "camera"),
        "style": value_for(args, data, "style"),
        "duration": value_for(args, data, "duration"),
        "aspect": value_for(args, data, "aspect"),
        "model": value_for(args, data, "model"),
        "notes": value_for(args, data, "notes") or "",
    }

    if isinstance(fields["reference"], str):
        fields["reference"] = [fields["reference"]]

    rewrites: dict[str, list[str]] = {}
    for key in ["persona", "appearance", "outfit", "scene", "mood", "action", "camera", "style", "notes"]:
        rewritten, changes = safe_rewrite(str(fields[key]))
        fields[key] = rewritten
        if changes:
            rewrites[key] = changes

    all_text = " ".join(str(value) for value in fields.values())
    flags = safety_flags(all_text)
    status = "needs_human_review" if flags else "ready"

    keyframe_prompt = make_keyframe_prompt(fields)
    video_prompt = make_video_prompt(fields)
    negative_prompt = make_negative_prompt()
    storyboard = make_storyboard(fields)

    return {
        "created_at": int(time.time()),
        "status": status,
        "safety_flags": flags,
        "rewrites": rewrites,
        "brief": fields,
        "keyframe_prompt": keyframe_prompt,
        "video_prompt": video_prompt,
        "negative_prompt": negative_prompt,
        "storyboard": storyboard,
        "creative_baseline": FIXED_CREATIVE_BASELINE,
        "compliance_notes": [
            "Primary subject must read as a genuinely beautiful adult woman.",
            "Swimwear, lingerie, and other minimal outfits are allowed when coverage stays clear and non-explicit.",
            "Sexy means elegant allure and subtle reveal, not vulgar posing or explicit content.",
            "Use only fictional adult characters or references the user has rights to use.",
            "Do not preserve the identity of a private person from a reference image unless the user confirms consent and rights.",
            "Keep the result tasteful: no nudity, no explicit sexual act, no underage styling, no coercion.",
            "Do not claim the output is real footage. Follow platform AI-content disclosure rules.",
        ],
    }


def make_keyframe_prompt(fields: dict[str, Any]) -> str:
    reference_note = ""
    if fields["reference"]:
        reference_note = (
            "Use the reference only for approved visual cues such as composition, lighting, "
            "hair, outfit, and mood; create a new fictional adult identity. "
        )

    return "\n".join(
        [
            f"Vertical {fields['aspect']} smartphone-style keyframe for a sensual short video.",
            FIXED_CREATIVE_BASELINE,
            reference_note
            + f"Subject: {fields['persona']}; {fields['appearance']}.",
            f"Outfit: {fields['outfit']}.",
            f"Scene: {fields['scene']}.",
            f"Mood and personality: {fields['mood']}.",
            f"Camera: {fields['camera']}.",
            "Realistic phone-camera lighting, natural skin texture, subtle beauty filter, "
            "sexy but not vulgar, elegant allure with implied rather than explicit reveal.",
        ]
    ).strip()


def make_video_prompt(fields: dict[str, Any]) -> str:
    reference_note = ""
    if fields["reference"]:
        reference_note = (
            "When using references, preserve only the requested style/composition cues and avoid cloning a real identity. "
        )

    style = str(fields["style"]).strip()
    style_phrase = style if re.search(r"\bvideo\b|视频", style, re.IGNORECASE) else f"{style} video"

    return "\n".join(
        [
            f"Create a {fields['duration']} vertical {fields['aspect']} {style_phrase}.",
            FIXED_CREATIVE_BASELINE,
            reference_note
            + f"The subject is a {fields['persona']} with {fields['appearance']}.",
            f"She wears {fields['outfit']} in {fields['scene']}.",
            f"Personality: {fields['mood']}.",
            f"Action: {fields['action']}.",
            f"Camera and motion: {fields['camera']}; stable framing, subtle natural motion, realistic cloth and hair movement.",
            "Make her genuinely beautiful first, then sensual and confident. "
            "Sexy but not vulgar: minimal outfits such as swimwear or lingerie are fine when coverage stays clear. "
            "Platform-friendly, no nudity, no explicit sexual content, no underage styling, no celebrity likeness, no real-person impersonation.",
        ]
    )


def make_negative_prompt() -> str:
    return (
        "underage, teen, childlike, school uniform, nudity, explicit sexual content, "
        "transparent clothing, wardrobe malfunction, coercion, intoxication,偷拍, "
        "celebrity likeness, real person impersonation, extra fingers, distorted hands, "
        "warped face, uncanny eyes, plastic skin, text, watermark, logo"
    )


def make_storyboard(fields: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "time": "0-3s",
            "shot": "Start with a medium close-up. She looks into the camera, adjusts hair, and settles into the rhythm.",
        },
        {
            "time": "3-7s",
            "shot": f"Main movement: {fields['action']}. Keep gestures small, elegant, and natural.",
        },
        {
            "time": "7-10s",
            "shot": "End with a confident soft smile and a clean loop-friendly pause.",
        },
    ]


def write_outputs(out_dir: Path, result: dict[str, Any]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "brief_json": out_dir / "beauty-video-brief.json",
        "brief_md": out_dir / "beauty-video-brief.md",
        "baseline": out_dir / "video-prompt-baseline.txt",
        "keyframe": out_dir / "gpt-image2-keyframe-prompt.txt",
        "video": out_dir / "video-model-prompt.txt",
        "negative": out_dir / "negative-prompt.txt",
    }

    paths["brief_json"].write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["brief_md"].write_text(render_markdown(result), encoding="utf-8")
    paths["baseline"].write_text(result["creative_baseline"] + "\n", encoding="utf-8")
    paths["keyframe"].write_text(result["keyframe_prompt"] + "\n", encoding="utf-8")
    paths["video"].write_text(result["video_prompt"] + "\n", encoding="utf-8")
    paths["negative"].write_text(result["negative_prompt"] + "\n", encoding="utf-8")
    return list(paths.values())


def render_markdown(result: dict[str, Any]) -> str:
    brief = result["brief"]
    lines = [
        "# Beauty Video Brief",
        "",
        f"- Status: `{result['status']}`",
        f"- Title: {brief['title']}",
        f"- Duration: {brief['duration']}",
        f"- Aspect: {brief['aspect']}",
        f"- Model: {brief['model']}",
        f"- References: {', '.join(brief['reference']) if brief['reference'] else 'none'}",
        "",
        "## Fixed Creative Baseline",
        "",
        "```text",
        result["creative_baseline"],
        "```",
        "",
        "## Normalized Brief",
        "",
        f"- Persona: {brief['persona']}",
        f"- Appearance: {brief['appearance']}",
        f"- Outfit: {brief['outfit']}",
        f"- Scene: {brief['scene']}",
        f"- Mood: {brief['mood']}",
        f"- Action: {brief['action']}",
        f"- Camera: {brief['camera']}",
        f"- Notes: {brief['notes'] or 'none'}",
        "",
        "## GPT Image 2 Keyframe Prompt",
        "",
        "```text",
        result["keyframe_prompt"],
        "```",
        "",
        "## Video Model Prompt",
        "",
        "```text",
        result["video_prompt"],
        "```",
        "",
        "## Negative Prompt",
        "",
        "```text",
        result["negative_prompt"],
        "```",
        "",
        "## Storyboard",
        "",
    ]
    for shot in result["storyboard"]:
        lines.append(f"- {shot['time']}: {shot['shot']}")

    lines.extend(["", "## Compliance Notes", ""])
    for note in result["compliance_notes"]:
        lines.append(f"- {note}")

    if result["rewrites"]:
        lines.extend(["", "## Safety Rewrites", ""])
        for key, changes in result["rewrites"].items():
            lines.append(f"- {key}: {len(changes)} rewrite rule(s) applied")

    if result["safety_flags"]:
        lines.extend(["", "## Needs Review", ""])
        for flag in result["safety_flags"]:
            lines.append(f"- Matched high-risk pattern: `{flag}`")

    return "\n".join(lines) + "\n"


def print_questions() -> None:
    for index, question in enumerate(QUESTION_SET, start=1):
        print(f"{index}. {question}")


def main() -> int:
    args = parse_args()
    if args.command == "questions":
        print_questions()
        return 0
    if args.command == "build":
        result = build_brief(args)
        paths = write_outputs(args.out_dir, result)
        print(json.dumps({"status": result["status"], "outputs": [str(path) for path in paths]}, ensure_ascii=False, indent=2))
        return 0

    print("Choose a command: questions or build", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
