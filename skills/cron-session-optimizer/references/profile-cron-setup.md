# Profile-Based Cron Job Setup

How to migrate, create, and manage cron jobs under a named Hermes profile (as opposed to the default/global scheduler).

## Profile Structure

A profile like `med-research` lives at `/opt/data/profiles/<name>/`. That directory acts as the profile's `HERMES_HOME`:

```
/opt/data/profiles/med-research/
├── .hermes/            # created as needed — not always present
│   └── scripts/        # no_agent=true script jobs MUST live here
├── config.yaml         # profile config
├── .env                # profile env vars
├── cron/
│   ├── jobs.json       # snapshot of jobs (manually placed, not auto-synced)
│   └── output/         # job output storage
├── state.db            # profile's own session & job state
├── skills/             # profile's skills
├── workspace/          # profile's working data
└── ...
```

## Creating Profile-Bound Cron Jobs

Use the `profile` parameter on `cronjob action=create`:

```
cronjob(
  action='create',
  name='My Job',
  prompt='...',
  skills=['my-skill'],
  schedule='0 9 * * *',
  deliver='discord',
  profile='med-research'
)
```

The job will run under that profile: it loads the profile's config, environment, skills, and state.db.

## Script-Based Jobs (no_agent=true)

For `no_agent=true` jobs (non-LLM, script-driven), the script parameter accepts **only a filename**, not an absolute path. The scheduler resolves it relative to the profile's `~/.hermes/scripts/` directory.

### Setup Steps

1. Create the scripts directory if it doesn't exist:
   ```bash
   mkdir -p /opt/data/profiles/<profile-name>/.hermes/scripts
   ```

2. Copy or symlink the script there:
   ```bash
   cp /path/to/script.sh /opt/data/profiles/<profile-name>/.hermes/scripts/
   chmod +x /opt/data/profiles/<profile-name>/.hermes/scripts/script.sh
   ```

3. Create the job with just the filename:
   ```
   cronjob(
     action='create',
     name='My Script Job',
     script='script.sh',          # not an absolute path!
     no_agent=true,
     schedule='5 11 * * *',
     deliver='discord',
     profile='med-research'
   )
   ```

### Common Pitfall

If you pass an absolute path (e.g. `'/opt/data/scripts/foo.sh'`), the API rejects it:
> *"Script path must be relative to ~/.hermes/scripts/. Got absolute or home-relative path."*

Always copy the script to the profile's `.hermes/scripts/` first.

## Migrating Jobs from Default Profile

To copy jobs from the default (global) scheduler to a named profile:

1. Read the source jobs from `/opt/data/cron/jobs.json`
2. Copy the file as a snapshot to the target profile:  
   `cp /opt/data/cron/jobs.json /opt/data/profiles/<name>/cron/jobs.json`
3. Create each job individually via `cronjob action=create` with `profile='<name>'`
4. For `no_agent` script jobs, move the script to the profile's `.hermes/scripts/` **before** creating the job
5. Model/provider overrides from the source job should be passed in the `model` dict parameter

### Duplicate Warning

The original default-profile jobs remain active after migration. The system does NOT de-duplicate. After confirming the profile jobs run correctly, consider pausing or removing the originals via `cronjob action=list` to find their IDs, then `cronjob action=remove`.
