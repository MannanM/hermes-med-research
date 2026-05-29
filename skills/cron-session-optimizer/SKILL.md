---
name: cron-session-optimizer
description: "Analyze a cron job's past session from state.db for inefficiencies (wasted tool calls, redundant reads, unnecessary todo/verification steps), then patch the skill to fix them."
version: 2.2.0
author: Hermes Agent
license: MIT
---

# Cron Session Optimizer

Analyze a cron job's most recent (or any specified) session from the Hermes state database, identify tool-call waste patterns, and patch the associated skill so future runs are more efficient.

## When to Use

- A cron job is using more messages and tool calls than expected for its workload
- After setting up a new cron job, to optimize its first few runs
- Periodically, to keep cron skills lean as workloads grow

## How It Works

1. Query `state.db` for the cron job's sessions by matching the job ID prefix in the session ID
2. Fetch the full message sequence for the most recent session
3. Load the skill used by that cron job
4. Analyze the message flow for known waste patterns
5. Patch the skill with concrete fixes

---

## 🔒 Golden Rule: Skills Must Be Infrastructure-Agnostic

This is the single most important principle of this optimizer. **The skill being patched must never know about cron configuration files, job IDs, deployment paths, or any other infrastructure detail.**

### Why It Matters

- Skills are reusable capabilities — the same `research-post-writer` skill is shared across MECFS, MCAS, and any future report type
- Cron job wiring (config files, job IDs, schedules) changes independently of skill logic
- A skill that embeds infrastructure details becomes fragile, non-portable, and needs re-patching every time the deployment changes

### Do's and Don'ts

| ❌ Don't (infra leak) | ✅ Do (infra-agnostic) |
|---|---|
| `Read REPORT.ini` from the workspace | `REPORT_TYPE`, `REPORT_DATE_FROM`, `REPORT_DATE_TO` are in your task context |
| `grep /opt/data/cron/jobs.json` | (never reference cron config at all) |
| `The cron job prompt says X` | `Your task instruction says X` |
| `Use job_id medical-draft-blog` | No — the skill shouldn't know job IDs |

**Exception:** `/opt/data/profiles/med-research/workspace/` is an acceptable absolute path — it prevents the agent from accidentally writing to `/opt/hermes/` when CWD isn't the workspace. Use it for directory references in file-reading/writing instructions.

### How to Check Your Patches

Before finalizing a patch, audit every sentence you're adding to the skill for infrastructure leaks:
- Does it mention a cron job, schedule, or job ID? ❌ Remove.
- Does it mention a config file path (REPORT.ini, cron/jobs.json)? ❌ Remove.
- Does it mention an arbitrary absolute path like `/opt/data/my-custom-thing/` that isn't the workspace? ❌ Remove.
- Does it say "the cron prompt provides X"? ❌ Say "your task context or prompt provides X" instead.
- Does it say "memory/session_search fail in cron"? ❌ Say "in this automated context" or just state the rule without explaining the mechanism.

**Allowed:** `/opt/data/profiles/med-research/workspace/` — this is the designated workspace root and prevents the agent from writing to the wrong CWD.

## Known Waste Patterns

These are the patterns detected during analysis, mapped to the fix that should be applied:

| # | Waste Pattern | Symptom | Fix |
|---|---------------|---------|-----|
| 1 | **Memory/session_search calls in cron** | First 2-3 messages are `memory()` or `session_search()` calls that return errors or empty results. The skill may reference `.last_run` files, MEMORY.md, config files, or tell the agent to "look up" variables, which also wastes calls. **A single distraction phrase like "may also appear in MEMORY.md" can trigger a cascade of wasted reads** — audit the skill for such dangling file-path mentions and remove or strongly guard them. | Add a cron tip: tell the agent to skip memory, session_search, and `.last_run` file reads. All variables are provided in the task context — use them directly, don't hunt. |
| 2 | **Sequential read_file for every article** | One `read_file()` per metadata file + per full text file, each in its own turn | Use a linked script (`scripts/` dir) read via `skill_view()` and run via `execute_code` — all articles read in 1 call. |
| 3 | **Reading all treatment profiles** | 5-10+ `read_file()` calls to check if a PMID is already referenced | Use `grep -l "PMID"` or `search_files(pattern="PMID", file_glob="*.md", output_mode="files_only")` instead. |
| 4 | **Todo list overhead** | 4+ `todo()` calls (create, update, update, final) in a non-interactive session | Tell the agent to skip `todo` — track progress in its own reasoning. |
| 5 | **Post-write verification** | Extra `ls` or `terminal` call after writing files to confirm they exist. **Variant: sprawled artifact verification** — for API-generated artifacts (images, audio), doing `ls -la` + `wc -c` + format check as 3 separate tool calls instead of one. | **Default fix:** Skip verification — `write_file` return already confirms success. **Artifact variant:** Consolidate verification into the generation script itself — append a `print(f"VERIFIED: {size} bytes, valid=True")` line to the same script that creates the artifact, so one `terminal()` call both produces and verifies. |
| 6 | **Reprocessing already-done work** | Reading and re-summarizing articles/treatments that already have outputs | Check for existing output files first (e.g., `ls */*-summary.md`), skip what's already done. |
| 7 | **Chatty intermediary messages** | "Let me now do X" messages between every action | Compress the plan — execute reads, writes, checks in larger batches. |
| 8 | **Inline scripts bloating SKILL.md** | Skill has 20+ lines of Python/bash inline, consuming context on every load | Move to `scripts/` linked files; reference via `skill_view(file_path=...)` |
| 9 | **Mid-run skill patching** | Agent calls `skill_manage(action='patch')` during a cron run to "fix" the skill based on what it just learned. 2+ wasted tool calls that also risk corrupting the skill midrun. | Add a rule: **Do NOT patch skills during the run.** If the skill has an issue, report it at the end and stop. The optimizer handles skill maintenance as a separate session. |

---

## Procedure

> **Profile-based cron setup reference:** For instructions on creating cron jobs under a named profile (including `no_agent` script job requirements, `.hermes/scripts/` setup, and migrating jobs from the default scheduler), load `skill_view(name='cron-session-optimizer', file_path='references/profile-cron-setup.md')`.
> 
> **Profile distribution publishing reference:** For instructions on preparing and pushing a profile to a public GitHub repo (secrets audit, tar-based file staging, distribution.yaml format, credential management), load `skill_view(name='cron-session-optimizer', file_path='references/profile-distribution-publish.md')`.

### Step 1: Identify the Target Cron Job

Use the cron job name or ID from the user's request. If none specified, check recent cron sessions:

```python
import sqlite3, datetime

db = "/opt/data/state.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

# Find recent cron sessions with session counts
cur.execute("""
    SELECT id, started_at, message_count, tool_call_count 
    FROM sessions WHERE source = 'cron'
    ORDER BY started_at DESC LIMIT 10
""")
for r in cur.fetchall():
    ts = datetime.datetime.fromtimestamp(r[1])
    print(f"{ts} | id={r[0][:50]}... | msgs={r[2]} | tools={r[3]}")
conn.close()
```

Look for sessions with high message/tool counts relative to their workload (e.g., 30+ msgs for 3 articles indicates waste).

### Step 2: Get the Full Session Transcript

Find the session ID for the cron job. The session ID format is `cron_{job_id}_{timestamp}`.

```python
import sqlite3
conn = sqlite3.connect("/opt/data/state.db")
cur = conn.cursor()

session_id = "cron_<job-id>_<timestamp>"
cur.execute("SELECT id, role, content, tool_name, timestamp FROM messages WHERE session_id=? ORDER BY timestamp ASC", (session_id,))
messages = cur.fetchall()

for m in messages:
    role = m[1]
    ts = datetime.datetime.fromtimestamp(m[4]) if m[4] else "N/A"
    if role == "user":
        print(f"[{ts}] USER: {m[2][:300] if m[2] else '(empty)'}")
    elif role == "assistant":
        if m[2]:
            print(f"[{ts}] ASSISTANT: {m[2][:200]}")
        else:
            print(f"[{ts}] ASSISTANT (tool calls)")
    elif role == "tool":
        print(f"  [{ts}] TOOL({m[3]}): {m[2][:150] if m[2] else '(empty)'}")

conn.close()
```

### Step 3: Identify Which Skill the Cron Job Uses

The cron job's first user message usually starts with the skill name. You can also check `cron/jobs.json`:

```bash
grep -A 5 '"id": "<job-id>"' /opt/data/cron/jobs.json
```

Look at the `"skill"` or `"skills"` field and the `"prompt"` to understand the task.

### Step 4: Load the Skill & Analyze for Waste

Load the skill: `skill_view(name="<skill-name>")`

Walk through the session and count occurrences of each waste pattern (1-8 above). For each pattern found, note:
- How many tool calls it wasted
- What specific instructions in the skill caused it

### Step 5: Patch the Skill

**Before writing any patch, re-read the 🔒 Golden Rule section at the top of this skill.** Every sentence you inject must pass the infra-audit check.

For each waste pattern found, add targeted instructions to the skill:

**Pattern 1 (memory calls):** Add a `### Cron Tip: Don't Hunt for Variables` subsection early in the workflow:
```
### Cron Tip: Don't Hunt for Variables

Do NOT call `memory()`, `session_search()`, or read `.last_run` files to find input
variables — these fail silently and waste tool calls in automated context.

The variables you need (`REPORT_TYPE`, `REPORT_DATE_FROM`, `REPORT_DATE_TO`) are
provided in your task context or prompt. Use them directly — don't go hunting.
```

**Pattern 2 (sequential reads):** Add a rule directing the agent to use a linked script file:

```markdown
### Batch Read Files

Do NOT read metadata and full text in separate sequential calls. Instead:
1. Load the script: `skill_view(name='<skill-name>', file_path='scripts/batch_read.py')`
2. Run it via `execute_code` in a single call to read all articles at once.
```

Also, if the skill has large inline Python code blocks in its SKILL.md, **move them to a linked file** (`scripts/` directory) and reference them from the skill. This saves context — inline code blocks are loaded every time the skill is invoked, while linked files are loaded only on demand via a single `skill_view(file_path=...)` call. See Pattern 8 for details.

**Pattern 3 (reading all profiles):** Add a rule:
```
### Check Files with grep, Not read_file

Instead of reading every profile/tracking file, use `grep -l "PMID" path/*.md`
or `search_files()` to check for existing references first.
```

**Pattern 4 (todo overhead):** Add:
```
### Skip Todo in Cron

Do NOT use the `todo` tool — track progress in your own reasoning instead.
```

**Pattern 5 (post-write verify):** Add:
```
### Skip Post-Write Verification

Do NOT verify written files — `write_file` returns success confirmation.
```

**Pattern 6 (reprocessing):** Add:
```
### Skip Already-Done Work

Before processing, check for existing output files with a single `ls` or glob.
Only process what's missing.
```

**Pattern 7 (chatty messages):** Add:
```
### Compress Turn Sequences

Plan reads, writes, and checks in larger batches. Avoid intermediary "let me now X"
messages — execute the plan directly.
```

**Pattern 8 (inline scripts bloating SKILL.md):** The skill has large code blocks (Python, bash, config templates) embedded inline in SKILL.md. Every time the skill is loaded, all those lines consume context — even when the agent doesn't need the script itself.

**Fix:** Move code blocks to linked files in the skill's `scripts/` directory. The SKILL.md should contain only a concise reference:

```markdown
## Step 4: Collect Input Summaries

Load the script: `skill_view(name='<skill-name>', file_path='scripts/collect_summaries.py')`
Run it via `execute_code` — it reads all summaries in one call.
```

**Tradeoff:** One `skill_view(file_path=...)` call to read the script when first needed (one-time, not per-article). Context saved on every subsequent turn the skill is loaded.

### When to Apply Pattern 8

- Any Python/bash script block longer than 15 lines that's embedded in SKILL.md
- The script is a utility/reusable function (not a one-off template)
- The script can accept parameters (REPORT_TYPE, dates) and produce structured output

**Don't** move short snippets (<10 lines), template stubs, or example code the agent needs to see in-context to follow structure (like the Substack markdown template in Step 3 — that's structural guidance, not a runnable script).

### Step 6: Update Verification Checklist

Add checklist items for the new rules so the agent self-checks.

### Step 7: Bump Skill Version

- Minor bump (e.g., `2.0.0` → `2.1.0`) for fixing existing patterns without changing the approach
- Major bump (e.g., `1.0.0` → `2.0.0`) when adding new patterns or changing the optimization strategy (e.g., switching from inline scripts to linked files)

---

## Verification

- [ ] Identified the target cron job and its most recent session
- [ ] Retrieved full message transcript from `state.db`
- [ ] Loaded the skill and identified specific waste patterns
- [ ] **Re-read the 🔒 Golden Rule** before writing any patches
- [ ] Audited every patch sentence for infrastructure leaks (REPORT.ini, absolute paths, cron job IDs, schedules)
- [ ] **Pattern 8 applied?** Checked for inline code blocks >15 lines and moved them to `scripts/` linked files if found
- [ ] **Pattern 1 extension: Distraction phrases?** Audited the skill for dangling "may also appear in <path>" mentions and removed them
- [ ] **Pattern 5 variant?** If the skill generates API artifacts (images, audio), used consolidated verification pattern
- [ ] **Pattern 9 check?** The skill doesn't instruct the agent to self-patch during the run
- [ ] Patched the skill with concrete "do this, not that" instructions for each pattern
- [ ] Bumped the skill version
- [ ] Updated the skill's verification checklist
