# App Screenshot To HTML

这是一个 Codex Skill，用来把移动端 App 页面截图高保真还原成 HTML/CSS 页面，也可以在还原过程中生成或编辑需要的图片素材。

它适合这类需求：

- 上传一张 iOS App 页面截图，让 Codex 复刻成 HTML
- 上传一张 Android App 页面截图，让 Codex 还原页面结构和样式
- 上传小程序、移动端 H5、App 内嵌 WebView 截图，生成可运行的网页
- 把登录页、个人中心、订单页、列表页、详情页、表单页、聊天页、仪表盘等 App 页面做成前端原型
- 根据截图拆解 UI：状态栏、导航栏、内容区、按钮、卡片、列表、底部 Tab、Safe Area 等
- 为页面生成或编辑头像、商品图、背景图、插画、海报、图标等位图素材
- 为成人女性短视频生成合规创意 brief、GPT Image 2 首帧提示词和视频模型提示词，风格可以吸引人、性感但不低俗

这个 Skill 的目标不是“描述图片”，而是让 Codex 像一个 App UI 复刻工程师一样工作：先理解截图结构，再写真实 HTML/CSS，然后通过浏览器截图校准效果。

## 能做到什么

使用这个 Skill 后，Codex 会按下面的方式处理 App 截图：

1. 识别截图尺寸、设备比例和页面类型
2. 拆解页面区域，比如状态栏、顶部导航、内容区、浮动按钮、底部 Tab、底部安全区
3. 提取可见文字、字号、字重、颜色、间距、圆角、阴影、分割线和图标位置
4. 生成真实的 HTML/CSS，而不是简单把原图当背景
5. 在浏览器中按截图尺寸渲染页面
6. 截图对比原图和生成页面
7. 根据差异继续调整布局、颜色、字体和细节

## 不适合什么

这个 Skill 专门面向 App 页面截图，不建议用于：

- 桌面网站截图
- 与 App 页面或前端素材无关的纯海报、Banner、营销长图排版
- 与 App 页面或前端素材无关的普通照片整理、摄影后期
- 纯图表图片
- 手绘草图
- 希望 100% 自动恢复原始设计稿、字体文件、图标源文件的场景

如果原图中包含头像、商品图、地图、品牌 Logo、复杂插画等素材，Codex 可以尽量裁剪、近似复刻，或按你的提示词生成替代素材，但在没有原始素材的情况下不能保证 100% 像素级一致。

## 安装方式

先克隆这个仓库：

```bash
git clone git@github.com:steven-3352/app-screenshot-to-html.git
cd app-screenshot-to-html
```

然后把 Skill 文件夹复制到 Codex 的 skills 目录：

```bash
mkdir -p ~/.codex/skills/app-screenshot-to-html
cp -R SKILL.md agents references scripts ~/.codex/skills/app-screenshot-to-html/
```

复制完成后，目录应该类似这样：

```text
~/.codex/skills/
└── app-screenshot-to-html/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/beauty-video.md
    ├── references/image-generation.md
    ├── references/mobile-ui-reconstruction.md
    ├── scripts/beauty_video_brief.py
    ├── scripts/generate_video.py
    ├── scripts/html_element_editor.mjs
    ├── scripts/generate_image.py
    └── scripts/compare_screenshots.py
```

重启或重新打开 Codex 会话后，就可以通过 `$app-screenshot-to-html` 调用这个 Skill。

## 基础使用

在 Codex 中上传一张 App 页面截图，然后输入：

```text
Use $app-screenshot-to-html to recreate this mobile app screenshot as high-fidelity HTML/CSS.
```

也可以用中文：

```text
使用 $app-screenshot-to-html，把这张 App 截图高保真还原成一个 HTML/CSS 页面。
```

如果你希望输出为单个 HTML 文件：

```text
使用 $app-screenshot-to-html，把这张 App 截图还原成 standalone HTML 文件，CSS 写在同一个文件里。
```

如果你希望输出到指定目录：

```text
使用 $app-screenshot-to-html，把这张 App 截图还原成 HTML/CSS，输出到 ./reconstructed-screen。
```

如果你希望使用前端框架：

```text
使用 $app-screenshot-to-html，把这张 App 截图还原成 React 组件，样式用 CSS Module。
```

```text
使用 $app-screenshot-to-html，把这张 App 截图还原成 Vue 单文件组件。
```

## 按编号修改 HTML 元素

Skill 里包含一个给 Codex 和产品经理协作使用的小工具：

```text
scripts/html_element_editor.mjs
```

它适合在页面已经生成之后继续调整内容和样式。Codex 输入本地 HTML 文件，工具会生成一个带编号的预览页和元素映射；产品经理只需要看编号，然后告诉 Codex“把 12 改成什么”。

生成编号预览：

```bash
node scripts/html_element_editor.mjs scan ./index.html --name homepage
```

输出文件默认在 `.codex-html-editor/`：

```text
.codex-html-editor/homepage.numbered.html
.codex-html-editor/homepage.map.json
```

把 `.numbered.html` 打开给产品经理看。页面上的可编辑元素会显示蓝色描边和编号，点击编号或元素可以锁定选中项。

查看映射表：

```bash
node scripts/html_element_editor.mjs list .codex-html-editor/homepage.map.json
```

按编号修改元素内部文案：

```bash
node scripts/html_element_editor.mjs text .codex-html-editor/homepage.map.json 12 "立即开始"
```

按编号追加或覆盖 inline 样式：

```bash
node scripts/html_element_editor.mjs style .codex-html-editor/homepage.map.json 12 "background: #111827; color: white; border-radius: 6px"
```

按编号修改属性，比如图片说明、链接地址、输入框占位文案：

```bash
node scripts/html_element_editor.mjs attr .codex-html-editor/homepage.map.json 8 alt "产品控制台截图"
```

每次写回源 HTML 前，工具会自动生成 `.bak.timestamp` 备份，并刷新编号预览和映射。

给产品经理的沟通方式可以很简单：

```text
把 12 的按钮文案改成“立即开始”
把 18 的背景改成黑色，文字改成白色
把 7 的图片说明改成“产品控制台截图”
```

注意：这个工具直接修改本地静态 HTML。React、Vue、Tailwind 等项目也可以用它生成编号预览来沟通，但最终最好让 Codex 根据编号回到组件源码里修改。

## 图片生成配置和用法

做图脚本会自动读取 `~/.codex/.env`。本地配置文件不要提交到仓库，格式如下：

```bash
GPT_IMAGE_2_BASE_URL="https://your-image-api-base-url/v1"
GPT_IMAGE_2_API_KEY="xxxxx"
```

使用 `$app-screenshot-to-html` 时不需要指定模型。Skill 会自动判断：

- 没有参考图的文生图：使用文生图模型
- 有参考图、编辑、重绘、融合、替换素材：使用图生图/编辑模型

如果你没有写尺寸、质量、数量、格式、背景、负面提示词或输出目录，Skill 会先提醒是否要设置；不设置就使用默认值：`1024x1024`、`high`、`1` 张、`png`、`auto` 背景。

文生图示例：

```text
使用 $app-screenshot-to-html 生成一张 App 首页顶部背景图。风格干净、科技感、适合移动端，尺寸 1024x1536，质量高，输出 png。
```

图生图/编辑示例：

```text
使用 $app-screenshot-to-html 根据这张参考图生成一张头像素材，用在页面顶部。尺寸 1024x1024，质量高，输出 png。
```

截图复刻时补图示例：

```text
使用 $app-screenshot-to-html 还原这张 App 截图。截图里的商品主图重新生成一张更清晰的图，保持原本构图和手机端比例。
```

也可以直接调用脚本生成素材：

```bash
python3 scripts/generate_image.py --prompt prompt.txt --out-dir generated-assets --size 1024x1024 --quality high --format png
python3 scripts/generate_image.py --prompt prompt.txt --image ref.png --out-dir generated-assets --size 1024x1024 --quality high --format png
```

## 成人女性短视频 Brief 和 Prompt

这个 Skill 也可以为“吸引人、性感但不低俗”的成人女性短视频生成创意 brief、GPT Image 2 首帧提示词、视频模型提示词和负面词。它适合先用 GPT Image 2 生成关键帧，再把关键帧和视频提示词交给 Grok 或其他视频模型，也可以调用已配置的视频 API 生成视频。

它会和用户确认几类信息：

- 参考图片或参考视频：只参考发型、服装、光线、构图、动作节奏等，不克隆真人身份
- 人物外貌：明确是成年虚构角色，比如年龄段、发型、妆容、气质
- 服装：泳装、精致内衣、吊带短裙、露肩上衣等；可少穿但要边界清晰、若隐若现，性感不等于低俗
- 场景：酒店房间、卧室、化妆台、咖啡馆、夜景窗边等
- 性格和镜头感：自信、温柔、俏皮、清冷、暧昧但克制
- 动作节奏：拨头发、轻微转身、靠近镜头、微笑定格等
- 输出参数：9:16、8-12 秒、目标视频模型、是否生成首帧、是否直接调用视频 API

如果用户输入里有低俗或高风险表达，Skill 会把它改写成安全视觉意图，比如把“擦边/过审”改成“平台友好、合规表达”，把“挑逗/勾引”改成“有吸引力的镜头互动”。它不会帮助规避平台审核、伪装 AI 成真人、生成未成年感、裸露或露骨性内容。

视频 API 默认从本地环境读取下面几个变量。key 和 base URL 只从环境变量读取，换供应商只改配置、不用改代码。不要把真实 key 提交到仓库：

```bash
VIDEO_API_KEY="sk-..."
VIDEO_API_BASE_URL="https://your-video-api-base-url"
VIDEO_MODEL="grok-video-3-10s"
```

Grok 视频文档当前对应默认接口 `POST /v1/videos`，请求体为 `multipart/form-data`，字段包括 `model`、`prompt`、`seconds`、`size` 和 `input_reference` 参考图文件。`grok-video-3-10s` 会把请求时长归一到 10 秒以内、尺寸归一到 `720P`。脚本会自动轮询 `GET /v1/videos/{id}`。如果上游返回 `no available platform found`，说明请求格式已通过但当前模型通道不可用；可稍后重试，或显式尝试 `--model grok-videos`，也可以用备用 JSON 格式 `--body-format grok-json --model grok-video-3`。

### 有参考图 vs 没有参考图

这个 Skill 出视频分两种情况，调用前先判断：

- **有参考图**（用户上传的照片，或指定的某一帧）：直接把它当首帧，跳过首帧生成，调用 `generate_video.py --image 参考图路径`。
- **没有参考图**：先用 `generate_image.py` 配合首帧提示词生成一张首帧图，确认效果后，再把这张图作为 `--image` 传给 `generate_video.py`。

当前默认模型 `grok-video-3-10s` 必须带参考图（`input_reference`），所以“没有参考图”的情况一定要先生成首帧，再出视频。

生成问题清单：

```bash
python3 scripts/beauty_video_brief.py questions
```

生成 brief 和 prompt 文件：

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

输出文件包括：

```text
video-brief/
├── beauty-video-brief.md
├── beauty-video-brief.json
├── video-prompt-baseline.txt
├── gpt-image2-keyframe-prompt.txt
├── video-model-prompt.txt
└── negative-prompt.txt
```

如果没有参考图，先用首帧提示词生成一张首帧：

```bash
python3 scripts/generate_image.py \
  --prompt video-brief/gpt-image2-keyframe-prompt.txt \
  --out-dir video-brief \
  --size 1024x1536 --quality high --format png
```

然后调用视频模型生成视频。当前默认 `grok-video-3-10s` 需要参考图，把参考图或上一步生成的首帧用 `--image` 传入：

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --image video-brief/first-frame.png \
  --out-dir video-brief/video-output \
  --size 9:16 \
  --duration 10
```

备用 Grok JSON 格式：

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --out-dir video-brief/video-output \
  --body-format grok-json \
  --model grok-video-3 \
  --size 9:16 \
  --quality 720P
```

只查询已有任务、不重新提交：

```bash
python3 scripts/generate_video.py \
  --task-id "grok:..." \
  --out-dir video-brief/video-output
```

如果想先检查请求体、不消耗视频额度：

```bash
python3 scripts/generate_video.py \
  --prompt video-brief/video-model-prompt.txt \
  --out-dir video-brief/video-output \
  --dry-run
```

视频做完后，如果要整理成可直接发小红书的内容并让用户直接观看效果，可以再生成发布包：

```bash
python3 scripts/beauty_video_xhs_package.py \
  --brief-json video-brief/beauty-video-brief.json \
  --manifest video-brief/video-output/video-manifest.json \
  --video video-brief/video-output/video-001.mp4 \
  --cover video-brief/xhs-video-cover.jpg \
  --out-dir video-brief/xhs-publish
```

会输出：

- `xhs-publish-content.md`
- `xhs-caption.txt`
- `watch-effect.html`
- `xhs-package.json`

推荐直接这样说：

```text
使用 $app-screenshot-to-html，帮我做一个成人女性短视频生成方案。风格要吸引人，性感但不低俗。请先问我参考图、外貌、服装、场景和动作，再生成 GPT Image 2 首帧提示词和 Grok 视频提示词。
```

## 推荐提示词

### 高保真 HTML 复刻

```text
使用 $app-screenshot-to-html 复刻这张 App 页面截图。请保持原截图的宽高比例、状态栏、导航栏、底部安全区、字体大小、颜色、圆角、阴影和间距。输出一个可直接打开的 HTML 文件，并尽量通过浏览器截图校准。
```

### 只做移动端页面，不做响应式扩展

```text
使用 $app-screenshot-to-html 还原这张移动端截图。请优先匹配截图本身，不需要做桌面端响应式适配。
```

### 需要可维护结构

```text
使用 $app-screenshot-to-html 还原这张 App 截图。请生成结构清晰的 HTML/CSS，使用 CSS variables 管理颜色、圆角和间距，方便后续继续修改。
```

### 对未知素材做说明

```text
使用 $app-screenshot-to-html 还原这张截图。如果有无法准确恢复的字体、图标、头像、图片或 Logo，请用近似方案处理，并在最后列出限制。
```

## 输出结果通常包含什么

Codex 使用这个 Skill 后，通常会输出：

- 一个 HTML 文件，或按你的要求输出 React/Vue 等前端文件
- 还原页面使用的 CSS
- 需要时生成的图片素材
- 可能的截图验证说明
- 采用的 viewport 尺寸
- 已知限制，比如未知字体、缺失图标、图片素材只能近似等

示例最终说明可能是：

```text
已生成 reconstructed/index.html。
使用 viewport: 390x844。
已按截图还原状态栏、导航栏、内容卡片和底部 Tab。
限制：原始头像和品牌图标没有源文件，使用了近似占位。
```

## 截图对比脚本

Skill 中包含一个可选脚本：

```text
scripts/compare_screenshots.py
```

它可以比较原始截图和浏览器渲染后的截图，输出平均差异、RMS 差异和可见差异比例。

使用方式：

```bash
python3 scripts/compare_screenshots.py source.png rendered.png --diff diff.png
```

如果提示缺少 Pillow，可以安装：

```bash
python3 -m pip install pillow
```

输出示例：

```text
size_match: true
size: 390x844
mean_channel_difference: 8.42
rms_channel_difference: 18.31
visible_difference_percent: 12.54
threshold: 16.00
diff_image: diff.png
```

注意：像素差异只是辅助指标。最终效果还需要人工看一遍，尤其是文字位置、字号、图标、按钮和整体观感。

## 工作流建议

想要更接近原图，可以这样要求 Codex：

1. 先按截图尺寸创建固定移动端画布
2. 粗略搭出状态栏、导航栏、内容区和底部区域
3. 再逐个调整文本、卡片、图标和按钮
4. 用 Playwright 或浏览器截图生成渲染图
5. 用对比脚本检查差异
6. 重复调整直到视觉接近

你可以直接这样说：

```text
使用 $app-screenshot-to-html 还原这张截图。请先实现第一版 HTML，然后用浏览器截图检查，再根据截图差异至少迭代一轮。
```

## 仓库结构

```text
app-screenshot-to-html/
├── README.md
├── SKILL.md
├── agents/openai.yaml
├── references/beauty-video.md
├── references/image-generation.md
├── references/mobile-ui-reconstruction.md
├── scripts/beauty_video_brief.py
├── scripts/generate_video.py
├── scripts/html_element_editor.mjs
├── scripts/generate_image.py
└── scripts/compare_screenshots.py
```

说明：

- `SKILL.md`：Skill 的核心触发描述和执行流程
- `agents/openai.yaml`：Codex UI 中展示 Skill 的名称、简介和默认提示词
- `references/beauty-video.md`：成人女性短视频 brief、合规改写和提示词结构参考
- `references/image-generation.md`：做图模型选择、参数提醒和 API 调用参考
- `references/mobile-ui-reconstruction.md`：移动端 App 页面复刻参考规范
- `scripts/beauty_video_brief.py`：生成短视频创意 brief、GPT Image 2 首帧提示词、视频提示词和负面词
- `scripts/generate_video.py`：读取 `VIDEO_API_KEY` / `VIDEO_API_BASE_URL` / `VIDEO_MODEL` 并调用视频模型生成短视频
- `scripts/html_element_editor.mjs`：生成 HTML 编号预览，并按编号修改文案、样式和属性
- `scripts/generate_image.py`：文生图/图生图辅助脚本
- `scripts/compare_screenshots.py`：原图和渲染截图的差异对比脚本

## 开发和验证

修改 Skill 后，可以运行 Codex 官方校验脚本：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

如果你改了截图对比脚本，可以做语法检查：

```bash
python3 -m py_compile scripts/compare_screenshots.py scripts/generate_image.py scripts/beauty_video_brief.py scripts/generate_video.py
```

如果你改了 HTML 编号编辑脚本，可以做 Node 语法检查：

```bash
node --check scripts/html_element_editor.mjs
```

## 重要限制

这个 Skill 追求高保真还原，但不承诺绝对 100% 还原。

常见限制包括：

- 原始 App 使用了未知字体
- 截图中的图标没有 SVG 或字体图标源文件
- 头像、商品图、Logo、地图等素材无法从截图外恢复
- 截图经过压缩，颜色和边缘有损失
- App 原生控件和浏览器 CSS 渲染存在差异
- 截图中部分文字太小或模糊，无法准确识别

更准确的使用方式是：把它当作“App 截图到 HTML 的高保真复刻工作流”，而不是万能的设计稿反编译工具。
