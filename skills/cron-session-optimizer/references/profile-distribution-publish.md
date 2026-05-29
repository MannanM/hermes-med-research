# Profile Distribution Publishing

How to prepare and push a Hermes Agent profile to a public GitHub repository, including secrets audit, file selection, and credential management.

## When to Use

- The user asks to "push this profile to GitHub" or "publish as a distribution"
- After setting up a new profile that should be shareable
- Before sharing a profile publicly (audit step is critical)

## Security: Secrets Audit (Mandatory First Step)

A public repo must contain **zero credentials**. Run these checks before staging anything:

### Check 1: Scan for Hardcoded Secrets in Skills

```bash
search_files(
  pattern="sk-[a-zA-Z0-9]+|api_key|password|token|Bearer|secret|dummy-",
  path="/opt/data/profiles/<profile-name>/skills",
  file_glob="*.md",
  output_mode="content"
)
```

False positives to allow:
- Env var names like `$OPEN_AI_API_KEY`, `$SUBSTACK_EMAIL` — these are references, not values
- Redaction pattern examples like `sk-pro...T5AA` — these describe how the key *appears* when redacted
- `api_key: ''` in config.yaml — empty placeholders are fine

### Check 2: Scan for Personal Emails and Passwords

```bash
search_files(
  pattern="<user>@<domain>|<password-value>",
  path="/opt/data/profiles/<profile-name>",
  file_glob="*.md"
)
```

Personal emails, real passwords, and Discord bot tokens must never appear in pushed files.

### Check 3: Verify Config YAML Has No Populated API Keys

Check `config.yaml` for any `api_key: <non-empty>` lines or populated `secret` entries. Empty strings (`''`) are safe.

### Check 4: Examine the .env File (Read-Only — Never Push It)

The `.env` file is the single source of truth for credentials — it must be in `.gitignore` and never staged. If the user's `.env` contains anything that was copy-pasted into a skill accidentally, that's a critical finding.

## Required Files for a Distribution

Create or verify these files in the profile root before pushing:

### distribution.yaml

The canonical distribution manifest. Required fields:

```yaml
name: my-profile-name
version: 1.0.0
description: "Short description of what the profile does and what skills it includes"
hermes_requires: ">=0.12.0"
author: "YourGitHubUsername"
license: "MIT"

# Tell installers which env vars users must configure
env_requires:
  - name: DEEPSEEK_API_KEY
    description: "DeepSeek API key (for research steps)"
    required: true
  - name: OPEN_AI_API_KEY
    description: "OpenAI API key (for image generation)"
    required: true

# Files/dirs to exclude during installation
exclude:
  - ".env"
  - "memories/"
  - "state.db*"
  - "state.db-shm"
  - "state.db-wal"
  - "logs/"
  - "audio_cache/"
  - "image_cache/"
  - "sessions/"
  - "plans/"
  - "bin/"
  - "cron/output/"
  - "auth.json"
  - "auth.lock"
  - "pairing/"
  - "hooks/"
  - "distribution.yaml.txt"
  - ".hermes_history"
  - ".update_check"
  - ".skills_prompt_snapshot.json"
  - "config.yaml.bak*"
  - "models_dev_cache.json"
  - "skills/.usage.json*"
  - "workspace/"
```

### .gitignore

Should mirror the distribution exclude list plus Python artifacts:

```
# Secrets and credentials
.env
.env.*
auth.json
auth.lock

# Generated / runtime data
state.db
state.db-shm
state.db-wal
logs/
audio_cache/
image_cache/
sessions/
plans/
pairing/
hooks/
memories/
workspace/
cron/output/
bin/
*.bak
*.bak.*

# Artifacts
*.pyc
__pycache__/
.skills_prompt_snapshot.json
.update_check
.hermes_history
models_dev_cache.json
skills/.usage.json*
distribution.yaml.txt
```

### README.md

Explain what the profile does, how the pipeline works, what API keys are needed, and how to set up a fresh copy. Should include a TOS note if any skills were removed for compliance reasons.

## Staging Files Without Secrets

Since `rsync` is often unavailable in containerized environments, use `tar` with `--exclude` patterns:

```bash
cd /opt/data/profiles/<profile-name>

# Copy to repo-clean directory using tar
tar --exclude='.env' \
  --exclude='.env.*' \
  --exclude='auth.json' \
  --exclude='auth.lock' \
  --exclude='state.db' \
  --exclude='state.db-shm' \
  --exclude='state.db-wal' \
  --exclude='logs' \
  --exclude='audio_cache' \
  --exclude='image_cache' \
  --exclude='sessions' \
  --exclude='plans' \
  --exclude='pairing' \
  --exclude='hooks' \
  --exclude='memories' \
  --exclude='workspace' \
  --exclude='cron/output' \
  --exclude='bin' \
  --exclude='*.bak*' \
  --exclude='.skills_prompt_snapshot.json' \
  --exclude='.update_check' \
  --exclude='.hermes_history' \
  --exclude='models_dev_cache.json' \
  --exclude='skills/.usage.json*' \
  --exclude='distribution.yaml.txt' \
  -cf - . | tar -xf - -C /path/to/repo-clean/
```

After copying, verify the staging directory has no leaked files:

```bash
cd /path/to/repo-clean && find . -not -path './.git/*' -type f | sort
```

Then do a final secrets sweep on the staged files.

## Clearing and Pushing the Repo

### Reset Existing Content

```bash
cd /path/to/repo-clean
# Remove everything except .git
rm -rf README.md <other-old-files> .gitignore
```

### Commit and Push

```bash
cd /path/to/repo-clean
git config user.email "your@email.com"
git config user.name "YourGitHubUsername"
git add -A
git commit -m "Meaningful commit message describing what the distribution contains"
git push origin main
```

### Credential Sources

If HTTPS push fails with "could not read Username", try these in order:

1. **Git credential store** — Check `/opt/data/home/.git-credentials` (the default profile's store path may differ from `~/.git-credentials`)
2. **`gh` CLI** — `gh auth status` to check if GitHub CLI is authenticated
3. **SSH keys** — Check `~/.ssh/id_*` for deploy keys
4. **Ask the user** — If none of the above work, prompt the user for a PAT

To use the default profile's credential store:

```bash
cd /path/to/repo-clean
git config credential.helper 'store --file /opt/data/home/.git-credentials'
git push origin main
# Unset after push to avoid contaminating the cloned repo's config
git config --unset credential.helper
```

## After Push

- Remove the temp clone directory: `rm -rf /path/to/repo-clean`
- Verify the repo is live: browse to `https://github.com/<user>/<repo>`
- The `.gitignore` patterns ensure no one who clones the repo accidentally commits their own `.env`
