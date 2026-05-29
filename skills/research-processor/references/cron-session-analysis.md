# Cron Session Analysis & Optimization

Technique used to analyze `Research Step 2: Process and Summarize` (cron job `medical-process-treatments`) and reduce its tool call count from 22 to ~10 per run.

## Finding the Right Session

Cron sessions are stored in the SQLite `state.db` at `$HERMES_HOME/state.db` (typically `/opt/data/state.db`). Cron sessions have `source='cron'` in the sessions table, and their `title` column is NULL (cron sessions don't get auto-titled). To find the right one, match by timestamp against `cron_jobs.last_run_at`:

```python
import sqlite3, datetime
conn = sqlite3.connect('/opt/data/state.db')
cur = conn.cursor()

# List all cron sessions with timestamps
cur.execute("""SELECT id, source, started_at, ended_at, message_count, tool_call_count 
FROM sessions WHERE source = 'cron' ORDER BY started_at DESC""")

# Then match against the cron job's last_run_at from cronjob action='list'
```

## Verify Which Skill Ran

Check the first user message to confirm which skill was loaded for this session:

```python
cur.execute('SELECT content FROM messages WHERE session_id=? AND role="user" ORDER BY timestamp ASC LIMIT 1', (session_id,))
msg = cur.fetchone()
# The skill name appears in the prompt: "the user has invoked the "research-processor" skill"
```

## Analyzing Inefficiencies

Map each assistant → tool → assistant turn and identify:

1. **Dead calls**: `memory()` and `session_search()` in cron context always fail (`"Memory is not available. It may be disabled"`). They waste 2+ tool calls per session. Count them.
2. **Sequential reads**: Count how many `read_file()` calls do sequential I/O that could be batched via `execute_code`.
3. **Redundant checks**: Count `todo()` calls (useless in non-interactive cron), `ls`/`terminal` verification after `write_file` already returned success.
4. **Over-read patterns**: Reading all treatment files to check if a PMID is mentioned, instead of using `grep -l` or `search_files()`.
5. **Re-processing**: Reading articles that already have a `*-summary.md` file.

## Optimization Template

For any cron-based skill, apply these rules (in order):

1. **Skip memory** — it's always disabled in cron. Go to state files (`.last_run`) or env vars.
2. **Skip already-processed artifacts** — check for output markers (e.g., `*-summary.md`) before reading input.
3. **Batch reads** — use `execute_code` with `from hermes_tools import read_file` to read multiple files in one call.
4. **Use grep/search_files to check** — don't read files just to check if a string exists.
5. **Skip todo tool** — no user to see progress in cron.
6. **Skip post-write verification** — tool return values confirm success.
7. **Skip intermediate commentary** — plan the full sequence and execute, don't narrate each step.

## Measuring Improvement

Before/after comparison using the `sessions` table:

```sql
-- Before optimization
SELECT message_count, tool_call_count FROM sessions WHERE id = '...before...';

-- After optimization
SELECT message_count, tool_call_count FROM sessions WHERE id = '...after...';
```

Target: 50-60% reduction in tool calls and message count for a typical run.
