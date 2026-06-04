# App Screenshot To HTML

Codex skill for reconstructing mobile app screenshots as high-fidelity HTML/CSS.

## What It Does

Use this skill when you upload or reference an iOS, Android, mini-program, mobile H5, or app-like screenshot and want Codex to recreate the screen as a browser-rendered HTML/CSS page.

The skill guides Codex to:

- inspect the screenshot as a mobile app UI
- break it into status bar, navigation, content, controls, tab bar, and safe-area regions
- implement a real HTML/CSS reconstruction
- render and screenshot the result
- compare the result against the source and iterate

## Install

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R app-screenshot-to-html ~/.codex/skills/
```

Then invoke it in Codex:

```text
Use $app-screenshot-to-html to recreate this mobile app screenshot as HTML/CSS.
```

## Repository Layout

```text
app-screenshot-to-html/
├── README.md
└── app-screenshot-to-html/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/mobile-ui-reconstruction.md
    └── scripts/compare_screenshots.py
```

## Notes

This skill aims for high visual fidelity, but exact 100% reconstruction is not always possible when the original fonts, icons, images, or app assets are unavailable.
