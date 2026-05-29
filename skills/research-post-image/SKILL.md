---
name: research-post-image
description: "Generate a blog feature image for a research post from its content, using OpenAI gpt-image-2, and save it as a PNG alongside the markdown file."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, blog, image, openai, feature-image]
    related_skills: [research-post-publish, research-post-writer]
---

# Research Post Image Generator

Generates a 1792x1024 feature image for a compiled research blog post in `/opt/data/profiles/med-research/workspace/blog/`. The image prompt is crafted from the article's title, subtitle, and key themes so the visual matches the content.

> **Dependency**: Uses `OPEN_AI_API_KEY` environment variable (set by the Hermes runtime). Calls `curl` + `python3` — no extra packages needed.

---

## When to Use

- After `research-post-writer` has compiled a post, before publishing
- When asked to "generate a feature image for the post" or "create a blog image"
- As the final step of the pipeline before `research-post-publish`

---

## Prerequisites — Set These Before Starting

| Variable | Example | Purpose |
|---|---|---|
| `REPORT_TYPE` | `MECFS` | Used to construct the date variable name and the blog file path |
| `REPORT_{TYPE}_DATE_TO` | `REPORT_MECFS_DATE_TO=2026-05-25` | The date of the blog post to image; variable name is dynamic: `REPORT_{REPORT_TYPE}_DATE_TO` |

The LLM must construct the date variable name dynamically:

```bash
DATE_VAR="REPORT_${REPORT_TYPE}_DATE_TO"
TARGET_DATE="${!DATE_VAR}"        # indirect expansion in bash
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"
IMAGE_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.png"
```

**If `POST_FILE` does not exist, return "[SKIP]" and do nothing.**
**If `IMAGE_FILE` already exists and is non-empty (> 10 KB), return "[SKIP] Image already exists." and do nothing.**

**Memory not available (cron environments):** If the `memory` tool is unavailable, `REPORT_{REPORT_TYPE}_DATE_TO` cannot be read from persistent storage. Fall back by listing post files on disk:

```bash
ls "workspace/blog/${REPORT_TYPE}-post-"*.md 2>/dev/null
```

Pick the most recent file and extract `TARGET_DATE` from the filename pattern `{REPORT_TYPE}-post-{YYYY-MM-DD}.md`. If no matching files exist, return "[SKIP]" and do nothing.

---

## ⚡ Cron Context

**These rules save ~12+ wasted tool calls per run. Follow them strictly.**

### 1. Don't Hunt for Variables — Use Your Context Directly

Do NOT call `memory()`, `session_search()`, read MEMORY.md, search config files, or grep for environment variables. These all fail or return redacted data in automated environments.

The values you need (`REPORT_TYPE`, `REPORT_{TYPE}_DATE_TO`) are provided in your task context. The API key env var name is `OPEN_AI_API_KEY` — **use it immediately, don't verify it**. Write your Python script in one shot using `os.environ.get('OPEN_AI_API_KEY')`.

### 2. Skip Todo

Do NOT use the `todo` tool — track progress in your own reasoning instead.

### 3. Skip Post-Write Verification (Consolidate It)

Do NOT run separate `ls -la` + `wc` + Python PNG-magic checks. Instead, do the verification **in the same script** that generates the image — print size + validity in the final line. See Step 4 for details.

### 4. Compress Turn Sequences

Plan the entire workflow (locate → read → prompt → generate → verify) and execute it without intermediary "now let me..." messages between steps. One announce + execute per step is enough.

---

## Step-by-Step: Generate a Feature Image

### 1. Locate and read the blog post file

```bash
REPORT_TYPE=MECFS
TARGET_DATE=2026-05-25
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"
IMAGE_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.png"

if [ ! -f "$POST_FILE" ]; then
    echo "[SKIP] No post file found at ${POST_FILE} -- nothing to image."
    exit 0
fi
if [ -f "$IMAGE_FILE" ] && [ "$(stat -c%s "$IMAGE_FILE" 2>/dev/null || wc -c < "$IMAGE_FILE" 2>/dev/null)" -gt 10240 ]; then
    echo "[SKIP] Image already exists at ${IMAGE_FILE}."
    exit 0
fi
```

Read the file contents with `read_file`.

### 2. Craft an image prompt from the article content

Extract these elements from the markdown:

- **Title**: First `# H1` line (before the colon, if any)
- **Subtitle**: The `### H3` line (editorial intro paragraph)
- **First body H2**: First `## H2` section heading
- **Key themes**: Scan the body for recurring scientific concepts, metaphors, and imagery

Construct a DALL-E / gpt-image-2 prompt following this pattern:

```
A stunning, cinematic blog feature image showing [central metaphor/key theme]. 
[Specific visual elements from the article — e.g., glowing calcium channels, 
mitochondrial networks, immune cells, converging pathways].
Dark navy and deep teal background with golden-orange and electric-blue highlights.
Scientific yet artistic, medical journal quality, 3D render style, 
1792x1024 landscape format, no text in the image itself.
```

**Prompt elements to vary by article content:**

| Article Focus | Visual Metaphor Ideas |
|---|---|
| TRPM3/calcium channels | Glowing gatekeeper protein on cell membrane, calcium wave through cytoplasm |
| Mitochondrial energy failure | Dim vs bright mitochondrial networks, power plants flickering |
| Post-viral syndrome overlap (ME/CFS, Long COVID, Fibromyalgia) | Three glowing pathways converging at a crossroads |
| Immune dysregulation | Immune cells with mixed signals, some overactive, some dormant |
| NK cell dysfunction | Natural killer cells with broken sensors drifting in bloodstream |
| Metabolic trap / itaconate shunt | Cellular factory floor, blocked metabolic pipeline |
| Case studies / clinical reports | Human silhouette with immune system mapped as constellation |
| Inflammation / neuroinflammation | Glowing neural pathways surrounded by inflamed glial cells |

### 3. Generate the image via OpenAI gpt-image-2

The only way to get the API key is via the `OPEN_AI_API_KEY` environment variable (**NOT** `OPENAI_API_KEY` — note the underscore).

**Do NOT** attempt any of these (all fail or return redacted output):
- `memory()` calls — fail silently in automated environments
- `read_file` of MEMORY.md or config files — the key is redacted to `sk-pro...T5AA`
- `grep` or `search_files` for API key patterns — no files store it unredacted
- `terminal("printenv")` or `os.environ` checks to "verify" the key — you can't see its value either way

**Do this instead:** Write the Python script in one shot using `os.environ.get('OPEN_AI_API_KEY')`. The subprocess inherits the environment from the parent Hermes process — the key will be available at runtime even though you can't see its value in tool output.

Write a standalone Python script (e.g., `workspace/blog/gen_feature_image.py`) that:

1. Reads the API key from `os.environ.get('OPEN_AI_API_KEY')` — note the underscore between OPEN and AI. Do NOT try `OPENAI_API_KEY`.
2. Sends the POST to OpenAI via `subprocess.run(["curl", ...])` with `capture_output=True` (do NOT use inline `curl | python3` — the security policy blocks pipe-to-interpreter patterns)
3. Decodes the `b64_json` field and writes the PNG

Example script skeleton:

```python
import json, base64, subprocess, sys, os

api_key = os.environ.get('OPEN_AI_API_KEY', '')

prompt = "..."  # from step 2

payload = json.dumps({
    "model": "gpt-image-2",
    "prompt": prompt,
    "size": "1792x1024"
})

result = subprocess.run(
    ["curl", "-s", "-X", "POST", "https://api.openai.com/v1/images/generations",
     "-H", f"Authorization: Bearer {api_key}",
     "-H", "Content-Type: application/json",
     "-d", payload],
    capture_output=True, text=True, timeout=120
)

data = json.loads(result.stdout)
b64 = data["data"][0]["b64_json"]
img = base64.b64decode(b64)
with open("$IMAGE_FILE", "wb") as f:
    f.write(img)
print(f"SUCCESS: Saved {len(img)} bytes to $IMAGE_FILE")
```

Run it with `python3 workspace/blog/gen_feature_image.py`.

**Clean up** the temporary script after a successful run with `rm -f workspace/blog/gen_feature_image.py`.

**Important**: The API key will be redacted/truncated in both `read_file` output and terminal output. Never try to copy-paste it — always have the Python script read it directly from the file.

### 4. Verify (Consolidated — Do Inline in Generate Script)

Do NOT run separate `ls`, `stat`, `wc`, and Python checks as separate tool calls. Instead, **append the verification to the Python generation script** so it prints size + PNG validity as the final output line:

```python
# Add to end of gen_feature_image.py, after saving the PNG:
import os
size = os.path.getsize(image_path)
with open(image_path, "rb") as f:
    magic = f.read(8)
is_valid = magic == b"\\x89PNG\\r\\n\\x1a\\n"
print(f"VERIFIED: {size} bytes, valid_png={is_valid}")
```

This way a single `terminal()` + `python3` call both generates **and** verifies the image in one shot.
- If the script fails, the error is visible in the output.
- If it succeeds, the output contains `VERIFIED: N bytes, valid_png=True`.

- Report the saved file path and size to the user
- (Optional) If the active model supports vision, use `vision_analyze` to visually verify the image quality. If it doesn't (e.g., deepseek-v4-flash), skip — the API-generated image is reliable.

---

## Pitfalls

- **`outputQuality` and `style` parameters are NOT accepted** by the API — omit them. Only `model`, `prompt`, and `size` are supported.
- **`gpt-image-2` returns `b64_json`, not a URL** — always decode via Python's `base64.b64decode()`. The `url` field is NOT present in the response.
- **API key only available via env var**: The `OPEN_AI_API_KEY` env var is the **only** way to get the key. It is redacted to `sk-pro...T5AA` in all tool output (`read_file`, `terminal`, `grep`, `search_files`). Never copy-paste it; always write a Python script that reads `os.environ.get('OPEN_AI_API_KEY')`.
- **`curl | python3` pipe blocked by security policy**: The inline `curl ... | python3 -c "..."` pattern triggers a "pipe to interpreter" security block. Write the Python script to a file first, then run separately.
- **`xxd` and `file(1)` may not be available**: Use Python's `open().read(8)` + PNG magic byte comparison (`b"\\x89PNG\\r\\n\\x1a\\n"`) to verify PNG validity.
- **Model may lack native vision**: If the active model doesn't support image inputs (e.g., deepseek-v4-flash), skip `vision_analyze` verification.
- **Memory unavailable in cron environments**: Falls back to scanning `workspace/blog/` for matching files.
- **Image already exists**: Skip regeneration to avoid unnecessary API cost.
- **Large images**: The base64 string can be ~3-4 MB for 1792x1024. The Python decode handles this fine.
- **Post file doesn't exist**: Return "[SKIP]" silently — this is expected when there's nothing to image yet.

---

## Verification Checklist

- [ ] Dynamic date variable `REPORT_{REPORT_TYPE}_DATE_TO` was constructed and resolved correctly (or fallback from file listing).
- [ ] Post file path checked. If missing, skipped with "[SKIP]".
- [ ] Image file path checked. If exists and non-empty, skipped.
- [ ] **Cron efficiency check**: Did NOT call `memory()`, `session_search()`, read MEMORY.md, or hunt for env vars.
- [ ] **Cron efficiency check**: Did NOT use `todo` tool.
- [ ] **Cron efficiency check**: Verification was consolidated inside the generate script (one shot), not split across separate tool calls.
- [ ] Prompt crafted from article's title, subtitle, and key themes.
- [ ] Image generated via gpt-image-2, decoded, saved as PNG.
- [ ] Saved file verified (> 10 KB, valid PNG) — output from single script run confirms this.
