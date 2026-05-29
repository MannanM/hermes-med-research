#!/usr/bin/env bash

# Redirect standard error (stderr) to standard output (stdout)
exec 2>&1

# Path to the new INI-style configuration file
FILE="/opt/data/profiles/med-research/workspace/REPORT.ini"

echo "Running report-refresh.sh..."

# Ensure the workspace directory and file exist
mkdir -p "$(dirname "$FILE")"
touch "$FILE"

# Calculate relative dates using GNU date
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
EIGHT_DAYS_AGO=$(date -d "8 days ago" +%Y-%m-%d)

# Helper function to update or append values in the INI file safely
set_key_val() {
    local key="$1"
    local value="$2"
    local target_file="$3"

    if grep -q "^${key}=" "$target_file"; then
        # Key exists: replace line safely using a temporary file
        local temp_file
        temp_file=$(mktemp)
        sed "s|^${key}=.*|${key}=${value}|" "$target_file" > "$temp_file"
        cat "$temp_file" > "$target_file"
        rm -f "$temp_file"
    else
        # Key does not exist: append to the end of the file
        echo "${key}=${value}" >> "$target_file"
    fi
}

# Check if REPORT_TYPE exists in the file
if ! grep -q "^REPORT_TYPE=" "$FILE"; then
    # Initial setup for a missing or empty INI file
    cat <<EOF > "$FILE"
REPORT_TYPE=MECFS
REPORT_MECFS_DATE_FROM=$EIGHT_DAYS_AGO
REPORT_MECFS_DATE_TO=$YESTERDAY
EOF
    echo "Initialized REPORT.ini with MECFS (from: $EIGHT_DAYS_AGO to: $YESTERDAY)."
    exit 0
fi

# Extract the current REPORT_TYPE (and strip any carriage returns)
current_type=$(grep "^REPORT_TYPE=" "$FILE" | cut -d'=' -f2 | tr -d '\r')

# Fallback if the extracted value is empty
if [ -z "$current_type" ]; then
    current_type="MECFS"
fi

# Rotate the report type: MECFS -> MCAS -> HYPER -> MECFS
case "$current_type" in
    MECFS)
        new_type="MCAS"
        ;;
    MCAS)
        new_type="HYPER"
        ;;
    HYPER|*)
        new_type="MECFS"
        ;;
esac

# Define the target date keys for the new report type
from_key="REPORT_${new_type}_DATE_FROM"
to_key="REPORT_${new_type}_DATE_TO"

# Retrieve the previous TO date for the new type to calculate the offset
prev_to=$(grep "^${to_key}=" "$FILE" | cut -d'=' -f2 | tr -d '\r')

if [ -n "$prev_to" ]; then
    # Calculate new FROM date as previous TO + 1 day
    new_from=$(date -d "$prev_to + 1 day" +%Y-%m-%d)
else
    # Default fallback date if the key is missing
    new_from="$EIGHT_DAYS_AGO"
fi

new_to="$YESTERDAY"

# Update values in the file
set_key_val "REPORT_TYPE" "$new_type" "$FILE"
set_key_val "$from_key" "$new_from" "$FILE"
set_key_val "$to_key" "$new_to" "$FILE"

echo "Rotated report type from $current_type to $new_type. Range set from $new_from to $new_to."
