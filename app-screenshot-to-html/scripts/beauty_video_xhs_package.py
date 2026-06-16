#!/usr/bin/env python3
"""Build a Xiaohongshu-ready publishing package for a generated beauty video."""

from __future__ import annotations

import argparse
import html
import json
import os
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Xiaohongshu copy and a local watch page from a beauty-video brief and manifest."
    )
    parser.add_argument("--brief-json", type=Path, required=True, help="Path to beauty-video-brief.json.")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to video-manifest.json.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--video", type=Path, help="Optional MP4 path. Defaults to manifest video path.")
    parser.add_argument("--cover", type=Path, help="Optional cover image path.")
    parser.add_argument("--title", default="", help="Override the primary Xiaohongshu title.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected object JSON: {path}")
    return data


def relpath(target: Path, base: Path) -> str:
    try:
        return os.path.relpath(target.resolve(), base.resolve())
    except OSError:
        return str(target)


def as_list_text(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def brief_value(brief: dict[str, Any], key: str, default: str = "") -> str:
    value = brief.get(key, default)
    return str(value or default).strip()


def make_content(brief_json: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    brief = brief_json.get("brief")
    if not isinstance(brief, dict):
        brief = {}

    title = "用 GPT Image 2 + Grok 跑通一条 10 秒竖屏 AI 短片"
    subtitle = "从参考图、提示词到成片下载，这次把流程整理成了可复用 Skill"
    body_lines = [
        "这次做的是一条 9:16 的 AI 竖屏短片，目标不是做夸张视觉，而是验证一条稳定、合规、可复用的视频生成流程。",
        "",
        "制作流程：",
        "1. 先定创意边界：虚构成人角色、自然镜头感、吸引人但不低俗，不做真人身份克隆。",
        "2. 准备参考图：只取发型、光线、构图和动作节奏这些视觉线索。",
        "3. 生成 brief：把人物外貌、服装、场景、动作和镜头语言整理成结构化字段。",
        "4. 拆成两类提示词：一份给 GPT Image 2 做首帧，一份给视频模型做图生视频。",
        "5. 调 Grok 视频模型：`grok-video-3-10s` 走 `/v1/videos`，参考图用 `input_reference` multipart 上传。",
        "6. 轮询任务：用 `/v1/videos/{id}` 查状态，完成后下载成本地 MP4。",
        "",
        "这次踩到的关键点：",
        "1. `grok-video-3-10s` 不能按普通文生视频理解，最好带参考图。",
        "2. 请求尺寸不是直接传 9:16，上游实际用 `720P` 更稳。",
        "3. 只传图片 URL 不够稳，本地图片按文件字段上传更接近可跑通的协议。",
        "",
        "成片参数：",
        f"- 模型：{manifest.get('model') or brief_value(brief, 'model', 'grok-video-3-10s')}",
        f"- 画幅：{brief_value(brief, 'aspect', str(manifest.get('size') or '9:16'))}",
        f"- 时长：{brief_value(brief, 'duration', str(manifest.get('duration') or '10s'))}",
        f"- 风格：{brief_value(brief, 'style', 'tasteful smartphone short video')}",
        "",
        "最终效果视频已经放在最后，可以直接看生成结果。",
        "",
        "说明：视频为 AI 生成示例，人物为虚构成人角色。发布时建议按平台规则标注 AI 生成。",
    ]
    tags = [
        "#AI视频",
        "#AIGC",
        "#GPTImage",
        "#Grok",
        "#图生视频",
        "#短视频制作",
        "#提示词",
        "#AI工具",
    ]
    cover_lines = [
        "参考图到成片",
        "10 秒 AI 竖屏视频",
        "GPT Image 2 + Grok",
    ]
    checklist = [
        "上传 `video-001.mp4` 作为主视频。",
        "用 `xhs-video-cover.jpg` 或视频第 2 秒画面做封面。",
        "正文保留 AI 生成说明，避免写成真人实拍。",
        "标题优先选技术流程向，降低擦边感。",
        "评论区可引导用户回复「视频流程」获取提示词和脚本。",
    ]
    comment_seed = "想要完整 prompt 和脚本的话，可以评论「视频流程」，我整理一版可复用模板。"

    return {
        "title": title,
        "subtitle": subtitle,
        "body": "\n".join(body_lines),
        "tags": tags,
        "cover_lines": cover_lines,
        "checklist": checklist,
        "comment_seed": comment_seed,
    }


def render_markdown(content: dict[str, Any], video: Path, cover: Path | None, watch_page: Path) -> str:
    tags = " ".join(content["tags"])
    lines = [
        "# Xiaohongshu Publish Package",
        "",
        "## Title",
        "",
        content["title"],
        "",
        "## Cover Text",
        "",
        as_list_text(content["cover_lines"]),
        "",
        "## Body",
        "",
        content["body"],
        "",
        tags,
        "",
        "## Comment Seed",
        "",
        content["comment_seed"],
        "",
        "## Publish Checklist",
        "",
        as_list_text(content["checklist"]),
        "",
        "## Assets",
        "",
        f"- Video: `{video}`",
        f"- Cover: `{cover}`" if cover else "- Cover: not provided",
        f"- Watch page: `{watch_page}`",
        "",
    ]
    return "\n".join(lines)


def render_caption(content: dict[str, Any]) -> str:
    return "\n".join([content["title"], "", content["body"], "", " ".join(content["tags"])]) + "\n"


def render_html(
    content: dict[str, Any],
    out_dir: Path,
    video: Path,
    cover: Path | None,
    brief_json: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    video_src = html.escape(relpath(video, out_dir))
    cover_attr = ""
    if cover:
        cover_attr = f' poster="{html.escape(relpath(cover, out_dir))}"'
    brief = brief_json.get("brief") if isinstance(brief_json.get("brief"), dict) else {}
    status = html.escape(str(brief_json.get("status") or "ready"))
    model = html.escape(str(manifest.get("model") or brief.get("model") or "grok-video-3-10s"))
    duration = html.escape(str(brief.get("duration") or manifest.get("duration") or "10s"))
    aspect = html.escape(str(brief.get("aspect") or manifest.get("size") or "9:16"))
    title = html.escape(content["title"])
    subtitle = html.escape(content["subtitle"])
    body = html.escape(content["body"])
    tags = html.escape(" ".join(content["tags"]))
    checklist = "".join(f"<li>{html.escape(item)}</li>" for item in content["checklist"])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f4ef;
      --ink: #151515;
      --muted: #6f6a64;
      --line: #ded7ce;
      --accent: #c5372f;
      --panel: #fffdf9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }}
    main {{
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: 28px 18px 40px;
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
      gap: 28px;
      align-items: start;
    }}
    .phone {{
      width: min(100%, 390px);
      margin: 0 auto;
      background: #101010;
      border: 1px solid #292929;
      border-radius: 8px;
      padding: 10px;
      box-shadow: 0 18px 45px rgba(20, 16, 10, 0.22);
    }}
    video {{
      width: 100%;
      aspect-ratio: 9 / 16;
      display: block;
      border-radius: 6px;
      background: #000;
    }}
    .meta {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }}
    .pill {{
      border: 1px solid #353535;
      color: #f3f3f3;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      line-height: 1.2;
    }}
    .content {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.22;
      font-weight: 780;
    }}
    .subtitle {{
      margin: 10px 0 22px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
    }}
    h2 {{
      margin: 22px 0 10px;
      font-size: 16px;
      line-height: 1.3;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      padding: 14px;
      border-radius: 8px;
      background: #f2ede5;
      color: #27211b;
      font: 14px/1.7 -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
      color: #332e29;
      line-height: 1.8;
    }}
    .tags {{
      color: var(--accent);
      font-weight: 650;
      line-height: 1.8;
    }}
    .note {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
    }}
    @media (max-width: 820px) {{
      main {{
        grid-template-columns: 1fr;
        padding: 18px 14px 30px;
      }}
      h1 {{ font-size: 23px; }}
      .content {{ padding: 18px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="phone" aria-label="效果视频">
      <video controls playsinline preload="metadata"{cover_attr}>
        <source src="{video_src}" type="video/mp4">
      </video>
      <div class="meta">
        <span class="pill">{model}</span>
        <span class="pill">{aspect}</span>
        <span class="pill">{duration}</span>
        <span class="pill">status: {status}</span>
      </div>
    </section>
    <section class="content">
      <h1>{title}</h1>
      <p class="subtitle">{subtitle}</p>
      <h2>小红书正文</h2>
      <pre>{body}</pre>
      <h2>话题标签</h2>
      <p class="tags">{tags}</p>
      <h2>发布前检查</h2>
      <ul>{checklist}</ul>
      <p class="note">本页是本地预览页，左侧视频可直接播放。发布到平台时请按平台规则标注 AI 生成。</p>
    </section>
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    brief_json = load_json(args.brief_json)
    manifest = load_json(args.manifest)

    video = args.video or Path(str(manifest.get("video") or ""))
    if not video:
        raise RuntimeError("Missing video path. Pass --video or provide manifest.video.")
    video = video.expanduser()
    if not video.is_absolute():
        video = (args.manifest.parent / video).resolve() if not video.exists() else video.resolve()
    if not video.exists():
        raise RuntimeError(f"Video not found: {video}")

    cover = args.cover.expanduser().resolve() if args.cover else None
    if cover and not cover.exists():
        raise RuntimeError(f"Cover not found: {cover}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    content = make_content(brief_json, manifest)
    if args.title.strip():
        content["title"] = args.title.strip()

    watch_page = args.out_dir / "watch-effect.html"
    publish_md = args.out_dir / "xhs-publish-content.md"
    caption_txt = args.out_dir / "xhs-caption.txt"
    package_json = args.out_dir / "xhs-package.json"

    watch_page.write_text(
        render_html(content, args.out_dir, video, cover, brief_json, manifest),
        encoding="utf-8",
    )
    publish_md.write_text(render_markdown(content, video, cover, watch_page), encoding="utf-8")
    caption_txt.write_text(render_caption(content), encoding="utf-8")
    package_json.write_text(
        json.dumps(
            {
                "created_at": int(time.time()),
                "title": content["title"],
                "video": str(video),
                "cover": str(cover or ""),
                "watch_page": str(watch_page),
                "publish_markdown": str(publish_md),
                "caption": str(caption_txt),
                "tags": content["tags"],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "watch_page": str(watch_page),
                "publish_markdown": str(publish_md),
                "caption": str(caption_txt),
                "package": str(package_json),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
