---
name: research-post-publish
description: "Create or update a draft post on Substack from a compiled research blog post, using REPORT_TYPE to locate the correct post file and populate relevant tags."
version: 3.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, substack, publishing, blogging, draft]
    related_skills: [research-post-writer, research-processor, research-roundup]
---

# Research Post Publisher

Publishes a draft post to Substack from a compiled markdown blog file in `/opt/data/profiles/med-research/workspace/blog/`. The post filename is determined by `REPORT_TYPE` and the date from `REPORT_{REPORT_TYPE}_DATE_TO`.

---

## Prerequisites -- Set These Before Starting

| Variable | Example | Purpose |
|---|---|---|
| `REPORT_TYPE` | `MECFS` | Used to construct the date variable name and the blog file path |
| `REPORT_{TYPE}_DATE_TO` | `REPORT_MECFS_DATE_TO=2026-05-25` | The date of the blog post to publish; variable name is dynamic: `REPORT_{REPORT_TYPE}_DATE_TO` |

The LLM must construct the date variable name dynamically:
```bash
# For REPORT_TYPE=MECFS:
DATE_VAR="REPORT_MECFS_DATE_TO"
TARGET_DATE="${!DATE_VAR}"  # indirect expansion in bash
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"
```

**If `POST_FILE` does not exist, report "[SKIP]" and do nothing.**

---

## Efficiency: Automated Context

In automated/cron contexts, follow these rules to minimize tool calls:

- **Don't hunt for variables**: REPORT_TYPE, REPORT_{TYPE}_DATE_TO are provided in your task context -- use them directly. No memory(), session_search(), or file scans to find them.
- **Skip todo**: Do not use the todo tool -- track progress in your own reasoning.
- **Skip post-write verification**: Do not verify written files or saved drafts with extra browser checks -- trust tool return values and the Saved indicator.
- **Batch browser actions**: Plan browser interactions in sequences rather than one click per turn. Avoid intermediary "let me now X" messages -- execute the plan directly.

---

## When to Use

- After `research-post-writer` has generated a post file
- When asked to "publish the blog post to Substack" or "draft on Substack"
- As the final step of the research pipeline

---

## Authentication

The Substack information is stored in the environment variables.

```
SUBSTACK_EMAIL
SUBSTACK_HANDLE
SUBSTACK_PASSWORD
```

### Password Form DOM Structure

The password form DOM structure (hidden inputs, CAPTCHA error detection, API diagnostic, cookie checks) is documented in the reference file: `references/captcha-auth-diagnostics.md`. Load it only if you encounter a CAPTCHA or silent reversion during password submit.

Substack sometimes forces email magic-link auth even when password is provided. Two strategies:

**Strategy A -- Password (try first, once):**
1. Navigate to substack.com, click "Sign in"
2. Click "Sign in with password"
3. Enter `$SUBSTACK_EMAIL` and password `$SUBSTACK_PASSWORD`
4. Click "Continue"
5. If CAPTCHA blocked or "Please sign in via email" appears, fall back to Strategy B. **Do not retry password.**

**Strategy B -- Magic link (try once):**
1. Navigate to substack.com, click "Sign in"
2. Enter `$SUBSTACK_EMAIL`, click "Continue"
3. Wait ~10-15 seconds, fetch latest messages from AgentMail inbox (subject contains "verification code" or "magic link")
4. Extract the tracking link from the email's HTML body (look for `href=` containing `email.mg-tx1.substack.com/c/`)
5. Navigate to that link -- it redirects to substack.com with an authenticated session
6. **IMPORTANT**: After magic link auth, stay on substack.com and use nav buttons -- do NOT navigate directly to subdomain URLs (mecfsresearch.substack.com) as the session is fragile. Click "Dashboard" in the nav, then use the sidebar.

**AgentMail JSON parsing tip**: If fetching the email body, use `json_parse()` from `hermes_tools` (not stdlib `json.loads`) -- the HTML body has raw control chars:

```python
from hermes_tools import terminal, json_parse
data = json_parse(terminal("curl ...")["output"])
html = data.get("html", "")
```

**Verification code fallback**: The magic link email also contains a numeric code. If navigating to the tracking link fails, check if Substack's "Check your email" page accepts the code directly into a text input.

**If the magic link email does not arrive** within 30 seconds (common with AgentMail):
   - Do NOT keep polling the inbox -- it's unlikely to arrive
   - Fall back to the **Early Pre-Check** (public homepage) to verify post status (no auth required)
   - ⚠️ **Do not retry password after failed magic-link** -- triggers 24-hour account lockout
   - Wait at least several hours before retrying any auth method

---

## Step-by-Step: Creating a Draft Post

### 1. Locate and read the blog post file

Construct the file path and verify it exists:

```bash
REPORT_TYPE=MECFS
TARGET_DATE=2026-05-25
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"

if [ ! -f "$POST_FILE" ]; then
    echo "[SKIP] No post file found at ${POST_FILE} -- nothing to publish."
    exit 0
fi
```

If the file exists, read its contents.

### 2. Extract title, subtitle, and body from markdown structure

The markdown file follows this structure (see attached `references/markdown-post-structure.md`):

```
# TITLE: Subtitle (optional)             <- H1 = post title, text before colon is title
                                          (blank line)
### Subtitle paragraph (editorial intro) <- H3 = subtitle paragraph (NOT Substack subtitle)
                                          (blank line)
> **Date:** YYYY-MM-DD                    <- metadata blockquote
> **Covered Range:** YYYY-MM-DD to YYYY-MM-DD
> **Editor's Note:** ...
                                          (blank line)
---                                       <- HR -- BODY STARTS HERE
                                          (blank line)
## First section heading                  <- H2 = first body section
...
```

- **Title**: The first H1 line (`# TITLE: Subtitle`), text before `:`. Example:
  `# The Immune Crossroads: How a Calcium Channel Defect May Connect Post-Viral Syndromes`
  -> Title: `"The Immune Crossroads"`
  If the H1 has no colon, use the entire H1 text as the title.
- **Subtitle**: The text AFTER the colon in the H1 title line. Example above -> Subtitle: `"How a Calcium Channel Defect May Connect Post-Viral Syndromes"`. If the title has no colon, leave subtitle empty.
- **Body**: Everything from the first `---` (HR) onward. This excludes the title, subtitle paragraph (H3), and editorial metadata. **Never include the title H1 in the body -- they go in separate Substack fields.**

### 3. Convert markdown to HTML for the body

Load the converter script:
`skill_view(name='research-post-publish', file_path='scripts/convert_md_to_html.py')`

Extract the body markdown (everything from the first `---` onward) and pipe it through the script via `execute_code` or `stdin`:

```python
from hermes_tools import terminal
result = terminal("python3 <script_path> < <body_tempfile>")
html = result["output"]
```

The script handles: headings (`<h2>`-`<h4>`), bold/italic, links, images, blockquotes, lists, `<hr>`, and HTML entity passthrough. Use the returned HTML as the `innerHTML` for the contenteditable div (Step 6).

### 4. Navigate to the post editor

After authentication, use the dashboard navigation path (avoids subdomain session issues):

1. On substack.com, click **"Dashboard"** in the top nav bar
2. In the left sidebar, click **"Create"** then select **"Article"** from the dropdown
3. This opens the post editor directly on substack.com (not a subdomain)

Alternatively, navigate directly to:
```
https://mecfsresearch.substack.com/publish/post/new
```

If the subdomain URL redirects to sign-in (session not preserved across subdomains), use the dashboard path instead. Re-authenticate first if needed.

### 5. Fill in the fields

The Substack editor has these fields (use browser_snapshot to find refs):

| Field | What to put |
|-------|-------------|
| Post title (textbox "title") | The `<h2>` text from the HTML, anything before `:` |
| Subtitle (textbox "Add a subtitle...") | Text after `:` in title, or leave empty. **NOT the first paragraph.** |
| Body (contenteditable div) | All HTML body content after the subtitle |
| File Settings > Title | Same as post title |
| File Settings > Description | Short SEO summary (1-2 sentences) |

### 6. Inject the body HTML

Use `browser_console` to set the innerHTML of the contenteditable div:

```javascript
const editor = document.querySelector('[contenteditable]');
editor.innerHTML = `...body HTML...`;
editor.dispatchEvent(new Event('input', { bubbles: true }));
```

The body HTML should include all formatting: `<h2>`, `<h3>`, `<p>`, `<ul>/<li>`, `<strong>`, `<em>`, `<a href="...">`, `<hr>`.

### 7. Continue and populate tags

After the body is injected, populate post tags relevant to the article:

1. Look for a **"Continue"** button near the top right of the editor. Click it to open the **Publish** dialog. (Despite its name, this dialog is a combined settings/tags screen — it does not auto-publish.)
2. Inside the Publish dialog, add relevant tags via the **"Select or create tags"** combobox:
   - Type a tag name, then click **"Create 'TagName'"** from the dropdown to add it as a new tag
   - Repeat for each tag. Tags appear as removable pill buttons above the combobox.
   - **Condition tags**: e.g., `ME/CFS`, `Long COVID`, `Fibromyalgia`
   - **Biological theme tags**: e.g., `Immunology`, `Mitochondria`, `Neuroinflammation`
   - **Content type tags**: `Research Summary`, `Weekly Roundup`
3. Tags should be derived from the actual content of the post -- scan the body for key topics.
4. **To keep as a draft:** Click **"Cancel"** (bottom-left of the dialog). The draft auto-saved when the "Saved" indicator appeared in the editor earlier — closing the dialog does not discard it.
5. **To publish immediately:** Click **"Send to everyone now"** instead.
6. Verify the draft appears in the dashboard's "Drafts" section by navigating back to the dashboard.

Common tags for ME/CFS posts: `ME/CFS`, `Myalgic Encephalomyelitis`, `Chronic Fatigue Syndrome`, `Research`, `Biomedical Research`, `Patient Advocacy`, `Treatment Updates`.

### 8. Verify and save

- Take a screenshot/snapshot to verify the content looks correct
- The draft auto-saves (look for "Saved" indicator)
- Use "Preview" to check rendering

---

## Subtitle Rules (CRITICAL)

The subtitle field on Substack is NOT for the first paragraph of the post. It must be either:

1. **Text after `:` in the title** -- e.g., title "The Big Picture: The Cellular Origin of Collapse" -> subtitle "The Cellular Origin of Collapse"
2. **Empty** -- if the title has no colon, leave the subtitle blank

**NEVER** put the first body paragraph in the subtitle field. The first paragraph belongs in the body. The subtitle is a short tagline, not introductory content.

---

## Pitfalls

- **Publish dialog ≠ publication**: The "Continue" button opens a dialog labeled "Publish" that confusingly looks like a final confirmation. It's actually the tags/settings screen. Click "Cancel" to keep as draft (auto-saved). Only click "Send to everyone now" to publish.
- **Subtitle field misuse**: Subtitle = text after colon in H1 title, or empty if no colon. NEVER put the first body paragraph in the subtitle field.
- **Magic link session fragility**: After magic-link auth, navigate from substack.com nav -> Dashboard, not by typing subdomain URLs directly.
- **Rate limiting (429)**: Substack aggressively rate-limits POST requests. If you see 429s after body HTML injection, wait 1-2 minutes for the cool-down and verify the "Saved" indicator appears.
- **Login rate-limit (24-hour disable)**: After 2-3 total auth attempts across both strategies, Substack disables the account. Detect via:
  ```javascript
  document.querySelector('.error.other-error')?.textContent
  // Returns: "Too many login attempts have been made on this account. Login is disabled for up to 24 hours."
  ```
  When detected, stop all auth attempts, report the lockout with post metadata (title, subtitle, file path) for manual publishing after cooldown.
- **Magic link email may silently fail at AgentMail**: If 10-15 seconds pass with no new verification email, do not keep polling -- use the Early Pre-Check (public homepage) instead.
- **Large body HTML in browser_console**: Template literals handle ~15KB. For larger posts, write HTML to a temp file and use `fetch('/path').then(r=>r.text())` in the console -- though this requires an HTTP server accessible to the browser session.

---

## Verification Checklist

- [ ] Dynamic date variable `REPORT_{REPORT_TYPE}_DATE_TO` constructed and resolved correctly (no hunting via memory/session_search).
- [ ] Blog file checked. Missing = "[SKIP]".
- [ ] Early Pre-Check: publication homepage confirms post NOT already published.
- [ ] Auth rate-limit checked after each attempt. If lockout detected, stopped and reported post metadata.
- [ ] Title and subtitle extracted from H1 colon split.
- [ ] Body starts at first `---`, excludes metadata blockquotes.
- [ ] Markdown converted to HTML via linked script (`scripts/convert_md_to_html.py`).
- [ ] Authenticated and fields filled (title, subtitle, body HTML).
- [ ] Tags populated via "Select or create tags" combobox.
- [ ] Draft kept as draft (Cancel on Publish dialog, not "Send to everyone now").
- [ ] Efficiency rules followed: no todo, no post-write verification, no hunting for variables.
